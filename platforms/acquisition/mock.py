"""Test-only bounded HackRF backend; never part of the product entry point."""

from __future__ import annotations

import threading
from pathlib import Path

from .contracts import AcquisitionError, CaptureResult, DeviceStatus, RXConfig, SweepResult, ToolInventory, ToolStatus
from .hackrf import TOOL_NAMES, parse_sweep_fixture


class DeterministicMockBackend:
    """Deterministic validation backend that never reports live RF or hardware."""

    backend_kind = "deterministic_test"

    def __init__(self, payload: bytes | None = None) -> None:
        self._payload = None if payload is None else bytes(payload)
        self._cancelled = False

    def discover_tools(self, *, inspect_help: bool = False) -> ToolInventory:
        del inspect_help
        return ToolInventory(tuple(ToolStatus(name, "unavailable") for name in TOOL_NAMES))

    def discover_device(self, cancellation: threading.Event | None = None) -> DeviceStatus:
        del cancellation
        return DeviceStatus("NOT_EXERCISED", reason_code="deterministic_test_source")

    def capture(self, config: RXConfig, cancellation: threading.Event | None = None) -> CaptureResult:
        if self._cancelled or (cancellation is not None and cancellation.is_set()):
            raise AcquisitionError("operation_cancelled", "Deterministik test capture işlemi iptal edildi.")
        expected = config.sample_count * 2
        payload = self._payload
        if payload is None:
            fixture = Path(__file__).resolve().parents[2] / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
            payload = fixture.read_bytes()
        if len(payload) != expected:
            reason = "short_capture" if len(payload) < expected else "long_capture"
            raise AcquisitionError(reason, "Deterministik capture boyutu beklenen değerle eşleşmiyor.")
        return CaptureResult("passed", payload, config, "deterministic_test")

    def coarse_sweep(self, cancellation: threading.Event | None = None) -> SweepResult:
        if self._cancelled or (cancellation is not None and cancellation.is_set()):
            raise AcquisitionError("operation_cancelled", "Deterministik sweep iptal edildi.")
        fixture = b"99000000,-72.0\n100000000,-18.0\n101000000,-70.5\n"
        return SweepResult("passed", parse_sweep_fixture(fixture))

    def cancel(self) -> None:
        self._cancelled = True

    def close(self) -> None:
        self.cancel()
