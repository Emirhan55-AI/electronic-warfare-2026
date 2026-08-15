"""Functional, Turkish-text, visual-state, and performance tests for the operator console."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtCore import QEventLoop, QThread, QTimer  # noqa: E402
from PySide6.QtGui import QFontMetrics, QRawFont  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from host.operator_console.application import build_application, run_playback_benchmark  # noqa: E402
from host.operator_console.controller import OperatorController  # noqa: E402
from host.operator_console.main_window import MainWindow  # noqa: E402
from host.operator_console.ui_text import TEXT, TURKISH_GLYPHS  # noqa: E402
from reference.spectrum import SigMFFrameSource  # noqa: E402
from reference.pipeline import ResolvedOperationProfile, load_profile  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
FIXTURE_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"


class OperatorConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app, cls.window, cls.controller = build_application(["test-operator-console"])
        cls.window.show()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.controller.close()
        cls.window.close()
        cls.app.processEvents()

    def setUp(self) -> None:
        self.controller.pause()
        self.window.show_empty()
        self.controller.source = None
        self.controller.last_result = None
        self.controller.last_detection = None
        self.controller.current_index = 0
        self.app.processEvents()

    def wait_for_frame(self, timeout_ms: int = 3000) -> None:
        if self.controller.last_result is not None and self.controller.active_task_count == 0:
            return
        loop = QEventLoop()
        self.controller.frame_rendered.connect(loop.quit)
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()
        self.controller.frame_rendered.disconnect(loop.quit)
        self.assertIsNotNone(self.controller.last_result)
        self.assertEqual(0, self.controller.active_task_count)

    def wait_until(self, predicate, timeout_ms: int = 3000) -> None:
        deadline = time.perf_counter() + timeout_ms / 1000.0
        while not predicate() and time.perf_counter() < deadline:
            self.app.processEvents()
            time.sleep(0.001)
        self.assertTrue(predicate())

    def load_fixture(self) -> None:
        self.assertTrue(self.controller.open_source(FIXTURE_META))
        self.wait_for_frame()

    def test_empty_state_is_truthful(self) -> None:
        self.assertEqual(TEXT["no_source"], self.window.source_value.text())
        self.assertFalse(self.window.start_button.isEnabled())
        self.assertEqual(0, self.window.spectrum_view.waterfall_count)
        self.assertEqual(0, self.window.spectrum_view.last_line_values.size)
        self.assertTrue(self.window.spectrum_view.spectrum_empty_label.isVisible())
        self.assertTrue(self.window.spectrum_view.waterfall_empty_label.isVisible())
        self.assertFalse(self.window.spectrum_view.spectrum_plot.getPlotItem().getAxis("bottom").isVisible())
        self.assertFalse(self.window.spectrum_view.waterfall_plot.getPlotItem().getAxis("bottom").isVisible())

    def test_stale_phase04_resolution_warns_and_keeps_phase03_parameters_disabled(self) -> None:
        window = MainWindow()
        resolved = ResolvedOperationProfile(
            load_profile(),
            None,
            "comparison_digest_mismatch",
        )
        with patch("host.operator_console.controller.resolve_default_operation_profile", return_value=resolved):
            controller = OperatorController(window)
        try:
            self.assertIsNone(controller.runtime_pipeline.parameters)
            self.assertEqual(TEXT["phase04_fallback"], window.notification.text())
            self.assertEqual(TEXT["no_parameter"], window.parameter_state.text())
        finally:
            controller.close()
            window.close()

    def test_fixture_loads_real_dsp_and_transport_controls(self) -> None:
        self.load_fixture()
        self.assertEqual(FIXTURE_META.name, self.window.source_value.text())
        self.assertEqual("ci8", self.window.metadata_values["datatype"].text())
        self.assertIn("8,000 MS/s", self.window.metadata_values["sample_rate"].text())
        self.assertIn("100,000 MHz", self.window.metadata_values["center_frequency"].text())
        self.assertEqual(4096, self.window.spectrum_view.last_line_values.size)
        self.assertEqual(2304, int(np.argmax(self.window.spectrum_view.last_line_values)))
        self.assertEqual(1, self.window.spectrum_view.waterfall_count)
        self.assertIsNotNone(self.controller.last_detection)
        self.assertEqual("regional", self.controller.runtime_pipeline.detector_method)
        self.assertIn("Doğrulanmış parametre zarfı", self.window.profile_value.text())

        self.controller.start()
        self.assertTrue(self.controller.playing)
        self.controller.pause()
        self.assertFalse(self.controller.playing)
        self.controller.stop()
        self.wait_for_frame()
        self.assertEqual(0, self.controller.current_index)
        self.assertLessEqual(self.controller.max_concurrent_tasks, 1)
        self.assertLessEqual(self.controller.max_pending_intents, 1)

    def test_metric_axis_dc_and_average_controls(self) -> None:
        self.load_fixture()
        self.window.axis_combo.setCurrentIndex(1)
        self.assertGreater(float(self.window.spectrum_view.last_x_mhz[0]), 90.0)
        self.window.metric_combo.setCurrentIndex(1)
        self.assertAlmostEqual(-36.823560529668725, self.window.spectrum_view.last_line_values[2304], delta=1e-8)
        self.window.average_checkbox.setChecked(True)
        self.assertTrue(self.window.average_checkbox.isChecked())
        self.window.dc_checkbox.setChecked(True)
        self.wait_for_frame()
        self.assertTrue(self.controller.last_result.dc_removed)  # type: ignore[union-attr]

    def test_warning_and_error_states_use_real_contract_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warning_meta = root / "warning.sigmf-meta"
            warning_data = root / "warning.sigmf-data"
            document = json.loads(FIXTURE_META.read_text(encoding="utf-8"))
            del document["global"]["core:num_channels"]
            warning_meta.write_text(json.dumps(document), encoding="utf-8")
            warning_data.write_bytes(FIXTURE_DATA.read_bytes())
            self.assertTrue(self.controller.open_source(warning_meta))
            self.wait_for_frame()
            self.assertTrue(self.window.notification.isVisible())
            self.assertIn("tek kanal", self.window.notification.text())

            bad_meta = root / "bad.sigmf-meta"
            bad_data = root / "bad.sigmf-data"
            bad_meta.write_text("{", encoding="utf-8")
            bad_data.write_bytes(bytes(8192))
            preserved_source = self.controller.source
            self.assertTrue(self.controller.open_source(bad_meta))
            self.wait_until(lambda: self.controller.active_task_count == 0)
            self.assertTrue(self.window.notification.isVisible())
            self.assertEqual("Metadata geçerli JSON değil.", self.window.notification.text())
            self.assertIs(preserved_source, self.controller.source)
            self.assertTrue(self.window.start_button.isEnabled())
            self.assertEqual(TEXT["ready"], self.window.state_value.text())

    def test_source_inspection_runs_off_ui_thread_and_heartbeat_continues(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        worker_thread: list[QThread] = []

        def controlled_factory(*args, **kwargs):
            worker_thread.append(QThread.currentThread())
            entered.set()
            self.assertTrue(release.wait(2.0))
            return SigMFFrameSource(*args, **kwargs)

        window = MainWindow()
        controller = OperatorController(window, source_factory=controlled_factory)
        window.show()
        heartbeats: list[int] = []
        timer = QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: heartbeats.append(1))
        timer.start()
        try:
            self.assertTrue(controller.open_source(FIXTURE_META))
            self.assertEqual(TEXT["opening_source"], window.state_value.text())
            QTimer.singleShot(150, release.set)
            self.wait_until(lambda: entered.is_set() and len(heartbeats) >= 5)
            self.wait_until(lambda: controller.last_result is not None and controller.active_task_count == 0)
            self.assertIsNot(worker_thread[0], self.app.thread())
            self.assertGreaterEqual(len(heartbeats), 5)
        finally:
            release.set()
            timer.stop()
            controller.close()
            window.close()

    def test_two_source_requests_reject_and_close_the_stale_result(self) -> None:
        first_entered = threading.Event()
        release_first = threading.Event()
        closed: list[str] = []
        calls = 0

        def controlled_factory(metadata_path, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                first_entered.set()
                self.assertTrue(release_first.wait(2.0))
            source = SigMFFrameSource(metadata_path, *args, **kwargs)
            original_close = source.close
            name = Path(metadata_path).name

            def tracked_close() -> None:
                closed.append(name)
                original_close()

            source.close = tracked_close  # type: ignore[method-assign]
            return source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name in ("first", "second"):
                metadata = root / f"{name}.sigmf-meta"
                data = root / f"{name}.sigmf-data"
                shutil.copyfile(FIXTURE_META, metadata)
                shutil.copyfile(FIXTURE_DATA, data)
                paths.append(metadata)
            window = MainWindow()
            controller = OperatorController(window, source_factory=controlled_factory)
            window.show()
            try:
                controller.open_source(paths[0])
                self.wait_until(first_entered.is_set)
                controller.open_source(paths[1])
                self.assertEqual(1, controller.pending_intent_count)
                release_first.set()
                self.wait_until(
                    lambda: controller.last_result is not None
                    and controller.active_task_count == 0
                    and window.source_value.text() == paths[1].name
                )
                self.assertIn(paths[0].name, closed)
                self.assertGreaterEqual(controller.stale_results_rejected, 1)
                self.assertEqual(1, controller.max_concurrent_tasks)
                self.assertLessEqual(controller.max_pending_intents, 1)
            finally:
                release_first.set()
                controller.close()
                window.close()

    def test_close_during_source_open_closes_worker_result(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        closed = threading.Event()

        def controlled_factory(*args, **kwargs):
            entered.set()
            release.wait(2.0)
            source = SigMFFrameSource(*args, **kwargs)
            original_close = source.close

            def tracked_close() -> None:
                original_close()
                closed.set()

            source.close = tracked_close  # type: ignore[method-assign]
            return source

        window = MainWindow()
        controller = OperatorController(window, source_factory=controlled_factory)
        window.show()
        controller.open_source(FIXTURE_META)
        self.wait_until(entered.is_set)
        threading.Timer(0.05, release.set).start()
        controller.close()
        window.close()
        self.app.processEvents()
        self.assertTrue(closed.wait(1.0))
        self.assertEqual(0, controller.thread_pool.activeThreadCount())
        self.assertEqual(0, controller.active_task_count)
        self.assertIsNone(controller.source)

    def test_turkish_catalog_and_font_are_complete(self) -> None:
        combined = "\n".join(TEXT.values())
        for character in TURKISH_GLYPHS:
            self.assertEqual(character, character.encode("utf-8").decode("utf-8"))
        for broken in ("�", "Ã", "Ä", "Å"):
            self.assertNotIn(broken, combined)
        raw_font = QRawFont.fromFont(self.app.font())
        self.assertTrue(raw_font.isValid())
        for character in TURKISH_GLYPHS:
            self.assertTrue(raw_font.supportsCharacter(ord(character)), character)
        visible_text = "\n".join(
            label.text() for label in self.window.findChildren(QLabel) if label.text()
        )
        self.assertNotIn("Ornekleme", visible_text)
        self.assertNotIn("Baglanti", visible_text)

    def test_stale_result_is_rejected_by_generation(self) -> None:
        self.load_fixture()
        result = self.controller.last_result
        assert result is not None
        stale_before = self.controller.stale_results_rejected
        rows_before = self.window.spectrum_view.waterfall_count
        self.controller._active_tasks = 1
        self.controller._task_completed(
            self.controller.generation - 1,
            self.controller.current_index,
            result,
            0.001,
        )
        self.assertEqual(stale_before + 1, self.controller.stale_results_rejected)
        self.assertEqual(rows_before, self.window.spectrum_view.waterfall_count)

    def test_repeated_requests_coalesce_to_one_pending_intent(self) -> None:
        self.load_fixture()
        self.controller._active_tasks = 1
        before = self.controller.requested_task_count
        for _ in range(100):
            self.assertFalse(self.controller.request_current_frame())
        self.assertEqual(before, self.controller.requested_task_count)
        self.assertEqual(1, self.controller.pending_intent_count)
        self.assertEqual(1, self.controller.max_pending_intents)
        self.controller._active_tasks = 0
        self.controller._refresh_pending = False

    def test_playback_performance_and_queue_bounds(self) -> None:
        self.load_fixture()
        ten = run_playback_benchmark(
            self.window,
            self.controller,
            target_fps=10,
            duration_seconds=1.6,
        )
        thirty_runs = [
            run_playback_benchmark(
                self.window,
                self.controller,
                target_fps=30,
                duration_seconds=1.2,
            )
            for _ in range(5)
        ]
        print(
            "UI performance benchmark:",
            {
                "ten_fps": {
                    "rendered_frames": ten.rendered_frames,
                    "achieved_fps": ten.achieved_fps,
                    "maximum_heartbeat_gap_ms": ten.maximum_heartbeat_gap_ms,
                },
                "thirty_fps_runs": [
                    {
                        "rendered_frames": item.rendered_frames,
                        "achieved_fps": item.achieved_fps,
                        "maximum_heartbeat_gap_ms": item.maximum_heartbeat_gap_ms,
                    }
                    for item in thirty_runs
                ],
            },
        )
        self.assertGreater(ten.rendered_frames, 0)
        self.assertGreater(ten.achieved_fps, 0.0)
        self.assertIn(ten.feature_history_bytes, {0, 67_840})
        for thirty in thirty_runs:
            self.assertGreater(thirty.rendered_frames, 0)
            self.assertGreater(thirty.achieved_fps, 0.0)
            self.assertLessEqual(thirty.waterfall_rows, 128)
            self.assertEqual(1, thirty.maximum_concurrent_tasks)
            self.assertLessEqual(thirty.maximum_pending_intents, 1)
            self.assertEqual(0, thirty.active_tasks_after_stop)
            self.assertIn(thirty.feature_history_bytes, {0, 67_840})

    def test_all_visible_labels_fit_at_minimum_logical_size(self) -> None:
        self.load_fixture()
        self.window.resize(960, 600)
        self.app.processEvents()
        for label in self.window.findChildren(QLabel):
            if not label.isVisible() or not label.text() or label.wordWrap():
                continue
            required = label.fontMetrics().horizontalAdvance(label.text())
            self.assertLessEqual(required, label.contentsRect().width() + 2, label.text())
        self.window.resize(1440, 900)


if __name__ == "__main__":
    unittest.main()
