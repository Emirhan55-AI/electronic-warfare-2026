"""Qt- and DSP-independent contracts for bounded HackRF receive acquisition."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Literal, Protocol


ToolState = Literal["available", "unavailable", "unverified"]
DeviceState = Literal["ready", "not_found", "not_exercised", "error"]
OperationState = Literal["passed", "failed", "cancelled", "not_exercised"]


class AcquisitionError(RuntimeError):
    """Typed, allowlisted acquisition failure safe for the controller boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ToolStatus:
    name: str
    state: ToolState
    help_verified: bool = False
    supported_options: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolInventory:
    tools: tuple[ToolStatus, ...]

    def get(self, name: str) -> ToolStatus:
        return next((item for item in self.tools if item.name == name), ToolStatus(name, "unavailable"))

    @property
    def receive_available(self) -> bool:
        item = self.get("hackrf_transfer")
        return item.state == "available" and item.help_verified


@dataclass(frozen=True)
class DeviceStatus:
    state: DeviceState
    device_count: int = 0
    reason_code: str | None = None


@dataclass(frozen=True)
class RXConfig:
    center_frequency_hz: int = 100_000_000
    sample_rate_hz: int = 8_000_000
    sample_count: int = 16_384
    rf_amplifier: bool = False
    lna_gain_db: int = 16
    vga_gain_db: int = 16

    def __post_init__(self) -> None:
        values = (self.center_frequency_hz, self.sample_rate_hz, self.sample_count, self.lna_gain_db, self.vga_gain_db)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise AcquisitionError("invalid_rx_config", "RX ayarları tam sayı olmalıdır.")
        if not 1_000_000 <= self.center_frequency_hz <= 6_000_000_000:
            raise AcquisitionError("invalid_center_frequency", "Merkez frekansı güvenli sınırın dışındadır.")
        if self.sample_rate_hz not in {8_000_000, 10_000_000, 20_000_000}:
            raise AcquisitionError("invalid_sample_rate", "Örnekleme hızı doğrulanan hazırlık zarfında değildir.")
        if not 4_096 <= self.sample_count <= 65_536 or self.sample_count % 4_096:
            raise AcquisitionError("invalid_sample_count", "Capture uzunluğu 4096 örneklik bounded çerçevelerden oluşmalıdır.")
        if self.lna_gain_db not in range(0, 41, 8):
            raise AcquisitionError("invalid_lna_gain", "IF/LNA kazancı 0–40 dB arasında 8 dB adımlı olmalıdır.")
        if self.vga_gain_db not in range(0, 63, 2):
            raise AcquisitionError("invalid_vga_gain", "Baseband/VGA kazancı 0–62 dB arasında 2 dB adımlı olmalıdır.")


@dataclass(frozen=True)
class CaptureResult:
    status: OperationState
    payload: bytes
    config: RXConfig
    backend_kind: Literal["real", "deterministic_test"]
    reason_code: str | None = None


@dataclass(frozen=True)
class SweepBin:
    frequency_hz: int
    power_dbfs: float


@dataclass(frozen=True)
class SweepResult:
    status: OperationState
    bins: tuple[SweepBin, ...] = ()
    reason_code: str | None = None


class HackRFBackend(Protocol):
    """Dependency-injection boundary; implementations must not depend on Qt or DSP."""

    backend_kind: Literal["real", "deterministic_test"]

    def discover_tools(self, *, inspect_help: bool = False) -> ToolInventory: ...

    def discover_device(self, cancellation: threading.Event | None = None) -> DeviceStatus: ...

    def capture(self, config: RXConfig, cancellation: threading.Event | None = None) -> CaptureResult: ...

    def coarse_sweep(self, cancellation: threading.Event | None = None) -> SweepResult: ...

    def cancel(self) -> None: ...

    def close(self) -> None: ...
