from __future__ import annotations

import os
import sqlite3
import struct
import threading
import time
import zlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QPersistentModelIndex
from PySide6.QtTest import QSignalSpy

from algorithms.p0 import CoarseDetection, CoarseDetectionFrame, IQFrame, TransportStats
from algorithms.p0.transport import InlineParameterField, InlineParameterResult, TransportError
from algorithms.p0.parameter_client import decode_response as decode_board_parameter_response
from algorithms.monitoring import AnalogMonitorResult
from app.operator_console.fixed_band_verification import FixedBandCandidate
from app.operator_console.live_ed import (
    LIVE_AUDIO_WINDOW_FRAMES,
    LiveEDConfiguration,
    LiveEDEvent,
    LiveEDResponse,
    LiveEDSessionResult,
    LiveEDSnapshot,
)
from app.operator_console.quick_view_model import MISSING_RECEIVER_ERROR_DISPLAY_MS, OperatorViewModel
from app.operator_console.automatic_parameter import AutomaticParameterOutcome
from app.operator_console.quick_runtime import _LiveSnapshotMailbox
from app.operator_console.quick_task_completion import _analog_voice_bandwidth_khz
from app.operator_console.detection_model import DetectionListModel
from platforms.acquisition import (
    AcquisitionError,
    DeviceIdentity,
    DeviceStatus,
    HackRFStreamStatistics,
    ToolInventory,
    ToolStatus,
    load_ed_rx_config,
)


SERIAL = load_ed_rx_config().serial
SECONDARY_SERIAL = next(
    receiver.serial
    for receiver in load_ed_rx_config().configured_receivers
    if receiver.role == "ED_RX_SECONDARY"
)


def test_analog_voice_bandwidth_suggestion_is_bounded() -> None:
    assert _analog_voice_bandwidth_khz(10_000.0) == 12.0
    assert _analog_voice_bandwidth_khz(200_000.0) == 25.0
    assert _analog_voice_bandwidth_khz(1_000.0) == 6.0


def test_slow_gui_preserves_parameter_results_while_coalescing_frames():
    mailbox = _LiveSnapshotMailbox()
    response = LiveEDResponse(0, 0, 7, 0, False, 0, (), (), 0)
    frame = IQFrame(0, 2_000_000, 820_000_000, b"\x00" * 8192, frame_id=0)
    first = AutomaticParameterOutcome(1, 1, 820_000_000.0, 1.0, 2000, 2020,
                                      "not_observed", "event_ownership_lost")
    second = replace(first, event_id=2, intent_id=2)
    assert mailbox.publish((LiveEDSnapshot(0, frame, response, (first,)), 1.0))
    assert not mailbox.publish((LiveEDSnapshot(1, frame, response, (second,)), 2.0))
    assert not mailbox.publish((LiveEDSnapshot(2, frame, response), 3.0))
    latest, received_at = mailbox.take()
    assert latest.sequence_number == 2
    assert received_at == 3.0
    assert latest.automatic_parameter_outcomes == (first, second)
    assert mailbox.take() is None
    assert mailbox.publish((LiveEDSnapshot(3, frame, response), 4.0))
    assert mailbox.take()[0].automatic_parameter_outcomes == ()


def test_parameter_delivery_overflow_is_explicit_and_preserves_pending_results():
    mailbox = _LiveSnapshotMailbox()
    mailbox.maximum_outcomes = 1
    response = LiveEDResponse(0, 0, 7, 0, False, 0, (), (), 0)
    frame = IQFrame(0, 2_000_000, 820_000_000, b"\x00" * 8192, frame_id=0)
    outcome = AutomaticParameterOutcome(1, 1, 820_000_000.0, 1.0, 2000, 2020,
                                        "not_observed", "event_ownership_lost")
    snapshot = LiveEDSnapshot(0, frame, response, (outcome,))
    mailbox.publish((snapshot, 1.0))
    with pytest.raises(AcquisitionError) as caught:
        mailbox.publish((snapshot, 2.0))
    assert caught.value.code == "parameter_delivery_overflow"
    assert mailbox.take() == (snapshot, 1.0)


def _fake_board_parameter_measurement(host, port, intent, iq, *, sample_rate_hz,
                                      center_frequency_hz, locked_channel_power=False):
    del host, port, sample_rate_hz
    token = 7
    payload = bytearray(176)
    count = len(iq) // 8192
    version = 4 if locked_channel_power else 3 if count == 16 else 2 if intent.span.width_bins > 512 else 1
    struct.pack_into('<4sHHIIQQIB', payload, 0, b'P0PR', version, 176, token, 0,
                     token, intent.event_id, intent.start_frame + count - 1, count)
    values = (center_frequency_hz, center_frequency_hz - 5_000,
              center_frequency_hz + 5_000, 10_000, -30, 12)
    for offset, value in zip(range(40, 112, 12), values):
        struct.pack_into('<BBHd', payload, offset, 1, 0, 0, value)
    struct.pack_into('<BBHd', payload, 144, 4, 9, 0, 0.)
    struct.pack_into('<IIII', payload, 156, 25_000, zlib.crc32(iq), 3, 4096)
    struct.pack_into('<I', payload, 172, zlib.crc32(payload[:172]))
    return decode_board_parameter_response(
        bytes(payload), intent, iq, token,
        locked_channel_power=locked_channel_power,
    )


class _Backend:
    backend_kind = "real"

    def discover_tools(self, *, inspect_help=False):
        del inspect_help
        return ToolInventory(
            (
                ToolStatus("hackrf_info", "available", True, (), "hackrf_info"),
                ToolStatus(
                    "hackrf_transfer",
                    "available",
                    True,
                    ("-B", "-d", "-f", "-g", "-l", "-n", "-r", "-s"),
                    "hackrf_transfer",
                ),
            )
        )

    def discover_device(self, cancellation=None):
        del cancellation
        return DeviceStatus("ONE_DEVICE", 1, devices=(DeviceIdentity(SERIAL),))

    def cancel(self):
        pass

    def close(self):
        pass


class _TwoReceiverBackend(_Backend):
    def discover_device(self, cancellation=None):
        del cancellation
        devices = tuple(
            DeviceIdentity(receiver.serial)
            for receiver in load_ed_rx_config().configured_receivers
        )
        return DeviceStatus("MULTIPLE_DEVICES", len(devices), devices=devices)


class _SecondaryReceiverBackend(_Backend):
    def discover_device(self, cancellation=None):
        del cancellation
        return DeviceStatus(
            "ONE_DEVICE", 1, devices=(DeviceIdentity(SECONDARY_SERIAL),)
        )


class _DisconnectedBackend(_Backend):
    def discover_device(self, cancellation=None):
        del cancellation
        return DeviceStatus("NO_DEVICE", reason_code="device_not_found")


class _DisconnectableBackend(_Backend):
    def __init__(self):
        self.connected = True

    def discover_device(self, cancellation=None):
        del cancellation
        if self.connected:
            return DeviceStatus("ONE_DEVICE", 1, devices=(DeviceIdentity(SERIAL),))
        return DeviceStatus("NO_DEVICE", reason_code="device_not_found")


class _PortaPackHandoffBackend(_Backend):
    def __init__(self):
        self.hackrf_mode = False

    def discover_device(self, cancellation=None):
        del cancellation
        if self.hackrf_mode:
            return DeviceStatus("ONE_DEVICE", 1, devices=(DeviceIdentity(SERIAL),))
        return DeviceStatus("NO_DEVICE", reason_code="device_not_found")


class _ToolsUnavailableBackend(_Backend):
    def discover_tools(self, *, inspect_help=False):
        del inspect_help
        return ToolInventory(
            (
                ToolStatus("hackrf_info", "unavailable", False),
                ToolStatus("hackrf_transfer", "unavailable", False),
            )
        )


class _FPGAReadyTransport:
    def connect(self, host, port, *, timeout_seconds):
        assert host == "192.168.7.2"
        assert port == 47_007
        assert timeout_seconds == 2.0

    def close(self):
        pass


class _FPGAMissingTransport(_FPGAReadyTransport):
    def connect(self, host, port, *, timeout_seconds):
        super().connect(host, port, timeout_seconds=timeout_seconds)
        raise TransportError("connection_failed", "FPGA hizmetine bağlanılamadı.")


class _Session:
    def __init__(self, executable: str, configuration: LiveEDConfiguration) -> None:
        assert executable == "hackrf_transfer"
        assert configuration.display_interval_frames == 15
        self.configuration = configuration
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def run(self, snapshot_handler):
        event = LiveEDEvent(
            event_id=31,
            first_frame_id=0,
            last_seen_frame_id=3,
            seen_count=4,
            state="confirmed",
            observed_this_frame=True,
            start_shifted_bin=2200,
            end_shifted_bin=2210,
            peak_shifted_bin=2205,
            coarse_span_bins=11,
            pfa_select=1,
            flags=0,
            peak_power=100.0,
            noise_power=1.0,
            threshold_power=10.0,
        )
        response = LiveEDResponse(3, 1, 7, 0, False, 0, (event,), (), 136)
        frame = IQFrame(3, 2_000_000, self.configuration.output_center_frequency_hz, bytes(8192), frame_id=3)
        snapshot_handler(LiveEDSnapshot(3, frame, response))
        hackrf = HackRFStreamStatistics(4, 4 * 32768, 0.01, 0, 0, 0, "")
        return LiveEDSessionResult(
            completed_frames=4,
            elapsed_seconds=0.01,
            frames_per_second=500.0,
            real_time_margin=1.024,
            raw_candidate_total=4,
            maximum_active_events=1,
            input_saturated_components=0,
            output_saturated_components=0,
            capture_queue_high_watermark=1,
            channelized_queue_high_watermark=1,
            hackrf_statistics=hackrf,
            transport_statistics=TransportStats(
                state="DISCONNECTED", frames_sent=4, frames_received=4
            ),
        )


class _BlockingSession:
    def __init__(self, executable: str, configuration: LiveEDConfiguration) -> None:
        del executable, configuration
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        self.cancelled.set()

    def run(self, snapshot_handler):
        del snapshot_handler
        while not self.cancelled.wait(0.01):
            pass
        raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")


class _MeasurementSession(_BlockingSession):
    def __init__(self, executable: str, configuration: LiveEDConfiguration) -> None:
        super().__init__(executable, configuration)
        self.configuration = configuration
        event = LiveEDEvent(
            event_id=31,
            first_frame_id=0,
            last_seen_frame_id=3,
            seen_count=4,
            state="confirmed",
            observed_this_frame=True,
            start_shifted_bin=2200,
            end_shifted_bin=2210,
            peak_shifted_bin=2205,
            coarse_span_bins=11,
            pfa_select=1,
            flags=0,
            peak_power=100.0,
            noise_power=1.0,
            threshold_power=10.0,
        )
        self.window = tuple(
            LiveEDSnapshot(
                index,
                IQFrame(
                    index,
                    2_000_000,
                    configuration.output_center_frequency_hz,
                    bytes(8192),
                    frame_id=index,
                ),
                LiveEDResponse(index, 1, 7, 0, False, 0, (replace(event, last_seen_frame_id=index),), (), 136),
            )
            for index in range(4)
        )

    def measurement_window(self, event_id: int):
        return self.window if event_id == 31 else ()

    def current_measurement_window(self, event_id: int):
        return self.window if event_id == 31 else ()

    def run(self, snapshot_handler):
        snapshot_handler(self.window[-1])
        while not self.cancelled.wait(0.01):
            pass
        raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")


class _LiveListeningSession(_BlockingSession):
    def __init__(self, executable: str, configuration: LiveEDConfiguration) -> None:
        super().__init__(executable, configuration)
        self.configuration = configuration
        payload = bytes(8192)
        self.window = tuple(
            IQFrame(
                index,
                2_000_000,
                configuration.output_center_frequency_hz,
                payload,
                frame_id=index,
            )
            for index in range(LIVE_AUDIO_WINDOW_FRAMES)
        )

    def audio_window_frame_count(self, event_id=None) -> int:
        return len(self.window) if event_id in {None, 31} else 0

    def audio_window_ready(self, event_id=None) -> bool:
        return self.audio_window_frame_count(event_id) == LIVE_AUDIO_WINDOW_FRAMES

    def audio_window(self, event_id=None):
        return self.window if event_id in {None, 31} else ()

    def audio_window_quality(self, event_id):
        return {
            "total_frames": len(self.window),
            "observed_frames": len(self.window) - 2,
            "observed_fraction": (len(self.window) - 2) / len(self.window),
            "max_consecutive_misses": 1,
            "acceptable": event_id == 31,
        }

    def audio_channel_frame_count(self, target_frequency_hz):
        return len(self.window) if np.isfinite(target_frequency_hz) else 0

    def audio_channel_ready(self, target_frequency_hz):
        return self.audio_channel_frame_count(target_frequency_hz) == LIVE_AUDIO_WINDOW_FRAMES

    def audio_channel_quality(self, target_frequency_hz):
        quality = self.audio_window_quality(31)
        quality.update(distinct_event_ids=2, event_id_changes=1, invalid_frames=0)
        return quality

    def audio_channel_window_snapshot(self, target_frequency_hz):
        quality = self.audio_channel_quality(target_frequency_hz)
        return (self.window, quality) if self.audio_channel_ready(target_frequency_hz) else ((), quality)

    def run(self, snapshot_handler):
        event = LiveEDEvent(
            event_id=31,
            first_frame_id=0,
            last_seen_frame_id=LIVE_AUDIO_WINDOW_FRAMES - 1,
            seen_count=LIVE_AUDIO_WINDOW_FRAMES,
            state="confirmed",
            observed_this_frame=True,
            start_shifted_bin=2200,
            end_shifted_bin=2210,
            peak_shifted_bin=2205,
            coarse_span_bins=11,
            pfa_select=1,
            flags=0,
            peak_power=100.0,
            noise_power=1.0,
            threshold_power=10.0,
        )
        response = LiveEDResponse(
            LIVE_AUDIO_WINDOW_FRAMES - 1,
            1,
            7,
            0,
            False,
            0,
            (event,),
            (),
            136,
        )
        snapshot_handler(
            LiveEDSnapshot(LIVE_AUDIO_WINDOW_FRAMES - 1, self.window[-1], response)
        )
        while not self.cancelled.wait(0.01):
            pass
        raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")


class _FailedSession(_Session):
    def run(self, snapshot_handler):
        super().run(snapshot_handler)
        raise AcquisitionError("usb_overrun", "USB akışında tampon taşması.")


class _ConnectionFailedSession(_Session):
    def run(self, snapshot_handler):
        del snapshot_handler
        raise AcquisitionError("connection_failed", "FPGA hizmetine bağlanılamadı.")


class _BinaryPipeFailedSession(_Session):
    def run(self, snapshot_handler):
        del snapshot_handler
        raise AcquisitionError(
            "binary_pipe_failed", "HackRF ikili alım bağlantısı kurulamadı."
        )


class _InvalidSnapshotSession(_Session):
    def run(self, snapshot_handler):
        def invalid_snapshot(snapshot):
            snapshot_handler(replace(snapshot, output_frame=replace(snapshot.output_frame, payload=b"")))

        return super().run(invalid_snapshot)


def _drain(app: QGuiApplication, predicate, timeout: float = 3.0) -> None:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline and predicate():
        app.processEvents()
        time.sleep(0.002)


def test_detection_settings_reach_actual_live_and_survey_configuration():
    captured = []
    class ConfiguredSession(_Session):
        def __init__(self, executable, configuration):
            self.configuration, self.cancelled = configuration, False
            captured.append(configuration)

    app = QGuiApplication.instance() or QGuiApplication(["settings-forwarding"])
    view = OperatorViewModel(acquisition_backend=_Backend(),
                             live_session_factory=ConfiguredSession,
                             fpga_transport_factory=_FPGAReadyTransport)
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        assert view.setDetectionSettings(8192, 32, 256, 16)
        view.startLiveEDSession(104_650_000, 16, 62, 4)
        assert not view.setDetectionSettings(4096, 8, 64, 8)
        _drain(app, lambda: view.busy)
        assert captured[0].display_fft_size == 8192
        assert captured[0].display_interval_frames == 32
        assert captured[0].vga_gain_db == 62
        with patch.object(view._survey_controller, "start") as start:
            view.startSurveyProfile(100, 102, 16, 62, "wideband_burst")
            config = start.call_args.args[2]
            assert config.frames_per_window == 256
            assert config.guard_frames == 16
            assert config.vga_gain_db == 62
            assert config.mode == "wideband_burst"
            assert view.sampleRateHz == 10_000_000
            view._live_has_data = True
            assert view.sampleRateText == "10 MS/s"
    finally:
        view.shutdown()


def test_live_hackrf_fpga_session_drives_product_spectrum_and_detection() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-view-model-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_Session,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    view_model.setSourceMode("hackrf")
    view_model.probeHackrf()
    _drain(app, lambda: view_model.busy)
    assert view_model.hackrfReady

    with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy or len(view_model.parameterHistory) < 1)

    assert view_model.sourceReady
    assert view_model.sampleRateText == "8 MS/s"
    assert not view_model.liveSessionActive
    assert view_model.sourceName == "Alıcı ve FPGA"
    assert view_model.centerFrequencyHz == 104_650_000
    assert view_model.sampleRateHz == 2_000_000
    assert view_model.frameIndex == 4
    assert len(view_model.spectrumValues) > 0
    assert len(view_model.detections) == 1
    assert view_model.detections[0]["state"] == "Son görüldü"
    assert not view_model.detectionMarkers
    blocks = {item["id"]: item for item in view_model.pipelineBlocks}
    assert blocks["fft_power"]["runtime"] == "FPGA"
    assert blocks["fft_power"]["implementation"] == "AMD FFT IP · SystemVerilog"
    assert blocks["regional"]["name"] == "OS-CFAR ve Aday Gruplama"
    assert blocks["regional"]["rtlPath"].endswith("axis_p0_os_cfar.sv")
    assert blocks["regional"]["hardwareStatus"] == "Bu oturumda kart yanıtı alındı"
    assert blocks["temporal"]["runtime"] == "ZYNQ PS"
    assert view_model.performanceText == "Canlı yol 500.00 kare/s"
    view_model.shutdown()


def test_system_probe_switches_portapack_only_after_fpga_is_ready() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["portapack-system-probe-test"])
    backend = _PortaPackHandoffBackend()
    calls = []

    def switch_mode() -> str:
        calls.append("switch")
        backend.hackrf_mode = True
        return "COM9"

    view_model = OperatorViewModel(
        acquisition_backend=backend,
        fpga_transport_factory=_FPGAReadyTransport,
        portapack_mode_switcher=switch_mode,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert calls == ["switch"]
        assert view_model.hackrfReady
    finally:
        view_model.shutdown()


def test_system_probe_does_not_switch_portapack_when_fpga_is_unavailable() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["portapack-fpga-gate-test"])
    backend = _PortaPackHandoffBackend()
    calls = []
    view_model = OperatorViewModel(
        acquisition_backend=backend,
        fpga_transport_factory=_FPGAMissingTransport,
        portapack_mode_switcher=lambda: calls.append("switch") or "COM9",
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert calls == []
        assert not view_model.hackrfReady
        assert view_model.errorTitle == "FPGA ve Alıcı algılanamadı"
    finally:
        view_model.shutdown()


def test_system_probe_explains_missing_portapack_control_connection() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["portapack-control-error-test"])
    backend = _PortaPackHandoffBackend()

    def switch_mode() -> str:
        raise AcquisitionError(
            "portapack_control_not_found",
            "PortaPack USB denetim bağlantısı bulunamadı.",
        )

    view_model = OperatorViewModel(
        acquisition_backend=backend,
        fpga_transport_factory=_FPGAReadyTransport,
        portapack_mode_switcher=switch_mode,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert not view_model.hackrfReady
        assert view_model.errorTitle == "Alıcı algılanmadı"
        assert view_model.errorMessage == (
            "Alıcı HackRF USB modunda bulunamadı ve PortaPack USB denetim "
            "bağlantısına erişilemedi."
        )
    finally:
        view_model.shutdown()


def test_probe_reports_both_serial_bound_receiver_roles() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["dual-receiver-probe-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_TwoReceiverBackend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert view_model.hackrfReady
        assert view_model.receiverSummary == "2/2 yapılandırılmış HackRF tanındı"
        assert [row["role"] for row in view_model.receiverRows] == [
            "ED_RX_PRIMARY",
            "ED_RX_SECONDARY",
        ]
        assert all(row["stateKey"] == "found" for row in view_model.receiverRows)
        assert "etkin ana RX yolu" in view_model.receiverRows[0]["state"]
        assert "hazır yedek" in view_model.receiverRows[1]["state"]
    finally:
        view_model.shutdown()


def test_secondary_receiver_is_safe_fallback_for_live_path() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["secondary-receiver-fallback-test"])
    captured_live = []

    def session_factory(executable, configuration):
        captured_live.append((executable, configuration))
        return _BlockingSession(executable, configuration)

    view_model = OperatorViewModel(
        acquisition_backend=_SecondaryReceiverBackend(),
        live_session_factory=session_factory,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert view_model.hackrfReady
        assert view_model._active_receiver_serial == SECONDARY_SERIAL
        assert view_model._receiver_role_for_serial(SECONDARY_SERIAL) == "ED_RX_SECONDARY"
        assert view_model._known_spurs_hz == (1_000_000_000,)
        assert "İkinci alıcı (yedek)" in view_model.sourceName
        assert view_model.receiverRows[1]["state"] == "Tanındı · etkin yedek RX yolu"

        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        assert captured_live[0][1].device_serial == SECONDARY_SERIAL
        view_model.stopLiveEDSession()
    finally:
        view_model.shutdown()


def test_secondary_receiver_is_forwarded_to_wideband_survey() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["secondary-survey-fallback-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_SecondaryReceiverBackend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        with patch.object(view_model._survey_controller, "start") as start:
            view_model.startSurveyProfile(100, 102, 16, 16, "wideband_burst")
            assert start.call_args.args[1] == SECONDARY_SERIAL
    finally:
        view_model.shutdown()


def test_automatic_parameter_outcomes_persist_across_restarted_live_sessions(tmp_path) -> None:
    def valid(value: float) -> InlineParameterField:
        return InlineParameterField("valid", value, None)

    parameter_result = InlineParameterResult(
        intent_id=7,
        event_id=31,
        frame_id=3,
        observation_count=4,
        emission_center_frequency_hz=valid(104_726_500.0),
        lower_occupied_edge_hz=valid(104_716_500.0),
        upper_occupied_edge_hz=valid(104_736_500.0),
        occupied_bandwidth_hz=valid(20_000.0),
        channel_power_dbfs=valid(-31.5),
        snr_estimate_db=valid(18.0),
        reference_difference_db=0.2,
        detection_significance=12.0,
        center_uncertainty_bins=0.1,
        temporal_edge_range_bins=0.2,
    )
    outcome = AutomaticParameterOutcome(
        event_id=31,
        intent_id=7,
        detected_frequency_hz=104_726_500.0,
        detected_peak_power=100.0,
        lower_shifted_bin=2200,
        upper_shifted_bin=2210,
        status="valid",
        reason=None,
        result=parameter_result,
    )

    class AutomaticSession(_Session):
        automatic_parameter_status = "Etkin · en güçlü doğrulanmış olaylar sırada"
        measurement_channelizer = {"profile": {"output_amplitude_scale": 1.0}}

        def run(self, snapshot_handler):
            def publish(snapshot):
                # All three arrive before the GUI consumes its one notification.
                mailbox = _LiveSnapshotMailbox()
                mailbox.publish((replace(snapshot, automatic_parameter_outcomes=(outcome,)), 1.0))
                mailbox.publish((snapshot, 2.0))
                mailbox.publish((snapshot, 3.0))
                snapshot_handler(mailbox.take()[0])
            return super().run(publish)

    app = QGuiApplication.instance() or QGuiApplication(["automatic-catalog-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=AutomaticSession,
        fpga_transport_factory=_FPGAReadyTransport,
        parameter_catalog_path=tmp_path / "automatic-parameters.sqlite3",
    )
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy or len(view_model.parameterHistory) < 1)
        assert len(view_model.parameterHistory) == 1
        assert view_model.parameterHistory[0]["dbfs"] == "-31.50 dBFS"
        assert view_model.parameterHistory[0]["dbm"] == "Kalibre değil"
        assert view_model.parameterHistory[0]["lowerEdge"] == "104.716500 MHz"
        assert view_model.parameterHistory[0]["upperEdge"] == "104.736500 MHz"
        assert view_model.parameterHistory[0]["snr"] == "18.00 dB"
        assert view_model.parameterHistory[0]["receiver"].startswith("Birincil alıcı")
        assert view_model.automaticParameterStatus.startswith("Etkin")

        # Kart olay kimlikleri yeni canlı koşuda yeniden başlayabilir. Katalog
        # oturum kimliği bu ikinci sonucu ilk koşuyla çakıştırmamalıdır.
        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy or len(view_model.parameterHistory) < 2)
        assert len(view_model.parameterHistory) == 2
        assert view_model.parameterCatalogSummary == "2 kayıt"
    finally:
        view_model.shutdown()


def test_corrupt_catalog_preserves_database_and_allows_application_start(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication(["corrupt-catalog-test"])
    path = tmp_path / "catalog.sqlite3"
    original = b"invalid database bytes"
    path.write_bytes(original)
    view = OperatorViewModel(acquisition_backend=_Backend(), parameter_catalog_path=path)
    try:
        assert view.parameterHistory == []
        assert "açılamadı" in view.automaticParameterStatus
        assert view.parameterCatalogPath == str(path)
        view.refreshParameterCatalog()
        assert "okunamadı" in view.automaticParameterStatus
        assert view.exportParameterCatalog() == ""
        assert path.read_bytes() == original
    finally:
        view.shutdown()
        app.processEvents()


def test_catalog_read_and_export_failures_are_reported(live_presentation):
    view = live_presentation
    with patch.object(view._parameter_catalog, "rows", side_effect=sqlite3.OperationalError("locked")):
        view.refreshParameterCatalog()
    assert "okunamadı" in view.automaticParameterStatus
    assert "okunamadı" in view.parameterCatalogActionStatus
    with patch.object(view._parameter_catalog, "export_csv", side_effect=sqlite3.OperationalError("locked")):
        assert view.exportParameterCatalog() == ""
    assert "aktarılamadı" in view.parameterCatalogActionStatus


def test_catalog_actions_report_success_and_write_csv(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication(["catalog-actions-test"])
    view = OperatorViewModel(
        acquisition_backend=_Backend(),
        parameter_catalog_path=tmp_path / "catalog.sqlite3",
    )
    try:
        view.refreshParameterCatalog()
        assert view.parameterCatalogActionStatus.startswith("Katalog yenilendi")
        exported = Path(view.exportParameterCatalog())
        assert exported.is_file()
        assert view.parameterCatalogActionStatus.startswith("CSV dışa aktarıldı")
        with patch("app.operator_console.quick_view_model.QDesktopServices.openUrl", return_value=True):
            assert view.openParameterCatalogFolder()
        assert view.parameterCatalogActionStatus.endswith(str(tmp_path))
        assert any(item["component"] == "Parametre kataloğu" for item in view.eventLog)
    finally:
        view.shutdown()
        app.processEvents()


def test_parameter_catalog_write_does_not_block_gui_thread(live_presentation):
    view = live_presentation
    entered = threading.Event()
    release = threading.Event()

    class SlowCatalog:
        def add_many(self, outcomes, **context):
            del context
            entered.set()
            assert release.wait(1.0)
            return len(outcomes)

        @staticmethod
        def rows():
            return [{"id": 1}]

    view._parameter_catalog = SlowCatalog()
    configuration = SimpleNamespace(
        device_serial=SERIAL,
        lna_gain_db=16,
        vga_gain_db=16,
    )
    started = time.perf_counter()
    view._queue_parameter_catalog_write(
        view._generation,
        tuple(object() for _ in range(64)),
        configuration,
        1.0,
    )

    assert time.perf_counter() - started < 0.05
    assert view._parameter_catalog_pending_outcomes == 64
    app = QGuiApplication.instance()
    assert app is not None
    _drain(app, lambda: not entered.is_set())
    release.set()
    _drain(app, lambda: view._parameter_catalog_pending_outcomes > 0)
    assert view.parameterHistory == [{"id": 1}]


def test_missing_receiver_probe_reports_an_actionable_error() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["missing-receiver-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_DisconnectedBackend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert not view_model.busy
        assert not view_model.hackrfReady
        assert view_model.sourceState == "Hata"
        assert view_model.errorTitle == "Alıcı algılanmadı"
        assert view_model.errorMessage == "Alıcı algılanmadı"
        assert view_model.statusMessage == view_model.errorMessage
        assert view_model._probe_error_timer.interval() == MISSING_RECEIVER_ERROR_DISPLAY_MS
        assert view_model._probe_error_timer.isActive()

        view_model._clear_missing_receiver_error()
        assert view_model.sourceState == "Kullanılmıyor"
        assert view_model.errorTitle == ""
        assert view_model.errorMessage == ""
        assert view_model.statusMessage == "Alıcı bağlantısı bekleniyor."
    finally:
        view_model.shutdown()


def test_short_worker_is_retained_until_queued_completion(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication(["retained-worker-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        parameter_catalog_path=tmp_path / "retained-worker.sqlite3",
    )
    try:
        view_model._submit(view_model._generation, "noop", lambda: "tamam")
        assert len(view_model._active_task_refs) == 1
        _drain(app, lambda: view_model.busy)
        assert not view_model._active_task_refs
    finally:
        view_model.shutdown()


def test_missing_receiver_tools_error_also_returns_to_waiting() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["missing-receiver-tools-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_ToolsUnavailableBackend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert view_model.sourceState == "Hata"
        assert view_model.errorTitle == "Alıcı algılanmadı"
        assert view_model.errorMessage == "Alıcı algılanmadı"
        assert view_model._probe_error_timer.isActive()

        view_model._clear_missing_receiver_error()
        assert view_model.sourceState == "Kullanılmıyor"
        assert view_model.errorMessage == ""
        assert view_model.statusMessage == "Alıcı bağlantısı bekleniyor."
    finally:
        view_model.shutdown()


def test_fpga_service_failure_blocks_ready_state_and_returns_to_waiting() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["missing-fpga-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        fpga_transport_factory=_FPGAMissingTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert not view_model.hackrfReady
        assert view_model.sourceState == "Hata"
        assert view_model.errorTitle == "FPGA algılanmadı"
        assert view_model.errorMessage == "FPGA algılanmadı"
        assert view_model._probe_error_timer.isActive()

        view_model._clear_missing_receiver_error()
        assert view_model.sourceState == "Kullanılmıyor"
        assert view_model.errorMessage == ""
    finally:
        view_model.shutdown()


def test_receiver_and_fpga_failures_are_reported_together() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["missing-receiver-and-fpga-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_ToolsUnavailableBackend(),
        fpga_transport_factory=_FPGAMissingTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)

        assert not view_model.hackrfReady
        assert view_model.sourceState == "Hata"
        assert view_model.errorTitle == "FPGA ve Alıcı algılanamadı"
        assert view_model.errorMessage == "FPGA ve Alıcı algılanamadı"
        assert view_model._probe_error_timer.isActive()
    finally:
        view_model.shutdown()


def test_live_pipeline_locations_match_display_without_claiming_an_active_device() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-pipeline-test"])
    view_model = OperatorViewModel(acquisition_backend=_Backend(), developer_mode=True)
    root = Path(__file__).resolve().parents[1]
    try:
        view_model.setSourceMode("hackrf")
        blocks = {item["id"]: item for item in view_model.pipelineBlocks}
        assert blocks["regional"]["state"] == "Kullanılmıyor"
        assert blocks["regional"]["hardwareStatus"] == "Bu oturumda kart yanıtı yok"
        assert not view_model.sourceReady
        for block in blocks.values():
            for key in ("hostPath", "rtlPath"):
                if block[key]:
                    assert (root / block[key]).is_file()
        with patch("app.operator_console.quick_view_model.QDesktopServices.openUrl", return_value=True) as opened:
            for component, target in (("source", "host"), ("regional", "rtl"), ("temporal", "rtl")):
                assert view_model.openImplementationLocation(component, target)
                assert Path(opened.call_args.args[0].toLocalFile()) == root / blocks[component][target + "Path"]
        view_model.setSourceMode("sigmf")
        restored = {item["id"]: item for item in view_model.pipelineBlocks}
        assert restored["regional"]["runtime"] == "HOST"
        assert restored["regional"]["rtlPath"].endswith("axis_regional_detector.sv")
    finally:
        view_model.shutdown()


def _event(event_id, *, state="confirmed", observed=True, peak=2205):
    return LiveEDEvent(event_id, 0, 3, 4, state, observed, peak - 2, peak + 2, peak, 5, 1, 0, 100.0, 1.0, 10.0)


@pytest.fixture
def live_presentation():
    app = QGuiApplication.instance() or QGuiApplication(["presentation-test"])
    view = OperatorViewModel(acquisition_backend=_Backend())
    view.setSourceMode("hackrf")
    view._live_output_center_frequency_hz = 104_650_000
    view._live_sample_rate_hz = 2_000_000
    view._receiver_sample_rate_hz = 8_000_000
    view._live_session = _BlockingSession("", None)
    view._live_has_data = True
    view._active_receiver_serial = SERIAL
    yield view
    view.shutdown()


def test_live_sample_rate_presentation_shows_receiver_rate(live_presentation) -> None:
    view = live_presentation
    view._spectrum_sample_rate_hz = 8_000_000
    assert view.sampleRateTitle == "ÖRNEKLEME HIZI"
    assert view.sampleRateText == "8 MS/s"
    view._spectrum_sample_rate_hz = 2_000_000
    assert view.sampleRateText == "8 MS/s"
    assert view.sampleRateHz == 2_000_000


def test_receiver_audio_settings_reject_active_sessions_and_invalid_values(live_presentation):
    view = live_presentation
    assert not view.setReceiverAndAudioSettings(True, 0.0)
    assert not view.receiverRFAmplifier
    view._live_session = None
    for value in (-1, 2001, float("nan"), float("inf"), True, "750"):
        assert not view.setReceiverAndAudioSettings(True, value)
    assert not view.setReceiverAndAudioSettings(1, 750.0)
    assert view.setReceiverAndAudioSettings(True, 0.0)
    assert view.receiverRFAmplifier
    assert view.listeningDeemphasisUs == 0.0
    assert not view._live_has_data
    assert view.setReceiverAndAudioSettings(False, 750.0)


def test_live_configuration_preserves_amp_and_rejects_non_boolean():
    config = LiveEDConfiguration(104_650_000, SERIAL, rf_amplifier=True)
    assert config.rx_config.rf_amplifier is True
    with pytest.raises(AcquisitionError):
        LiveEDConfiguration(104_650_000, SERIAL, rf_amplifier=1)


def _present(view, frame_id, *events):
    coarse_candidates = []
    spacing = 2_000_000.0 / 4096.0
    center = float(view._live_output_center_frequency_hz)
    for event in events:
        if event.state != "confirmed" or not event.observed_this_frame:
            continue
        coarse_candidates.append(CoarseDetection(
            int(event.event_id),
            "confirmed",
            True,
            center + (event.start_shifted_bin - 2048) * spacing,
            center + (event.end_shifted_bin - 2048) * spacing,
            center + (event.peak_shifted_bin - 2048) * spacing,
            event.peak_to_noise_db,
        ))
    view._coarse_detection_frame = CoarseDetectionFrame(
        frame_id,
        center,
        8_000_000.0,
        tuple(coarse_candidates),
    )
    view._coarse_detection_sequence = frame_id
    view._frame_index = frame_id
    view._update_live_detections(LiveEDResponse(frame_id, len(events), 7, 0, False, 0, events, (), 0))


def test_live_list_only_keeps_confirmed_frequency_observations(live_presentation):
    view = live_presentation
    _present(view, 0, _event(1), _event(2, state="tentative"), _event(3, observed=False))
    assert [row["eventId"] for row in view.detections] == [1]
    view.setShowLiveCandidates(True)
    assert [row["eventId"] for row in view.detections] == [1]
    assert [row["eventId"] for row in view.detectionMarkers] == [1]
    view.setShowLiveCandidates(False)
    assert [row["eventId"] for row in view.detections] == [1]


def test_live_list_orders_new_confirmed_signals_by_contrast(live_presentation):
    view = live_presentation
    weak = replace(_event(1, peak=2205), peak_power=10.0, noise_power=1.0)
    strong = replace(_event(2, peak=2405), peak_power=1000.0, noise_power=1.0)
    _present(view, 0, weak, strong)
    assert [row["eventId"] for row in view.detections] == [2, 1]
    assert view.detections[0]["state"] == "Kararlılık ölçülüyor"
    assert view.detections[0]["title"] == "FPGA adayı"


def test_wide_supported_live_candidate_keeps_a_bounded_analysis_draft(live_presentation):
    view = live_presentation
    event = replace(
        _event(71, peak=2045),
        start_shifted_bin=1800,
        end_shifted_bin=2290,
        coarse_span_bins=491,
    )
    _present(view, 0, event)
    view.selectDetection(71)

    assert view._analysis_span_draft is not None
    lower, upper = view._analysis_span_draft
    assert upper - lower + 1 == 619
    assert lower <= event.start_shifted_bin <= event.peak_shifted_bin
    assert event.peak_shifted_bin <= event.end_shifted_bin <= upper
    assert not view.analysisSpanLimited


def test_oversized_live_candidate_gets_direct_bounded_confirmation(live_presentation):
    view = live_presentation
    event = replace(
        _event(72, peak=2280),
        start_shifted_bin=1500,
        end_shifted_bin=3000,
        coarse_span_bins=1501,
    )
    _present(view, 0, event)
    view.selectDetection(72)

    assert view._analysis_span_draft is not None
    lower, upper = view._analysis_span_draft
    assert upper - lower + 1 == 1629
    assert lower <= event.peak_shifted_bin <= upper
    assert lower <= event.start_shifted_bin <= event.end_shifted_bin <= upper
    assert not view.analysisSpanLimited
    view._live_session.measurement_window = lambda event_id: (None,) * 4
    view.confirmAnalysisSpan(float(view.analysisLowerMHzText), float(view.analysisUpperMHzText))
    assert view.analysisSpanConfirmed, view.statusMessage
    assert view._analysis_span.width_bins == 1629


def test_live_presentation_excludes_channelizer_transition_band(live_presentation):
    view = live_presentation
    _present(
        view,
        0,
        _event(1, peak=2048),
        _event(2, peak=3648),
        _event(3, peak=256),
    )
    assert [row["eventId"] for row in view.detections] == [1]


def test_selected_row_migrates_by_channel_without_extending_detector_lifetime(live_presentation):
    view = live_presentation
    _present(view, 0, _event(4430))
    view.selectDetection(4430)
    coordinate = view.selectedRegionPeakNormalized
    assert view.selectedDetectionCurrent
    # The UI follows the unique same-channel successor while the detector keeps
    # its independent event identity and lifetime.
    _present(view, 16, _event(4431))
    assert view.selectedDetectionId == 4431
    assert view.selectedRegionPeakNormalized == coordinate
    assert view.selectedDetectionCurrent
    assert view.selectedDetectionReady
    assert [row["eventId"] for row in view.detectionMarkers] == [4431]
    assert [row["eventId"] for row in view.detections] == [4431]
    _present(view, 256)
    assert [row["eventId"] for row in view.detections] == [4431]
    assert view.selectedDetectionId == 4431
    assert not view.selectedDetectionCurrent
    assert not view.selectedDetectionReady


def test_presentation_pacing_and_same_event_selection_follow_observations(live_presentation):
    view = live_presentation
    _present(view, 0, _event(1))
    view.selectDetection(1)
    _present(view, 16, _event(2))
    assert [row["eventId"] for row in view.detections] == [2]
    assert view.selectedDetectionId == 2
    assert view.selectedDetectionCurrent
    _present(view, 32, _event(1, peak=2210))
    assert view.selectedDetectionCurrent
    assert view.selectedRegionPeakNormalized == pytest.approx(2210 / 4096)
    mapped_hz = view.centerFrequencyHz + (view.selectedRegionPeakNormalized - .5) * view.sampleRateHz
    expected_hz = view.centerFrequencyHz + (2210 - 2048) * view.sampleRateHz / 4096
    assert mapped_hz == pytest.approx(expected_hz)
    _present(view, 112, _event(2))
    assert [row["eventId"] for row in view.detections] == [2]
    assert view.selectedDetectionId == 2
    assert view.selectedDetectionCurrent
    assert not view._event_observation_history


def test_completed_capture_is_not_presented_as_current_rx(live_presentation):
    view = live_presentation
    _present(view, 0, _event(1))
    view.selectDetection(1)
    view._live_session = None
    view._refresh_live_detection_list(force=True)
    assert view.selectedDetectionStateText == "Alım durdu"
    assert not view.selectedDetectionCurrent
    assert not view.detectionMarkers
    assert len(view.detections) == 1
    assert view.detections[0]["state"] == "Son görüldü"


def test_same_frequency_is_retained_once_across_new_fpga_event_ids(live_presentation):
    view = live_presentation
    _present(view, 0, _event(101, peak=2205))
    first_key = view.detections[0]["rowKey"]
    _present(view, 16, _event(102, peak=2205))
    assert len(view.detections) == 1
    assert view.detections[0]["eventId"] == 102
    assert view.detections[0]["rowKey"] == first_key
    assert view.detections[0]["observationCount"] == 2
    _present(view, 32)
    assert len(view.detections) == 1
    assert view.detections[0]["state"] == "Kısa süreli izleniyor"
    assert view.detections[0]["held"]
    _present(view, 176)
    assert view.detections[0]["state"] == "Son görüldü"
    _present(view, 48, _event(103, peak=2505))
    assert len(view.detections) == 2


def test_fixed_detection_cards_keep_position_and_display_frequency(live_presentation):
    view = live_presentation
    _present(view, 0, _event(401, peak=2205))
    first_key = view.detections[0]["rowKey"]
    first_frequency = view.detections[0]["frequency"]

    _present(view, 16, _event(402, peak=2240))
    assert view.detections[0]["rowKey"] == first_key
    assert view.detections[0]["frequency"] == first_frequency

    stronger = replace(_event(403, peak=2505), peak_power=1_000.0, noise_power=1.0)
    _present(view, 32, _event(404, peak=2240), stronger)
    assert [row["rowKey"] for row in view.detections] == [first_key, "frequency-2"]


def test_live_listening_target_stays_latched_across_event_id_migration(live_presentation):
    view = live_presentation
    _present(view, 0, _event(201, peak=2205))
    view.selectDetection(201)
    target_hz = view._listening_channel_target_hz()

    _present(view, 16, _event(202, peak=2300))

    assert view.selectedDetectionId == 202
    assert view._listening_channel_target_hz() == target_hz


def test_peak_wander_is_one_operator_visible_emission(live_presentation):
    view = live_presentation
    weak = replace(_event(201, peak=2205), peak_power=25.0, noise_power=1.0)
    strong = replace(_event(202, peak=2250), peak_power=400.0, noise_power=1.0)
    _present(view, 0, weak, strong)
    assert view.activeDetectionCount == 1
    assert len(view.detectionMarkers) == 1
    assert len(view.detections) == 1
    assert view.detections[0]["eventId"] == 202
    assert view.detections[0]["componentCount"] == 2


def test_stale_history_does_not_count_as_a_live_detection(live_presentation):
    view = live_presentation
    _present(view, 0, _event(301))
    assert view.activeDetectionCount == 1
    _present(view, 16)
    assert view.activeDetectionCount == 0
    assert not view.detectionMarkers
    assert len(view.detections) == 1
    assert view.detections[0]["state"] == "Kısa süreli izleniyor"
    assert not view.detections[0]["historyBoundary"]
    _present(view, 144)
    assert view.activeDetectionCount == 0
    assert len(view.detections) == 1
    assert not view.detections[0]["historyBoundary"]


def test_confirmed_host_candidate_is_not_presented_without_fpga_agreement(live_presentation):
    view = live_presentation
    view._coarse_detection_frame = CoarseDetectionFrame(
        7,
        104_650_000.0,
        8_000_000.0,
        (CoarseDetection(9, "confirmed", True, 104_700_000.0, 104_730_000.0, 104_715_000.0, 18.0),),
    )
    assert not view.detectionMarkers
    assert not view.hasCoarseCandidateAwaitingFpga
    assert not view.coarseDetectionMarkers


def test_intermittent_fpga_event_is_not_presented_as_stable_broadcast(live_presentation):
    view = live_presentation
    intermittent = replace(
        _event(390),
        first_frame_id=0,
        last_seen_frame_id=127,
        seen_count=16,
    )

    _present(view, 127, intermittent)

    assert not view.detections
    assert not view.detectionMarkers
    assert view._fixed_verification_candidate is None


def test_persistent_same_iq_fpga_and_rx_agreement_stays_an_unverified_candidate(live_presentation):
    view = live_presentation
    persistent = replace(
        _event(391),
        first_frame_id=0,
        last_seen_frame_id=127,
        seen_count=120,
    )

    _present(view, 127, persistent)

    assert view.stableDetectionCount == 0
    assert view.detectionMarkers[0]["verificationKey"] == "rx_supported"
    assert view.detections[0]["state"] == "Alımda güçlü aday görüldü; yeniden ölçün."
    assert view.detections[0]["title"] == "FPGA adayı"
    assert view._fixed_verification_candidate is None
    assert view._live_session is not None


def test_only_two_lo_record_promotes_fpga_candidate_to_stable(live_presentation):
    view = live_presentation
    event = _event(401)
    frequency_hz = 104_650_000 + (event.peak_shifted_bin - 2048) * 2_000_000 / 4096
    view._fixed_verification_records[1] = {
        "frequency_hz": frequency_hz,
        "state": "verified_two_lo",
        "source": "fpga",
        "result": None,
    }
    _present(view, 0, event)
    assert view.stableDetectionCount == 1
    assert view.detectionMarkers[0]["verificationKey"] == "verified_two_lo"
    assert view.detections[0]["state"] == "Aynı frekans tekrar görüldü; önce bunu inceleyin."
    assert view.detections[0]["title"] == "Kararlı RF adayı"


def test_live_spur_guard_revokes_stale_verification_and_rearms_on_rf_shoulders(
    live_presentation,
):
    view = live_presentation
    spur_hz = 1_000_000_000
    view._known_spurs_hz = (spur_hz,)
    view._fixed_verification_records[1] = {
        "frequency_hz": float(spur_hz),
        "state": "verified_two_lo",
        "source": "fpga",
        "result": None,
    }
    frequencies = np.linspace(996_000_000.0, 1_004_000_000.0, 16_384, endpoint=False)
    quiet_power = np.ones(frequencies.size, dtype=np.float64)

    def spectrum(power):
        return SimpleNamespace(
            center_frequency_hz=1_000_000_000.0,
            sample_rate_hz=8_000_000.0,
            display=SimpleNamespace(
                bin_power_fs2=power,
                frequency_absolute_hz=frequencies,
            ),
        )

    for _ in range(8):
        view._update_live_spur_guard(spectrum(quiet_power))
    assert view._fixed_verification_records[1]["state"] == "live_guard_failed"

    shoulder_power = quiet_power.copy()
    offsets = np.abs(frequencies - spur_hz)
    shoulder_power[(offsets >= 2_000.0) & (offsets <= 25_000.0)] = 10.0
    for _ in range(8):
        view._update_live_spur_guard(spectrum(shoulder_power))
    assert not view._fixed_verification_records


def test_coarse_candidate_outside_fixed_detection_band_is_not_presented_or_verified(
    live_presentation,
):
    view = live_presentation
    frame = CoarseDetectionFrame(
        8,
        104_650_000.0,
        8_000_000.0,
        (CoarseDetection(10, "confirmed", True, 106_040_000.0, 106_080_000.0, 106_060_000.0, 21.0),),
    )
    view._coarse_detection_frame = frame

    assert not view.coarseDetectionMarkers
    assert not view.hasCoarseCandidateAwaitingFpga
    view._maybe_verify_coarse_candidate(frame)
    assert view._fixed_verification_candidate is None
    assert not view._fixed_verification_queue


def test_multiple_coarse_candidates_are_retained_for_serial_verification(live_presentation):
    view = live_presentation
    view._hackrf_ready = True
    view._hackrf_transfer_executable = "hackrf_transfer"
    frame = CoarseDetectionFrame(
        9,
        104_650_000.0,
        8_000_000.0,
        (
            CoarseDetection(11, "confirmed", True, 104_690_000.0, 104_710_000.0, 104_700_000.0, 24.0),
            CoarseDetection(12, "confirmed", True, 104_880_000.0, 104_900_000.0, 104_890_000.0, 21.0),
        ),
    )

    view._maybe_verify_coarse_candidate(frame)

    assert view._fixed_verification_candidate is not None
    assert view._fixed_verification_candidate.frequency_hz == 104_700_000.0
    assert [item.frequency_hz for item in view._fixed_verification_queue] == [104_890_000.0]

    view._fixed_verification_candidate = None
    view._fixed_verifier = None
    view._start_next_fixed_verification()
    assert view._fixed_verification_candidate is not None
    assert view._fixed_verification_candidate.frequency_hz == 104_890_000.0
    assert not view._fixed_verification_queue


def test_high_resolution_fpga_fft_does_not_start_4096_only_fixed_verification(
    live_presentation,
):
    view = live_presentation
    view._live_session.configuration = SimpleNamespace(fpga_fft_size=8192)
    view._offer_fixed_verification_candidates([
        FixedBandCandidate(104_700_000.0, 104_700_000.0, 104_690_000.0,
                           104_710_000.0, 24.0, "fpga")
    ])

    assert view._fixed_verification_candidate is None
    assert not view._fixed_verification_queue


def test_clear_resets_retained_rows_and_selection(live_presentation):
    view = live_presentation
    _present(view, 0, _event(1))
    view.selectDetection(1)
    view._clear_results()
    assert view.detectionModel.rowCount() == 0
    assert not view.detections
    assert not view.detectionMarkers
    assert view.selectedDetectionId == -1


def test_keyed_model_preserves_delegate_identity_during_update_and_reorder():
    app = QGuiApplication.instance() or QGuiApplication(["keyed-model-test"])
    model = DetectionListModel()
    resets = QSignalSpy(model.modelReset)
    model.set_rows([{"eventId": 1, "value": 1}, {"eventId": 2, "value": 2}])
    retained = QPersistentModelIndex(model.index(0))
    model.set_rows([{"eventId": 2, "value": 3}, {"eventId": 1, "value": 4}, {"eventId": 3}])
    assert retained.isValid() and retained.row() == 1
    assert retained.data(model.RowRole) == {"eventId": 1, "value": 4}
    model.set_rows([{"eventId": 1, "value": 5}])
    assert retained.isValid() and retained.row() == 0
    assert resets.count() == 0
    with pytest.raises(ValueError):
        model.set_rows([{"eventId": 1}, {"eventId": 1}])


def test_operator_can_cancel_live_session_without_false_error_state() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-cancel-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_BlockingSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    view_model.setSourceMode("hackrf")
    view_model.probeHackrf()
    _drain(app, lambda: view_model.busy)
    view_model.startLiveEDSession(104_650_000, 16, 16, 4)
    assert view_model.liveSessionActive

    view_model.stopLiveEDSession()
    _drain(app, lambda: view_model.busy)

    assert not view_model.busy
    assert not view_model.liveSessionActive
    assert not view_model.sourceReady
    assert view_model.sourceState == "Kullanılmıyor"
    assert view_model.errorMessage == ""
    assert view_model.statusMessage == "Canlı ED oturumu operatör tarafından durduruldu."
    view_model.shutdown()


def test_operator_stop_cancels_pending_fixed_verification_instead_of_retuning(
    live_presentation,
) -> None:
    view = live_presentation
    candidate = SimpleNamespace(frequency_hz=104_700_000.0)

    class _Verifier:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    verifier = _Verifier()
    view._fixed_verification_candidate = candidate
    view._fixed_verifier = verifier
    generation = view._generation

    view.stopLiveEDSession()
    view._live_failed(generation, "operation_cancelled", "stopped")

    assert verifier.cancelled
    assert view._fixed_verification_candidate is None
    assert view._fixed_verifier is None
    assert view._active_task_kind != "fixed_verify"
    assert view.statusMessage == "Canlı ED oturumu operatör tarafından durduruldu."


def test_manual_restart_keeps_same_setting_verification_records_but_gain_change_clears_them() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["fixed-restart-context-test"])
    view = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_BlockingSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        view._fixed_verification_records[1] = {
            "frequency_hz": 104_700_000.0,
            "state": "verified_two_lo",
            "source": "fpga",
            "result": None,
        }
        view._spectrum_values = [-82.0, -71.0]
        view._spectral_display.append(
            np.asarray([-82.0, -71.0]),
            timestamp=0.0,
            binding=("hackrf", 103_150_000.0, 8_000_000.0, 16, 16),
        )

        view.startLiveEDSession(104_650_000, 16, 16, 4)
        assert view._fixed_verification_records
        assert view.spectrumValues == [-82.0, -71.0]
        assert view.spectralDisplay.count == 1
        view.stopLiveEDSession()
        _drain(app, lambda: view.busy)

        view.startLiveEDSession(104_650_000, 24, 16, 4)
        assert not view._fixed_verification_records
        assert not view.spectrumValues
        assert view.spectralDisplay.count == 0
        view.stopLiveEDSession()
        _drain(app, lambda: view.busy)
    finally:
        view.shutdown()


def test_fpga_connection_failure_revokes_combined_receiver_readiness() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["fpga-readiness-revocation-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_ConnectionFailedSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert view_model.hackrfReady

        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy)

        assert not view_model.hackrfReady
        assert view_model._hackrf_transfer_executable == ""
        assert view_model.sourceState == "Hata"
        assert view_model.errorTitle == "FPGA algılanmadı"
        assert view_model.errorMessage == "FPGA algılanmadı"
    finally:
        view_model.shutdown()


def test_binary_pipe_failure_is_reported_as_receiver_disconnect_and_revokes_ready() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["receiver-disconnect-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_BinaryPipeFailedSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert view_model.hackrfReady

        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy)

        assert not view_model.hackrfReady
        assert view_model._active_receiver_serial is None
        assert view_model.errorTitle == "Alıcı bağlantısı koptu"
        assert view_model.errorMessage == (
            "Alıcı HackRF USB modunda görünmüyor. Sistemi Denetle ile yeniden bağlanın."
        )
    finally:
        view_model.shutdown()


def test_idle_receiver_health_check_detects_usb_mode_loss() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["receiver-health-test"])
    backend = _DisconnectableBackend()
    view_model = OperatorViewModel(
        acquisition_backend=backend,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert view_model.hackrfReady
        assert view_model._receiver_health_timer.isActive()

        backend.connected = False
        view_model._poll_receiver_health()
        _drain(app, lambda: view_model._receiver_health_in_flight)

        assert not view_model.hackrfReady
        assert not view_model._receiver_health_timer.isActive()
        assert view_model.errorTitle == "Alıcı bağlantısı koptu"
    finally:
        view_model.shutdown()


def test_inconclusive_idle_receiver_health_check_preserves_ready_state() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["receiver-health-indeterminate-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model._receiver_health_completed(
            view_model._generation,
            "receiver_health",
            DeviceStatus("DEVICE_ERROR", reason_code="device_probe_failed"),
            0.01,
        )
        assert view_model.hackrfReady
        assert view_model.errorTitle == ""
    finally:
        view_model.shutdown()


def test_scan_start_waits_for_inflight_receiver_health_check() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["receiver-health-start-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_BlockingSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model._receiver_health_in_flight = True
        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        assert not view_model.liveSessionActive

        view_model._receiver_health_in_flight = False
        _drain(app, lambda: not view_model.liveSessionActive)
        assert view_model.liveSessionActive
        view_model.stopLiveEDSession()
        _drain(app, lambda: view_model.busy)
    finally:
        view_model.shutdown()


def test_band_survey_start_waits_for_inflight_receiver_health_check() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["receiver-health-survey-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        with patch.object(view_model._survey_controller, "start") as start:
            view_model._receiver_health_in_flight = True
            view_model.startSurveyProfile(100, 102, 16, 16, "wideband_burst")
            assert not start.called

            view_model._receiver_health_in_flight = False
            _drain(app, lambda: not start.called)
            assert start.called
    finally:
        view_model.shutdown()


def test_candidate_capacity_error_keeps_connected_hardware_ready() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["candidate-capacity-readiness-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        assert view_model.hackrfReady

        detail = (
            "FPGA tespit kapasitesi aşıldı: kare 72, ham aday 91, etkin olay 64, "
            "izlemeye alınamayan aday 4. Bu bağlantı hatası değildir. "
            "LNA/VGA kazançlarını azaltıp yeniden deneyin."
        )
        view_model._live_failed(view_model._generation, "candidate_drop", detail)

        assert view_model.hackrfReady
        assert view_model._hackrf_transfer_executable
        assert view_model.errorTitle == "FPGA tespit kapasitesi aşıldı"
        assert view_model.errorMessage == detail
    finally:
        view_model.shutdown()


def test_long_capture_error_explains_receiver_and_display_length_mismatch() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["long-capture-message-test"])
    view_model = OperatorViewModel()
    try:
        view_model._show_error(
            "long_capture", "HackRF capture beklenen uzunluktan uzun."
        )

        assert view_model.errorTitle == "Alıcı veri boyu uyuşmadı"
        assert "görüntü işleme örnek boyları uyuşmadı" in view_model.errorMessage
        assert "karttan FFT ayarını yeniden okuyun" in view_model.errorMessage
        assert "Sistemi Denetle" in view_model.errorMessage
    finally:
        view_model.shutdown()


def test_local_dma_failure_is_presented_as_an_fft_card_mismatch() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["local-dma-message-test"])
    view_model = OperatorViewModel()
    try:
        view_model._show_error("local_dma_failure", "FPGA DMA işlemi tamamlanamadı.")

        assert view_model.errorTitle == "FFT ayarı kartla uyuşmuyor"
        assert "Karttan FFT ayarını yeniden okuyup" in view_model.errorMessage
        assert "local_dma_failure" not in view_model.errorMessage
    finally:
        view_model.shutdown()


def test_live_detection_measurement_uses_four_consecutive_fpga_frames(tmp_path) -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-measurement-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path,
    )
    board_patch = patch("app.operator_console.measurement_record.measure_on_board",
                        side_effect=_fake_board_parameter_measurement)
    board_patch.start()
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            view_model.startLiveEDSession(104_650_000, 0, 0, 4_096)
            _drain(app, lambda: not view_model.detections)
        assert view_model.liveSessionActive
        _drain(
            app,
            lambda: not any(
                int(row["eventId"]) == 31 and bool(row["observed"])
                for row in view_model.detections
            ),
        )
        view_model.selectDetection(31)
        assert view_model.selectedDetectionReady
        current_measurement_window = view_model._live_session.current_measurement_window
        _present(view_model, 200, _event(99, peak=2800))
        view_model._live_session.current_measurement_window = lambda event_id: ()
        assert not view_model.selectedDetectionCurrent
        assert not view_model.selectedDetectionReady
        assert view_model.measurementSelectionReady
        view_model.requestMeasurement()
        assert view_model._pending_live_measurement is None
        assert not view_model.parameterRows
        view_model._live_session.current_measurement_window = current_measurement_window
        _present(view_model, 201, _event(31))
        assert view_model.measurementSelectionReady
        original_configuration = view_model._live_session.configuration
        view_model._live_session.configuration = replace(
            original_configuration, fpga_fft_size=8192)
        assert not view_model.measurementSelectionReady
        view_model._live_session.configuration = original_configuration
        view_model._analysis_span_draft = None
        view_model._prepare_analysis_span_draft(31)
        assert view_model.analysisLowerMHzText
        view_model.confirmAnalysisSpan(
            float(view_model.analysisLowerMHzText),
            float(view_model.analysisUpperMHzText),
        )
        assert view_model.measurementReady

        session = view_model._live_session
        # The selected cache remains at 0..3; a new measurement must use 10..13.
        previous_span = (
            view_model._analysis_span.lower_shifted_bin,
            view_model._analysis_span.upper_shifted_bin,
        )
        session.window = tuple(replace(item, sequence_number=index + 10,
            output_frame=replace(item.output_frame, sequence_number=index + 10, frame_id=index + 10),
            response=replace(
                item.response,
                frame_id=index + 10,
                active=(replace(
                    item.response.active[0],
                    start_shifted_bin=previous_span[0] - 12,
                    end_shifted_bin=previous_span[1] + 9,
                    last_seen_frame_id=index + 10,
                ),),
            ))
            for index, item in enumerate(session.window))
        view_model.requestMeasurement()
        _drain(app, lambda: not view_model.parameterRows and not view_model.errorMessage)

        assert not view_model.liveSessionActive
        assert not view_model.busy
        assert view_model.errorMessage == ""
        assert len(view_model.parameterRows) == 15
        estimated = next(row for row in view_model.parameterRows if row["key"] == "estimated_power_dbm")
        assert estimated["label"] == "Tahmini Güç (dBm)"
        assert estimated["state"] == "estimated"
        assert "dBm" in estimated["value"] and "±" in estimated["value"]
        quality_rows = {row["key"]: row for row in view_model.parameterRows}
        assert quality_rows["measurement_quality"]["label"] == "Kart ölçüm kalite kapısı"
        assert quality_rows["measurement_quality"]["value"] == "Geçti · 4/4 kare"
        assert quality_rows["measurement_quality"]["state"] == "valid"
        assert quality_rows["reference_difference_db"]["value"].endswith(" dB")
        assert quality_rows["center_uncertainty_bins"]["value"].endswith(" hücre")
        assert quality_rows["temporal_edge_range_bins"]["value"].endswith(" hücre")
        assert "parametre ölçümü tamamlandı" in view_model.statusMessage
        from app.operator_console.measurement_record import read_measurement, replay_measurement
        path = Path(view_model.measurementRecordPath)
        assert path.parent == tmp_path
        document, _ = read_measurement(path)
        assert document["intent"]["span"]["provenance"] == "automatic_live_expansion"
        assert document["intent"]["span"]["lower_shifted_bin"] == previous_span[0] - 12
        assert document["intent"]["span"]["upper_shifted_bin"] == previous_span[1] + 9
        assert document["source"]["receiver_settings"]["lna_gain_db"] == 0
        assert document["source"]["sequence_numbers"] == [10, 11, 12, 13]
        assert document["source"]["board_identity"] is None
        assert document["source"]["channelizer"] is None
        assert document["source"]["upstream_amplitude_scale"] is None
        assert document["source"]["transport_iq_sha256"]
        assert replay_measurement(path).intent.event_id == 31
        assert view_model.measurementInfo["durationMs"] == 8.192
        assert view_model.measurementInfo["completedUtc"] == document["completed_utc"]
        assert view_model.listeningSuggestedOffsetKHz == 0.0
        assert view_model.listeningSuggestedBandwidthKHz == 12.0
        assert "Parametre ölçümü" in view_model.listeningParameterBasisText
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            assert view_model.restartParameterAcquisition()
            assert not view_model.parameterRows
            assert not view_model.measurementInfo
            assert not view_model.measurementRecordPath
            assert view_model.selectedDetectionId == -1
            assert not view_model.analysisSpanConfirmed
            _drain(app, lambda: not any(row["eventId"] == 31 and row["observed"] for row in view_model.detections))
        view_model.selectDetection(31)
        view_model.confirmAnalysisSpan(float(view_model.analysisLowerMHzText), float(view_model.analysisUpperMHzText))
        view_model.confirmAnalysisSpan(float("nan"), float("nan"))
        assert not view_model.analysisSpanConfirmed
        assert not view_model.measurementReady
        view_model.confirmAnalysisSpan(float(view_model.analysisLowerMHzText), float(view_model.analysisUpperMHzText))
        view_model.requestMeasurement()
        _drain(app, lambda: not view_model.parameterRows and not view_model.errorMessage)
        assert view_model.parameterRows
        assert Path(view_model.measurementRecordPath) != path
        assert path.exists() and len(list(tmp_path.glob("*.zip"))) == 2
    finally:
        board_patch.stop()
        view_model.shutdown()


def test_parameter_handoff_reacquires_and_revalidates_listening_target() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["parameter-listening-handoff-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model._listening_parameter_target_hz = 104_726_660.15625
        view_model._listening_parameter_bandwidth_khz = 12.0
        view_model._listening_parameter_record_path = "measurement.zip"

        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            assert view_model.continueToListening()
            _drain(app, lambda: view_model.selectedDetectionId < 0)

        assert view_model.liveSessionActive
        assert view_model.selectedDetectionId == 31
        assert view_model.selectedDetectionReady
        assert view_model._pending_listening_frequency_hz is None
        assert view_model.listeningSuggestedOffsetKHz == pytest.approx(76.66015625)
        assert view_model.listeningSuggestedBandwidthKHz == 12.0
        assert "Parametre ölçümü" in view_model.listeningParameterBasisText
    finally:
        view_model.shutdown()


def test_parameter_handoff_waits_for_receiver_health_check() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["parameter-listening-health-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model._listening_parameter_target_hz = 104_726_660.15625
        view_model._listening_parameter_bandwidth_khz = 12.0
        view_model._listening_parameter_record_path = "measurement.zip"
        view_model._receiver_health_in_flight = True

        assert view_model.continueToListening()
        assert not view_model.liveSessionActive
        assert "otomatik başlayacak" in view_model.listeningState
        assert view_model._listening_parameter_target_hz == pytest.approx(104_726_660.15625)

        view_model._receiver_health_in_flight = False
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            _drain(app, lambda: not view_model.liveSessionActive)
            _drain(app, lambda: view_model.selectedDetectionId < 0)
        assert view_model.liveSessionActive
        assert view_model.selectedDetectionId == 31
    finally:
        view_model.shutdown()


class _DirectionSession(_MeasurementSession):
    """Use the production collector with post-request responses and changing IDs."""

    def __init__(self, executable, configuration):
        super().__init__(executable, configuration)
        from app.operator_console.live_ed import LiveEDSession
        self.collector = LiveEDSession(executable, configuration)
        self._direction_after_sequence = -1
        self._direction_require_observed_target = True

    def begin_direction_capture(self, lower, upper, require_observed_target=True):
        self._direction_require_observed_target = require_observed_target
        self.collector.begin_direction_capture(
            lower, upper, require_observed_target=require_observed_target
        )
        self._direction_after_sequence = self.collector._direction_after_sequence

    def current_measurement_window(self, event_id):
        return ()  # The operator must not need to catch an instantaneous window.

    def direction_capture(self):
        for index, snapshot in enumerate(self.window, start=10):
            event = replace(snapshot.response.active[0], event_id=100 + index,
                            last_seen_frame_id=index)
            active = (event,) if self._direction_require_observed_target else ()
            self.collector._record_measurement_snapshot(replace(
                snapshot, sequence_number=index,
                output_frame=replace(snapshot.output_frame, sequence_number=index, frame_id=index),
                response=replace(snapshot.response, frame_id=index, active=active)))
        return self.collector.direction_capture()

    def cancel_direction_capture(self):
        self.collector.cancel_direction_capture()

    @staticmethod
    def direction_channel_owner(snapshot, lower, upper):
        from app.operator_console.live_ed import LiveEDSession
        return LiveEDSession.direction_channel_owner(snapshot, lower, upper)


class _ParameterChannelSession(_MeasurementSession):
    """Return a fresh channel-bound window whose FPGA event ID changes."""

    def __init__(self, executable, configuration):
        super().__init__(executable, configuration)
        from app.operator_console.live_ed import LiveEDSession
        self.collector = LiveEDSession(executable, configuration)
        self._parameter_after_sequence = -1

    def begin_parameter_capture(self, lower, upper):
        self.collector.begin_parameter_capture(lower, upper)
        self._parameter_after_sequence = self.collector._parameter_after_sequence

    def current_measurement_window(self, event_id):
        return ()

    def parameter_capture(self):
        for index, snapshot in enumerate(self.window, start=10):
            event = replace(
                snapshot.response.active[0],
                event_id=100 + index,
                last_seen_frame_id=index,
            )
            self.collector._record_measurement_snapshot(replace(
                snapshot,
                sequence_number=index,
                output_frame=replace(
                    snapshot.output_frame, sequence_number=index, frame_id=index
                ),
                response=replace(snapshot.response, frame_id=index, active=(event,)),
            ))
        return self.collector.parameter_capture()

    def cancel_parameter_capture(self):
        self.collector.cancel_parameter_capture()

    @staticmethod
    def direction_channel_owner(snapshot, lower, upper):
        from app.operator_console.live_ed import LiveEDSession
        return LiveEDSession.direction_channel_owner(snapshot, lower, upper)


@pytest.mark.parametrize("frame_count", [4, 16])
def test_live_parameter_measurement_survives_fpga_event_id_churn(tmp_path, frame_count) -> None:
    class ParameterSession(_ParameterChannelSession):
        parameter_measurement_frame_count = frame_count

        def __init__(self, executable, configuration):
            super().__init__(executable, configuration)
            from algorithms.p0 import TransportCapabilities
            self.collector._transport._capabilities = TransportCapabilities(extended_parameter=frame_count == 16)
            self.window = self.window * (frame_count // 4)

        def measurement_window(self, event_id):
            return self.window[-4:] if event_id == 31 else ()

    app = QGuiApplication.instance() or QGuiApplication(["parameter-channel-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=ParameterSession,
        fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path,
    )
    board_patch = patch(
        "app.operator_console.measurement_record.measure_on_board",
        side_effect=_fake_board_parameter_measurement,
    )
    board_patch.start()
    try:
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            view_model.startLiveEDSession(104_650_000, 8, 16, 4_096)
            _drain(app, lambda: not view_model.detections)
        view_model.selectDetection(31)
        view_model.confirmAnalysisSpan(
            float(view_model.analysisLowerMHzText),
            float(view_model.analysisUpperMHzText),
        )
        previous_span = (
            view_model._analysis_span.lower_shifted_bin,
            view_model._analysis_span.upper_shifted_bin,
        )
        _present(
            view_model,
            50,
            replace(
                _event(31),
                start_shifted_bin=previous_span[0] - 12,
                end_shifted_bin=previous_span[1] + 9,
            ),
        )
        assert view_model.analysisSpanLimited
        view_model.requestMeasurement()
        _drain(app, lambda: not view_model.parameterRows and not view_model.errorMessage)

        assert view_model.parameterRows
        assert not view_model.errorMessage
        import json
        import zipfile
        from app.operator_console.measurement_record import replay_measurement
        path = Path(view_model.measurementRecordPath)
        with zipfile.ZipFile(path) as archive:
            document = json.loads(archive.read("measurement.json"))
        assert document["intent"]["span"]["provenance"] == "automatic_live_expansion"
        assert document["intent"]["span"]["lower_shifted_bin"] == previous_span[0] - 12
        assert document["intent"]["span"]["upper_shifted_bin"] == previous_span[1] + 9
        assert document["source"]["channel_capture"]["event_ids"] == list(range(110, 110 + frame_count))
        assert document["intent"]["context"]["owner_observed_frames"] == [False] * (frame_count - 1) + [True]
        assert document["iq"]["frames"] == frame_count
        assert document["observation_duration_s"] == frame_count * 4096 / 2000000
        assert "KTR-4.4" not in document["requirements"]
        replay_measurement(path)
    finally:
        board_patch.stop()
        view_model.shutdown()


def test_live_direction_uses_multiframe_board_power_and_resumes_rx(tmp_path) -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-direction-power-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_DirectionSession,
        fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path,
    )
    board_patch = patch(
        "app.operator_console.measurement_record.measure_on_board",
        side_effect=_fake_board_parameter_measurement,
    )
    board_patch.start()
    coarse_patch = patch.object(view_model, "_coarse_supports_fpga_region", return_value=True)
    coarse_patch.start()
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model.startLiveEDSession(104_650_000, 8, 16, 4_096)
        _drain(app, lambda: not view_model.detections)
        view_model.selectDetection(31)
        assert view_model.selectedDetectionReady
        assert view_model._analysis_span_draft is not None
        assert view_model.measurementSelectionReady
        assert view_model.directionMeasurementReady
        assert view_model.directionNextAngleDeg == 0.0
        assert view_model.directionNextAngleText == "0°"
        assert "başlangıç" in view_model.directionStepInstructionText

        view_model.addNextClockwiseDirectionMeasurement()
        _drain(
            app,
            lambda: view_model.directionMeasurementCount != 1 or not view_model.liveSessionActive,
            timeout=8.0,
        )

        assert view_model.directionMeasurementCount == 1, (
            view_model.statusMessage,
            view_model.errorMessage,
            view_model._active_task_kind,
            view_model._pending_direction_measurement,
        )
        assert view_model.directionPoints[0]["power"] == "-30.00 dBFS"
        assert view_model.directionPoints[0]["angle"] == "0.0°"
        assert view_model.directionPoints[0]["bearing"] == "—"
        assert view_model.directionNextAngleDeg == 15.0
        assert view_model.directionNextAngleText == "15°"
        assert view_model.directionReferenceText == "Coğrafi referans yok · yalnız bağıl yön"
        assert view_model.liveSessionActive
        assert view_model._live_session.configuration.lna_gain_db == 8
        assert view_model._live_session.configuration.vga_gain_db == 16
        assert any(
            row["component"] == "Yön Bulma" and "kanal gücü kaydedildi" in row["message"]
            for row in view_model.eventLog
        )
        _drain(
            app,
            lambda: not any(
                int(row["eventId"]) == 31 and bool(row["observed"])
                for row in view_model.detections
            ),
        )
        # A new RX session has no selected event. The locked channel survives.
        assert view_model.selectedDetectionId == -1
        assert view_model.directionMeasurementReady, (
            view_model.measurementSelectionReady,
            view_model.selectedDetectionReady,
            view_model.selectedDetectionCurrent,
            view_model._analysis_span_draft,
            view_model._live_fpga_fft_size(),
            view_model._coarse_detection_sequence,
            view_model._frame_index,
        )
        view_model.addNextClockwiseDirectionMeasurement()
        _drain(
            app,
            lambda: view_model.directionMeasurementCount != 2 or not view_model.liveSessionActive,
            timeout=8.0,
        )
        assert view_model.directionMeasurementCount == 2
        assert [row["angle"] for row in view_model.directionPoints] == ["0.0°", "15.0°"]
        assert view_model.directionPoints[1]["source"] == "Lob dışı · kilitli kanal"
        assert view_model.directionNextAngleDeg == 345.0
        assert "0° başlangıç yönüne geri" in view_model.directionStepInstructionText
        assert "tersine 15°" in view_model.directionStepInstructionText
        assert len({item.frame_id for item in view_model._df.measurements}) == 2
        assert list(tmp_path.glob("*.zip"))
        import json
        import zipfile
        from app.operator_console.measurement_record import replay_measurement
        for path in tmp_path.glob("*.zip"):
            with zipfile.ZipFile(path) as archive:
                document = json.loads(archive.read("measurement.json"))
            capture = document["source"]["direction_capture"]
            if capture["angle_deg"] == 0.0:
                assert capture["binding"] == "operator_selected_channel_v1"
                assert capture["event_ids"] == [110, 111, 112, 113]
                assert document["intent"]["context"]["owner_observed_frames"] == [False, False, False, True]
            else:
                assert capture["binding"] == "operator_locked_channel_power_v2"
                assert capture["event_ids"] == [None, None, None, None]
                assert capture["target_observed_frames"] == [False, False, False, False]
                assert document["intent"]["context"]["owner_observed_frames"] == [False] * 4
            assert "KTR-4.4" in document["requirements"]
            assert document["board_measurement"]["protocol"] == "P0PM-v4"
            assert document["board_measurement"]["power_basis"] == "locked_channel_total_signal_plus_noise"
            assert document["fields"]["channel_power_dbfs"]["method_id"] == "power.locked-channel-total-signal-plus-noise-v1"
            replay_measurement(path)
    finally:
        coarse_patch.stop()
        board_patch.stop()
        view_model.shutdown()


def test_live_direction_accepts_wide_p0pm_v2_channel(tmp_path) -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-direction-wide-channel-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_DirectionSession,
        fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path,
    )
    board_patch = patch(
        "app.operator_console.measurement_record.measure_on_board",
        side_effect=_fake_board_parameter_measurement,
    )
    board_patch.start()
    coarse_patch = patch.object(view_model, "_coarse_supports_fpga_region", return_value=True)
    coarse_patch.start()
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model.startLiveEDSession(104_650_000, 8, 16, 4_096)
        _drain(app, lambda: not view_model.detections)
        view_model.selectDetection(31)
        view_model._analysis_span_draft = (1_200, 2_788)
        assert view_model._analysis_span_draft[1] - view_model._analysis_span_draft[0] + 1 == 1_589
        assert view_model.directionMeasurementReady

        view_model.addNextClockwiseDirectionMeasurement()
        _drain(
            app,
            lambda: view_model.directionMeasurementCount != 1 or not view_model.liveSessionActive,
            timeout=8.0,
        )

        assert view_model.directionMeasurementCount == 1, view_model.directionCaptureText
        assert view_model._df_channel_span == (1_200, 2_788)
        assert view_model.directionPoints[0]["angle"] == "0.0°"
    finally:
        coarse_patch.stop()
        board_patch.stop()
        view_model.shutdown()


def test_live_direction_start_failure_does_not_lock_channel(tmp_path) -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-direction-start-failure-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_DirectionSession,
        fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path,
    )
    coarse_patch = patch.object(view_model, "_coarse_supports_fpga_region", return_value=True)
    coarse_patch.start()
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model.startLiveEDSession(104_650_000, 8, 16, 4_096)
        _drain(app, lambda: not view_model.detections)
        view_model.selectDetection(31)
        view_model._live_session.begin_direction_capture = (
            lambda lower, upper, require_observed_target=True: (_ for _ in ()).throw(
                ValueError("geçersiz kanal")
            )
        )

        view_model.addNextClockwiseDirectionMeasurement()

        assert view_model.directionMeasurementCount == 0
        assert view_model._df_channel_span is None
        assert view_model._pending_direction_measurement is None
        assert "başlatılamadı" in view_model.directionCaptureText
    finally:
        coarse_patch.stop()
        view_model.shutdown()


@pytest.mark.parametrize("action", ["timeout", "cancel", "stop", "settings", "fft", "no_span"])
def test_direction_capture_reports_blocks_and_discards_cancelled_angles(tmp_path, action):
    app = QGuiApplication.instance() or QGuiApplication(["direction-lifecycle"])
    view = OperatorViewModel(acquisition_backend=_Backend(), live_session_factory=_DirectionSession,
                             fpga_transport_factory=_FPGAReadyTransport,
                             measurement_record_directory=tmp_path)
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        with patch.object(view, "_coarse_supports_fpga_region", return_value=True):
            view.startLiveEDSession(104_650_000, 8, 16, 4096)
            _drain(app, lambda: not view.detections)
        view.selectDetection(31)
        if action == "fft":
            view._live_session.configuration = replace(view._live_session.configuration, fpga_fft_size=8192)
            assert not view.directionMeasurementReady
            assert "4096" in view.directionCaptureText
            return
        if action == "no_span":
            view._analysis_span_draft = None
            assert not view.directionMeasurementReady
            assert "kanal aralığı" in view.directionCaptureText
            return
        view.addDirectionMeasurement(0, "north", 0)
        assert view.directionCaptureCancellable
        if action == "timeout":
            view._pending_direction_measurement["deadline"] = time.monotonic() - 1
            view._poll_direction_capture()
            assert "5 saniyede" in view.directionCaptureText
        elif action == "cancel":
            view.cancelDirectionMeasurement()
            assert "iptal" in view.directionCaptureText
        elif action == "stop":
            view.stopLiveEDSession()
        else:
            view._live_session.configuration = replace(view._live_session.configuration, lna_gain_db=16)
            view._poll_direction_capture()
            assert not view.directionMeasurementReady
        assert not view.directionCapturePending
        assert view.directionMeasurementCount == 0
        assert not list(tmp_path.glob("*.zip"))
    finally:
        view.shutdown()


@pytest.mark.parametrize("stage", ["stopping_rx", "worker"])
def test_parameter_cancel_prevents_late_result_publication(tmp_path, stage):
    from app.operator_console.quick_measurement_actions import measure_and_record
    app = QGuiApplication.instance() or QGuiApplication(["measurement-cancel"])
    vm = OperatorViewModel(acquisition_backend=_Backend(), live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport, measurement_record_directory=tmp_path)
    entered, release = threading.Event(), threading.Event()

    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return measure_and_record(*args, **kwargs)

    try:
        vm.probeHackrf()
        _drain(app, lambda: vm.busy)
        with patch.object(vm, "_coarse_supports_fpga_region", return_value=True):
            vm.startLiveEDSession(104_650_000, 0, 0, 4096)
            _drain(app, lambda: not vm.detections)
        vm.selectDetection(31)
        vm.confirmAnalysisSpan(float(vm.analysisLowerMHzText), float(vm.analysisUpperMHzText))
        with patch("app.operator_console.quick_measurement_actions.measure_and_record", side_effect=delayed):
            vm.requestMeasurement()
            assert vm.parameterMeasurementActive
            if stage == "worker":
                _drain(app, lambda: not entered.is_set())
                assert entered.is_set()
            vm.cancelParameterMeasurement()
            assert not vm.parameterMeasurementActive
            release.set()
            _drain(app, lambda: vm.busy or vm.liveSessionActive)
        assert not vm.parameterRows
        assert not vm.measurementRecordPath
        assert not vm.measurementInfo
        assert vm._pending_live_measurement is None
        if stage == "stopping_rx":
            assert not entered.is_set()
            assert not list(tmp_path.iterdir())
    finally:
        release.set()
        vm.shutdown()


@pytest.mark.parametrize("mutation", ["frequency", "rate", "frame_id", "dma", "drops"])
def test_live_measurement_rejects_mixed_capture_context(tmp_path, mutation):
    app = QGuiApplication.instance() or QGuiApplication(["measurement-context"])
    vm = OperatorViewModel(acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession, fpga_transport_factory=_FPGAReadyTransport,
        measurement_record_directory=tmp_path)
    try:
        vm.probeHackrf()
        _drain(app, lambda: vm.busy)
        with patch.object(vm, "_coarse_supports_fpga_region", return_value=True):
            vm.startLiveEDSession(104_650_000, 0, 0, 4096)
            _drain(app, lambda: not vm.detections)
        vm.selectDetection(31)
        vm.confirmAnalysisSpan(float(vm.analysisLowerMHzText), float(vm.analysisUpperMHzText))
        session = vm._live_session
        snapshots = list(session.window)
        selected = snapshots[1]
        if mutation == "frequency":
            selected = replace(selected, output_frame=replace(selected.output_frame, center_frequency_hz=104_000_000))
        elif mutation == "rate":
            selected = replace(selected, output_frame=replace(selected.output_frame, sample_rate_hz=8_000_000))
        elif mutation == "frame_id":
            selected = replace(selected, output_frame=replace(selected.output_frame, frame_id=999))
        elif mutation == "dma":
            selected = replace(selected, response=replace(selected.response, dma_status_flags=0))
        else:
            selected = replace(selected, response=replace(selected.response, dropped_candidates=1))
        snapshots[1] = selected
        session.window = tuple(snapshots)
        vm._selected_live_measurement_window = session.window
        vm.requestMeasurement()
        assert not vm.parameterRows
        assert not vm.measurementRecordPath
        assert not list(tmp_path.iterdir())
        assert vm._pending_live_measurement is None
        assert "bağlamı uyuşmuyor" in vm.statusMessage
    finally:
        vm.shutdown()


def test_live_measurement_record_write_failure_keeps_results_empty(tmp_path):
    app = QGuiApplication.instance() or QGuiApplication(["measurement-write-failure"])
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("preserve", encoding="utf-8")
    vm = OperatorViewModel(acquisition_backend=_Backend(), live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport, measurement_record_directory=blocked)
    try:
        vm.probeHackrf()
        _drain(app, lambda: vm.busy)
        with patch.object(vm, "_coarse_supports_fpga_region", return_value=True):
            vm.startLiveEDSession(104_650_000, 0, 0, 4096)
            _drain(app, lambda: not vm.detections)
        vm.selectDetection(31)
        vm.confirmAnalysisSpan(float(vm.analysisLowerMHzText), float(vm.analysisUpperMHzText))
        vm.requestMeasurement()
        _drain(app, lambda: not vm.errorMessage, timeout=12.0)
        assert vm.errorMessage, (
            vm.statusMessage,
            vm.analysisLowerMHzText,
            vm.analysisUpperMHzText,
            vm.analysisSpanConfirmed,
            vm.measurementSelectionReady,
            vm.parameterMeasurementActive,
        )
        assert not vm.parameterRows
        assert not vm.measurementRecordPath
        assert blocked.read_text(encoding="utf-8") == "preserve"
    finally:
        vm.shutdown()


def test_live_detection_listening_uses_five_second_consecutive_iq_window() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-listening-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_LiveListeningSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    audio = np.zeros(240_000, dtype=np.float64)
    monitor_result = AnalogMonitorResult(
        mode="am",
        sample_rate_hz=48_000,
        audio=audio,
        pcm16=bytes(audio.size * 2),
        dominant_tone_hz=1_000.0,
        clipping_count=0,
        input_frame_count=LIVE_AUDIO_WINDOW_FRAMES,
        input_complex_samples=LIVE_AUDIO_WINDOW_FRAMES * 4096,
        transient_guard_input_samples=0,
        quality_code="valid",
        observation_interval_s=0.25,
        observation_times_s=(0.125, 0.375),
        channel_power_dbfs_trace=(-20.0, -19.5),
        residual_frequency_hz_trace=(-12.0, 8.0),
    )
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            view_model.startLiveEDSession(104_650_000, 0, 0, 4_096)
            _drain(app, lambda: not view_model.detections)
        view_model.selectDetection(31)

        assert view_model.liveSessionActive
        assert view_model.listeningSelectionReady
        assert view_model.liveListeningBufferText == "Dinleme verisi 5.0 / 5.0 s · sinyal hazır"
        session = view_model._live_session
        assert session is not None
        unstable = {
            "total_frames": LIVE_AUDIO_WINDOW_FRAMES,
            "observed_frames": 100,
            "observed_fraction": 100 / LIVE_AUDIO_WINDOW_FRAMES,
            "max_consecutive_misses": 50,
            "invalid_frames": 0,
            "acceptable": False,
        }
        with patch.object(session, "audio_channel_frame_count", return_value=100), patch.object(
            session, "audio_channel_quality", return_value=unstable
        ):
            # The captured data remains full even when channel confidence drops.
            assert view_model.liveListeningBufferText == (
                "Dinleme verisi 5.0 / 5.0 s · hedef sinyal kesiliyor"
            )

        with patch(
            "app.operator_console.quick_listening_actions.AnalogMonitor.process_continuous",
            return_value=monitor_result,
        ) as process_continuous:
            view_model.requestListening("am", 76.660, 16.0, 0.8)
            view_model.clearDetectionSelection()
            assert view_model.selectedDetectionId == 31
            _drain(app, lambda: not view_model.listeningReady and not view_model.errorMessage)

        assert not view_model.liveSessionActive
        assert not view_model.busy
        assert view_model.errorMessage == ""
        assert view_model.listeningReady
        assert not view_model.listeningShortPreview
        assert view_model.listeningState == "Ses hazır."
        rows = {row["label"]: row["value"] for row in view_model.listeningRows}
        assert rows["Alım seviyesi"] == "-20.00…-19.50 dBFS"
        assert rows["Frekans sapması"] == "-12.0…+8.0 Hz"
        assert rows["Ses profili"] == "Net ses"
        assert len(rows) == 6
        assert view_model.listeningObservationPoints == [
            {"time": 0.125, "power": -20.0, "frequency": -12.0},
            {"time": 0.375, "power": -19.5, "frequency": 8.0},
        ]
        blocks = process_continuous.call_args.args[0]
        assert sum(block.size for block in blocks) == LIVE_AUDIO_WINDOW_FRAMES * 4096
    finally:
        view_model.shutdown()


@pytest.mark.parametrize("session_factory", [_FailedSession, _InvalidSnapshotSession])
def test_failed_live_session_clears_results_and_can_retry(session_factory) -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-retry-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=session_factory,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy)

        assert not view_model.busy
        assert not view_model.liveSessionActive
        assert not view_model.sourceReady
        assert view_model.frameIndex == 0
        assert view_model.spectrumValues == []
        assert view_model.detections == []
        assert view_model.errorMessage
        assert view_model.errorTitle
        assert view_model.sourceState == "Hata"

        # A queued callback from a terminated session must not restore old results.
        _Session("hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL, display_interval_frames=15)).run(
            lambda snapshot: view_model._live_snapshot(view_model._generation, snapshot)
        )
        assert not view_model.sourceReady
        assert view_model.detections == []

        view_model._live_session_factory = _Session
        view_model.startLiveEDSession(104_650_000, 16, 16, 4)
        _drain(app, lambda: view_model.busy)
        assert view_model.sourceReady
        assert view_model.sourceState == "Hazır"
        assert view_model.errorMessage == ""
        assert view_model.frameIndex == 4
    finally:
        view_model.shutdown()


def test_frequency_survey_excludes_other_sources_and_keeps_historical_selection(tmp_path):
    from app.operator_console.rx_survey import SurveyResult, SurveyUpdate
    class SurveyStub:
        def __init__(self, executable, serial, config, audit_path):
            self.config, self.audit_path = config, audit_path
            self.cancelled = threading.Event()
        def cancel(self):
            self.cancelled.set()
        def run(self, callback):
            window = self.config.windows()[0]
            callback(SurveyUpdate(window, "running", 0.0))
            event = _event(31)
            frame = IQFrame(127, 2_000_000, window.center_hz, bytes(8192), frame_id=127)
            snapshot = LiveEDSnapshot(127, frame, LiveEDResponse(127, 1, 7, 0, False, 0, (event,), (), 136))
            callback(SurveyUpdate(window, "preview", .3, snapshot=snapshot))
            callback(SurveyUpdate(window, "complete", .5,
                ({"key": "0:31", "frequency_hz": window.center_hz, "observed_frames": 120},), snapshot))
            assert self.cancelled.wait(3)
            return SurveyResult("cancelled", len(self.config.windows()), 1, 0, .6, str(self.audit_path))
    app = QGuiApplication.instance() or QGuiApplication(["survey-view-model-test"])
    view = OperatorViewModel(
        acquisition_backend=_Backend(),
        survey_factory=SurveyStub,
        live_session_factory=_Session,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        view.startFrequencySurvey(1, 6000, 16, 16)
        _drain(app, lambda: view.survey.observationModel.rowCount() == 0)
        assert view.busy and view.survey.running
        assert view.sourceReady and view.centerFrequencyHz == 1_300_000
        assert view.survey.coverageText == "1 / 9999 pencere tarandı · 0 hata"
        assert not view.detections  # Survey history is not a live detection list.
        view.survey.selectObservation("0:31")
        assert view.survey.selectedFrequency == 1_300_000
        assert not view.monitorSurveyObservation()
        view.setSourceMode("sigmf")
        assert view.sourceMode == "hackrf"
        view.pause()
        _drain(app, lambda: view.busy)
        assert not view.busy and not view.survey.running
        assert view.survey.state == "Durduruldu"
        assert view.survey.selectedKey == "0:31"
        assert view.survey.observationModel.rowCount() == 1
        assert view.monitorSurveyObservation()
        assert view.liveReceiveSettings == {"center_hz": 1_200_000, "lna_db": 16, "vga_db": 16,
                                            "rf_amplifier": False}
        _drain(app, lambda: view.busy)
        assert view.centerFrequencyHz == 1_200_000
    finally:
        view.shutdown()


def test_survey_parameter_action_reacquires_and_selects_matching_live_detection():
    from app.operator_console.rx_survey import SurveyConfig

    app = QGuiApplication.instance() or QGuiApplication(["survey-parameter-transfer-test"])
    view = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        view.survey._config = SurveyConfig(1_000_000, 2_000_000, 16, 16)
        view.survey._rows = [{"eventId": "survey:31", "frequencyHz": 1_300_000.0}]
        view.survey.selectObservation("survey:31")
        ready = QSignalSpy(view.surveyParameterReady)

        with patch.object(view, "_coarse_supports_fpga_region", return_value=True):
            assert view.openSurveyObservationParameters()
            _drain(app, lambda: ready.count() == 0)

        assert ready.count() == 1
        assert view.selectedDetectionId == 31
        assert view.measurementSelectionReady
        assert view.selectedDetectionFrequencyText != "—"
    finally:
        view.shutdown()


def test_live_parameter_setup_keeps_latched_window_during_brief_detection_gap():
    app = QGuiApplication.instance() or QGuiApplication(["parameter-latched-window-test"])
    view = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _drain(app, lambda: view.busy)
        with patch.object(view, "_coarse_supports_fpga_region", return_value=True):
            view.startLiveEDSession(1_200_000, 16, 16, 4096)
            _drain(app, lambda: not view.detections)

        view.selectDetection(31)
        assert view.measurementSelectionReady
        assert len(view._selected_live_measurement_window) == 4

        view._live_session.current_measurement_window = lambda event_id: ()
        view._selected_live_detection = dict(
            view._selected_live_detection,
            observed=False,
            state="Sinyal yok",
            stateKey="stale",
        )

        assert view.measurementSelectionReady
        view.confirmAnalysisSpan(
            float(view.analysisLowerMHzText),
            float(view.analysisUpperMHzText),
        )
        assert view.analysisSpanConfirmed
        view.requestMeasurement()
        assert view.parameterMeasurementActive
        assert "dört ardışık FPGA karesi" in view.statusMessage
    finally:
        view.shutdown()


def test_frequency_survey_sorts_by_frequency_without_losing_recency():
    from app.operator_console.detection_model import DetectionListModel
    from app.operator_console.rx_survey import SurveyConfig, SurveyUpdate
    from app.operator_console.survey_controller import SurveyController

    controller = SurveyController()
    controller._windows = SurveyConfig(1_000_000, 4_000_000).windows()
    controller._states = [0] * len(controller._windows)
    first, second = controller._windows[:2]
    controller._update(SurveyUpdate(first, "complete", .5, ({
        "key": "0:first", "frequency_hz": first.center_hz, "observed_frames": 40,
        "event": {"peak_power": 10.0, "noise_power": 1.0},
        "verification": {"observed_frames": 12},
    },)))
    controller._update(SurveyUpdate(second, "complete", 1.0, ({
        "key": "1:newest", "frequency_hz": second.center_hz, "observed_frames": 80,
        "event": {"peak_power": 100.0, "noise_power": 1.0},
        "verification": {"observed_frames": 30},
    },)))

    model = controller.observationModel
    older = model.data(model.index(0), DetectionListModel.RowRole)
    newest = model.data(model.index(1), DetectionListModel.RowRole)
    assert older["frequencyHz"] < newest["frequencyHz"]
    assert newest["eventId"] == "1:newest"
    assert newest["latestWindow"] is True
    assert newest["detail"] == "P/N 20.0 dB · 80 kare · 2. ayar 30 kare"
    assert older["latestWindow"] is False
    assert controller.currentObservationText == "Son pencerede 1 iki ayarlı RF adayı"


def test_completed_single_survey_places_local_energy_region_above_event_history():
    from app.operator_console.detection_model import DetectionListModel
    from app.operator_console.rx_survey import SurveyConfig, SurveyResult, SurveyUpdate
    from app.operator_console.survey_controller import SurveyController

    controller = SurveyController()
    controller._config = SurveyConfig(1_500_000_000, 1_518_000_000)
    controller._windows = controller._config.windows()
    controller._states = [0] * len(controller._windows)
    controller._run_condition = "unspecified"
    for window in controller._windows:
        power = -31.0 if window.index in {12, 13, 14} else -40.0
        controller._update(SurveyUpdate(
            window,
            "complete",
            float(window.index),
            (),
            window_metrics={"channel_power_dbfs": power},
        ))
    controller._complete(SurveyResult(
        "completed", len(controller._windows), len(controller._windows), 0, 1.0, "unused.jsonl"
    ))
    row = controller.observationModel.data(
        controller.observationModel.index(0), DetectionListModel.RowRole
    )
    assert row["evidenceKey"] == "energy_candidate"
    assert row["evidence"] == "ÖNE ÇIKAN ENERJİ"
    assert row["frequencyHz"] == controller._windows[12].center_hz
    assert "1 öne çıkan enerji bölgesi" in controller.observationText
