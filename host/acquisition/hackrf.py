"""Production HackRF RX command-line implementation."""

from __future__ import annotations

import math
import re
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Callable

from .contracts import (
    AcquisitionError,
    CaptureResult,
    DeviceIdentity,
    DeviceStatus,
    RXConfig,
    SweepBin,
    SweepResult,
    ToolInventory,
    ToolStatus,
)
from .process import SafeProcessRunner


TOOL_NAMES = ("hackrf_info", "hackrf_transfer", "hackrf_sweep")
TRANSFER_OPTIONS = ("-d", "-r", "-f", "-s", "-n", "-a", "-l", "-g")
MAX_SWEEP_POINTS = 4096
MAX_SWEEP_BYTES = 262_144


def _help_options(payload: bytes) -> tuple[str, ...]:
    text = payload.decode("utf-8", errors="replace")
    found = set(re.findall(r"(?<![\w-])-[A-Za-z](?![\w-])", text))
    return tuple(sorted(found))


def parse_hackrf_info(payload: bytes) -> tuple[DeviceIdentity, ...]:
    """Parse bounded `hackrf_info` identity fields without selecting USB index zero."""

    text = payload.decode("utf-8", errors="replace")
    serial_matches = list(re.finditer(r"(?im)^\s*Serial number:\s*([^\s]+)\s*$", text))
    devices: list[DeviceIdentity] = []
    for index, match in enumerate(serial_matches):
        start = match.start()
        end = serial_matches[index + 1].start() if index + 1 < len(serial_matches) else len(text)
        block = text[start:end]

        def field(pattern: str) -> str | None:
            found = re.search(pattern, block, flags=re.IGNORECASE | re.MULTILINE)
            return found.group(1).strip() if found else None

        serial = match.group(1).strip()
        if not 8 <= len(serial) <= 64 or any(character not in "0123456789abcdefABCDEF" for character in serial):
            raise AcquisitionError("device_output_unrecognized", "HackRF seri kimliği güvenle çözümlenemedi.")
        devices.append(
            DeviceIdentity(
                serial=serial,
                board_id=field(r"^\s*Board ID Number:\s*(.+)$"),
                firmware_version=field(r"^\s*Firmware Version:\s*(.+)$"),
                part_id=field(r"^\s*Part ID Number:\s*(.+)$"),
            )
        )
    return tuple(devices)


def build_receive_argv(executable: str, config: RXConfig, destination: Path) -> list[str]:
    """Build the sole production HackRF command path: serial-bound bounded RX."""

    if config.device_serial is None:
        raise AcquisitionError("device_serial_unassigned", "ED_RX HackRF seri kimliği henüz atanmadı.")
    return [
        executable,
        "-d",
        config.device_serial,
        "-r",
        str(destination),
        "-f",
        str(config.center_frequency_hz),
        "-s",
        str(config.sample_rate_hz),
        "-n",
        str(config.sample_count),
        "-a",
        "1" if config.rf_amplifier else "0",
        "-l",
        str(config.lna_gain_db),
        "-g",
        str(config.vga_gain_db),
    ]


def parse_sweep_fixture(payload: bytes, *, maximum_points: int = MAX_SWEEP_POINTS) -> tuple[SweepBin, ...]:
    """Parse the bounded project fixture format: one `frequency_hz,power_dbfs` row."""
    if len(payload) > MAX_SWEEP_BYTES:
        raise AcquisitionError("sweep_output_too_large", "Sweep çıktısı bounded sınırı aşıyor.")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AcquisitionError("sweep_invalid_utf8", "Sweep çıktısı geçerli UTF-8 değil.") from exc
    rows: list[SweepBin] = []
    previous = -1
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 2:
            raise AcquisitionError("sweep_malformed", "Sweep satırı iki alandan oluşmalıdır.")
        try:
            frequency = int(parts[0])
            power = float(parts[1])
        except ValueError as exc:
            raise AcquisitionError("sweep_malformed", "Sweep satırında sayısal olmayan alan var.") from exc
        if not 1_000_000 <= frequency <= 6_000_000_000 or not math.isfinite(power) or frequency <= previous:
            raise AcquisitionError("sweep_value_invalid", "Sweep değeri veya sırası geçersizdir.")
        rows.append(SweepBin(frequency, power))
        previous = frequency
        if len(rows) > maximum_points:
            raise AcquisitionError("sweep_point_limit", "Sweep nokta sınırı aşıldı.")
    if not rows:
        raise AcquisitionError("sweep_empty", "Sweep çıktısında örnek bulunamadı.")
    return tuple(rows)


class RealHackRFBackend:
    """Conservative CLI adapter; it never assumes undocumented streaming behavior."""

    backend_kind = "real"

    def __init__(
        self,
        *,
        runner: SafeProcessRunner | None = None,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.runner = runner or SafeProcessRunner()
        self.which = which
        self._inventory: ToolInventory | None = None
        self._cancel_event = threading.Event()

    def discover_tools(self, *, inspect_help: bool = False) -> ToolInventory:
        tools: list[ToolStatus] = []
        for name in TOOL_NAMES:
            path = self.which(name)
            if path is None:
                tools.append(ToolStatus(name, "unavailable"))
                continue
            if not inspect_help:
                tools.append(ToolStatus(name, "available", False, (), path))
                continue
            try:
                result = self.runner.run([path, "-h"], timeout_seconds=2.0)
            except AcquisitionError:
                tools.append(ToolStatus(name, "unverified", executable_path=path))
                continue
            payload = result.stdout + b"\n" + result.stderr
            options = _help_options(payload)
            help_text = payload.decode("utf-8", errors="replace").casefold()
            verified = result.returncode in {0, 1} and bool(
                options if name != "hackrf_info" else ("hackrf_info" in help_text or "usage" in help_text)
            )
            tools.append(ToolStatus(name, "available" if verified else "unverified", verified, options, path))
        self._inventory = ToolInventory(tuple(tools))
        return self._inventory

    def discover_device(self, cancellation: threading.Event | None = None) -> DeviceStatus:
        inventory = self._inventory or self.discover_tools(inspect_help=True)
        info = inventory.get("hackrf_info")
        path = self.which("hackrf_info")
        if info.state != "available" or path is None:
            return DeviceStatus("TOOLCHAIN_UNAVAILABLE", reason_code="tools_unavailable")
        token = cancellation or self._cancel_event
        try:
            result = self.runner.run([path], timeout_seconds=3.0, cancellation=token)
        except AcquisitionError as exc:
            return DeviceStatus("DEVICE_ERROR", reason_code=exc.code)
        payload = result.stdout + b"\n" + result.stderr
        output = payload.decode("utf-8", errors="replace").casefold()
        if "no hackrf boards found" in output or "hackrf_open() failed" in output:
            return DeviceStatus("NO_DEVICE", reason_code="device_not_found")
        if result.returncode != 0:
            return DeviceStatus("DEVICE_ERROR", reason_code="device_probe_failed")
        try:
            devices = parse_hackrf_info(payload)
        except AcquisitionError as exc:
            return DeviceStatus("DEVICE_ERROR", reason_code=exc.code)
        if not devices:
            return DeviceStatus("DEVICE_ERROR", reason_code="device_output_unrecognized")
        state = "ONE_DEVICE" if len(devices) == 1 else "MULTIPLE_DEVICES"
        return DeviceStatus(state, len(devices), devices=devices)

    def capture(self, config: RXConfig, cancellation: threading.Event | None = None) -> CaptureResult:
        inventory = self._inventory or self.discover_tools(inspect_help=True)
        transfer = inventory.get("hackrf_transfer")
        path = self.which("hackrf_transfer")
        if path is None or transfer.state != "available" or not transfer.help_verified:
            raise AcquisitionError("tools_unavailable", "HackRF receive aracı doğrulanamadı.")
        if not set(TRANSFER_OPTIONS) <= set(transfer.supported_options):
            raise AcquisitionError("cli_options_unverified", "Gerekli HackRF RX seçenekleri yardım çıktısında doğrulanmadı.")
        descriptor, raw_path = tempfile.mkstemp(prefix="phase08a-rx-", suffix=".ci8")
        capture_path = Path(raw_path)
        try:
            import os

            os.close(descriptor)
            argv = build_receive_argv(path, config, capture_path)
            result = self.runner.run(argv, timeout_seconds=10.0, cancellation=cancellation or self._cancel_event)
            if result.returncode != 0:
                raise AcquisitionError("capture_process_failed", "HackRF capture aracı başarısız oldu.")
            expected = config.sample_count * 2
            with capture_path.open("rb") as stream:
                payload = stream.read(expected + 1)
            if len(payload) < expected:
                raise AcquisitionError("short_capture", "HackRF capture beklenen uzunluktan kısa.")
            if len(payload) > expected:
                raise AcquisitionError("long_capture", "HackRF capture beklenen uzunluktan uzun.")
            return CaptureResult("passed", payload, config, "real")
        finally:
            capture_path.unlink(missing_ok=True)

    def coarse_sweep(self, cancellation: threading.Event | None = None) -> SweepResult:
        del cancellation
        return SweepResult("not_exercised", reason_code="real_sweep_format_not_verified")

    def cancel(self) -> None:
        self._cancel_event.set()
        self.runner.close()
        self._cancel_event = threading.Event()

    def close(self) -> None:
        self.cancel()
