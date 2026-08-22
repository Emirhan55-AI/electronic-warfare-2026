"""Qt bindings for the TX-locked ET task console."""

from __future__ import annotations

import os
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from host.operator_console.main_window import MainWindow
from reference.et import SafetyMode
from qt_test_support import isolate_qt_module


class OperatorETTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["operator-et-test"])

    def setUp(self) -> None:
        self.window = MainWindow(laboratory_mode=True)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def _advance_live_et_animation(self) -> None:
        """Advance a few live frames, then stop the operator-controlled display."""

        for _ in range(8):
            self.window._advance_et_animation()
        self.assertTrue(self.window.et_animation_timer.isActive())
        self.window._stop_et_mission()
        self.assertFalse(self.window.et_animation_timer.isActive())

    def test_task_cards_keep_controls_separated(self) -> None:
        self.assertEqual({"continuous", "interleaved", "analog", "gnss"}, set(self.window.et_task_card_buttons))
        self.window._select_et_task("analog")
        self.assertEqual(2, self.window.et_control_stack.currentIndex())
        self.assertEqual("Analog Aldatma", self.window.et_header_values["task"].text())
        self.assertTrue(self.window.et_task_card_buttons["analog"].isChecked())
        self.assertFalse(self.window.et_task_card_buttons["continuous"].isChecked())

    def test_continuous_barrage_binds_real_samples_and_immediate_spectrum(self) -> None:
        self.window.et_family_combo.setCurrentIndex(self.window.et_family_combo.findData("barrage"))
        self.window._run_continuous_test()
        self.assertTrue(self.window.et_animation_timer.isActive())
        self.assertIn("SONUÇ HAZIR", self.window.et_header_values["status"].text())
        self.assertGreater(self.window.et_spectrum_curve.xData.size, 0)
        first_waveform = self.window.et_waveform_curve.yData.copy()
        self.window._advance_et_animation()
        self.assertFalse(np.allclose(self.window.et_waveform_curve.yData, first_waveform))
        self._advance_live_et_animation()
        barrage = self.window.last_et_result
        self.assertIsNotNone(barrage)
        assert barrage is not None
        self.assertEqual("barrage", barrage.waveform_type)
        self.assertGreater(float(barrage.details["occupied_bandwidth_hz"]), 10_000.0)
        self.assertGreater(self.window.et_spectrum_curve.xData.size, 0)
        self.assertEqual("KİLİTLİ", barrage.tx_state)
        self.assertIn("Merkez: 0 kHz", self.window.et_result_values["detail"].text())
        self.assertIn("✓ PASS", self.window.et_result_values["status"].text())

    def test_interleaved_analog_and_gnss_tasks_bind_structured_results(self) -> None:
        self.window._select_et_task("interleaved")
        self.window.et_interleaved_scenario.setCurrentIndex(self.window.et_interleaved_scenario.findData("intermittent"))
        self.window._run_interleaved_test()
        self.assertTrue(self.window.et_animation_timer.isActive())
        self.assertGreater(self.window.et_interleaved_timeline_curve.xData.size, 0)
        self._advance_live_et_animation()
        interleaved = self.window.last_et_result
        self.assertIsNotNone(interleaved)
        assert interleaved is not None
        self.assertEqual("interleaved_jamming", interleaved.task_type)
        self.assertGreaterEqual(int(interleaved.details["task_activation_count"]), 1)
        self.assertGreater(self.window.et_interleaved_timeline_curve.xData.size, 0)
        self.assertIn(self.window.et_interleaved_values["state"].text(), {"DİNLE", "KARAR", "GÖREV", "KORUMA"})

        self.window._select_et_task("analog")
        self.window._run_analog_loopback_test()
        self.assertTrue(self.window.et_animation_timer.isActive())
        self.assertGreater(self.window.et_analog_audio_curve.xData.size, 0)
        first_audio = self.window.et_analog_audio_curve.yData.copy()
        self.window._advance_et_animation()
        self.assertFalse(np.allclose(self.window.et_analog_audio_curve.yData, first_audio))
        self._advance_live_et_animation()
        analog = self.window.last_et_result
        self.assertIsNotNone(analog)
        assert analog is not None
        self.assertEqual("analog_deception", analog.task_type)
        self.assertGreaterEqual(float(analog.details["loopback_correlation"]), 0.999)
        self.assertGreater(self.window.et_analog_audio_curve.xData.size, 0)
        self.assertIn("Modülasyon: NFM", self.window.et_result_values["detail"].text())

        self.window._select_et_task("gnss")
        self.window.et_gnss_validate.click()
        self.app.processEvents()
        gnss = self.window.last_et_result
        self.assertIsNotNone(gnss)
        assert gnss is not None
        self.assertEqual("gnss_scenario", gnss.task_type)
        self.assertEqual(0, gnss.sample_count)
        self.assertIn("Servis: GPS L1 C/A", self.window.et_gnss_visual_result.text())
        self.assertIn("RF TX YOK", self.window.et_gnss_visual_result.text())
        self.assertEqual("KİLİTLİ", gnss.tx_state)

    def test_all_et_screens_keep_visible_tx_lock_badges(self) -> None:
        for task_key in ("continuous", "interleaved", "analog", "gnss"):
            self.window._select_et_task(task_key)
            self.assertEqual("OFFLINE", self.window.et_header_values["mode"].text())
            self.assertEqual("TX KİLİTLİ", self.window.et_header_values["tx_lock"].text())
            self.assertEqual("RF TX YOK", self.window.et_header_values["rf_tx"].text())


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
