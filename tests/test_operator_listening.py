"""Qt worker, stale-state and truthful UI tests for PHASE-05 listening."""

from __future__ import annotations

import os
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QScrollArea

from host.operator_console.application import build_application
from host.operator_console.audio_playback import AudioPlayback
from host.operator_console.ui_text import TEXT
from qt_test_support import isolate_qt_module


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase05"


class OperatorListeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _drain(self, controller: object, timeout: float = 4.0) -> None:
        deadline = time.monotonic() + timeout
        stable = 0
        while time.monotonic() < deadline:
            self.app.processEvents()
            if controller.active_task_count == 0 and controller.pending_intent_count == 0:  # type: ignore[attr-defined]
                stable += 1
                if stable > 3:
                    return
            else:
                stable = 0
            time.sleep(0.005)
        self.fail("worker did not drain")

    def _loaded_confirmed(self, fixture: str = "am-tone-ci8"):
        playback = AudioPlayback(available_override=False)
        app, window, controller = build_application([], audio_playback=playback)
        controller.open_source(FIXTURES / f"{fixture}.sigmf-meta")
        self._drain(controller)
        controller.current_index = 1
        controller.request_current_frame()
        self._drain(controller)
        confirmed = [
            row
            for row in range(window.detection_list.count())
            if "Hazır" in window.detection_list.item(row).text()
        ]
        self.assertTrue(confirmed)
        window.detection_list.setCurrentRow(confirmed[0])
        self.app.processEvents()
        return app, window, controller

    def test_confirmed_event_prepares_bounded_audio_off_ui_thread(self) -> None:
        app, window, controller = self._loaded_confirmed("am-tone-ci8")
        self.assertTrue(window.prepare_listening_button.isEnabled())
        self.assertIn("canlı RF değildir", window.fixture_live_warning.text())
        self.assertTrue(controller.request_listening())
        self._drain(controller)
        self.assertIsNotNone(controller._listening_result)
        self.assertEqual(48_000, controller._listening_result.sample_rate_hz)
        self.assertEqual("AM", window.listening_values["mode"].text())
        self.assertIn("REPLAY / HOST", window.listening_values["backend"].text())
        self.assertIn("mono PCM16", window.listening_values["audio_rate"].text())
        self.assertNotEqual("—", window.listening_values["duration"].text())
        self.assertNotEqual("—", window.listening_values["levels"].text())
        self.assertFalse(window.play_audio_button.isEnabled())
        self.assertTrue(window.export_wav_button.isEnabled())
        self.assertIn(TEXT["audio_backend_unavailable"], window.audio_backend_state.text())
        self.assertLessEqual(controller.max_concurrent_tasks, 1)
        self.assertLessEqual(controller.max_pending_intents, 1)
        controller.close()
        window.close()

    def test_source_and_configuration_changes_clear_audio_and_stale_results(self) -> None:
        app, window, controller = self._loaded_confirmed("nfm-tone-ci8")
        window.demod_combo.setCurrentIndex(1)
        self.assertTrue(controller.request_listening())
        key = controller._listening_intent.generation_key
        window.source_type_combo.setCurrentIndex(2)
        self._drain(controller)
        self.assertIsNone(controller._listening_result)
        before = controller.stale_results_rejected
        controller._listening_completed(key, object())
        self.assertGreater(controller.stale_results_rejected, before)
        controller.close()
        self.assertEqual(0, controller.active_task_count)
        window.close()

    def test_noise_only_never_enables_listening(self) -> None:
        playback = AudioPlayback(available_override=False)
        app, window, controller = build_application([], audio_playback=playback)
        controller.open_source(FIXTURES / "noise-only-ci8.sigmf-meta")
        self._drain(controller)
        for frame in range(1, 4):
            controller.current_index = frame
            controller.request_current_frame()
            self._drain(controller)
        self.assertFalse(window.prepare_listening_button.isEnabled())
        self.assertFalse(controller.request_listening())
        controller.close()
        window.close()

    def test_turkish_listening_labels_are_preserved(self) -> None:
        app, window, controller = build_application([], audio_playback=AudioPlayback(available_override=False))
        labels = (
            window.workspace_tabs.tabText(2),
            window.prepare_listening_button.text(),
            window.export_wav_button.text(),
            window.demod_combo.itemText(1),
        )
        self.assertEqual(("Dinleme", "Dinle", "WAV Dışa Aktar", "Dar Bant FM (NFM)"), labels)
        scroll = window.findChild(QScrollArea, "listeningScroll")
        self.assertIsNotNone(scroll)
        self.assertTrue(scroll.widgetResizable())
        controller.close()
        window.close()


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
