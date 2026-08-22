from __future__ import annotations

import os
import time
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from host.acquisition import (
    CaptureResult,
    DeviceIdentity,
    DeviceStatus,
    EDRXDeviceConfig,
    RealHackRFBackend,
    ToolInventory,
    ToolStatus,
)
from host.acquisition.mock import DeterministicMockBackend
from host.operator_console.application import build_application
from host.operator_console.laboratory import build_laboratory_application
from host.operator_console.ui_text import TEXT
from qt_test_support import isolate_qt_module


class OperatorHackRFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _drain(self, controller: object, timeout: float = 3.0) -> None:
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

    def test_no_tools_keeps_live_controls_disabled_and_turkish(self) -> None:
        app, window, controller = build_application([], acquisition_backend=RealHackRFBackend(which=lambda _: None))
        window.source_type_combo.setCurrentIndex(1)
        self.assertFalse(window.hackrf_start_button.isEnabled())
        controller.probe_hackrf()
        self._drain(controller)
        self.assertIn(TEXT["hackrf_tools_missing"], window.hackrf_status.text())
        self.assertFalse(window.hackrf_start_button.isEnabled())
        controller.close()
        window.close()

    def test_ready_tools_without_device_or_serial_remain_truthfully_disconnected(self) -> None:
        class PreparedBackend:
            backend_kind = "real"

            def discover_tools(self, *, inspect_help: bool = False) -> ToolInventory:
                del inspect_help
                return ToolInventory(
                    (
                        ToolStatus("hackrf_info", "available", True),
                        ToolStatus("hackrf_transfer", "available", True, ("-d", "-r", "-f", "-s", "-n", "-a", "-l", "-g")),
                        ToolStatus("hackrf_sweep", "available", True),
                    )
                )

            def discover_device(self, cancellation=None) -> DeviceStatus:
                del cancellation
                return DeviceStatus("NO_DEVICE", reason_code="device_not_found")

            def capture(self, config, cancellation=None) -> CaptureResult:
                raise AssertionError("capture must not run without a device")

            def coarse_sweep(self, cancellation=None):
                raise AssertionError("sweep is outside B0 UI readiness")

            def cancel(self) -> None:
                pass

            def close(self) -> None:
                pass

        _, window, controller = build_application([], acquisition_backend=PreparedBackend())  # type: ignore[arg-type]
        window.source_type_combo.setCurrentIndex(1)
        controller.probe_hackrf()
        self._drain(controller)
        self.assertEqual("Hazır", window.system_status_values["hackrf_tools"].text())
        self.assertEqual("Bağlı Değil", window.system_status_values["hackrf"].text())
        self.assertEqual("Atanmadı", window.system_status_values["serial"].text())
        self.assertEqual("Durduruldu", window.system_status_values["rx"].text())
        self.assertEqual("Bilgisayar Referansı", window.system_status_values["processing"].text())
        self.assertEqual("Kullanılmıyor", window.system_status_values["zedboard"].text())
        self.assertEqual("Kullanılmıyor", window.system_status_values["fpga"].text())
        self.assertFalse(window.hackrf_start_button.isEnabled())
        controller.close()
        window.close()

    def test_one_device_without_assigned_serial_never_enables_capture(self) -> None:
        serial = "0000000000000000123456789abcdef0"

        class OneDeviceBackend:
            backend_kind = "real"

            def discover_tools(self, *, inspect_help: bool = False) -> ToolInventory:
                del inspect_help
                return ToolInventory(
                    (
                        ToolStatus("hackrf_info", "available", True),
                        ToolStatus("hackrf_transfer", "available", True, ("-d", "-r", "-f", "-s", "-n", "-a", "-l", "-g")),
                    )
                )

            def discover_device(self, cancellation=None) -> DeviceStatus:
                del cancellation
                return DeviceStatus("ONE_DEVICE", 1, devices=(DeviceIdentity(serial),))

            def capture(self, config, cancellation=None):
                raise AssertionError("unassigned serial must block capture")

            def coarse_sweep(self, cancellation=None):
                raise AssertionError("sweep is outside B0 UI readiness")

            def cancel(self) -> None:
                pass

            def close(self) -> None:
                pass

        _, window, controller = build_application(
            [],
            acquisition_backend=OneDeviceBackend(),  # type: ignore[arg-type]
            ed_rx_config=EDRXDeviceConfig(),
        )
        window.source_type_combo.setCurrentIndex(1)
        controller.probe_hackrf()
        self._drain(controller)
        self.assertIn("seri kimliği atanmadı", window.hackrf_status.text())
        self.assertFalse(window.hackrf_start_button.isEnabled())
        controller.close()
        window.close()

    def test_deterministic_source_runs_existing_spectrum_and_detector_pipeline(self) -> None:
        app, window, controller = build_laboratory_application([])
        window.source_type_combo.setCurrentIndex(2)
        self.assertEqual("deterministic_test", window.source_kind)
        self.assertTrue(controller.open_deterministic_source())
        self._drain(controller)
        self.assertIsNotNone(controller.source)
        self.assertIsNotNone(controller.last_result)
        self.assertIsNotNone(controller.last_detection)
        self.assertIn("canlı RF değildir", window.notification.text())
        self.assertEqual("phase03-operation-default", controller.profile.profile_id)
        self.assertLessEqual(controller.max_concurrent_tasks, 1)
        self.assertLessEqual(controller.max_pending_intents, 1)
        controller.close()
        window.close()

    def test_pending_is_bounded_and_source_change_rejects_stale_generation(self) -> None:
        app, window, controller = build_laboratory_application([], test_backend_factory=DeterministicMockBackend)
        window.source_type_combo.setCurrentIndex(2)
        controller.open_deterministic_source()
        controller.open_deterministic_source()
        self.assertLessEqual(controller.pending_intent_count, 1)
        window.source_type_combo.setCurrentIndex(0)
        self._drain(controller)
        self.assertIsNone(controller.source)
        controller._acquisition_completed(controller.generation - 1, "probe", object())
        self.assertGreaterEqual(controller.stale_results_rejected, 1)
        controller.close()
        self.assertEqual(0, controller.active_task_count)
        window.close()

    def test_capture_and_fixture_read_run_outside_ui_thread(self) -> None:
        worker_threads: list[int] = []

        class RecordingBackend(DeterministicMockBackend):
            def capture(self, config: object, cancellation: object = None) -> object:
                worker_threads.append(threading.get_ident())
                return super().capture(config, cancellation)  # type: ignore[arg-type]

        ui_thread = threading.get_ident()
        app, window, controller = build_laboratory_application([], test_backend_factory=RecordingBackend)
        window.source_type_combo.setCurrentIndex(2)
        controller.open_deterministic_source()
        self._drain(controller)
        self.assertEqual(1, len(worker_threads))
        self.assertNotEqual(ui_thread, worker_threads[0])
        controller.close()
        window.close()

    def test_ui_does_not_import_or_call_subprocess(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        for relative in ("host/operator_console/controller.py", "host/operator_console/main_window.py"):
            text = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("import subprocess", text)
            self.assertNotIn("subprocess.", text)


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
