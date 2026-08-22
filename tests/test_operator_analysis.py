from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QEventLoop, QThread, QThreadPool, QTimer, Qt
from PySide6.QtWidgets import QApplication

from host.operator_console.controller import MeasurementTask
from host.operator_console.application import build_application
from host.operator_console.main_window import MainWindow
from host.operator_console.ui_text import TEXT
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
        expected = (
            TEXT["operation_workspace"],
            TEXT["analysis_workspace"],
            TEXT["listening_workspace"],
            "Yön",
            TEXT["system_status_workspace"],
        )
        self.assertEqual(window.workspace_tabs.count(), len(expected))
        self.assertEqual(tuple(window.workspace_tabs.tabText(index) for index in range(len(expected))), expected)
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

    def test_confirmed_replay_selection_persists_and_p0_measurement_updates_ui(self) -> None:
        fixture = Path(__file__).resolve().parents[1] / "datasets" / "fixtures" / "phase05" / "am-tone-ci8.sigmf-meta"
        app, window, controller = build_application([])
        self.addCleanup(dispose_qt_fixture, app, controller=controller, window=window)

        def drain(timeout: float = 5.0) -> None:
            deadline = time.perf_counter() + timeout
            while (controller.active_task_count or controller.pending_intent_count) and time.perf_counter() < deadline:
                app.processEvents()
                time.sleep(0.002)
            self.assertEqual(0, controller.active_task_count)
            self.assertEqual(0, controller.pending_intent_count)

        controller.open_source(fixture)
        drain()
        for frame_index in range(1, 4):
            controller.current_index = frame_index
            controller.request_current_frame()
            drain()

        self.assertTrue(window.search_start_button.isEnabled())
        window.search_mode_combo.setCurrentIndex(0)
        window.search_start_button.click()
        self.assertGreater(len(window.last_search_result.parameters), 0)
        window.search_mode_combo.setCurrentIndex(1)
        window.judge_band_lower_spin.setValue(100.010)
        window.judge_band_upper_spin.setValue(100.040)
        window.search_start_button.click()
        self.assertGreater(len(window.last_search_result.parameters), 0)
        window.search_mode_combo.setCurrentIndex(2)
        window.judge_frequency_spin.setValue(100.024)
        window.search_start_button.click()
        self.assertGreater(len(window.last_search_result.parameters), 0)
        canonical_count = window.detection_list.count()
        window.judge_frequency_spin.setValue(200.0)
        window.search_start_button.click()
        self.assertEqual((), window.last_search_result.parameters)
        self.assertEqual(canonical_count, window.detection_list.count())
        self.assertEqual(TEXT["not_validated"], window.parameter_values["p0_carrier"].text())
        self.assertEqual(TEXT["not_validated"], window.parameter_values["emission_center"].text())
        self.assertEqual("SigMF / Replay · Aktif", window.system_status_values["source"].text())
        self.assertIn("doğrulanmadı", window.system_status_values["fpga"].text())

        confirmed_rows = [
            row
            for row in range(window.detection_list.count())
            if window.detection_list.item(row).data(Qt.ItemDataRole.UserRole + 1) == "confirmed"
        ]
        self.assertGreaterEqual(len(confirmed_rows), 2)
        window.detection_list.setCurrentRow(confirmed_rows[0])
        app.processEvents()
        first_event_id = controller._selected_event_id
        self.assertIsNotNone(first_event_id)
        self.assertTrue(window.measure_button.isEnabled())
        self.assertEqual(4096, window.analysis_spectrum.curve.xData.size)
        np.testing.assert_allclose(
            window.analysis_spectrum.curve.yData,
            controller.last_result.display.bin_power_dbfs,
        )
        self.assertEqual(
            window.analysis_spectrum.curve.xData.size,
            window.analysis_spectrum.curve.yData.size,
        )
        self.assertTrue(np.all(np.diff(window.analysis_spectrum.curve.xData) > 0.0))
        self.assertTrue(np.all(np.isfinite(window.analysis_spectrum.curve.yData)))
        lower, upper = window.analysis_spectrum.region.getRegion()
        carrier = window.analysis_spectrum.carrier_marker.value()
        self.assertLess(lower, carrier)
        self.assertLess(carrier, upper)

        window.workspace_tabs.setCurrentIndex(1)
        controller.current_index = 4
        controller.request_current_frame()
        drain()
        self.assertEqual(first_event_id, controller._selected_event_id)
        self.assertEqual(1, len(window.detection_list.selectedItems()))
        self.assertTrue(window.measure_button.isEnabled())
        self.assertEqual(4096, window.analysis_spectrum.curve.xData.size)

        window.measure_button.click()
        drain()
        self.assertIn("tamamlandı", window.measurement_state.text())
        self.assertIn("Sonuçlar güncellendi", window.parameter_state.text())
        self.assertEqual("REPLAY", window.parameter_values["p0_source"].text())
        self.assertIn("dBFS/bin", window.parameter_values["p0_peak_power"].text())
        self.assertIn("KALİBRASYON BEKLİYOR", window.parameter_values["p0_power"].text())
        self.assertNotEqual(TEXT["not_validated"], window.parameter_values["p0_carrier"].text())
        self.assertEqual(4096, window.analysis_spectrum.curve.xData.size)
        self.assertLess(
            window.analysis_spectrum.lower_marker.value(),
            window.analysis_spectrum.carrier_marker.value(),
        )
        self.assertLess(
            window.analysis_spectrum.carrier_marker.value(),
            window.analysis_spectrum.upper_marker.value(),
        )

        second_row = next(
            row
            for row in confirmed_rows[1:]
            if int(window.detection_list.item(row).data(Qt.ItemDataRole.UserRole)) != first_event_id
        )
        window.detection_list.setCurrentRow(second_row)
        app.processEvents()
        self.assertNotEqual(first_event_id, controller._selected_event_id)
        self.assertEqual(TEXT["not_validated"], window.parameter_values["p0_carrier"].text())
        controller.clear_analysis()
        self.assertEqual(0, window.analysis_spectrum.last_x_data.size)
        self.assertEqual(TEXT["select_confirmed_event"], window.analysis_event_value.text())

    def test_measurement_without_selection_is_visible_and_never_fabricates_output(self) -> None:
        app, window, controller = build_application([])
        self.addCleanup(dispose_qt_fixture, app, controller=controller, window=window)
        self.assertFalse(controller.request_measurement())
        self.assertEqual(TEXT["measurement_no_selection"], window.measurement_state.text())
        self.assertTrue(
            all(value.text() == TEXT["not_validated"] for value in window.parameter_values.values())
        )


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
