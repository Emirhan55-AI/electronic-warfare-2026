"""Qt Quick presentation boundary for the release operator application."""

from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
from collections import deque
from typing import Callable, Literal

import numpy as np
from PySide6.QtCore import QObject, Property, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .rx_survey import RXSurvey
from .survey_controller import SurveyController

from algorithms.et import (
    AnalogDeceptionEngine,
    ContinuousJammingEngine,
    ETMissionController,
    GNSSScenarioValidator,
    InterleavedTaskController,
    SafetyMode,
)
from algorithms.monitoring import (
    AnalogMonitorResult,
)
from algorithms.p0.df import ManualAmplitudeDF
from algorithms.p0.coarse_detection import CoarseDetectionFrame
from algorithms.parameters import (
    AnalysisSpan,
    F1ParameterResult,
    F5ParameterEstimator,
    suggest_analysis_span,
)
from algorithms.pipeline import (
    RuntimeFrameResult,
    RuntimePipeline,
    load_phase04f5_capability,
    resolve_default_operation_profile,
)
from algorithms.spectrum import SigMFFrameSource
from algorithms.p0.transport import TCPClientIQTransport, TransportError
from platforms.acquisition import (
    DeviceStatus,
    HackRFBackend,
    RealHackRFBackend,
    ToolInventory,
    load_ed_rx_config,
)

from .audio_playback import AudioPlayback
from .detection_model import DetectionListModel
from .fixed_band_verification import (
    FIXED_PRESENTATION_HOLD_FRAMES,
    FIXED_PRIMARY_MIN_SEEN_FRAMES,
    FIXED_SPUR_MATCH_HZ,
    FIXED_VERIFY_MATCH_HZ,
    FixedBandCandidate,
    FixedBandVerification,
    FixedBandVerifier,
    fixed_candidate_reference_frequency,
    known_spur_shoulder_evidence,
)
from .known_spurs import load_known_spurs
from .spectral_display import SpectralDisplay
from .live_ed import (
    LIVE_AUDIO_WINDOW_FRAMES,
    LIVE_AUDIO_WINDOW_SECONDS,
    LIVE_DEFAULT_LNA_GAIN_DB,
    LIVE_DEFAULT_VGA_GAIN_DB,
    LIVE_BOARD_HOST,
    LIVE_BOARD_PORT,
    LIVE_USABLE_HALF_BAND_HZ,
    LiveEDConfiguration,
    LiveEDSession,
    LiveEDSessionResult,
    LiveEDSnapshot,
    LiveEDPreview,
)

from .quick_detection_state import (
    LIVE_PRESENTATION_CLUSTER_HZ,
    LIVE_SPUR_GUARD_WINDOW,
    SUPPRESSED_VERIFICATION_STATES,
    QuickDetectionStateMixin,
)
from .quick_direction_actions import QuickDirectionActionsMixin
from .quick_et_actions import QuickETActionsMixin
from .quick_listening_actions import QuickListeningActionsMixin
from .quick_measurement_actions import QuickMeasurementActionsMixin
from .quick_scan_actions import QuickScanActionsMixin
from .quick_runtime import (
    ERROR_TEXT,
    ERROR_TITLE,
    LIVE_PIPELINE_DETAILS,
    PIPELINE_COMPONENTS,
    _LatestWorkMailbox,
    _LiveMailbox,
    _LiveTask,
    _Task,
    _reduce_display_max,
)


__all__ = (
    "MISSING_RECEIVER_ERROR_DISPLAY_MS",
    "OperatorViewModel",
    "_LatestWorkMailbox",
    "_LiveMailbox",
    "_LiveTask",
    "_reduce_display_max",
)


MISSING_RECEIVER_ERROR_DISPLAY_MS = 10_000
READINESS_INVALIDATING_LIVE_ERRORS = frozenset(
    {
        "connection_failed",
        "dma_status",
        "candidate_drop",
        "transport_integrity",
        "stream_integrity",
        "live_queue_timeout",
        "live_capture_timeout",
    }
)

# FPGA event identifiers are deliberately short lived. A modulated carrier can
# move by several FFT bins and be reborn with another event identifier even
# though it is still one operator-visible emission. This tolerance is used only
# for presentation/history grouping; raw FPGA events and measurement windows
# retain their original identifiers.
OPERATOR_DEFAULT_LNA_GAIN_DB = 16
OPERATOR_DEFAULT_VGA_GAIN_DB = 16


class OperatorViewModel(
    QuickDetectionStateMixin,
    QuickDirectionActionsMixin,
    QuickETActionsMixin,
    QuickListeningActionsMixin,
    QuickMeasurementActionsMixin,
    QuickScanActionsMixin,
    QObject,
):
    """Bounded product state exposed to QML; it never manufactures RF data."""

    stateChanged = Signal()
    spectrumChanged = Signal()
    detectionsChanged = Signal()
    directionChanged = Signal()
    logChanged = Signal()
    listeningChanged = Signal()
    playbackChanged = Signal()
    pipelineChanged = Signal()
    etChanged = Signal()
    liveReceiveSettingsChanged = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        acquisition_backend: HackRFBackend | None = None,
        source_factory: Callable[..., SigMFFrameSource] = SigMFFrameSource,
        live_session_factory: Callable[[str, LiveEDConfiguration], LiveEDSession] = LiveEDSession,
        fpga_transport_factory: Callable[[], TCPClientIQTransport] = TCPClientIQTransport,
        survey_factory=RXSurvey,
        fixed_verifier_factory=FixedBandVerifier,
        developer_mode: bool | None = None,
    ) -> None:
        super().__init__(parent)
        resolved = resolve_default_operation_profile()
        self._pipeline = RuntimePipeline(resolved.profile, verified_binding=resolved.binding)
        self._profile_summary = self._pipeline.validated_summary
        self._profile_warning = resolved.fallback_code
        self._parameter_capability = load_phase04f5_capability()
        self._parameter_estimator = F5ParameterEstimator() if self._parameter_capability is not None else None
        self._source_factory = source_factory
        self._live_session_factory = live_session_factory
        self._fpga_transport_factory = fpga_transport_factory
        self._fixed_verifier_factory = fixed_verifier_factory
        self._backend = acquisition_backend or RealHackRFBackend()
        self._device_config = load_ed_rx_config()
        self._known_spurs_hz = load_known_spurs(self._device_config.serial)
        self._live_spur_guard_binding: tuple[float, float, int] | None = None
        self._live_spur_guard_power: deque[np.ndarray] = deque(maxlen=LIVE_SPUR_GUARD_WINDOW)
        self._live_spur_guard_passed: dict[int, bool] = {}
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._advance)
        self._playback_timer = QTimer(self)
        self._playback_timer.setInterval(100)
        self._playback_timer.timeout.connect(self._refresh_listening_playback)
        self._probe_error_timer = QTimer(self)
        self._probe_error_timer.setSingleShot(True)
        self._probe_error_timer.setInterval(MISSING_RECEIVER_ERROR_DISPLAY_MS)
        self._probe_error_timer.timeout.connect(self._clear_missing_receiver_error)

        self._generation = 0
        self._closed = False
        self._busy = False
        self._pending_frame = False
        self._playing = False
        self._source: object | None = None
        self._source_mode: Literal["sigmf", "hackrf"] = "hackrf"
        self._source_name = "Alıcı"
        self._source_state = "Kullanılmıyor"
        self._status_message = "Alıcı bağlantısı bekleniyor."
        self._error_title = ""
        self._error_message = ""
        self._missing_receiver_error_visible = False
        self._frame_index = 0
        self._frame_count = 0
        self._last_result: RuntimeFrameResult | None = None
        self._spectrum_values: list[float] = []
        self._spectral_display = SpectralDisplay(self)
        self._spectral_display.levelsChanged.connect(self.spectrumChanged)
        self._spectrum_min_db = -120.0
        self._spectrum_max_db = 0.0
        self._viewport_points = 900
        self._detections: list[dict[str, object]] = []
        self._detection_model = DetectionListModel(self)
        self._live_detection_rows: list[dict[str, object]] = []
        self._live_detection_history: list[dict[str, object]] = []
        self._coarse_detection_frame: CoarseDetectionFrame | None = None
        self._coarse_detection_sequence = -1
        self._coarse_detection_error = ""
        self._fixed_verification_records: dict[int, object] = {}
        self._fixed_verification_candidate: FixedBandCandidate | None = None
        self._fixed_verification_queue: list[FixedBandCandidate] = []
        self._fixed_verifier = None
        self._fixed_verification_stop_requested = False
        self._fixed_resume_settings: dict[str, int] | None = None
        self._fixed_preserved_history: list[dict[str, object]] = []
        self._selected_live_detection: dict[str, object] | None = None
        self._visible_live_measurement_windows: dict[int, tuple[LiveEDSnapshot, ...]] = {}
        self._show_live_candidates = False
        self._live_list_frame = -1
        self._selected_detection_id = -1
        self._measurement_requested = False
        self._parameter_rows: list[dict[str, str]] = []
        self._analysis_span: AnalysisSpan | None = None
        self._analysis_span_draft: tuple[int, int] | None = None
        self._span_revision = 0
        self._event_observation_history: dict[int, list[tuple[int, bool]]] = {}
        self._reduced_motion = False
        self._hackrf_ready = False
        self._hackrf_transfer_executable = ""
        self._live_session: LiveEDSession | None = None
        self._live_presentation_error: tuple[str, str] | None = None
        self._live_has_data = False
        self._live_received_at = 0.0
        self._live_response_at = 0.0
        self._live_age_ms = 0.0
        self._live_fpga_enabled = True
        self._live_health_timer = QTimer(self)
        self._live_health_timer.setInterval(250)
        self._live_health_timer.timeout.connect(self._refresh_live_health)
        self._live_output_center_frequency_hz = 0
        self._spectrum_center_frequency_hz = 0.0
        self._spectrum_sample_rate_hz = 0.0
        self._live_receive_settings = {
            "center_hz": 104_650_000,
            "lna_db": OPERATOR_DEFAULT_LNA_GAIN_DB,
            "vga_db": OPERATOR_DEFAULT_VGA_GAIN_DB,
        }
        self._live_sample_rate_hz = 0
        self._live_frames_per_second = 0.0
        self._survey_controller = SurveyController(self, factory=survey_factory)
        self._survey_controller.preview.connect(self._survey_preview)
        self._survey_controller.finished.connect(self._survey_finished)
        self._pending_live_measurement: Callable[[], F1ParameterResult] | None = None
        self._pending_live_listening: Callable[
            [], tuple[AnalogMonitorResult, str, float, float, float]
        ] | None = None
        self._selected_live_measurement_window: tuple[LiveEDSnapshot, ...] = ()
        self._operation_samples_ms: list[float] = []
        self._event_log: list[dict[str, str]] = []
        self._log_sequence = 0
        self._developer_mode = (
            bool(developer_mode)
            if developer_mode is not None
            else os.environ.get("EH_CONSOLE_DEVELOPER_MODE", "").strip().casefold() in {"1", "true", "yes"}
        )
        self._active_task_kind = ""

        self._audio_playback = AudioPlayback(self)
        self._listening_result: AnalogMonitorResult | None = None
        self._listening_state = "Doğrulanmış bir tespit seçin."
        self._listening_rows: list[dict[str, str]] = []
        self._listening_waveform: list[float] = []
        self._listening_short_preview = False
        self._listening_playback_state = "Ses hazırlanmadı"
        self._listening_playback_position_s = 0.0
        self._listening_playback_duration_s = 0.0

        self._df = ManualAmplitudeDF()
        self._df_points: list[dict[str, str]] = []
        self._df_status = "En az üç farklı anten açısında gerçek güç ölçümü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self._df_reference_key: tuple[str, float | None] | None = None
        self._direction_frame_power_dbfs: float | None = None

        self._et_task = "continuous"
        self._et_status = "HAZIR"
        self._et_result_title = "Görev seçildi"
        self._et_result_detail = "Görev türünü seçin ve çalışma parametrelerini belirleyin."
        self._et_metric_rows: list[dict[str, str]] = []
        self._et_primary_values: list[float | None] = []
        self._et_secondary_values: list[float] = []
        self._et_timeline: list[dict[str, str]] = []
        self._et_primary_title = "Zaman Alanı"
        self._et_secondary_title = "Spektrum"
        self._et_mission = ETMissionController(SafetyMode.OFFLINE)
        self._et_continuous = ContinuousJammingEngine()
        self._et_interleaved = InterleavedTaskController()
        self._et_analog = AnalogDeceptionEngine()
        self._et_gnss = GNSSScenarioValidator()
        self._add_log("Sistem", "Operatör uygulaması hazır")
        if self._profile_warning:
            self._add_log("İşleme", "Parametre profili doğrulanamadı; güvenli tespit profili kullanılıyor")
        if self._parameter_capability is None:
            self._add_log("Parametre", "Parametre ölçüm profili doğrulanamadı; ölçüm kapalı")

    @Property(str, notify=stateChanged)
    def sourceMode(self) -> str:
        return self._source_mode

    @Property(str, notify=stateChanged)
    def sourceName(self) -> str:
        return self._source_name

    @Property(str, notify=stateChanged)
    def sourceState(self) -> str:
        return self._source_state

    @Property(str, notify=stateChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=stateChanged)
    def errorTitle(self) -> str:
        return self._error_title

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=stateChanged)
    def sourceReady(self) -> bool:
        return self._source is not None or self._live_has_data

    @Property(bool, notify=stateChanged)
    def hackrfReady(self) -> bool:
        return self._hackrf_ready

    @Property(bool, notify=stateChanged)
    def liveSessionActive(self) -> bool:
        return (self._live_session is not None and self._playing) or (
            self._fixed_verification_candidate is not None and self._fixed_verifier is not None
        )

    @Property(QObject, constant=True)
    def survey(self):
        return self._survey_controller

    @Property(bool, notify=stateChanged)
    def recordedIQReady(self) -> bool:
        return self._source is not None

    @Property(bool, notify=stateChanged)
    def playing(self) -> bool:
        return self._playing

    @Property(int, notify=stateChanged)
    def frameIndex(self) -> int:
        if self._source_mode == "hackrf" and not self._live_has_data:
            return 0
        return self._frame_index + 1 if self._frame_count else 0

    @Property(int, notify=stateChanged)
    def frameCount(self) -> int:
        return self._frame_count

    @Property(str, notify=stateChanged)
    def centerFrequencyText(self) -> str:
        if self._source is None and not self._live_has_data:
            return "—"
        return self._format_frequency(self.centerFrequencyHz)

    @Property(str, notify=stateChanged)
    def sampleRateText(self) -> str:
        if self._source is None and not self._live_has_data:
            return "—"
        if self._source_mode == "hackrf" and self._live_has_data and self._spectrum_sample_rate_hz > self.sampleRateHz:
            return f"RX {self._spectrum_sample_rate_hz / 1_000_000:g} · FPGA {self.sampleRateHz / 1_000_000:g} MS/s"
        return f"{self.sampleRateHz / 1_000_000:g} MS/s" if self.sampleRateHz >= 1_000_000 else f"{self.sampleRateHz / 1_000:g} kS/s"

    @Property(str, notify=stateChanged)
    def liveHealthText(self) -> str:
        if self._source_mode != "hackrf":
            return "Kayıtlı I/Q"
        if not self.liveSessionActive:
            return "Alım durdu" if self._live_has_data else "RX bekleniyor"
        now = time.perf_counter()
        rx = "RX bekleniyor" if not self._live_received_at else f"RX veri yaşı {(now - self._live_received_at) * 1000:.0f} ms"
        fpga = "FPGA yanıtı bekleniyor" if not self._live_response_at else (
            "FPGA yanıtı gecikti" if now - self._live_response_at > .25 else "FPGA yanıtı güncel")
        if not self._live_fpga_enabled:
            fpga = "Yalnız RX önizleme · FPGA tespiti kapalı"
        return f"{rx} · {fpga}"

    @Property(str, notify=stateChanged)
    def liveTuningText(self) -> str:
        if self._source_mode != "hackrf" or not self._live_has_data:
            return ""
        if self._spectrum_sample_rate_hz <= self._live_sample_rate_hz:
            return f"FPGA pencere merkezi {self._format_precise_rf(self._live_output_center_frequency_hz)}"
        return (
            f"İzleme merkezi {self._format_precise_rf(self._live_output_center_frequency_hz)} · "
            f"ham RX LO {self._format_precise_rf(self._spectrum_center_frequency_hz)} · "
            "ham merkez çizgisi DC/LO olabilir; tek başına yayın değildir"
        )

    @Property(bool, notify=stateChanged)
    def liveDetectionEnabled(self) -> bool:
        return self._live_fpga_enabled

    @Slot()
    def _refresh_live_health(self):
        if self.liveSessionActive:
            # Stale detections must not remain marked as current during a stall.
            if self._live_response_at and time.perf_counter() - self._live_response_at > .25:
                self._live_detection_rows = [self._last_observation(row) for row in self._live_detection_rows]
                self._refresh_live_detection_list(force=True)
            self.stateChanged.emit()

    @Property(float, notify=stateChanged)
    def centerFrequencyHz(self) -> float:
        if self._source is not None:
            return float(getattr(self._source, "center_frequency_hz", 0.0))
        return float(self._live_output_center_frequency_hz)

    @Property(float, notify=spectrumChanged)
    def spectrumCenterFrequencyHz(self) -> float:
        return self._spectrum_center_frequency_hz or self.centerFrequencyHz

    @Property(float, notify=spectrumChanged)
    def spectrumSampleRateHz(self) -> float:
        return self._spectrum_sample_rate_hz or self.sampleRateHz

    @Property(float, notify=stateChanged)
    def liveDetectionStartNormalized(self) -> float:
        return self._normalized_live_frequency(self._live_output_center_frequency_hz - LIVE_USABLE_HALF_BAND_HZ)

    @Property(float, notify=stateChanged)
    def liveDetectionEndNormalized(self) -> float:
        return self._normalized_live_frequency(self._live_output_center_frequency_hz + LIVE_USABLE_HALF_BAND_HZ)

    @Property(float, notify=stateChanged)
    def liveOutputCenterNormalized(self) -> float:
        return self._normalized_live_frequency(self._live_output_center_frequency_hz)

    @Property("QVariantMap", notify=liveReceiveSettingsChanged)
    def liveReceiveSettings(self):
        return dict(self._live_receive_settings)

    @Property(float, notify=stateChanged)
    def sampleRateHz(self) -> float:
        if self._source is not None:
            return float(getattr(self._source, "sample_rate_hz", 0.0))
        return float(self._live_sample_rate_hz)

    @Property(str, notify=stateChanged)
    def calibrationText(self) -> str:
        return "Kalibrasyonsuz · dBFS" if self.sourceReady else "—"

    @Property(str, constant=True)
    def profileSummary(self) -> str:
        return self._profile_summary

    @Property("QVariantList", notify=spectrumChanged)
    def spectrumValues(self) -> list[float]:
        return self._spectrum_values

    @Property(int, notify=spectrumChanged)
    def spectrumPointCount(self) -> int:
        return len(self._spectrum_values)

    @Property(float, notify=spectrumChanged)
    def spectrumMinDb(self) -> float:
        return self._spectral_display.floorDb

    @Property(float, notify=spectrumChanged)
    def spectrumMaxDb(self) -> float:
        return self._spectral_display.floorDb + self._spectral_display.spanDb

    @Property(QObject, constant=True)
    def spectralDisplay(self):
        return self._spectral_display

    @Property("QVariantList", notify=detectionsChanged)
    def detections(self) -> list[dict[str, object]]:
        return self._detections

    @Property(int, notify=detectionsChanged)
    def activeDetectionCount(self) -> int:
        rows = self._live_detection_rows if self._source_mode == "hackrf" else self._detections
        if (
            self._source_mode == "hackrf"
            and self._live_session is None
            and self._fixed_verification_candidate is None
        ):
            return 0
        return sum(
            row.get("stateKey") == "confirmed" and bool(row.get("observed", True))
            and not bool(row.get("held", False))
            and row.get("verificationKey") not in SUPPRESSED_VERIFICATION_STATES
            for row in rows
        )

    @Property(int, notify=detectionsChanged)
    def stableDetectionCount(self) -> int:
        rows = self._live_detection_rows if self._source_mode == "hackrf" else self._detections
        if (
            self._source_mode == "hackrf"
            and self._live_session is None
            and self._fixed_verification_candidate is None
        ):
            return 0
        return sum(
            row.get("verificationKey") == "verified_two_lo"
            and row.get("stateKey") == "confirmed"
            and bool(row.get("observed", True))
            and not bool(row.get("held", False))
            for row in rows
        )

    @Property(QObject, constant=True)
    def detectionModel(self):
        return self._detection_model

    @Property(bool, notify=detectionsChanged)
    def showLiveCandidates(self) -> bool:
        return self._show_live_candidates

    @Property(bool, notify=detectionsChanged)
    def selectedDetectionCurrent(self) -> bool:
        selected = self._selected_detection_item()
        return selected is not None and bool(selected.get("observed", True)) and (
            self._source_mode != "hackrf" or self._live_session is not None
        )

    @Property("QVariantList", notify=detectionsChanged)
    def detectionMarkers(self) -> list[dict[str, object]]:
        rows = self._live_detection_rows if self._source_mode == "hackrf" else self._detections
        if (
            self._source_mode == "hackrf"
            and self._live_session is None
            and self._fixed_verification_candidate is None
        ):
            return []
        return [
            row for row in rows
            if row["stateKey"] == "confirmed"
            and row.get("observed", True)
            and not row.get("held", False)
            and row.get("verificationKey") not in SUPPRESSED_VERIFICATION_STATES
        ][:12]

    @Property("QVariantList", notify=detectionsChanged)
    def coarseDetectionMarkers(self) -> list[dict[str, object]]:
        frame = self._coarse_detection_frame
        if frame is None or self._live_session is None:
            return []
        candidates = sorted(
            (
                item for item in frame.candidates
                if item.state == "confirmed" and item.observed_this_frame
                and abs(fixed_candidate_reference_frequency(
                    item.lower_frequency_hz,
                    item.upper_frequency_hz,
                    item.peak_frequency_hz,
                ) - self._live_output_center_frequency_hz)
                <= LIVE_USABLE_HALF_BAND_HZ
                and any(
                    row.get("stateKey") == "confirmed"
                    and bool(row.get("observed", True))
                    and (
                        max(
                            0.0,
                            min(float(row["upperFrequencyHz"]), float(item.upper_frequency_hz))
                            - max(float(row["lowerFrequencyHz"]), float(item.lower_frequency_hz)),
                        ) > 0.0
                        or abs(float(row["peakFrequencyHz"]) - float(item.peak_frequency_hz))
                        <= LIVE_PRESENTATION_CLUSTER_HZ
                    )
                    for row in self._live_detection_rows
                )
            ),
            key=lambda item: (
                -item.peak_to_noise_db if math.isfinite(item.peak_to_noise_db) else float("inf"),
                item.peak_frequency_hz,
            ),
        )
        return [
            {
                "eventId": int(item.track_id),
                "startNormalized": self._normalized_live_frequency(item.lower_frequency_hz),
                "endNormalized": self._normalized_live_frequency(item.upper_frequency_hz),
                "peakNormalized": self._normalized_live_frequency(item.peak_frequency_hz),
                "frequency": self._format_frequency(fixed_candidate_reference_frequency(
                    item.lower_frequency_hz,
                    item.upper_frequency_hz,
                    item.peak_frequency_hz,
                )),
                "contrast": f"{item.peak_to_noise_db:.1f} dB" if math.isfinite(item.peak_to_noise_db) else "—",
                "insideFpgaBand": abs(fixed_candidate_reference_frequency(
                    item.lower_frequency_hz,
                    item.upper_frequency_hz,
                    item.peak_frequency_hz,
                ) - self._live_output_center_frequency_hz)
                <= LIVE_USABLE_HALF_BAND_HZ,
                "verificationKey": self._fixed_verification_state(fixed_candidate_reference_frequency(
                    item.lower_frequency_hz,
                    item.upper_frequency_hz,
                    item.peak_frequency_hz,
                )),
            }
            for item in candidates
            if self._fixed_verification_state(fixed_candidate_reference_frequency(
                item.lower_frequency_hz,
                item.upper_frequency_hz,
                item.peak_frequency_hz,
            )) not in SUPPRESSED_VERIFICATION_STATES
        ][:12]

    @Property(bool, notify=detectionsChanged)
    def hasCoarseCandidateAwaitingFpga(self) -> bool:
        return not self.detectionMarkers and bool(self.coarseDetectionMarkers)

    @Property(str, notify=detectionsChanged)
    def coarseDetectionStatusText(self) -> str:
        if self._coarse_detection_error and self._live_session is not None:
            return "8 MHz kaba RX tespiti kullanılamıyor"
        frame = self._coarse_detection_frame
        if frame is None or self._live_session is None:
            return "8 MHz kaba RX tespiti bekleniyor"
        count = sum(item.state == "confirmed" and item.observed_this_frame for item in frame.candidates)
        outside = sum(
            item.state == "confirmed" and item.observed_this_frame
            and abs(item.peak_frequency_hz - self._live_output_center_frequency_hz) > LIVE_USABLE_HALF_BAND_HZ
            for item in frame.candidates
        )
        if outside:
            return f"Kaba RX adayı: {count} · {outside} aday FPGA alanı dışında"
        return f"Kaba RX adayı: {count} · FPGA doğrulaması değildir"

    @Property(int, notify=detectionsChanged)
    def selectedDetectionId(self) -> int:
        return self._selected_detection_id

    @Property(bool, notify=detectionsChanged)
    def selectedDetectionReady(self) -> bool:
        if self._source_mode == "hackrf":
            selected = self._selected_detection_item()
            return self.selectedDetectionCurrent and selected is not None and selected["stateKey"] == "confirmed"
        return any(
            int(item["eventId"]) == self._selected_detection_id and item["stateKey"] == "confirmed"
            for item in self._detections
        )

    @Property(bool, notify=detectionsChanged)
    def measurementSelectionReady(self) -> bool:
        if self._source_mode != "hackrf":
            return self.selectedDetectionReady
        session = self._live_session
        selected = self._selected_detection_item()
        if (
            session is None
            or selected is None
            or not bool(selected.get("confirmed", selected["stateKey"] == "confirmed"))
            or not hasattr(session, "measurement_window")
        ):
            return False
        return len(self._live_measurement_window()) == 4

    @Property(str, notify=detectionsChanged)
    def selectedDetectionTitle(self) -> str:
        selected = self._selected_detection_item()
        return str(selected["title"]) if selected is not None else "Tespit seçilmedi"

    @Property(str, notify=detectionsChanged)
    def selectedDetectionFrequencyText(self) -> str:
        selected = self._selected_detection_item()
        return str(selected["frequency"]) if selected is not None else "—"

    @Property(str, notify=detectionsChanged)
    def selectedDetectionContrastText(self) -> str:
        selected = self._selected_detection_item()
        return str(selected["snr"]) if selected is not None else "—"

    @Property(str, notify=detectionsChanged)
    def selectedDetectionStateText(self) -> str:
        selected = self._selected_detection_item()
        if selected is not None and self._source_mode == "hackrf" and self._live_session is None:
            return "Alım durdu"
        return str(selected["state"]) if selected is not None else "Seçim bekleniyor"

    @Property(float, notify=detectionsChanged)
    def selectedRegionStartNormalized(self) -> float:
        return self._selected_detection_coordinate("startNormalized")

    @Property(float, notify=detectionsChanged)
    def selectedRegionEndNormalized(self) -> float:
        return self._selected_detection_coordinate("endNormalized")

    @Property(float, notify=detectionsChanged)
    def selectedRegionPeakNormalized(self) -> float:
        return self._selected_detection_coordinate("peakNormalized")

    @Property(float, notify=detectionsChanged)
    def analysisSpanStartNormalized(self) -> float:
        bins = self._analysis_span_bins()
        if bins is None:
            return -1.0
        return self._normalized_live_bin(bins[0]) if self._source_mode == "hackrf" else self._normalized_shifted_bin(bins[0])

    @Property(float, notify=detectionsChanged)
    def analysisSpanEndNormalized(self) -> float:
        bins = self._analysis_span_bins()
        if bins is None:
            return -1.0
        return self._normalized_live_bin(bins[1]) if self._source_mode == "hackrf" else self._normalized_shifted_bin(bins[1])

    @Property("QVariantList", notify=detectionsChanged)
    def parameterRows(self) -> list[dict[str, str]]:
        return self._parameter_rows

    @Property(bool, constant=True)
    def parameterCapabilityReady(self) -> bool:
        return self._parameter_capability is not None

    @Property(bool, notify=detectionsChanged)
    def analysisSpanConfirmed(self) -> bool:
        return self._analysis_span is not None

    @Property(str, notify=detectionsChanged)
    def analysisLowerMHzText(self) -> str:
        return self._analysis_frequency_text(0)

    @Property(str, notify=detectionsChanged)
    def analysisUpperMHzText(self) -> str:
        return self._analysis_frequency_text(1)

    @Property(bool, notify=detectionsChanged)
    def measurementReady(self) -> bool:
        if self._source_mode == "hackrf":
            return (
                self.parameterCapabilityReady
                and self.measurementSelectionReady
                and self._analysis_span is not None
            )
        return (
            self.parameterCapabilityReady
            and self._source is not None
            and self.selectedDetectionReady
            and self._analysis_span is not None
            and self._has_four_observed_frames(self._selected_detection_id)
        )

    @Property(bool, notify=stateChanged)
    def reducedMotion(self) -> bool:
        return self._reduced_motion

    @Property(bool, constant=True)
    def developerMode(self) -> bool:
        return self._developer_mode

    @Property(str, notify=etChanged)
    def etTask(self) -> str:
        return self._et_task

    @Property(str, notify=etChanged)
    def etStatus(self) -> str:
        return self._et_status

    @Property(str, notify=etChanged)
    def etResultTitle(self) -> str:
        return self._et_result_title

    @Property(str, notify=etChanged)
    def etResultDetail(self) -> str:
        return self._et_result_detail

    @Property("QVariantList", notify=etChanged)
    def etMetricRows(self) -> list[dict[str, str]]:
        return self._et_metric_rows

    @Property("QVariantList", notify=etChanged)
    def etPrimaryValues(self) -> list[float | None]:
        return self._et_primary_values

    @Property("QVariantList", notify=etChanged)
    def etSecondaryValues(self) -> list[float]:
        return self._et_secondary_values

    @Property("QVariantList", notify=etChanged)
    def etTimeline(self) -> list[dict[str, str]]:
        return self._et_timeline

    @Property(str, notify=etChanged)
    def etPrimaryTitle(self) -> str:
        return self._et_primary_title

    @Property(str, notify=etChanged)
    def etSecondaryTitle(self) -> str:
        return self._et_secondary_title

    @Property("QVariantList", constant=True)
    def etTaskCards(self) -> list[dict[str, str]]:
        return [
            {"id": "continuous", "name": "Sürekli Karıştırma", "detail": "Tekli · Çoklu · Baraj · Süpürme", "maturity": "TABAN BANT"},
            {"id": "interleaved", "name": "Arabakışlı Karıştırma", "detail": "Dinle · Gecikme · Görev · Koruma", "maturity": "ZAMANLAMA"},
            {"id": "analog", "name": "Analog Telsiz Aldatma", "detail": "AM · FM · NFM", "maturity": "YEREL DÖNGÜ"},
            {"id": "gnss", "name": "GPS L1 Senaryosu", "detail": "Konum · UTC · PRN", "maturity": "METADATA"},
        ]

    @Property("QVariantList", notify=pipelineChanged)
    def pipelineBlocks(self) -> list[dict[str, object]]:
        live = self._source_mode == "hackrf"
        source = "Hata" if self._error_message and not self.sourceReady else self._source_state
        processing = (
            "Çalışıyor"
            if (self._playing or self._busy) and self.sourceReady
            else "Hazır" if self.sourceReady else "Kullanılmıyor"
        )
        states = {
            "source": source,
            "preprocess": processing,
            "fft_power": processing,
            "regional": processing,
            "temporal": processing,
            "parameters": (
                "Çalışıyor"
                if self._busy and self._active_task_kind == "measurement"
                else "Hazır" if self._parameter_rows
                else "Bekliyor" if self._parameter_capability is not None and self._source is not None
                else "Kullanılmıyor"
            ),
            "monitoring": (
                "Çalışıyor"
                if self._busy and self._active_task_kind == "listening"
                else "Hazır" if self._listening_result is not None
                else "Bekliyor" if self.sourceReady
                else "Kullanılmıyor"
            ),
        }
        blocks: list[dict[str, object]] = []
        for component in PIPELINE_COMPONENTS:
            block = dict(component, state=states[str(component["id"])])
            if live:
                block.update(LIVE_PIPELINE_DETAILS.get(str(component["id"]), {}))
            if block["runtime"] in {"FPGA", "ZYNQ PS"}:
                block["hardwareStatus"] = (
                    "Bu oturumda kart yanıtı alındı"
                    if self._live_response_at > 0
                    else "Kart yanıtı bekleniyor" if self._live_session is not None
                    else "Bu oturumda kart yanıtı yok"
                )
                if not self._live_fpga_enabled:
                    block["state"] = "Kullanılmıyor"
                    block["hardwareStatus"] = "RX önizleme modu; FPGA tespiti yapılmıyor"
                elif self._live_session is not None and not self._live_response_at:
                    block["state"] = "Bekliyor"
            else:
                block["hardwareStatus"] = "Bilgisayar üzerinde yürütülür"
            blocks.append(block)
        return blocks

    @Slot(str, str, result=bool)
    def openImplementationLocation(self, component_id: str, target: str) -> bool:
        if not self._developer_mode or target not in {"host", "rtl"}:
            return False
        component = next((item for item in self.pipelineBlocks if item["id"] == component_id), None)
        if component is None:
            return False
        relative = str(component["hostPath"] if target == "host" else component["rtlPath"])
        if not relative:
            return False
        repository_root = Path(__file__).resolve().parents[2]
        location = (repository_root / relative).resolve()
        try:
            location.relative_to(repository_root)
        except ValueError:
            return False
        if not location.exists():
            return False
        opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(location))))
        if opened:
            self._add_log("Sistem", f"{component['name']} kaynak konumu açıldı")
        return opened


    @Property(str, notify=stateChanged)
    def performanceText(self) -> str:
        if self._source_mode == "hackrf" and self._live_frames_per_second > 0.0:
            return f"Canlı yol {self._live_frames_per_second:.2f} kare/s"
        if not self._operation_samples_ms:
            return "Henüz ölçüm yok"
        measured = self._operation_samples_ms[5:] if len(self._operation_samples_ms) > 10 else self._operation_samples_ms
        values = sorted(measured)
        index = min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)
        return f"İşleme p95 {values[index]:.2f} ms · {len(values)} kare"

    @Property("QVariantList", notify=logChanged)
    def eventLog(self) -> list[dict[str, str]]:
        return self._event_log

    @Property("QVariantList", notify=directionChanged)
    def directionPoints(self) -> list[dict[str, str]]:
        return self._df_points

    @Property(str, notify=directionChanged)
    def directionStatus(self) -> str:
        return self._df_status

    @Property(str, notify=directionChanged)
    def directionStatusText(self) -> str:
        return {
            "LOB HAZIR": "Tek istasyon radyo kerterizi hazır",
            "YETERSİZ AÇI": "En az üç farklı anten açısı gerekli",
            "BELİRSİZ MAKSİMUM": "Güç maksimumu ayrıştırılamadı",
        }.get(self._df_status, self._df_status)

    @Property(bool, notify=directionChanged)
    def directionReady(self) -> bool:
        return self._df_status == "LOB HAZIR"

    @Property(int, notify=directionChanged)
    def directionMeasurementCount(self) -> int:
        return len(self._df.measurements)

    @Property(int, notify=directionChanged)
    def directionDistinctAngleCount(self) -> int:
        return len({item.angle_deg for item in self._df.measurements})

    @Property(float, notify=directionChanged)
    def directionProgress(self) -> float:
        return min(1.0, self.directionDistinctAngleCount / 3.0)

    @Property(str, notify=directionChanged)
    def directionRequirementText(self) -> str:
        count = self.directionDistinctAngleCount
        return f"{count}/3 farklı açı · {self.directionMeasurementCount} ölçüm"

    @Property(str, notify=directionChanged)
    def directionReferenceText(self) -> str:
        if self._df_reference_key is None:
            return "İlk ölçümde sabitlenir"
        mode, angle = self._df_reference_key
        if mode == "north":
            return "Gerçek kuzey · anten 0°"
        if mode == "manual" and angle is not None:
            return f"Anten 0° gerçek kerterizi · {angle:.1f}°"
        return "Coğrafi referans yok · yalnız bağıl yön"

    @Property(str, notify=directionChanged)
    def relativeArrivalText(self) -> str:
        return self._df_relative

    @Property(str, notify=directionChanged)
    def bearingText(self) -> str:
        return self._df_bearing

    @Property(str, notify=spectrumChanged)
    def directionFramePowerText(self) -> str:
        power = self._direction_frame_power_dbfs
        return "—" if power is None else f"{power:.2f} dBFS"

    @Property(str, notify=detectionsChanged)
    def listeningDetectionTitle(self) -> str:
        return self.selectedDetectionTitle

    @Property(str, notify=detectionsChanged)
    def listeningDetectionFrequencyText(self) -> str:
        return self.selectedDetectionFrequencyText

    @Property(float, notify=detectionsChanged)
    def selectedDetectionOffsetKHz(self) -> float:
        selected = self._selected_detection_item()
        return float(selected["offsetKHz"]) if selected is not None else 0.0

    @Property(bool, notify=listeningChanged)
    def listeningReady(self) -> bool:
        return self._listening_result is not None

    @Property(bool, notify=stateChanged)
    def listeningSelectionReady(self) -> bool:
        if self._source_mode != "hackrf":
            return self.selectedDetectionReady
        session = self._live_session
        selected = self._selected_detection_item()
        return bool(
            session is not None
            and selected is not None
            and self.selectedDetectionReady
            and self._pending_live_listening is None
            and self._pending_live_measurement is None
            and hasattr(session, "audio_window_ready")
            and session.audio_window_ready(self._selected_detection_id)
        )

    @Property(str, notify=stateChanged)
    def liveListeningBufferText(self) -> str:
        if self._source_mode != "hackrf":
            return ""
        session = self._live_session
        if session is None or not hasattr(session, "audio_window_frame_count"):
            return "Canlı I/Q tamponu hazır değil"
        frames = min(LIVE_AUDIO_WINDOW_FRAMES, int(session.audio_window_frame_count(self._selected_detection_id)))
        seconds = frames * 4096.0 / self.sampleRateHz if self.sampleRateHz > 0.0 else 0.0
        return f"Canlı I/Q tamponu {seconds:.1f} / {LIVE_AUDIO_WINDOW_SECONDS:.1f} s"

    @Property(bool, notify=listeningChanged)
    def listeningAudioAvailable(self) -> bool:
        return self._audio_playback.available and self._listening_result is not None

    @Property(str, notify=listeningChanged)
    def listeningState(self) -> str:
        return self._listening_state

    @Property(bool, notify=listeningChanged)
    def listeningShortPreview(self) -> bool:
        return self._listening_short_preview

    @Property("QVariantList", notify=listeningChanged)
    def listeningRows(self) -> list[dict[str, str]]:
        return self._listening_rows

    @Property("QVariantList", notify=listeningChanged)
    def listeningWaveform(self) -> list[float]:
        return self._listening_waveform

    @Property(str, notify=playbackChanged)
    def listeningPlaybackState(self) -> str:
        return self._listening_playback_state

    @Property(str, notify=playbackChanged)
    def listeningPlaybackPositionText(self) -> str:
        return self._format_duration(self._listening_playback_position_s)

    @Property(str, notify=playbackChanged)
    def listeningPlaybackDurationText(self) -> str:
        return self._format_duration(self._listening_playback_duration_s)

    @Property(float, notify=playbackChanged)
    def listeningPlaybackProgress(self) -> float:
        if self._listening_playback_duration_s <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self._listening_playback_position_s / self._listening_playback_duration_s))

    @Property(str, notify=playbackChanged)
    def listeningOutputState(self) -> str:
        return "Ses çıkışı hazır" if self._audio_playback.available else "Ses çıkışı yok · WAV kullanılabilir"

    @Property(str, notify=stateChanged)
    def sourceDurationText(self) -> str:
        if self._source is None and not self._live_has_data:
            return "—"
        frame_length = int(getattr(self._source, "frame_length", 4096))
        duration = self._frame_count * frame_length / self.sampleRateHz
        return f"{duration:.3f} s"

    @Slot(str)
    def setSourceMode(self, mode: str) -> None:
        if self._busy or mode not in {"sigmf", "hackrf"} or mode == self._source_mode:
            return
        self.stop()
        self._probe_error_timer.stop()
        self._missing_receiver_error_visible = False
        self._generation += 1
        self._close_source()
        self._source_mode = mode  # type: ignore[assignment]
        self._source_name = "Kaynak seçilmedi"
        self._source_state = "Kullanılmıyor"
        self._error_title = ""
        self._error_message = ""
        self._hackrf_ready = False
        self._hackrf_transfer_executable = ""
        self._live_has_data = False
        self._live_output_center_frequency_hz = 0
        self._live_sample_rate_hz = 0
        self._spectrum_center_frequency_hz = 0.0
        self._spectrum_sample_rate_hz = 0.0
        self._live_frames_per_second = 0.0
        self._status_message = (
            "Standart bir .sigmf-meta kaydı seçin."
            if mode == "sigmf"
            else "Önce yapılandırılmış alıcıyı denetleyin."
        )
        self._clear_results()
        self.stateChanged.emit()

    @Slot(str)
    def openSigmf(self, value: str) -> None:
        if self._busy:
            return
        if self._source_mode != "sigmf":
            self.setSourceMode("sigmf")
        url = QUrl(value)
        path = Path(url.toLocalFile() if url.isLocalFile() else value)
        if not path.name:
            return
        self.stop()
        self._generation += 1
        generation = self._generation
        self._set_busy(True, "SigMF sözleşmesi denetleniyor…")
        self._submit(
            generation,
            "open",
            lambda: self._source_factory(path, mode="standard", frame_length=4096),
        )

    @Slot()
    def probeHackrf(self) -> None:
        if self._source_mode != "hackrf" or self._busy:
            return
        self.stop()
        self._probe_error_timer.stop()
        self._missing_receiver_error_visible = False
        self._generation += 1
        generation = self._generation
        self._set_busy(True, "Alıcı bağlantısı denetleniyor…")

        def operation() -> tuple[ToolInventory, DeviceStatus, bool, str]:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="receiver-probe") as executor:
                hackrf_future = executor.submit(self._probe_hackrf_device)
                fpga_future = executor.submit(self._probe_fpga_service)
                inventory, device = hackrf_future.result()
                fpga_ready, fpga_reason = fpga_future.result()
            return inventory, device, fpga_ready, fpga_reason

        self._submit(generation, "probe", operation)

    def _probe_hackrf_device(self) -> tuple[ToolInventory, DeviceStatus]:
        inventory = self._backend.discover_tools(inspect_help=True)
        if not inventory.receive_available:
            return inventory, DeviceStatus("TOOLCHAIN_UNAVAILABLE", reason_code="tools_unavailable")
        return inventory, self._backend.discover_device()

    def _probe_fpga_service(self) -> tuple[bool, str]:
        transport = self._fpga_transport_factory()
        try:
            transport.connect(LIVE_BOARD_HOST, LIVE_BOARD_PORT, timeout_seconds=2.0)
            return True, ""
        except TransportError as exc:
            return False, exc.code
        except OSError:
            return False, "connection_failed"
        finally:
            transport.close()


    @Slot(int)
    def selectDetection(self, event_id: int) -> None:
        if self._pending_live_listening is not None or self._pending_live_measurement is not None or (
            self._busy and self._active_task_kind in {"listening", "measurement"}
        ):
            return
        if not any(int(item["eventId"]) == event_id for item in self._detections):
            return
        if event_id != self._selected_detection_id:
            self._clear_listening("Seçili kanal değişti; dinlemeyi yeniden hazırlayın.")
        self._selected_detection_id = event_id
        if self._source_mode == "hackrf":
            self._selected_live_detection = dict(next(row for row in self._detections if row["eventId"] == event_id))
            self._selected_live_measurement_window = ()
            window = self._live_measurement_window()
            if len(window) == 4:
                self._selected_live_measurement_window = window
        self._measurement_requested = False
        self._parameter_rows = []
        self._analysis_span = None
        self._prepare_analysis_span_draft(event_id)
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot(bool)
    def setShowLiveCandidates(self, enabled: bool) -> None:
        if self._source_mode != "hackrf":
            return
        self._show_live_candidates = bool(enabled)
        self._refresh_live_detection_list(force=True)

    @Slot()
    def clearDetectionSelection(self) -> None:
        if self._pending_live_listening is not None or self._pending_live_measurement is not None or (
            self._busy and self._active_task_kind in {"listening", "measurement"}
        ):
            return
        self._selected_detection_id = -1
        self._selected_live_detection = None
        self._selected_live_measurement_window = ()
        self._analysis_span = None
        self._analysis_span_draft = None
        self._parameter_rows = []
        self._clear_listening("Doğrulanmış bir tespit seçin.")
        self.detectionsChanged.emit()
        self.stateChanged.emit()


    @Slot(bool)
    def setReducedMotion(self, enabled: bool) -> None:
        if self._reduced_motion != enabled:
            self._reduced_motion = enabled
            self.stateChanged.emit()

    @Slot(int)
    def setSpectrumViewportWidth(self, width: int) -> None:
        bounded = max(320, min(1600, int(width)))
        if abs(bounded - self._viewport_points) < 32:
            return
        self._viewport_points = bounded
        if self._spectral_display.latest.size:
            self._spectrum_values = _reduce_display_max(self._spectral_display.latest, bounded).tolist()
            self.spectrumChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.stop()
        self._probe_error_timer.stop()
        self._playback_timer.stop()
        self._generation += 1
        self._backend.cancel()
        self._pool.waitForDone(2000)
        self._audio_playback.close()
        self._close_source()
        self._backend.close()

    def _submit(self, generation: int, kind: str, operation: Callable[[], object]) -> None:
        task = _Task(generation, kind, operation)
        task.signals.completed.connect(self._task_completed)
        task.signals.failed.connect(self._task_failed)
        self._active_task_kind = kind
        self._busy = True
        if kind != "frame":
            self.pipelineChanged.emit()
            self.stateChanged.emit()
        self._pool.start(task)

    @Slot(int, object)
    def _live_preview(self, generation: int, prepared: object) -> None:
        if isinstance(prepared, _LiveMailbox):
            prepared = prepared.take()
        if generation != self._generation or self._live_session is None or prepared is None:
            return
        if len(prepared) == 3:
            preview, spectrum, processing_ms = prepared
        else:
            # Compatibility with older/injected live-task fixtures.
            preview, spectrum, _coarse, processing_ms = prepared
        if not isinstance(preview, LiveEDPreview) or preview.sequence_number < self._frame_index:
            return
        self._operation_samples_ms.append(processing_ms)
        self._operation_samples_ms = self._operation_samples_ms[-256:]
        first_preview = not self._live_has_data
        self._live_has_data = True
        self._frame_index = preview.sequence_number
        self._live_received_at = preview.received_monotonic
        self._live_age_ms = (time.perf_counter() - self._live_received_at) * 1000
        self._source_state = "Çalışıyor"
        self._update_spectrum_result(spectrum)
        if first_preview:
            self._start_next_fixed_verification()
        if first_preview:
            self.stateChanged.emit()

    @Slot(int, object)
    def _live_coarse(self, generation: int, prepared: object) -> None:
        if isinstance(prepared, _LiveMailbox):
            prepared = prepared.take()
        if generation != self._generation or self._live_session is None or prepared is None:
            return
        sequence_number, coarse = prepared
        if sequence_number < self._coarse_detection_sequence or not isinstance(coarse, CoarseDetectionFrame):
            return
        self._coarse_detection_sequence = sequence_number
        self._coarse_detection_frame = coarse
        self._coarse_detection_error = ""
        self.detectionsChanged.emit()

    @Slot(int, str)
    def _live_coarse_failed(self, generation: int, error_type: str) -> None:
        if generation != self._generation or self._live_session is None:
            return
        self._coarse_detection_frame = None
        self._coarse_detection_error = error_type
        self._add_log("Kaba RX tespiti", "Kaba tespit işçisi durdu; spektrum ve FPGA zinciri çalışmayı sürdürüyor.")
        self.detectionsChanged.emit()

    @Slot(int, object)
    def _live_snapshot(self, generation: int, snapshot: object) -> None:
        if isinstance(snapshot, _LiveMailbox):
            snapshot = snapshot.take()
        response_at = time.perf_counter()
        if isinstance(snapshot, tuple):
            snapshot, response_at = snapshot
        if (
            generation != self._generation
            or self._live_session is None
            or self._live_presentation_error is not None
            or not isinstance(snapshot, LiveEDSnapshot)
        ):
            return
        first_response = not self._live_response_at
        self._live_response_at = response_at
        self._update_live_detections(snapshot.response)
        self._status_message = (
            f"Canlı FPGA karesi {snapshot.sequence_number + 1}/{self._frame_count} doğrulandı."
        )
        if first_response:
            self.pipelineChanged.emit()
            self.stateChanged.emit()

    @Slot(int, object, float)
    def _live_completed(self, generation: int, result: object, elapsed: float) -> None:
        del elapsed
        if generation != self._generation or not isinstance(result, LiveEDSessionResult):
            return
        self._live_health_timer.stop()
        if self._live_presentation_error is not None:
            self._live_failed(generation, *self._live_presentation_error)
            return
        self._live_session = None
        self._busy = False
        self._playing = False
        self._active_task_kind = ""
        self._source_state = "Hazır"
        self._live_frames_per_second = result.frames_per_second
        self._status_message = (
            f"Canlı FPGA oturumu tamamlandı · {result.completed_frames} kare · "
            f"USB taşması {result.hackrf_statistics.overruns}."
        )
        if not result.fpga_enabled:
            self._status_message = f"RX önizleme tamamlandı · {result.completed_frames} kare. FPGA tespiti yapılmadı."
        self._add_log("Canlı ED", self._status_message)
        self._refresh_live_detection_list(force=True)
        self.pipelineChanged.emit()
        self.stateChanged.emit()
        self._start_pending_live_task()

    @Slot(int, str, str)
    def _live_failed(self, generation: int, code: str, detail: str) -> None:
        if generation != self._generation:
            return
        self._live_health_timer.stop()
        if self._live_presentation_error is not None:
            code, detail = self._live_presentation_error
        self._live_session = None
        self._busy = False
        self._playing = False
        self._active_task_kind = ""
        if code == "operation_cancelled":
            if (
                not self._fixed_verification_stop_requested
                and self._fixed_verification_candidate is not None
                and self._fixed_verifier is not None
            ):
                candidate = self._fixed_verification_candidate
                verifier = self._fixed_verifier
                self._source_state = "Denetleniyor"
                self._status_message = "Aday ikinci fiziksel alıcı ayarında sınanıyor."
                self._submit(generation, "fixed_verify", lambda: verifier.run(candidate))
                self.detectionsChanged.emit()
                self.pipelineChanged.emit()
                self.stateChanged.emit()
                return
            if self._fixed_verification_stop_requested:
                self._fixed_verification_candidate = None
                self._fixed_verifier = None
                self._fixed_resume_settings = None
                self._fixed_preserved_history = []
                self._fixed_verification_stop_requested = False
            self._source_state = "Hazır" if self._live_has_data else "Kullanılmıyor"
            self._status_message = "Canlı ED oturumu operatör tarafından durduruldu."
            self._add_log("Canlı ED", self._status_message)
            self._refresh_live_detection_list(force=True)
        else:
            self._pending_live_measurement = None
            self._pending_live_listening = None
            self._measurement_requested = False
            if code in READINESS_INVALIDATING_LIVE_ERRORS:
                self._hackrf_ready = False
                self._hackrf_transfer_executable = ""
            self._live_has_data = False
            self._live_frames_per_second = 0.0
            self._clear_results(keep_source=True)
            self._source_state = "Hata"
            self._show_error(code, detail)
        self.detectionsChanged.emit()
        self.pipelineChanged.emit()
        self.stateChanged.emit()
        if code == "operation_cancelled":
            self._start_pending_live_task()

    @Slot(int, str, object, float)
    def _task_completed(self, generation: int, kind: str, result: object, elapsed: float) -> None:
        self._busy = False
        self._active_task_kind = ""
        if generation != self._generation:
            if hasattr(result, "close"):
                result.close()  # type: ignore[attr-defined]
            if kind != "frame":
                self.pipelineChanged.emit()
            self.stateChanged.emit()
            return
        if kind == "fixed_verify":
            if not isinstance(result, FixedBandVerification):
                self._show_error("fixed_verification_result", "Sabit bant doğrulama sonucu geçersiz.")
                self.stateChanged.emit()
                return
            record = self._fixed_verification_record(result.candidate.frequency_hz)
            if record is not None:
                record.update(state=result.state, result=result)
            resume = self._fixed_resume_settings
            preserved = [self._apply_fixed_verification(row) for row in self._fixed_preserved_history]
            self._fixed_verification_candidate = None
            self._fixed_verifier = None
            self._fixed_verification_stop_requested = False
            self._fixed_resume_settings = None
            self._fixed_preserved_history = []
            if resume is None:
                self._show_error("fixed_verification_resume", "Sabit bant görünümü yeniden başlatılamadı.")
                self.stateChanged.emit()
                return
            center_hz = resume["center_hz"]
            self._status_message = (
                (
                    "Aday FPGA tarafından iki alıcı ayarında yeniden görüldü; görünüm sürdürülüyor."
                    if result.verification_method == "fpga"
                    else "Aday alıcı spektrumunda iki fiziksel ayarda yeniden görüldü; FPGA görünümü sürdürülüyor."
                )
                if result.verified else
                "Aday ikinci ayarlarda yeniden görülmedi; önceki görünüm sürdürülüyor."
            )
            self._add_log("Sabit bant doğrulama", self._status_message)
            self.startLiveEDSession(
                center_hz,
                resume["lna_db"],
                resume["vga_db"],
                resume["frame_count"],
                preserve_fixed_context=True,
            )
            if self._live_session is not None:
                self._live_detection_history = preserved
                self._refresh_live_detection_list(force=True)
            return
        if kind == "open":
            self._install_source(result, Path(getattr(result, "metadata_path")).name)
        elif kind == "probe":
            inventory, device, fpga_ready, fpga_reason = result  # type: ignore[misc]
            self._apply_probe(inventory, device, fpga_ready, fpga_reason)
        elif kind == "frame":
            if not isinstance(result, RuntimeFrameResult):
                self._show_error("processing_failed", "İşleme sonucu sözleşmeyle eşleşmedi.")
                return
            self._operation_samples_ms.append(elapsed * 1000.0)
            self._operation_samples_ms = self._operation_samples_ms[-256:]
            self._last_result = result
            self._update_spectrum(result)
            self._update_detections(result)
            self._status_message = f"Kare {self._frame_index + 1}/{self._frame_count} işlendi."
            if self._pending_frame:
                self._pending_frame = False
                self._advance()
        elif kind == "measurement":
            self._measurement_requested = False
            if not isinstance(result, F1ParameterResult) or self._parameter_capability is None:
                self._show_error("measurement_failed", "Parametre sonucu sözleşmeyle eşleşmedi.")
                return
            if result.persistent_payload_bytes > self._parameter_capability.maximum_persistent_payload_bytes:
                self._show_error("measurement_failed", "Parametre ölçümü kalıcı bellek sınırını aştı.")
                return
            self._parameter_rows = self._f5_parameter_rows(result)
            self._status_message = f"Tespit #{self._selected_detection_id} parametre ölçümü tamamlandı."
            self._add_log("Parametre", self._status_message)
            self.detectionsChanged.emit()
        elif kind == "listening":
            if not isinstance(result, tuple) or len(result) != 5 or not isinstance(result[0], AnalogMonitorResult):
                self._show_error("insufficient_audio", "Dinleme sonucu sözleşmeyle eşleşmedi.")
                return
            listening, scope, input_duration, offset_hz, bandwidth_hz = result
            self._listening_result = listening
            self._audio_playback.load(listening.pcm16)
            self._playback_timer.stop()
            self._listening_playback_position_s = 0.0
            self._listening_playback_duration_s = self._audio_playback.duration_seconds
            self._listening_playback_state = "Oynatmaya hazır"
            self._listening_short_preview = float(input_duration) < LIVE_AUDIO_WINDOW_SECONDS
            audio_duration = listening.audio.size / listening.sample_rate_hz
            channel_frequency = self.centerFrequencyHz + float(offset_hz)
            self._listening_rows = [
                {"label": "Demodülasyon", "value": "AM" if listening.mode == "am" else "Dar Bant FM (NFM)"},
                {"label": "Kanal merkez frekansı", "value": self._format_frequency(channel_frequency)},
                {"label": "Kanal bant genişliği", "value": self._format_rate(float(bandwidth_hz))},
                {"label": "Giriş kapsamı", "value": f"{scope} · {float(input_duration):.3f} s"},
                {"label": "Ses çıkışı", "value": "48 kHz · mono PCM16"},
                {"label": "Üretilen ses süresi", "value": f"{audio_duration:.3f} s"},
                {"label": "Baskın ses bileşeni", "value": self._format_rate(listening.dominant_tone_hz)},
            ]
            waveform_points = min(720, listening.audio.size)
            indices = np.linspace(0, listening.audio.size - 1, waveform_points, dtype=np.int64)
            self._listening_waveform = [float(listening.audio[index]) for index in indices]
            self._listening_state = (
                "Kısa önizleme hazır; kesintisiz dinleme kabulü için en az 5 saniyelik kayıt gerekir."
                if self._listening_short_preview
                else "Kesintisiz kanal sesi hazır."
            )
            self._status_message = f"Tespit #{self._selected_detection_id} dinleme kanalı hazırlandı."
            self._add_log("Dinleme", self._status_message)
            self.playbackChanged.emit()
            self.listeningChanged.emit()
        elif kind == "wav_export":
            self._status_message = f"WAV kaydedildi: {Path(str(result)).name}"
            self._listening_state = self._status_message
            self._add_log("Dinleme", self._status_message)
            self.listeningChanged.emit()
        if kind != "frame":
            self.pipelineChanged.emit()
        self.stateChanged.emit()

    @Slot(int, str, str)
    def _task_failed(self, generation: int, code: str, detail: str) -> None:
        self._busy = False
        task_kind = self._active_task_kind
        self._active_task_kind = ""
        if generation == self._generation:
            if task_kind == "fixed_verify":
                candidate = self._fixed_verification_candidate
                resume = self._fixed_resume_settings
                if candidate is not None:
                    record = self._fixed_verification_record(candidate.frequency_hz)
                    if record is not None:
                        record.update(state="verification_error", result=None)
                stopped = self._fixed_verification_stop_requested or self._closed
                self._fixed_verification_candidate = None
                self._fixed_verifier = None
                self._fixed_verification_stop_requested = False
                self._fixed_resume_settings = None
                self._fixed_preserved_history = []
                if stopped and code == "operation_cancelled":
                    self._source_state = "Hazır" if self._live_has_data else "Kullanılmıyor"
                    self._status_message = "Sabit frekans taraması durduruldu."
                elif resume is not None and not self._closed:
                    self._add_log(
                        "Sabit bant doğrulama",
                        "İkinci alıcı ayarı tamamlanamadı; ana görünüm yeniden başlatılıyor.",
                    )
                    self.startLiveEDSession(
                        resume["center_hz"],
                        resume["lna_db"],
                        resume["vga_db"],
                        resume["frame_count"],
                        preserve_fixed_context=True,
                    )
                else:
                    self._show_error(code, detail)
                self.pipelineChanged.emit()
                self.stateChanged.emit()
                return
            if task_kind == "measurement":
                self._measurement_requested = False
            if task_kind in {"listening", "wav_export"}:
                self._listening_state = ERROR_TEXT.get(code, f"Dinleme işlemi tamamlanamadı ({code}).")
                self._add_log("Dinleme", self._listening_state)
                self.listeningChanged.emit()
            else:
                self._show_error(code, detail)
        self.pipelineChanged.emit()
        self.stateChanged.emit()

    def _request_frame(self) -> None:
        if self._source is None:
            return
        if self._busy:
            self._pending_frame = True
            return
        generation = self._generation
        index = self._frame_index
        source = self._source
        pipeline = self._pipeline

        def operation() -> RuntimeFrameResult:
            frame = source.read_frame(index)  # type: ignore[attr-defined]
            return pipeline.process(
                frame,
                sample_rate_hz=float(source.sample_rate_hz),  # type: ignore[attr-defined]
                center_frequency_hz=float(source.center_frequency_hz),  # type: ignore[attr-defined]
                frame_index=index,
            )

        self._submit(generation, "frame", operation)

    @Slot()
    def _advance(self) -> None:
        if self._source is None:
            return
        if self._busy:
            self._pending_frame = True
            return
        if self._last_result is not None:
            self._frame_index = (self._frame_index + 1) % self._frame_count
        self._request_frame()

    def _install_source(self, source: object, label: str) -> None:
        self._close_source()
        self._source = source
        self._source_name = label
        self._source_state = "Hazır"
        self._frame_index = 0
        self._frame_count = int(getattr(source, "frame_count"))
        self._error_title = ""
        self._error_message = ""
        self._status_message = "Kaynak doğrulandı; tarama başlatılabilir."
        self._pipeline.detection.reset()
        if self._pipeline.parameters is not None:
            self._pipeline.parameters.reset()
        self._clear_results(keep_source=True)
        self._add_log("Kaynak", f"{label} doğrulandı")
        self.pipelineChanged.emit()
        self._request_frame()

    def _apply_probe(
        self,
        inventory: ToolInventory,
        device: DeviceStatus,
        fpga_ready: bool,
        fpga_reason: str,
    ) -> None:
        serial = self._device_config.serial
        transfer = inventory.get("hackrf_transfer")
        self._hackrf_transfer_executable = ""
        self._error_title = ""
        self._error_message = ""
        hackrf_error = ""
        hackrf_detail = device.reason_code
        if not inventory.receive_available or device.state == "TOOLCHAIN_UNAVAILABLE":
            hackrf_error = "tools_unavailable"
        elif device.state == "NO_DEVICE":
            hackrf_error = "device_not_found"
        elif serial is None:
            hackrf_error = "device_serial_unassigned"
            hackrf_detail = "device_serial_unassigned"
        elif device.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"} and any(
            item.serial.casefold() == serial.casefold() for item in device.devices
        ) and transfer.executable_path and "-B" in transfer.supported_options:
            self._hackrf_transfer_executable = transfer.executable_path
        elif device.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"} and any(
            item.serial.casefold() == serial.casefold() for item in device.devices
        ):
            hackrf_error = "stream_integrity"
            hackrf_detail = "cli_options_unverified"
        else:
            hackrf_error = "configured_serial_not_found"

        if hackrf_error or not fpga_ready:
            self._hackrf_ready = False
            self._hackrf_transfer_executable = ""
            if hackrf_error and not fpga_ready:
                code = "receiver_and_fpga_unavailable"
                detail = f"hackrf={hackrf_detail or hackrf_error}; fpga={fpga_reason or 'connection_failed'}"
            elif hackrf_error:
                code = hackrf_error
                detail = hackrf_detail or hackrf_error
            else:
                code = "connection_failed"
                detail = fpga_reason or "connection_failed"
            self._show_transient_probe_error(code, detail)
            self.pipelineChanged.emit()
            return

        self._hackrf_ready = True
        self._source_state = "Hazır"
        self._source_name = f"Alıcı ve FPGA bağlı · …{serial[-8:]}"
        self._status_message = "Alıcı ve FPGA bağlantısı hazır; tarama başlatılabilir."
        self._add_log("Alıcı", self._status_message)
        self.pipelineChanged.emit()

    def _show_transient_probe_error(self, code: str, detail: str) -> None:
        self._show_error(code, detail)
        self._missing_receiver_error_visible = True
        self._probe_error_timer.start()

    @Slot()
    def _clear_missing_receiver_error(self) -> None:
        if not self._missing_receiver_error_visible:
            return
        self._missing_receiver_error_visible = False
        if self._closed or self._busy or self._source_mode != "hackrf" or self._hackrf_ready:
            return
        self._source_state = "Kullanılmıyor"
        self._error_title = ""
        self._error_message = ""
        self._status_message = "Alıcı bağlantısı bekleniyor."
        self.pipelineChanged.emit()
        self.stateChanged.emit()

    def _clear_listening(self, message: str) -> None:
        self._playback_timer.stop()
        self._audio_playback.stop()
        self._listening_result = None
        self._listening_rows = []
        self._listening_waveform = []
        self._listening_short_preview = False
        self._listening_state = message
        self._listening_playback_state = "Ses hazırlanmadı"
        self._listening_playback_position_s = 0.0
        self._listening_playback_duration_s = 0.0
        self.playbackChanged.emit()
        self.listeningChanged.emit()
        self.pipelineChanged.emit()

    def _close_source(self) -> None:
        source, self._source = self._source, None
        if source is not None and hasattr(source, "close"):
            source.close()  # type: ignore[attr-defined]
        if source is not None:
            self.pipelineChanged.emit()

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        self._error_title = ""
        self._error_message = ""
        self._status_message = message
        self.pipelineChanged.emit()
        self.stateChanged.emit()

    def _show_error(self, code: str, detail: str) -> None:
        self._source_state = "Hata" if self._source is None else self._source_state
        self._error_title = ERROR_TITLE.get(code, "İşlem tamamlanamadı")
        self._error_message = ERROR_TEXT.get(code, f"İşlem tamamlanamadı ({code}).")
        self._status_message = self._error_message
        self._add_log("Hata", f"{code} · {detail}")
        self.stateChanged.emit()

    def _add_log(self, component: str, message: str) -> None:
        self._log_sequence += 1
        self._event_log.insert(
            0,
            {
                "sequence": f"{self._log_sequence:04d}",
                "time": time.strftime("%H:%M:%S"),
                "level": "HATA" if component == "Hata" else "UYARI" if "doğrulanamadı" in message else "BİLGİ",
                "component": component,
                "message": message,
            },
        )
        self._event_log = self._event_log[:20]
        self.logChanged.emit()

    @Slot()
    def _refresh_listening_playback(self) -> None:
        self._listening_playback_position_s = self._audio_playback.position_seconds
        if (
            self._listening_playback_duration_s > 0.0
            and self._listening_playback_position_s >= self._listening_playback_duration_s - 0.01
        ):
            self._playback_timer.stop()
            self._listening_playback_position_s = self._listening_playback_duration_s
            self._listening_playback_state = "Oynatma tamamlandı"
        self.playbackChanged.emit()

    @staticmethod
    def _format_frequency(value: float) -> str:
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.6g} GHz"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.6g} MHz"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.6g} kHz"
        return f"{value:.6g} Hz"

    @staticmethod
    def _format_precise_rf(value: float) -> str:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.4f} MHz"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.3f} kHz"
        return f"{value:.1f} Hz"

    @staticmethod
    def _format_rate(value: float) -> str:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.6g} MHz"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.6g} kHz"
        return f"{value:.6g} Hz"

    @staticmethod
    def _format_duration(value: float) -> str:
        bounded = max(0.0, float(value))
        minutes = int(bounded // 60.0)
        seconds = bounded - minutes * 60.0
        return f"{minutes:02d}:{seconds:04.1f}"

    @staticmethod
    def _field_state(state: str) -> str:
        return {
            "not_observed": "Gözlenmedi",
            "not_applicable": "Uygulanamaz",
            "insufficient_quality": "Kalite yetersiz",
            "uncertain": "Belirsiz",
        }.get(state, "Ölçülemedi")

    def _prepare_analysis_span_draft(self, event_id: int) -> None:
        if self._source_mode == "hackrf":
            selected = next(
                (row for row in self._live_detection_rows if int(row["eventId"]) == event_id),
                None,
            )
            if (
                selected is None
                and self._selected_live_detection is not None
                and int(self._selected_live_detection["eventId"]) == event_id
            ):
                selected = self._selected_live_detection
            if selected is None:
                self._analysis_span_draft = None
                return
            start = int(selected["startBin"])
            end = int(selected["endBin"])
            peak = int(selected["peakBin"])
            margin = max(8, min(64, math.ceil((end - start + 1) / 2.0)))
            lower = max(56, start - margin)
            upper = min(4039, end + margin)
            for neighbor in self._live_detection_rows:
                if int(neighbor["eventId"]) == event_id or neighbor["stateKey"] != "confirmed":
                    continue
                neighbor_start = int(neighbor["startBin"])
                neighbor_end = int(neighbor["endBin"])
                if neighbor_end < peak:
                    lower = max(lower, neighbor_end + 5, math.ceil((neighbor_end + start) / 2.0))
                elif neighbor_start > peak:
                    upper = min(upper, neighbor_start - 5, math.floor((end + neighbor_start) / 2.0))
            self._analysis_span_draft = (
                (lower, upper)
                if lower <= peak <= upper and 8 <= upper - lower + 1 <= 512
                else None
            )
            return
        if self._last_result is None:
            self._analysis_span_draft = None
            return
        event = next(
            (item for item in self._last_result.detection.active_events if item.event_id == event_id),
            None,
        )
        if event is None:
            self._analysis_span_draft = None
            return
        suggested = suggest_analysis_span(event, self._last_result.detection.active_events)
        if suggested is None:
            self._analysis_span_draft = None
            return
        lower = max(56, suggested.lower_shifted_bin)
        upper = min(4039, suggested.upper_shifted_bin)
        self._analysis_span_draft = (lower, upper) if upper - lower + 1 >= 8 else None

    def _analysis_frequency_text(self, index: int) -> str:
        bins = self._analysis_span_bins()
        if bins is None:
            return ""
        if self._source_mode == "hackrf":
            frequency_hz = self.centerFrequencyHz + (bins[index] - 2048.0) * self.sampleRateHz / 4096.0
        elif self._last_result is not None:
            spectrum = self._last_result.spectrum
            frequency_hz = spectrum.center_frequency_hz + (bins[index] - 2048.0) * spectrum.bin_spacing_hz
        else:
            return ""
        return f"{frequency_hz / 1_000_000.0:.6f}"

    def _analysis_span_bins(self) -> tuple[int, int] | None:
        if self._analysis_span is not None:
            return self._analysis_span.lower_shifted_bin, self._analysis_span.upper_shifted_bin
        return self._analysis_span_draft

    def _selected_detection_item(self) -> dict[str, object] | None:
        if self._source_mode == "hackrf":
            return self._selected_live_detection
        return next(
            (item for item in self._detections if int(item["eventId"]) == self._selected_detection_id),
            None,
        )

    def _live_measurement_window(self) -> tuple[LiveEDSnapshot, ...]:
        if self._selected_live_measurement_window:
            return self._selected_live_measurement_window
        cached = self._visible_live_measurement_windows.get(self._selected_detection_id, ())
        if cached:
            return cached
        session = self._live_session
        if session is None or not hasattr(session, "measurement_window"):
            return ()
        return tuple(session.measurement_window(self._selected_detection_id))

    def _selected_detection_coordinate(self, field: str) -> float:
        selected = self._selected_detection_item()
        return float(selected[field]) if selected is not None else -1.0

    def _selected_detection_bin(self, field: str) -> int | None:
        if self._source_mode == "hackrf":
            selected = self._selected_detection_item()
            value = selected.get(field) if selected is not None else None
            return int(value) if isinstance(value, (int, float)) else None
        if self._last_result is None:
            return None
        event = next(
            (
                item for item in self._last_result.detection.active_events
                if item.event_id == self._selected_detection_id
            ),
            None,
        )
        if event is None:
            return None
        return {
            "startBin": int(event.region.start_bin),
            "endBin": int(event.region.end_bin),
            "peakBin": int(event.region.peak_bin),
        }.get(field)

    @staticmethod
    def _normalized_shifted_bin(value: int) -> float:
        return max(0.0, min(1.0, float(value) / 4096.0))

    def _normalized_live_frequency(self, frequency_hz: float) -> float:
        rate = self.spectrumSampleRateHz
        if rate <= 0:
            return -1.0
        return max(0.0, min(1.0, .5 + (float(frequency_hz) - self.spectrumCenterFrequencyHz) / rate))

    def _normalized_live_bin(self, value: int) -> float:
        frequency = self._live_output_center_frequency_hz + (float(value) - 2048.0) * 2_000_000.0 / 4096.0
        return self._normalized_live_frequency(frequency)

    def _has_four_observed_frames(self, event_id: int) -> bool:
        if self._frame_index < 3:
            return False
        history = self._event_observation_history.get(event_id, ())
        tail = history[-4:]
        return (
            len(tail) == 4
            and tuple(item[0] for item in tail) == tuple(range(self._frame_index - 3, self._frame_index + 1))
            and all(item[1] for item in tail)
        )

    def _f5_parameter_rows(self, result: F1ParameterResult) -> list[dict[str, str]]:
        validated = set(self._parameter_capability.validated_fields if self._parameter_capability else ())

        def measured(capability: str, field: object, formatter: Callable[[float], str]) -> str:
            if capability not in validated:
                return "Henüz doğrulanmadı"
            state = str(getattr(field, "state", "uncertain"))
            value = getattr(field, "value", None)
            return formatter(float(value)) if state == "valid" and isinstance(value, (int, float)) else self._field_state(state)

        domain = (
            str(result.signal_domain.value)
            if "signal_domain" in validated and result.signal_domain.state == "valid"
            else self._field_state(result.signal_domain.state)
        )
        return [
            {"label": "Emisyon merkez frekansı", "value": measured("emission_center_frequency", result.emission_center_frequency, self._format_frequency)},
            {"label": "Gözlenen taşıyıcı frekansı", "value": measured("carrier_line_frequency", result.carrier_line_frequency, self._format_frequency)},
            {"label": "Alt OBW sınırı", "value": measured("occupied_bandwidth", result.lower_band_edge, self._format_frequency)},
            {"label": "Üst OBW sınırı", "value": measured("occupied_bandwidth", result.upper_band_edge, self._format_frequency)},
            {"label": "OBW %99", "value": measured("occupied_bandwidth", result.occupied_bandwidth, self._format_rate)},
            {"label": "Kalibre edilmemiş kanal gücü", "value": measured("uncalibrated_channel_power_dbfs", result.channel_power_dbfs, lambda value: f"{value:.2f} dBFS")},
            {"label": "SNR kestirimi", "value": measured("snr_estimate_db", result.snr_estimate_db, lambda value: f"{value:.2f} dB")},
            {"label": "Sinyal türü", "value": domain},
            {"label": "Güç referansı", "value": "Kalibre edilmemiş · dBFS"},
        ]
