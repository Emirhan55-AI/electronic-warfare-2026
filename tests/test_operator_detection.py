"""Operator integration tests for the validated PHASE-03 detection pipeline."""

from __future__ import annotations

import os
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from host.operator_console.application import build_application  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"


class OperatorDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app, cls.window, cls.controller = build_application(["test-operator-detection"])
        cls.window.show()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.controller.close()
        cls.window.close()
        cls.app.processEvents()

    def wait_until(self, predicate, timeout: float = 4.0) -> None:
        deadline = time.perf_counter() + timeout
        while not predicate() and time.perf_counter() < deadline:
            self.app.processEvents()
            time.sleep(0.001)
        self.assertTrue(predicate())

    def test_profile_drives_real_detection_overlay_and_event_list(self) -> None:
        self.controller.open_source(FIXTURE_META)
        self.wait_until(
            lambda: self.controller.last_detection is not None
            and self.controller.active_task_count == 0
        )
        self.assertEqual("regional", self.controller.runtime_pipeline.detector_method)
        self.assertIn("Bölgesel", self.window.profile_value.text())
        self.assertGreater(len(self.controller.last_detection.regions), 0)  # type: ignore[union-attr]
        self.assertIsNotNone(self.window.spectrum_view.threshold_curve.xData)
        self.assertGreater(self.window.detection_list.count(), 0)
        self.assertLessEqual(self.window.detection_list.count(), 12)

    def test_detector_setting_change_resets_generation_and_temporal_state(self) -> None:
        if self.controller.source is None:
            self.controller.open_source(FIXTURE_META)
            self.wait_until(lambda: self.controller.last_detection is not None)
        generation = self.controller.generation
        self.window.pfa_combo.setCurrentIndex(0)
        self.assertGreater(self.controller.generation, generation)
        self.assertEqual(1e-3, self.controller.runtime_pipeline.pfa)
        self.assertIsNone(self.controller.last_detection)
        self.wait_until(lambda: self.controller.last_detection is not None)
        generation = self.controller.generation
        self.window.center_checkbox.setChecked(False)
        self.assertGreater(self.controller.generation, generation)
        self.assertFalse(self.controller.runtime_pipeline.evaluate_center)
        self.wait_until(lambda: self.controller.last_detection is not None)
        self.assertEqual(4055, self.controller.last_detection.cells.evaluated_count)  # type: ignore[union-attr]

    def test_worker_and_ui_memory_bounds_are_preserved(self) -> None:
        self.assertEqual(1, self.controller.thread_pool.maxThreadCount())
        self.assertLessEqual(self.controller.max_concurrent_tasks, 1)
        self.assertLessEqual(self.controller.max_pending_intents, 1)
        self.assertLessEqual(self.window.spectrum_view.waterfall_count, 128)
        if self.controller.last_detection is not None:
            self.assertLessEqual(len(self.controller.last_detection.active_events), 64)
            self.assertLessEqual(len(self.controller.last_detection.ended_history), 128)
        self.assertLessEqual(self.window.detection_list.count(), 12)


if __name__ == "__main__":
    unittest.main()
