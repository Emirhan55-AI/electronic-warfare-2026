from __future__ import annotations

from types import SimpleNamespace

import pytest

from platforms.acquisition import (
    AcquisitionError,
    PORTAPACK_HACKRF_COMMAND,
    PORTAPACK_USB_SERIAL_PID,
    PORTAPACK_USB_SERIAL_VID,
    switch_portapack_to_hackrf_mode,
)
from platforms.acquisition.portapack import PORTAPACK_COMMAND_SETTLE_SECONDS


def _port(device: str, vid: int, pid: int) -> SimpleNamespace:
    return SimpleNamespace(device=device, vid=vid, pid=pid)


def test_portapack_switch_targets_only_exact_usb_serial_identity() -> None:
    opened = []
    events = []

    class Connection:
        def __init__(self, **settings):
            opened.append(settings)
            self.closed = False

        def write(self, payload: bytes) -> int:
            assert payload == PORTAPACK_HACKRF_COMMAND
            events.append("write")
            return len(payload)

        def flush(self) -> None:
            events.append("flush")

        def close(self) -> None:
            events.append("close")
            self.closed = True

    selected = switch_portapack_to_hackrf_mode(
        port_enumerator=lambda: (
            _port("COM6", 0x04B4, 0x0008),
            _port("COM9", PORTAPACK_USB_SERIAL_VID, PORTAPACK_USB_SERIAL_PID),
        ),
        serial_factory=Connection,
        sleeper=lambda seconds: events.append(("sleep", seconds)),
    )

    assert selected == "COM9"
    assert opened[0]["port"] == "COM9"
    assert opened[0]["baudrate"] == 115_200
    assert events == [
        "write",
        "flush",
        ("sleep", PORTAPACK_COMMAND_SETTLE_SECONDS),
        "close",
    ]


@pytest.mark.parametrize(
    "ports,code",
    [
        ((_port("COM6", 0x04B4, 0x0008),), "portapack_control_not_found"),
        (
            (
                _port("COM9", PORTAPACK_USB_SERIAL_VID, PORTAPACK_USB_SERIAL_PID),
                _port("COM10", PORTAPACK_USB_SERIAL_VID, PORTAPACK_USB_SERIAL_PID),
            ),
            "portapack_control_ambiguous",
        ),
    ],
)
def test_portapack_switch_fails_closed_without_one_exact_port(ports, code) -> None:
    with pytest.raises(AcquisitionError) as caught:
        switch_portapack_to_hackrf_mode(
            port_enumerator=lambda: ports,
            serial_factory=lambda **kwargs: pytest.fail(f"unexpected serial open: {kwargs}"),
            sleeper=lambda seconds: pytest.fail(f"unexpected sleep: {seconds}"),
        )
    assert caught.value.code == code


def test_portapack_switch_rejects_partial_command_write() -> None:
    class PartialConnection:
        def __init__(self, **settings):
            del settings

        @staticmethod
        def write(payload: bytes) -> int:
            return len(payload) - 1

        @staticmethod
        def close() -> None:
            pass

    with pytest.raises(AcquisitionError) as caught:
        switch_portapack_to_hackrf_mode(
            port_enumerator=lambda: (
                _port("COM9", PORTAPACK_USB_SERIAL_VID, PORTAPACK_USB_SERIAL_PID),
            ),
            serial_factory=PartialConnection,
            sleeper=lambda seconds: pytest.fail(f"unexpected sleep: {seconds}"),
        )
    assert caught.value.code == "portapack_mode_switch_failed"
