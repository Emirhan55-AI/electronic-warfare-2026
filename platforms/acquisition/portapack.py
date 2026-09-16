"""Fail-closed PortaPack USB-serial handoff to HackRF mode."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import time
from typing import Any

from .contracts import AcquisitionError


PORTAPACK_USB_SERIAL_VID = 0x1D50
PORTAPACK_USB_SERIAL_PID = 0x6018
PORTAPACK_HACKRF_COMMAND = b"hackrf\r\n"
PORTAPACK_COMMAND_SETTLE_SECONDS = 0.5


def switch_portapack_to_hackrf_mode(
    *,
    port_enumerator: Callable[[], Iterable[object]] | None = None,
    serial_factory: Callable[..., Any] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> str:
    """Send Mayhem's ``hackrf`` command to one exact CDC device.

    General COM ports are never guessed. Exactly one USB-serial interface with
    Mayhem's VID/PID must be present, and the complete command must be written.
    """

    try:
        import serial
        from serial.tools import list_ports
    except ImportError as exc:
        raise AcquisitionError(
            "portapack_serial_unavailable",
            "PortaPack USB denetim bileşeni kurulu değil.",
        ) from exc

    enumerate_ports = port_enumerator or list_ports.comports
    candidates = sorted(
        {
            str(getattr(port, "device", "")).strip()
            for port in enumerate_ports()
            if getattr(port, "vid", None) == PORTAPACK_USB_SERIAL_VID
            and getattr(port, "pid", None) == PORTAPACK_USB_SERIAL_PID
            and str(getattr(port, "device", "")).strip()
        }
    )
    if not candidates:
        raise AcquisitionError(
            "portapack_control_not_found",
            "PortaPack USB denetim bağlantısı bulunamadı.",
        )
    if len(candidates) != 1:
        raise AcquisitionError(
            "portapack_control_ambiguous",
            "Birden fazla PortaPack USB denetim bağlantısı bulundu.",
        )

    port_name = candidates[0]
    open_serial = serial_factory or serial.Serial
    connection = None
    try:
        connection = open_serial(
            port=port_name,
            baudrate=115_200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5,
            write_timeout=1.0,
        )
        written = connection.write(PORTAPACK_HACKRF_COMMAND)
        if written != len(PORTAPACK_HACKRF_COMMAND):
            raise AcquisitionError(
                "portapack_mode_switch_failed",
                "PortaPack HackRF modu komutu tamamlanamadı.",
            )
        flush = getattr(connection, "flush", None)
        if callable(flush):
            flush()
        # Mayhem consumes the shell command asynchronously. Keep the CDC port
        # open as its own Windows flasher does; closing immediately can discard
        # the command before firmware handles the line and starts USB reset.
        (sleeper or time.sleep)(PORTAPACK_COMMAND_SETTLE_SECONDS)
    except AcquisitionError:
        raise
    except (OSError, ValueError, serial.SerialException) as exc:
        raise AcquisitionError(
            "portapack_mode_switch_failed",
            "PortaPack HackRF moduna geçirilemedi.",
        ) from exc
    finally:
        if connection is not None:
            try:
                connection.close()
            except (OSError, serial.SerialException):
                pass
    return port_name
