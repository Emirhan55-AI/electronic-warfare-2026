"""Qt- and DSP-independent contracts for bounded HackRF receive acquisition."""

from __future__ import annotations

import threading
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol


ToolState = Literal["available", "unavailable", "unverified"]
DeviceState = Literal[
    "TOOLCHAIN_UNAVAILABLE",
    "NO_DEVICE",
    "ONE_DEVICE",
    "MULTIPLE_DEVICES",
    "DEVICE_ERROR",
    "NOT_EXERCISED",
]
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
    executable_path: str | None = None


@dataclass(frozen=True)
class ToolInventory:
    tools: tuple[ToolStatus, ...]

    def get(self, name: str) -> ToolStatus:
        return next((item for item in self.tools if item.name == name), ToolStatus(name, "unavailable"))

    @property
    def receive_available(self) -> bool:
        info = self.get("hackrf_info")
        transfer = self.get("hackrf_transfer")
        return all(item.state == "available" and item.help_verified for item in (info, transfer))


@dataclass(frozen=True)
class DeviceIdentity:
    serial: str
    board_id: str | None = None
    firmware_version: str | None = None
    part_id: str | None = None


@dataclass(frozen=True)
class DeviceStatus:
    state: DeviceState
    device_count: int = 0
    reason_code: str | None = None
    devices: tuple[DeviceIdentity, ...] = ()


@dataclass(frozen=True)
class EDRXReceiverConfig:
    role: Literal["ED_RX_PRIMARY", "ED_RX_SECONDARY"]
    serial: str
    purpose: str

    def __post_init__(self) -> None:
        if self.role not in {"ED_RX_PRIMARY", "ED_RX_SECONDARY"}:
            raise AcquisitionError(
                "device_config_invalid",
                "HackRF alıcı rolü ED_RX_PRIMARY veya ED_RX_SECONDARY olmalıdır.",
            )
        if not isinstance(self.serial, str) or not isinstance(self.purpose, str):
            raise AcquisitionError(
                "device_config_invalid", "HackRF seri kimliği ve görev açıklaması metin olmalıdır."
            )
        serial = self.serial.strip()
        if not 8 <= len(serial) <= 64 or any(
            character not in "0123456789abcdefABCDEF" for character in serial
        ):
            raise AcquisitionError(
                "invalid_device_serial",
                "HackRF seri kimliği geçerli onaltılık biçimde olmalıdır.",
            )
        if not self.purpose.strip() or len(self.purpose) > 120:
            raise AcquisitionError(
                "device_config_invalid", "HackRF alıcı görevi açıklanmalıdır."
            )


@dataclass(frozen=True)
class EDRXDeviceConfig:
    role: Literal["ED_RX"] = "ED_RX"
    device_type: Literal["HackRF One"] = "HackRF One"
    serial: str | None = None
    search_ranges_hz: tuple[tuple[int, int], ...] = ()
    receivers: tuple[EDRXReceiverConfig, ...] = ()

    def __post_init__(self) -> None:
        if self.role != "ED_RX" or self.device_type != "HackRF One":
            raise AcquisitionError("device_config_invalid", "HackRF rolü ED_RX ve cihaz türü HackRF One olmalıdır.")
        if self.serial is not None:
            if not isinstance(self.serial, str):
                raise AcquisitionError(
                    "invalid_device_serial", "HackRF seri kimliği metin olmalıdır."
                )
            serial = self.serial.strip()
            if not 8 <= len(serial) <= 64 or any(character not in "0123456789abcdefABCDEF" for character in serial):
                raise AcquisitionError("invalid_device_serial", "HackRF seri kimliği geçerli onaltılık biçimde olmalıdır.")
        if self.receivers:
            roles = tuple(item.role for item in self.receivers)
            serials = tuple(item.serial.casefold() for item in self.receivers)
            if (
                roles.count("ED_RX_PRIMARY") != 1
                or roles.count("ED_RX_SECONDARY") > 1
                or len(roles) != len(set(roles))
                or len(serials) != len(set(serials))
                or self.serial is None
                or self.serial.casefold()
                != next(
                    item.serial.casefold()
                    for item in self.receivers
                    if item.role == "ED_RX_PRIMARY"
                )
            ):
                raise AcquisitionError(
                    "device_config_invalid",
                    "ED_RX alıcı rolleri ve seri kimlikleri benzersiz olmalıdır.",
                )
        for lower, upper in self.search_ranges_hz:
            if not 1_000_000 <= lower < upper <= 6_000_000_000:
                raise AcquisitionError("invalid_search_range", "HackRF arama aralığı alıcı sınırlarının dışındadır.")

    @property
    def configured_receivers(self) -> tuple[EDRXReceiverConfig, ...]:
        if self.receivers:
            return self.receivers
        if self.serial is None:
            return ()
        return (
            EDRXReceiverConfig(
                "ED_RX_PRIMARY", self.serial, "Tespit ve ölçüm alıcısı"
            ),
        )

    @property
    def serials(self) -> tuple[str, ...]:
        return tuple(item.serial for item in self.configured_receivers)


def load_ed_rx_config(path: Path | None = None) -> EDRXDeviceConfig:
    config_path = path or Path(__file__).resolve().parents[2] / "config" / "p0" / "hackrf_ed_rx.json"
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("device_config_unreadable", "ED_RX HackRF yapılandırması okunamadı.") from exc
    if not isinstance(document, dict):
        raise AcquisitionError("device_config_invalid", "ED_RX HackRF yapılandırması nesne olmalıdır.")
    schema_version = document.get("schema_version", 1)
    if isinstance(schema_version, bool) or schema_version not in {1, 2}:
        raise AcquisitionError(
            "device_config_invalid", "ED_RX yapılandırma şeması desteklenmiyor."
        )
    ranges = document.get("search_ranges_hz", [])
    if not isinstance(ranges, list):
        raise AcquisitionError("device_config_invalid", "HackRF arama aralıkları liste olmalıdır.")
    parsed_ranges: list[tuple[int, int]] = []
    for item in ranges:
        if not isinstance(item, dict) or set(item) != {"lower_frequency_hz", "upper_frequency_hz"}:
            raise AcquisitionError("device_config_invalid", "HackRF arama aralığı alt ve üst Hz alanları gerektirir.")
        lower, upper = item["lower_frequency_hz"], item["upper_frequency_hz"]
        if isinstance(lower, bool) or isinstance(upper, bool) or not isinstance(lower, int) or not isinstance(upper, int):
            raise AcquisitionError("device_config_invalid", "HackRF arama sınırları tam sayı Hz olmalıdır.")
        parsed_ranges.append((lower, upper))
    receiver_items = document.get("receivers", [])
    if not isinstance(receiver_items, list):
        raise AcquisitionError(
            "device_config_invalid", "HackRF alıcı rolleri liste olmalıdır."
        )
    receivers: list[EDRXReceiverConfig] = []
    for item in receiver_items:
        if not isinstance(item, dict) or set(item) != {"role", "serial", "purpose"}:
            raise AcquisitionError(
                "device_config_invalid",
                "Her HackRF alıcısı rol, seri kimliği ve görev açıklaması gerektirir.",
            )
        try:
            receivers.append(
                EDRXReceiverConfig(
                    role=item["role"],
                    serial=item["serial"],
                    purpose=item["purpose"],
                )
            )
        except (TypeError, ValueError) as exc:
            raise AcquisitionError(
                "device_config_invalid", "HackRF alıcı rolü geçersizdir."
            ) from exc
    primary_serial = document.get("serial")
    if receivers:
        primary = next(
            (item for item in receivers if item.role == "ED_RX_PRIMARY"), None
        )
        if primary is None:
            raise AcquisitionError(
                "device_config_invalid", "Birincil ED_RX alıcısı tanımlanmalıdır."
            )
        if primary_serial is not None and str(primary_serial).casefold() != primary.serial.casefold():
            raise AcquisitionError(
                "device_config_invalid", "Birincil HackRF seri kimlikleri uyuşmuyor."
            )
        primary_serial = primary.serial
    return EDRXDeviceConfig(
        role=document.get("role"),
        device_type=document.get("device_type"),
        serial=primary_serial,
        search_ranges_hz=tuple(parsed_ranges),
        receivers=tuple(receivers),
    )


@dataclass(frozen=True)
class RXConfig:
    center_frequency_hz: int = 100_000_000
    sample_rate_hz: int = 8_000_000
    sample_count: int = 16_384
    rf_amplifier: bool = False
    lna_gain_db: int = 16
    vga_gain_db: int = 16
    device_serial: str | None = None

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
        if self.device_serial is not None:
            serial = self.device_serial.strip()
            if not 8 <= len(serial) <= 64 or any(character not in "0123456789abcdefABCDEF" for character in serial):
                raise AcquisitionError("invalid_device_serial", "HackRF seri kimliği geçerli onaltılık biçimde olmalıdır.")


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
