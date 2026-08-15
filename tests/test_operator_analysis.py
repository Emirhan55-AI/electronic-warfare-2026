from __future__ import annotations

import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QEventLoop, QThread, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

from host.operator_console.controller import MeasurementTask
from host.operator_console.application import build_application
from host.operator_console.main_window import MainWindow
from reference.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from reference.parameters.scenes import generate_parameter_scene
from reference.spectrum import SpectrumProcessor
from qt_test_support import dispose_qt_fixture, isolate_qt_module


class OperatorAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def intent(span: AnalysisSpan) -> MeasurementIntent:
        owner = MeasurementCandidate(1, 4, span.lower_shifted_bin, span.upper_shifted_bin)
        context = MeasurementContext(1, 1, 1, 1, 4, (True, True, True, True), (owner,))
        return MeasurementIntent(1, 1, 1, 1, 4, 0, span, context)

    def test_workspaces_and_scrollable_panels_exist(self) -> None:
        window = MainWindow()
        self.assertEqual(window.workspace_tabs.count(), 3)
        self.assertEqual(window.workspace_tabs.tabText(0), "Operasyon")
        self.assertEqual(window.workspace_tabs.tabText(1), "Sinyal Analizi")
        self.assertEqual(window.workspace_tabs.tabText(2), "Dinleme")
        self.assertTrue(window.findChild(type(window.workspace_tabs), "workspaceTabs") is not None)
        window.close()

    def test_unvalidated_fields_never_show_numbers(self) -> None:
        window = MainWindow()
        window.clear_measurement_result()
        self.assertTrue(all(value.text() == "Henüz doğrulanmadı" for value in window.parameter_values.values()))
        self.assertIn("Kalibrasyon yapılmadı", window.findChild(type(window.quality_value), "calibrationNote").text())
        window.close()

    def test_measurement_read_and_dsp_run_outside_ui_thread(self) -> None:
        class Source:
            frame_count = 8
            sample_rate_hz = 8_000_000.0
            center_frequency_hz = 100_000_000.0

            def __init__(self) -> None:
                self.threads = []

            def read_frame(self, index: int) -> np.ndarray:
                self.threads.append(QThread.currentThread())
                return generate_parameter_scene("am-carrier", trial_index=0, frame_index=index).samples

        source = Source()
        intent = self.intent(AnalysisSpan(2020, 2076, "operator_adjusted"))
        task = MeasurementTask(intent, source, SpectrumProcessor())
        pool = QThreadPool()
        pool.setMaxThreadCount(1)
        loop = QEventLoop()
        task.signals.completed.connect(lambda *_: loop.quit())
        task.signals.failed.connect(lambda *_: loop.quit())
        pool.start(task)
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        pool.waitForDone()
        self.assertEqual(4, len(source.threads))
        self.assertTrue(all(item is not QThread.currentThread() for item in source.threads))
        self.assertEqual(1, pool.maxThreadCount())

    def test_measurement_worker_is_responsive_and_queue_is_bounded(self) -> None:
        frames = tuple(
            generate_parameter_scene("am-carrier", trial_index=3, frame_index=index).samples
            for index in range(4)
        )

        class SlowSource:
            frame_count = 8
            sample_rate_hz = 8_000_000.0
            center_frequency_hz = 100_000_000.0

            def read_frame(self, index: int) -> np.ndarray:
                time.sleep(0.02)
                return frames[index]

            def close(self) -> None:
                return None

        capability = SimpleNamespace(validated_fields=("occupied_bandwidth",), automatic_span_validated=False)
        with patch("host.operator_console.controller.load_phase04e1_capability", return_value=capability):
            app, window, controller = build_application([])
        controller.source = SlowSource()
        for frame_index, samples in enumerate(frames):
            runtime = controller.runtime_pipeline.process(
                samples,
                sample_rate_hz=8_000_000.0,
                center_frequency_hz=100_000_000.0,
                frame_index=frame_index,
            )
        controller.last_result = runtime.spectrum
        controller.last_detection = runtime.detection
        event = next(item for item in runtime.detection.active_events if item.state == "confirmed")
        controller._selected_event_id = event.event_id
        controller._span = AnalysisSpan(1740, 1860, "operator_adjusted", 1)
        controller.current_index = 3
        controller._event_observation_history[event.event_id] = [True, True, True, True]

        heartbeats: list[int] = []
        heartbeat = QTimer()
        heartbeat.setInterval(5)
        heartbeat.timeout.connect(lambda: heartbeats.append(1))
        self.addCleanup(
            dispose_qt_fixture,
            app,
            controller=controller,
            window=window,
            timers=(heartbeat,),
        )
        heartbeat.start()
        self.assertTrue(controller.request_measurement())
        self.assertTrue(controller.request_measurement())
        deadline = time.perf_counter() + 3.0
        while controller.completed_task_count < 2 and time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(0.002)
        heartbeat.stop()

        self.assertGreaterEqual(len(heartbeats), 5)
        self.assertEqual(1, controller.max_concurrent_tasks)
        self.assertEqual(1, controller.max_pending_intents)
        self.assertEqual(0, controller.active_task_count)
        self.assertEqual(0, controller.pending_intent_count)


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
