"""Bounded HackRF receive acquisition contracts and backends."""

from .contracts import (
    AcquisitionError,
    CaptureResult,
    DeviceIdentity,
    DeviceStatus,
    EDRXDeviceConfig,
    EDRXReceiverConfig,
    HackRFBackend,
    RXConfig,
    SweepBin,
    SweepResult,
    ToolInventory,
    ToolStatus,
    load_ed_rx_config,
)
from .hackrf import (
    RealHackRFBackend,
    build_receive_argv,
    parse_hackrf_info,
    parse_sweep_fixture,
)
from .process import ProcessResult, SafeProcessRunner
from .portapack import (
    PORTAPACK_HACKRF_COMMAND,
    PORTAPACK_USB_SERIAL_PID,
    PORTAPACK_USB_SERIAL_VID,
    switch_portapack_to_hackrf_mode,
)
from .source import BoundedCI8FrameSource, decode_ci8
from .search import HackRFSearchBackend
from .continuous import (
    HackRFContinuousRX,
    HackRFStreamStatistics,
    build_continuous_receive_argv,
    parse_hackrf_buffer_statistics,
)

__all__ = [
    "AcquisitionError",
    "BoundedCI8FrameSource",
    "CaptureResult",
    "DeviceIdentity",
    "DeviceStatus",
    "EDRXDeviceConfig",
    "EDRXReceiverConfig",
    "HackRFBackend",
    "HackRFSearchBackend",
    "ProcessResult",
    "RXConfig",
    "RealHackRFBackend",
    "SafeProcessRunner",
    "PORTAPACK_HACKRF_COMMAND",
    "PORTAPACK_USB_SERIAL_PID",
    "PORTAPACK_USB_SERIAL_VID",
    "SweepBin",
    "SweepResult",
    "ToolInventory",
    "ToolStatus",
    "build_receive_argv",
    "load_ed_rx_config",
    "parse_hackrf_info",
    "switch_portapack_to_hackrf_mode",
    "decode_ci8",
    "parse_sweep_fixture",
]
from .rx_sources import HackRFHostRxSource, NormalizedIQFrame, ReplayRxSource, RXSourceStatistics, RxSource

__all__ += ["HackRFHostRxSource", "NormalizedIQFrame", "ReplayRxSource", "RXSourceStatistics", "RxSource"]
__all__ += [
    "HackRFContinuousRX",
    "HackRFStreamStatistics",
    "build_continuous_receive_argv",
    "parse_hackrf_buffer_statistics",
]
