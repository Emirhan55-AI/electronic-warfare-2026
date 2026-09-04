from __future__ import annotations

import os
import threading
import time
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
from algorithms.p0.transport import TransportError
from algorithms.monitoring import AnalogMonitorResult
from app.operator_console.live_ed import (
    LIVE_AUDIO_WINDOW_FRAMES,
    LiveEDConfiguration,
    LiveEDEvent,
    LiveEDResponse,
    LiveEDSessionResult,
    LiveEDSnapshot,
)
from app.operator_console.quick_view_model import MISSING_RECEIVER_ERROR_DISPLAY_MS, OperatorViewModel
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


class _DisconnectedBackend(_Backend):
    def discover_device(self, cancellation=None):
        del cancellation
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
        _drain(app, lambda: view_model.busy)

    assert view_model.sourceReady
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
    assert blocks["regional"]["rtlPath"].endswith("p0_candidate_reducer_packetizer_top.sv")
    assert blocks["regional"]["hardwareStatus"] == "Bu oturumda kart yanıtı alındı"
    assert blocks["temporal"]["runtime"] == "ZYNQ PS"
    assert view_model.performanceText == "Canlı yol 500.00 kare/s"
    view_model.shutdown()


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
        assert view_model.errorTitle == "Alıcı bağlı değil"
        assert view_model.errorMessage == "Yapılandırılmış alıcı bulunamadı. USB bağlantısını denetleyin."
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
        assert view_model.errorTitle == "Alıcı yazılımı bulunamadı"
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
        assert view_model.errorTitle == "FPGA bağlantısı kurulamadı"
        assert view_model.errorMessage == "FPGA hizmetine bağlanılamadı."
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
        assert view_model.errorTitle == "Alıcı ve FPGA bağlı değil"
        assert view_model.errorMessage == (
            "Alıcı ve FPGA bağlantısı kurulamadı. USB ve FPGA ağ bağlantılarını denetleyin."
        )
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
    view._live_session = _BlockingSession("", None)
    view._live_has_data = True
    yield view
    view.shutdown()


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


def test_selected_row_drops_from_live_list_without_extending_detector_lifetime(live_presentation):
    view = live_presentation
    _present(view, 0, _event(4430))
    view.selectDetection(4430)
    coordinate = view.selectedRegionPeakNormalized
    assert view.selectedDetectionCurrent
    # A new ID at the same frequency is not proof of the same emitter.
    _present(view, 16, _event(4431))
    assert view.selectedDetectionId == 4430
    assert view.selectedRegionPeakNormalized == coordinate
    assert view.selectedDetectionStateText == "Sinyal yok"
    assert not view.selectedDetectionCurrent
    assert not view.selectedDetectionReady
    assert [row["eventId"] for row in view.detectionMarkers] == [4431]
    assert [row["eventId"] for row in view.detections] == [4431]
    _present(view, 128, _event(4431))
    assert [row["eventId"] for row in view.detections] == [4431]
    assert view.selectedDetectionId == 4430
    view.clearDetectionSelection()
    assert view.selectedDetectionId == -1
    assert view.selectedRegionPeakNormalized == -1


def test_presentation_pacing_and_same_event_selection_follow_observations(live_presentation):
    view = live_presentation
    _present(view, 0, _event(1))
    view.selectDetection(1)
    _present(view, 16, _event(2))
    assert [row["eventId"] for row in view.detections] == [2]
    assert not view.selectedDetectionCurrent
    _present(view, 32, _event(1, peak=2210))
    assert view.selectedDetectionCurrent
    assert view.selectedRegionPeakNormalized == pytest.approx(2210 / 4096)
    mapped_hz = view.centerFrequencyHz + (view.selectedRegionPeakNormalized - .5) * view.sampleRateHz
    expected_hz = view.centerFrequencyHz + (2210 - 2048) * view.sampleRateHz / 4096
    assert mapped_hz == pytest.approx(expected_hz)
    _present(view, 112, _event(2))
    assert [row["eventId"] for row in view.detections] == [2]
    assert view.selectedDetectionId == 1
    assert not view.selectedDetectionCurrent
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
    assert view.detections[0]["historyBoundary"]


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
    assert view.detections[0]["state"] == "FPGA + RX spektrumu uyumlu"
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
    assert view.detections[0]["state"] == "2 ayarda kararlı"
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
        assert view_model.errorTitle == "FPGA bağlantısı kurulamadı"
        assert view_model.errorMessage == "FPGA hizmetine bağlanılamadı."
    finally:
        view_model.shutdown()


def test_live_detection_measurement_uses_four_consecutive_fpga_frames() -> None:
    app = QGuiApplication.instance() or QGuiApplication(["live-measurement-test"])
    view_model = OperatorViewModel(
        acquisition_backend=_Backend(),
        live_session_factory=_MeasurementSession,
        fpga_transport_factory=_FPGAReadyTransport,
    )
    try:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        _drain(app, lambda: view_model.busy)
        with patch.object(view_model, "_coarse_supports_fpga_region", return_value=True):
            view_model.startLiveEDSession(104_650_000, 0, 0, 4_096)
            _drain(app, lambda: not view_model.detections)
        assert view_model.liveSessionActive
        view_model.selectDetection(31)
        assert view_model.selectedDetectionReady
        _present(view_model, 50, _event(99))
        assert not view_model.selectedDetectionCurrent
        assert not view_model.selectedDetectionReady
        assert view_model.measurementSelectionReady
        view_model._analysis_span_draft = None
        view_model._prepare_analysis_span_draft(31)
        assert view_model.analysisLowerMHzText
        view_model.confirmAnalysisSpan(
            float(view_model.analysisLowerMHzText),
            float(view_model.analysisUpperMHzText),
        )
        assert view_model.measurementReady

        view_model.requestMeasurement()
        _drain(app, lambda: not view_model.parameterRows and not view_model.errorMessage)

        assert not view_model.liveSessionActive
        assert not view_model.busy
        assert view_model.errorMessage == ""
        assert len(view_model.parameterRows) == 9
        assert "parametre ölçümü tamamlandı" in view_model.statusMessage
    finally:
        view_model.shutdown()


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
        assert view_model.liveListeningBufferText == "Canlı I/Q tamponu 5.0 / 5.0 s"

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
        assert view_model.listeningState == "Kesintisiz kanal sesi hazır."
        assert any(
            row["label"] == "Giriş kapsamı"
            and row["value"].startswith("Canlı kesintisiz alım · 5.001 s")
            for row in view_model.listeningRows
        )
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
        assert view.liveReceiveSettings == {"center_hz": 1_200_000, "lna_db": 16, "vga_db": 16}
        _drain(app, lambda: view.busy)
        assert view.centerFrequencyHz == 1_200_000
    finally:
        view.shutdown()


def test_frequency_survey_presents_newest_verified_observations_first():
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
    newest = model.data(model.index(0), DetectionListModel.RowRole)
    older = model.data(model.index(1), DetectionListModel.RowRole)
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
