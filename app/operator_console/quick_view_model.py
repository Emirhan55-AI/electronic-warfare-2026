"""Qt Quick presentation boundary for the release operator application."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
from collections import deque
from typing import Callable, Literal

import numpy as np
from PySide6.QtCore import QObject, Property, QStandardPaths, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .rx_survey import RXSurvey
from .survey_controller import SurveyController
from .measurement_record import RecordedMeasurement
from .parameter_catalog import ParameterCatalog

from algorithms.monitoring import (
    AnalogMonitorResult,
)
from algorithms.p0.adaptive_df import AdaptiveDirectionSweep
from algorithms.p0.df import FIELD_AMPLITUDE_DF_PROFILE, ManualAmplitudeDF
from algorithms.p0.direction_client import BoardDFEstimate
from algorithms.p0.coarse_detection import CoarseDetectionFrame
from algorithms.parameters import (
    AnalysisSpan,
    F1ParameterResult,
    F5ParameterEstimator,
)
from algorithms.pipeline import (
    RuntimeFrameResult,
    RuntimePipeline,
    load_phase04f5_capability,
    resolve_default_operation_profile,
)
from algorithms.spectrum import SigMFFrameSource
from algorithms.p0.transport import TCPClientIQTransport, TransportError
from algorithms.p0.detection_config import (
    DetectionProfile, DetectionConfigError, exchange_profile, NORMAL_DEFAULT, WEAK_DEFAULT,
)
from platforms.acquisition import (
    AcquisitionError,
    DeviceStatus,
    HackRFBackend,
    RealHackRFBackend,
    ToolInventory,
    load_ed_rx_config,
    switch_portapack_to_hackrf_mode,
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
from .quick_listening_actions import QuickListeningActionsMixin
from .quick_measurement_actions import QuickMeasurementActionsMixin
from .quick_scan_actions import QuickScanActionsMixin
from .quick_task_completion import QuickTaskCompletionMixin
from .quick_runtime import (
    ERROR_TEXT,
    ERROR_TITLE,
    LIVE_PIPELINE_DETAILS,
    PIPELINE_COMPONENTS,
    _LatestWorkMailbox,
    _CatalogTask,
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
PORTAPACK_REENUMERATION_TIMEOUT_SECONDS = 8.0
PORTAPACK_REENUMERATION_POLL_SECONDS = 0.25
RECEIVER_HEALTH_INTERVAL_MS = 1_500
READINESS_INVALIDATING_LIVE_ERRORS = frozenset(
    {
        "connection_failed",
        "dma_status",
        "transport_integrity",
        "stream_integrity",
        "live_queue_timeout",
        "live_capture_timeout",
        "binary_pipe_failed",
        "receiver_connection_lost",
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
    QuickTaskCompletionMixin,
    QuickDirectionActionsMixin,
    QuickListeningActionsMixin,
    QuickMeasurementActionsMixin,
    QuickScanActionsMixin,
    QObject,
):
    """Bounded product state exposed to QML; it never manufactures RF data."""

    stateChanged = Signal()
    spectrumChanged = Signal()
    detectionsChanged = Signal()
    surveyParameterReady = Signal()
    directionChanged = Signal()
    logChanged = Signal()
    listeningChanged = Signal()
    playbackChanged = Signal()
    pipelineChanged = Signal()
    liveReceiveSettingsChanged = Signal()
    detectionSettingsChanged = Signal()
    detectionProfileChanged = Signal()
    parameterCatalogChanged = Signal()

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
        measurement_record_directory: Path | None = None,
        parameter_catalog_path: Path | None = None,
        portapack_mode_switcher: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(parent)
        resolved = resolve_default_operation_profile()
        self._pipeline = RuntimePipeline(resolved.profile, verified_binding=resolved.binding)
        self._profile_summary = self._pipeline.validated_summary
        self._profile_warning = resolved.fallback_code
        self._parameter_capability = load_phase04f5_capability()
        self._parameter_estimator = F5ParameterEstimator() if self._parameter_capability is not None else None
        self._initialize_measurement_recording(measurement_record_directory)
        self._live_catalog_session_id = ""
        self._source_factory = source_factory
        self._live_session_factory = live_session_factory
        self._fpga_transport_factory = fpga_transport_factory
        self._fixed_verifier_factory = fixed_verifier_factory
        self._backend = acquisition_backend or RealHackRFBackend()
        self._portapack_mode_switcher = (
            portapack_mode_switcher
            if portapack_mode_switcher is not None
            else (switch_portapack_to_hackrf_mode if acquisition_backend is None else None)
        )
        self._device_config = load_ed_rx_config()
        self._active_receiver_serial: str | None = None
        catalog_path = parameter_catalog_path or (
            (Path(measurement_record_directory).parent if measurement_record_directory is not None else
             Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)))
            / "parameter-catalog.sqlite3"
        )
        self._parameter_catalog_path = Path(catalog_path)
        self._parameter_catalog = None
        self._automatic_parameter_rows = []
        self._automatic_parameter_status = "Kart canlı parametre yeteneği henüz denetlenmedi."
        self._parameter_catalog_action_status = ""
        try:
            self._parameter_catalog = ParameterCatalog(
                catalog_path,
                Path(__file__).resolve().parents[2] / "config" / "p0" / "rx_calibration.json",
            )
            self._automatic_parameter_rows = self._parameter_catalog.rows()
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._parameter_catalog = None
            self._automatic_parameter_status = f"Parametre kataloğu açılamadı: {exc}"
        self._receiver_rows = [
            {
                "role": receiver.role,
                "roleLabel": "Birincil alıcı" if receiver.role == "ED_RX_PRIMARY" else "İkinci alıcı",
                "serial": receiver.serial,
                "serialShort": f"…{receiver.serial[-8:]}",
                "purpose": receiver.purpose,
                "state": "Denetlenmedi",
                "stateKey": "unverified",
            }
            for receiver in self._device_config.configured_receivers
        ]
        self._known_spurs_hz: tuple[int, ...] = ()
        self._live_spur_guard_binding: tuple[float, float, int] | None = None
        self._live_spur_guard_power: deque[np.ndarray] = deque(maxlen=LIVE_SPUR_GUARD_WINDOW)
        self._live_spur_guard_passed: dict[int, bool] = {}
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._catalog_pool = QThreadPool(self)
        self._catalog_pool.setMaxThreadCount(1)
        self._receiver_health_pool = QThreadPool(self)
        self._receiver_health_pool.setMaxThreadCount(1)
        self._receiver_health_in_flight = False
        # A QRunnable can finish before its queued completion signal reaches
        # the GUI thread.  Keep its Python owner alive until that signal is
        # consumed; otherwise a fast probe can leave the UI permanently busy.
        self._active_task_refs: set[object] = set()
        self._parameter_catalog_pending_outcomes = 0
        self._parameter_catalog_pending_inserted = 0
        self._parameter_catalog_latest_rows: list[dict[str, object]] | None = None
        self._parameter_catalog_buffer: list[
            tuple[tuple[object, ...], dict[str, object]]
        ] = []
        self._parameter_catalog_flush_timer = QTimer(self)
        self._parameter_catalog_flush_timer.setSingleShot(True)
        self._parameter_catalog_flush_timer.setInterval(500)
        self._parameter_catalog_flush_timer.timeout.connect(
            self._flush_parameter_catalog_buffer
        )
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
        self._receiver_health_timer = QTimer(self)
        self._receiver_health_timer.setInterval(RECEIVER_HEALTH_INTERVAL_MS)
        self._receiver_health_timer.timeout.connect(self._poll_receiver_health)

        self._generation = 0
        self._closed = False
        self._busy = False
        self._card_detection_profile = None
        self._card_detection_message = "Etkin tespit ayarları karttan henüz okunmadı."
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
        self._detection_settings = {
            "display_fft_size": 16384, "display_interval_frames": 15,
            "survey_frames": 128, "survey_guard_frames": 8,
        }
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
        self._active_receiver_serial = None
        self._known_spurs_hz = ()
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
        self._receiver_sample_rate_hz = 0.0
        self._live_receive_settings = {
            "center_hz": 104_650_000,
            "lna_db": OPERATOR_DEFAULT_LNA_GAIN_DB,
            "vga_db": OPERATOR_DEFAULT_VGA_GAIN_DB,
        }
        self._receiver_rf_amplifier = False
        self._listening_deemphasis_us = 0.0
        self._live_sample_rate_hz = 0
        self._live_frames_per_second = 0.0
        self._survey_controller = SurveyController(self, factory=survey_factory)
        self._survey_controller.preview.connect(self._survey_preview)
        self._survey_controller.finished.connect(self._survey_finished)
        self._pending_survey_parameter_frequency_hz: int | None = None
        self._pending_listening_frequency_hz: int | None = None
        self._listening_live_target_hz: float | None = None
        self._pending_live_measurement: Callable[[], RecordedMeasurement] | None = None
        self._pending_live_listening: Callable[
            [], tuple[AnalogMonitorResult, str, float, float, float, dict | None]
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
        self._listening_comparison: dict[str, tuple] = {}
        self._listening_parameter_target_hz: float | None = None
        self._listening_parameter_bandwidth_khz = 16.0
        self._listening_measured_bandwidth_hz: float | None = None
        self._listening_parameter_record_path = ""
        self._listening_state = "Doğrulanmış bir tespit seçin."
        self._listening_rows: list[dict[str, str]] = []
        self._listening_waveform: list[float] = []
        self._listening_observation_points: list[dict[str, float]] = []
        self._listening_short_preview = False
        self._listening_playback_state = "Ses hazırlanmadı"
        self._listening_playback_position_s = 0.0
        self._listening_playback_duration_s = 0.0

        self._df = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        self._df_sweep = AdaptiveDirectionSweep()
        self._df_points: list[dict[str, str]] = []
        self._df_status = "UYARLAMALI TARAMA SÜRÜYOR"
        self._df_relative = "—"
        self._df_bearing = "—"
        self._df_reference_key: tuple[str, float | None] | None = None
        self._direction_frame_power_dbfs: float | None = None
        self._direction_frame_frequency_hz: float | None = None
        self._direction_frame_bandwidth_hz: float | None = None
        self._direction_receiver_binding = ""
        self._direction_frame_id: int | None = None
        self._pending_direction_measurement: dict[str, object] | None = None
        self._df_capture_binding = None
        self._df_capture_message = ""
        self._df_channel_span: tuple[int, int] | None = None
        self._df_target_frequency_hz: float | None = None
        self._df_target_event_id: int | None = None

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

    @Property(bool, notify=stateChanged)
    def fixedVerificationActive(self) -> bool:
        return self._fixed_verification_candidate is not None and self._fixed_verifier is not None

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
    def sampleRateTitle(self) -> str:
        return "ÖRNEKLEME HIZI"

    @Property(str, notify=stateChanged)
    def sampleRateText(self) -> str:
        if self._source is None and not self._live_has_data:
            return "—"
        rate = self._receiver_sample_rate_hz if self._source_mode == "hackrf" else self.sampleRateHz
        if rate <= 0:
            return "—"
        return f"{rate / 1_000_000:g} MS/s" if rate >= 1_000_000 else f"{rate / 1_000:g} kS/s"

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
        self._poll_direction_capture()
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

    @Property("QVariantMap", notify=detectionSettingsChanged)
    def detectionSettings(self):
        return dict(self._detection_settings)

    @Property(bool, notify=detectionSettingsChanged)
    def receiverRFAmplifier(self):
        return self._receiver_rf_amplifier

    @Property(float, notify=detectionSettingsChanged)
    def listeningDeemphasisUs(self):
        return self._listening_deemphasis_us

    @Slot(bool, float, result=bool)
    def setReceiverAndAudioSettings(self, rf_amplifier, deemphasis_us):
        # Settings never mutate a running capture or a pending measurement.
        if self._busy or self._live_session is not None or self._closed:
            return False
        if (type(rf_amplifier) is not bool or isinstance(deemphasis_us, bool)
                or not isinstance(deemphasis_us, (int, float))
                or not math.isfinite(deemphasis_us) or not 0 <= deemphasis_us <= 2000):
            return False
        if rf_amplifier != self._receiver_rf_amplifier:
            self._fixed_verification_records.clear()
            self._fixed_preserved_history = []
            self._fixed_verification_queue.clear()
            self._survey_controller.clearReference()
            if self._source_mode == "hackrf":
                self._clear_results(keep_source=True)
                self._live_has_data = False
        self._receiver_rf_amplifier = rf_amplifier
        self._listening_deemphasis_us = float(deemphasis_us)
        self.detectionSettingsChanged.emit()
        return True

    @Property("QVariantMap", notify=detectionProfileChanged)
    def cardDetectionProfile(self):
        profile = self._card_detection_profile
        return {"ready": profile is not None, "message": self._card_detection_message,
                "normal": f"{profile.alpha_q32 / (1 << 32):.10f}" if profile else "",
                "weak": f"{profile.weak_alpha_q32 / (1 << 32):.10f}" if profile else "",
                "generation": profile.generation if profile else 0,
                "fftSize": profile.fft_size if profile else 4096,
                "runtimeFftSupported": profile.runtime_fft_supported if profile else False}

    def _start_detection_profile_request(self, profile=None, *, reconcile_current=False):
        if self._busy or self._live_session is not None or self._closed:
            return False
        self._generation += 1
        generation = self._generation
        self._active_task_kind = "detection_config"
        self._set_busy(True, "Kart tespit ayarları doğrulanıyor…")
        def operation():
            try:
                requested = profile
                if reconcile_current and requested is not None:
                    current = exchange_profile(LIVE_BOARD_HOST, LIVE_BOARD_PORT)
                    if requested.fft_size < current.fft_size:
                        return {
                            "profile": current,
                            "error": "Daha küçük FPGA FFT boyutu için kartı yeniden başlatın.",
                        }
                    if not current.runtime_fft_supported and requested.fft_size != current.fft_size:
                        return {
                            "profile": current,
                            "error": "Kart imajı çalışma zamanında FFT değişimini desteklemiyor.",
                        }
                    requested = DetectionProfile(
                        current.generation,
                        requested.alpha_q32,
                        requested.weak_alpha_q32,
                        requested.fft_size,
                        current.runtime_fft_supported,
                    )
                return {"profile": exchange_profile(
                    LIVE_BOARD_HOST, LIVE_BOARD_PORT, profile=requested)}
            except Exception as exc:
                return {"error": str(exc) if isinstance(exc, DetectionConfigError) else "Kart tespit ayarları doğrulanamadı."}
        task = _Task(generation, "detection_config", operation)
        task.signals.completed.connect(self._on_detection_profile_completed)
        self._start_retained_task(self._pool, task)
        return True

    @Slot()
    def refreshCardDetectionProfile(self):
        self._start_detection_profile_request()

    @Slot(str, str, result=bool)
    def applyCardDetectionProfile(self, normal, weak):
        fft_size = self._card_detection_profile.fft_size if self._card_detection_profile else 4096
        return self._apply_card_detection_profile(fft_size, normal, weak)

    @Slot(int, str, str, result=bool)
    def applyCardDetectionProfileWithFFT(self, fft_size, normal, weak):
        return self._apply_card_detection_profile(fft_size, normal, weak)

    def _apply_card_detection_profile(self, fft_size, normal, weak):
        if self._busy or self._card_detection_profile is None:
            return False
        try:
            if fft_size not in (4096, 8192, 16384):
                raise ValueError()
            if (not self._card_detection_profile.runtime_fft_supported
                    and fft_size != self._card_detection_profile.fft_size):
                raise DetectionConfigError("Kart imajı çalışma zamanında FFT değişimini desteklemiyor.")
            values = [Decimal(value.strip().replace(",", ".")) for value in (normal, weak)]
            if any(not value.is_finite() or value < 1 or value >= limit
                   for value, limit in zip(values, (16, 4))):
                raise ValueError()
            quantized = [int((value * (1 << 32)).to_integral_value(rounding=ROUND_HALF_EVEN)) for value in values]
            profile = DetectionProfile(
                self._card_detection_profile.generation, *quantized, fft_size,
                self._card_detection_profile.runtime_fft_supported)
        except DetectionConfigError as exc:
            self._card_detection_message = str(exc)
            self.detectionProfileChanged.emit()
            return False
        except (InvalidOperation, ValueError):
            self._card_detection_message = (
                "FFT 4096, 8192 veya 16384 olmalı ve kart imajı seçimi desteklemeli. "
                "Normal katsayı 1–16, zayıf katsayı 1–4 aralığında ve üst sınırdan "
                "küçük olmalı; zayıf eşik normali aşamaz.")
            self.detectionProfileChanged.emit()
            return False
        return self._start_detection_profile_request(
            profile,
            reconcile_current=(
                self._card_detection_profile.runtime_fft_supported
                and fft_size < self._card_detection_profile.fft_size
            ),
        )

    @Slot(result=bool)
    def restoreCardDetectionProfile(self):
        if self._card_detection_profile is None:
            return False
        if (self._card_detection_profile.runtime_fft_supported
                and self._card_detection_profile.fft_size > 4096):
            self._card_detection_message = (
                "4096 varsayılanına dönmek için kartı yeniden başlatın; "
                "tam güç kesmeli cold-start gerekmez."
            )
            self.detectionProfileChanged.emit()
            return False
        return self._start_detection_profile_request(DetectionProfile(
            self._card_detection_profile.generation, NORMAL_DEFAULT, WEAK_DEFAULT,
            4096, self._card_detection_profile.runtime_fft_supported))

    @Slot(int, str, object, float)
    def _on_detection_profile_completed(self, generation, kind, result, elapsed):
        if generation != self._generation or self._closed:
            return
        self._card_detection_profile = result.get("profile")
        self._card_detection_message = result.get("error", "Etkin katsayılar FPGA’dan okundu. Yeni alım bu profille başlayacak.")
        self._active_task_kind = ""
        self._set_busy(False, self._card_detection_message)
        self.detectionProfileChanged.emit()

    @Slot(int, int, int, int, result=bool)
    def setDetectionSettings(self, fft_size, interval, survey_frames, guard_frames):
        if self._busy or self._live_session is not None:
            return False
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in (fft_size, interval, survey_frames, guard_frames)):
            return False
        if (fft_size not in (4096, 8192, 16384) or interval not in (8, 15, 32, 64)
                or survey_frames not in (64, 128, 256, 512)
                or guard_frames not in (8, 16, 32)
                or guard_frames >= survey_frames - 3):
            return False
        self._detection_settings = {
            "display_fft_size": fft_size, "display_interval_frames": interval,
            "survey_frames": survey_frames, "survey_guard_frames": guard_frames,
        }
        self.detectionSettingsChanged.emit()
        return True

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
            or self._live_fpga_fft_size() != 4096
            or selected is None
            or not bool(selected.get("confirmed", selected["stateKey"] == "confirmed"))
            or not hasattr(session, "measurement_window")
        ):
            return False
        # Range setup is based on the last immutable four-frame FPGA window.
        # The actual measurement still uses current_measurement_window() and
        # remains armed until a fresh four-frame window passes ownership checks.
        # Requiring the setup UI to coincide with that sub-10 ms window made a
        # valid survey handoff fall back to "Tespit bekliyor" before an operator
        # could confirm the range.
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

    @Property("QVariantList", notify=parameterCatalogChanged)
    def parameterHistory(self) -> list[dict[str, object]]:
        return self._automatic_parameter_rows

    @Property(str, notify=parameterCatalogChanged)
    def parameterCatalogSummary(self) -> str:
        count = len(self._automatic_parameter_rows)
        return f"{count} kayıt" if count else "Henüz kayıt yok"

    @Property(str, notify=parameterCatalogChanged)
    def parameterCatalogPath(self) -> str:
        return str(self._parameter_catalog_path)

    @Property(str, notify=parameterCatalogChanged)
    def automaticParameterStatus(self) -> str:
        return self._automatic_parameter_status

    @Property(str, notify=parameterCatalogChanged)
    def parameterCatalogActionStatus(self) -> str:
        return self._parameter_catalog_action_status

    @Property("QVariantList", notify=stateChanged)
    def receiverRows(self) -> list[dict[str, str]]:
        return self._receiver_rows

    @Property(str, notify=stateChanged)
    def receiverSummary(self) -> str:
        found = sum(row["stateKey"] == "found" for row in self._receiver_rows)
        return f"{found}/{len(self._receiver_rows)} yapılandırılmış HackRF tanındı"

    @Slot()
    def refreshParameterCatalog(self) -> None:
        try:
            if self._parameter_catalog is None:
                raise ValueError("Parametre kataloğu kullanılamıyor.")
            self._automatic_parameter_rows = self._parameter_catalog.rows()
            if self._automatic_parameter_status.startswith("Katalog okunamadı:"):
                self._automatic_parameter_status = "Katalog hazır."
            self._parameter_catalog_action_status = (
                f"Katalog yenilendi · {len(self._automatic_parameter_rows)} kayıt okunuyor."
            )
            self._add_log("Parametre kataloğu", self._parameter_catalog_action_status)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._automatic_parameter_status = f"Katalog okunamadı: {exc}"
            self._parameter_catalog_action_status = self._automatic_parameter_status
            self._add_log("Parametre kataloğu", self._parameter_catalog_action_status)
        self.parameterCatalogChanged.emit()

    @Slot(result=bool)
    def openParameterCatalogFolder(self) -> bool:
        folder = self._parameter_catalog_path.parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._parameter_catalog_action_status = f"Kayıt klasörü hazırlanamadı: {exc}"
            self._add_log("Parametre kataloğu", self._parameter_catalog_action_status)
            self.parameterCatalogChanged.emit()
            return False
        opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))))
        if not opened and hasattr(os, "startfile"):
            try:
                os.startfile(str(folder))
                opened = True
            except OSError:
                opened = False
        self._parameter_catalog_action_status = (
            f"Kayıt klasörü açıldı: {folder}" if opened else
            f"Kayıt klasörü açılamadı: {folder}"
        )
        self._add_log("Parametre kataloğu", self._parameter_catalog_action_status)
        self.parameterCatalogChanged.emit()
        return opened

    @Slot(result=str)
    def exportParameterCatalog(self) -> str:
        try:
            if self._parameter_catalog is None:
                raise ValueError("Parametre kataloğu kullanılamıyor.")
            path = self._parameter_catalog.export_csv()
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._parameter_catalog_action_status = f"CSV dışa aktarılamadı: {exc}"
            self._add_log("Parametre kataloğu", self._parameter_catalog_action_status)
            self.parameterCatalogChanged.emit()
            return ""
        self._parameter_catalog_action_status = f"CSV dışa aktarıldı: {path}"
        self._add_log("Parametre kataloğu", f"CSV dışa aktarıldı: {path}")
        self.parameterCatalogChanged.emit()
        return str(path)

    @Property("QVariantMap", notify=stateChanged)
    def measurementInfo(self):
        return self._measurement_info if self._parameter_rows else {}

    @Property(bool, notify=stateChanged)
    def parameterMeasurementActive(self):
        return self._measurement_requested and (
            self._pending_live_measurement is not None
            or self._active_task_kind == "measurement"
            or (self._source_mode == "hackrf" and self._live_session is not None)
        )

    @Property(str, notify=stateChanged)
    def measurementRecordPath(self) -> str:
        return self._measurement_record_path if self._parameter_rows else ""

    @Property(bool, constant=True)
    def parameterCapabilityReady(self) -> bool:
        return self._parameter_capability is not None

    @Property(bool, notify=detectionsChanged)
    def analysisSpanConfirmed(self) -> bool:
        return self._analysis_span is not None

    @Property(bool, notify=detectionsChanged)
    def analysisSpanLimited(self) -> bool:
        bins = self._analysis_span_bins()
        start = self._selected_detection_bin("startBin")
        end = self._selected_detection_bin("endBin")
        return bool(
            bins is not None
            and start is not None
            and end is not None
            and not (bins[0] <= min(start, end) and max(start, end) <= bins[1])
        )

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
            "UYARLAMALI TARAMA SÜRÜYOR": self._df_sweep.status_text,
            "LOB HAZIR": "Bağıl tepe yönü hazır",
            "YETERSİZ AÇI": "Lob sınırları ve hassas ölçümler tamamlanmadı",
            "YETERSİZ AÇI KAPSAMI": "Lob sınırları yeterli biçimde çevrelenmedi",
            "YETERSİZ TEKRAR": "Her açı için ek güç ölçümü gerekli",
            "ALICI AYARI DEĞİŞTİ": "Alıcı ayarları ölçüm sırasında değişti",
            "HEDEF FREKANSI DEĞİŞTİ": "Aynı RF kaynağı izlenemedi",
            "ÖN/ARKA BELİRSİZ": "Anten ön ve arka yönü ayıramadı",
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
        if self._source_mode == "hackrf":
            return self._df_sweep.progress
        return min(1.0, self.directionDistinctAngleCount / 24.0)

    @Property(bool, notify=directionChanged)
    def directionSweepComplete(self) -> bool:
        if self._source_mode == "hackrf":
            return self._df_sweep.complete
        return self._next_clockwise_direction_angle() is None

    @Property(float, notify=directionChanged)
    def directionNextAngleDeg(self) -> float:
        angle = self._next_clockwise_direction_angle()
        return -1.0 if angle is None else angle

    @Property(str, notify=directionChanged)
    def directionNextAngleText(self) -> str:
        angle = self._next_clockwise_direction_angle()
        if angle is None:
            return "TARAMA TAMAMLANDI" if self.directionSweepComplete else "LOB SINIRI BULUNAMADI"
        return f"{angle:.0f}°"

    @Property(str, notify=directionChanged)
    def directionStepInstructionText(self) -> str:
        if self._source_mode == "hackrf":
            return self._df_sweep.instruction_text
        angle = self._next_clockwise_direction_angle()
        if angle is None:
            return "Uyarlamalı anten taraması tamamlandı."
        if angle == 0.0:
            return "Antenin başlangıç yönünü 0° kabul edin ve ilk ölçümü alın."
        if angle > 180.0:
            return (
                f"Anteni başlangıç yönünden saat yönünün tersine "
                f"{360.0 - angle:.0f}° konumuna çevirin ve ölçümü alın."
            )
        return f"Anteni başlangıç yönünden saat yönünde {angle:.0f}° konumuna çevirin ve ölçümü alın."

    @Property(str, notify=directionChanged)
    def directionRequirementText(self) -> str:
        count = self.directionDistinctAngleCount
        if self._source_mode == "hackrf":
            return f"{count} farklı açı · {self._df_sweep.status_text}"
        return f"{count} farklı açı · {self.directionMeasurementCount} ölçüm"

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
        if self._source_mode == "hackrf" and self.selectedDetectionReady:
            return "Ölçümle alınır"
        power = self._direction_frame_power_dbfs
        return "—" if power is None else f"{power:.2f} dBFS"

    @Property(bool, notify=stateChanged)
    def directionMeasurementReady(self) -> bool:
        if self._source_mode == "hackrf":
            return not self._direction_unavailable_reason()
        return bool(
            self.selectedDetectionReady
            and self._direction_frame_power_dbfs is not None
            and self._direction_frame_frequency_hz is not None
            and self._direction_frame_bandwidth_hz is not None
        )

    @Property(str, notify=stateChanged)
    def directionCaptureText(self) -> str:
        if self._source_mode != "hackrf":
            return self.directionTargetText
        reason = self._direction_unavailable_reason()
        if self._pending_direction_measurement is None and reason:
            return reason
        return self._df_capture_message or reason or self.directionStepInstructionText

    @Property(bool, notify=stateChanged)
    def directionCapturePending(self) -> bool:
        return self._pending_direction_measurement is not None

    @Property(bool, notify=stateChanged)
    def directionChannelLocked(self) -> bool:
        return self._df_channel_span is not None

    @Property(bool, notify=stateChanged)
    def directionCaptureCancellable(self) -> bool:
        return bool(self._pending_direction_measurement is not None
                    and "deadline" in self._pending_direction_measurement)

    @Property(str, notify=spectrumChanged)
    def directionTargetText(self) -> str:
        frequency_hz = self._direction_frame_frequency_hz
        bandwidth_hz = self._direction_frame_bandwidth_hz
        if self._source_mode == "hackrf":
            selected = self._selected_detection_item()
            if self._df_channel_span is not None:
                frequency_hz = self._df_target_frequency_hz
                bandwidth_hz = (self._df_channel_span[1] - self._df_channel_span[0] + 1) * self.sampleRateHz / 4096.0
            elif selected is not None:
                frequency_hz = self._df_target_frequency_hz or float(selected["frequencyHz"])
                span = self._df_channel_span or self._analysis_span_draft
                if span is not None:
                    bandwidth_hz = (span[1] - span[0] + 1) * self.sampleRateHz / 4096.0
        if frequency_hz is None or bandwidth_hz is None:
            return "Doğrulanmış bir tespit seçin"
        return (
            f"{self._format_frequency(frequency_hz)} · "
            f"{self._format_rate(bandwidth_hz)} kanal"
        )


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

    @Property(float, notify=detectionsChanged)
    def listeningSuggestedOffsetKHz(self) -> float:
        if self._listening_parameter_target_hz is not None and self.centerFrequencyHz > 0.0:
            return (self._listening_parameter_target_hz - self.centerFrequencyHz) / 1_000.0
        return self.selectedDetectionOffsetKHz

    @Property(float, notify=detectionsChanged)
    def listeningSuggestedBandwidthKHz(self) -> float:
        return self._listening_parameter_bandwidth_khz

    @Property(str, notify=listeningChanged)
    def listeningParameterBasisText(self) -> str:
        if self._listening_parameter_target_hz is None:
            return ""
        return (
            f"Parametre ölçümü · {self._format_frequency(self._listening_parameter_target_hz)} · "
            f"Önerilen kanal {self._format_rate(self._listening_parameter_bandwidth_khz * 1_000.0)}"
        )

    @Property(str, notify=listeningChanged)
    def listeningBandwidthWarning(self) -> str:
        width = self._listening_measured_bandwidth_hz
        if width is not None and width > 25_000:
            return "Ölçülen yayın 25 kHz'den geniş. Bu dar bant ses yolu yayının tamamını kapsamaz; doğru çözümleme garanti edilmez."
        return ""

    def _listening_channel_target_hz(self) -> float | None:
        target = self._listening_parameter_target_hz
        if target is not None and math.isfinite(float(target)):
            return float(target)
        target = self._listening_live_target_hz
        if target is not None and math.isfinite(float(target)):
            return float(target)
        selected = self._selected_detection_item()
        if selected is None:
            return None
        value = selected.get("frequencyHz")
        return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None

    @Property("QStringList", notify=listeningChanged)
    def listeningComparisonModes(self):
        return list(getattr(self, "_listening_comparison", {}))

    @Property(bool, notify=listeningChanged)
    def listeningReady(self) -> bool:
        return self._listening_result is not None

    @Property(bool, notify=stateChanged)
    def listeningSelectionReady(self) -> bool:
        if self._source_mode != "hackrf":
            return self.selectedDetectionReady
        session = self._live_session
        selected = self._selected_detection_item()
        target_hz = self._listening_channel_target_hz()
        if (
            session is not None
            and target_hz is not None
            and hasattr(session, "audio_channel_ready")
        ):
            buffer_ready = session.audio_channel_ready(target_hz)
        else:
            buffer_ready = bool(
                session is not None
                and hasattr(session, "audio_window_ready")
                and session.audio_window_ready(self._selected_detection_id)
            )
        return bool(
            session is not None
            and selected is not None
            and self.selectedDetectionReady
            and self._pending_live_listening is None
            and self._pending_live_measurement is None
            and buffer_ready
        )

    @Property(str, notify=stateChanged)
    def liveListeningBufferText(self) -> str:
        if self._source_mode != "hackrf":
            return ""
        session = self._live_session
        if session is None or not hasattr(session, "audio_window_frame_count"):
            return "Dinleme verisi hazır değil"
        # This counter describes the contiguous I/Q data already captured. The
        # channel confidence gate is reported separately below; using its reset
        # counter here made an intact receiver stream appear to restart whenever
        # the detector briefly lost a modulated signal.
        count = session.audio_window_frame_count()
        frames = min(LIVE_AUDIO_WINDOW_FRAMES, int(count))
        seconds = frames * 4096.0 / self.sampleRateHz if self.sampleRateHz > 0.0 else 0.0
        prefix = f"Dinleme verisi {seconds:.1f} / {LIVE_AUDIO_WINDOW_SECONDS:.1f} s"
        if frames < LIVE_AUDIO_WINDOW_FRAMES:
            return prefix

        target_hz = self._listening_channel_target_hz()
        if target_hz is not None and hasattr(session, "audio_channel_quality"):
            quality = dict(session.audio_channel_quality(target_hz))
        elif self._selected_detection_id >= 0 and hasattr(session, "audio_window_quality"):
            quality = dict(session.audio_window_quality(self._selected_detection_id))
        else:
            quality = {}
        if quality.get("acceptable", False):
            return prefix + " · sinyal hazır"
        if int(quality.get("invalid_frames", 0)) > 0:
            return prefix + " · aynı kanalda birden fazla aday var"
        if quality:
            return prefix + " · hedef sinyal kesiliyor"
        return prefix + " · sinyal doğrulanıyor"

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

    @Property("QVariantList", notify=listeningChanged)
    def listeningObservationPoints(self) -> list[dict[str, float]]:
        return self._listening_observation_points

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
        self._receiver_health_timer.stop()
        self._missing_receiver_error_visible = False
        self._generation += 1
        self._close_source()
        self._source_mode = mode  # type: ignore[assignment]
        self._receiver_sample_rate_hz = 0.0
        self._source_name = "Kaynak seçilmedi"
        self._source_state = "Kullanılmıyor"
        self._error_title = ""
        self._error_message = ""
        self._hackrf_ready = False
        self._hackrf_transfer_executable = ""
        self._active_receiver_serial = None
        self._known_spurs_hz = ()
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
        self._pending_listening_frequency_hz = None
        self._clear_listening_parameter_basis()
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
        self._receiver_health_timer.stop()
        self.stop()
        self._probe_error_timer.stop()
        self._missing_receiver_error_visible = False
        self._generation += 1
        generation = self._generation
        self._set_busy(True, "Alıcı bağlantısı denetleniyor…")

        def operation() -> tuple[ToolInventory, DeviceStatus, bool, str, str]:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="receiver-probe") as executor:
                hackrf_future = executor.submit(self._probe_hackrf_device)
                fpga_future = executor.submit(self._probe_fpga_service)
                inventory, device = hackrf_future.result()
                fpga_ready, fpga_reason = fpga_future.result()

            portapack_error = ""
            if (
                fpga_ready
                and inventory.receive_available
                and not self._configured_receiver_is_visible(device)
                and self._portapack_mode_switcher is not None
            ):
                try:
                    self._portapack_mode_switcher()
                except AcquisitionError as exc:
                    portapack_error = exc.code
                else:
                    deadline = time.monotonic() + PORTAPACK_REENUMERATION_TIMEOUT_SECONDS
                    while True:
                        device = self._backend.discover_device()
                        if self._configured_receiver_is_visible(device):
                            break
                        if time.monotonic() >= deadline:
                            portapack_error = "portapack_mode_timeout"
                            break
                        time.sleep(PORTAPACK_REENUMERATION_POLL_SECONDS)
            return inventory, device, fpga_ready, fpga_reason, portapack_error

        self._submit(generation, "probe", operation)

    def _probe_hackrf_device(self) -> tuple[ToolInventory, DeviceStatus]:
        inventory = self._backend.discover_tools(inspect_help=True)
        if not inventory.receive_available:
            return inventory, DeviceStatus("TOOLCHAIN_UNAVAILABLE", reason_code="tools_unavailable")
        return inventory, self._backend.discover_device()

    def _selected_configured_receiver(self, device: DeviceStatus):
        if device.state not in {"ONE_DEVICE", "MULTIPLE_DEVICES"}:
            return None
        discovered = {item.serial.casefold() for item in device.devices}
        configured = sorted(
            self._device_config.configured_receivers,
            key=lambda receiver: receiver.role != "ED_RX_PRIMARY",
        )
        return next(
            (receiver for receiver in configured if receiver.serial.casefold() in discovered),
            None,
        )

    def _configured_receiver_is_visible(self, device: DeviceStatus) -> bool:
        return self._selected_configured_receiver(device) is not None

    @Slot()
    def _poll_receiver_health(self) -> None:
        if (
            self._closed
            or not self._hackrf_ready
            or self._busy
            or self._live_session is not None
            or self._active_receiver_serial is None
            or self._receiver_health_in_flight
        ):
            return
        generation = self._generation
        self._receiver_health_in_flight = True
        task = _Task(generation, "receiver_health", self._backend.discover_device)
        task.signals.completed.connect(self._receiver_health_completed)
        task.signals.failed.connect(self._receiver_health_failed)
        self._start_retained_task(self._receiver_health_pool, task)

    @Slot(int, str, object, float)
    def _receiver_health_completed(
        self, generation: int, kind: str, result: object, elapsed: float
    ) -> None:
        del kind, elapsed
        self._receiver_health_in_flight = False
        if (
            generation != self._generation
            or self._closed
            or not self._hackrf_ready
            or not isinstance(result, DeviceStatus)
            or self._active_receiver_serial is None
        ):
            return
        if result.state not in {"NO_DEVICE", "ONE_DEVICE", "MULTIPLE_DEVICES"}:
            # An inconclusive diagnostic is retried; it does not prove that a
            # previously identified USB receiver disappeared.
            return
        active_serial = self._active_receiver_serial.casefold()
        active_visible = result.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"} and any(
            device.serial.casefold() == active_serial for device in result.devices
        )
        if not active_visible:
            self._revoke_receiver_readiness()
            self._source_state = "Hata"
            self._show_error("receiver_connection_lost", result.reason_code)
            self.pipelineChanged.emit()
            self.stateChanged.emit()

    @Slot(int, str, str)
    def _receiver_health_failed(self, generation: int, code: str, detail: str) -> None:
        del generation, code, detail
        # A failed diagnostic is not proof that the receiver disappeared. The
        # next bounded poll retries without changing operator-visible readiness.
        self._receiver_health_in_flight = False

    def _revoke_receiver_readiness(self) -> None:
        self._receiver_health_timer.stop()
        self._hackrf_ready = False
        self._hackrf_transfer_executable = ""
        self._active_receiver_serial = None
        self._known_spurs_hz = ()

    def _receiver_role_for_serial(self, serial: str) -> str:
        serial_key = serial.casefold()
        return next(
            (
                receiver.role
                for receiver in self._device_config.configured_receivers
                if receiver.serial.casefold() == serial_key
            ),
            "ED_RX_UNASSIGNED",
        )

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
        if self._pending_direction_measurement is not None:
            return
        self._df_capture_message = ""
        if self._pending_live_listening is not None or self._pending_live_measurement is not None or (
            self._busy and self._active_task_kind in {"listening", "measurement"}
        ):
            return
        selected_row = next(
            (item for item in self._detections if int(item["eventId"]) == event_id), None
        )
        if selected_row is None:
            return
        if event_id != self._selected_detection_id:
            target_hz = self._pending_listening_frequency_hz
            preserves_handoff = False
            if target_hz is not None and self._source_mode == "hackrf":
                row_frequency_hz = float(selected_row["frequencyHz"])
                preserves_handoff = bool(
                    float(selected_row.get("lowerFrequencyHz", row_frequency_hz)) - 50_000.0
                    <= target_hz
                    <= float(selected_row.get("upperFrequencyHz", row_frequency_hz)) + 50_000.0
                )
            if not preserves_handoff:
                self._pending_listening_frequency_hz = None
                self._clear_listening_parameter_basis()
        if event_id != self._selected_detection_id:
            self._clear_listening("Seçili kanal değişti; dinlemeyi yeniden hazırlayın.")
            self._listening_live_target_hz = (
                float(selected_row["frequencyHz"])
                if self._source_mode == "hackrf"
                else None
            )
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
        if self._last_result is not None:
            self._set_direction_channel_power(self._last_result.spectrum)
            self.spectrumChanged.emit()
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
        if self._pending_listening_frequency_hz is None:
            self._clear_listening_parameter_basis()
        self._selected_detection_id = -1
        self._listening_live_target_hz = None
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
        self._receiver_health_timer.stop()
        self._playback_timer.stop()
        self._parameter_catalog_flush_timer.stop()
        self._generation += 1
        self._backend.cancel()
        self._pool.waitForDone(2000)
        self._receiver_health_pool.waitForDone(2000)
        self._flush_parameter_catalog_buffer()
        self._catalog_pool.waitForDone(2500)
        self._active_task_refs.clear()
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
        self._start_retained_task(self._pool, task)

    def _start_retained_task(self, pool: QThreadPool, task: object) -> None:
        """Start a Qt worker and retain it through queued signal delivery."""
        self._active_task_refs.add(task)

        def release(*_args, retained=task) -> None:
            self._active_task_refs.discard(retained)

        task.signals.completed.connect(release)
        task.signals.failed.connect(release)
        pool.start(task)

    @Slot(int, object)
    def _live_preview(self, generation: int, prepared: object) -> None:
        if isinstance(prepared, _LiveMailbox):
            prepared = prepared.take()
        if generation != self._generation or self._live_session is None or prepared is None:
            return
        display_spectrum = None
        if len(prepared) == 3:
            preview, spectrum, processing_ms = prepared
        else:
            # Compatibility with older/injected live-task fixtures.
            preview, spectrum, _coarse, processing_ms = prepared
            if isinstance(_coarse, type(spectrum)):
                display_spectrum = _coarse
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
        self._update_spectrum_result(spectrum, display_spectrum=display_spectrum)
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

    def _queue_parameter_catalog_write(
        self,
        generation: int,
        outcomes: tuple[object, ...],
        configuration: object,
        output_amplitude_scale: float,
    ) -> None:
        catalog = self._parameter_catalog
        if catalog is None:
            return
        if configuration is None:
            self._automatic_parameter_status = "Kayıt hatası · canlı alıcı yapılandırması kullanılamıyor."
            self._add_log("Parametre kataloğu", self._automatic_parameter_status)
            self.parameterCatalogChanged.emit()
            return
        outcome_count = len(outcomes)
        if self._parameter_catalog_pending_outcomes + outcome_count > 1024:
            self._live_presentation_error = (
                "parameter_delivery_overflow",
                "Arayüz parametre kayıtlarını zamanında alamadı; alım durduruldu.",
            )
            if self._live_session is not None:
                self._live_session.cancel()
            return
        session_id = (
            self._live_catalog_session_id
            or f"{self._measurement_namespace}:{generation}"
        )
        receiver_serial = str(getattr(configuration, "device_serial"))
        context = {
            "session_id": session_id,
            "receiver_role": self._receiver_role_for_serial(receiver_serial),
            "receiver_serial": receiver_serial,
            "sample_rate_hz": 2_000_000,
            "lna_gain_db": int(getattr(configuration, "lna_gain_db")),
            "vga_gain_db": int(getattr(configuration, "vga_gain_db")),
            "output_amplitude_scale": output_amplitude_scale,
            "rf_amplifier": bool(getattr(configuration, "rf_amplifier", False)),
        }

        self._parameter_catalog_pending_outcomes += outcome_count
        self._parameter_catalog_buffer.append((outcomes, context))
        if not self._parameter_catalog_flush_timer.isActive():
            self._parameter_catalog_flush_timer.start()

    @Slot()
    def _flush_parameter_catalog_buffer(self) -> None:
        catalog = self._parameter_catalog
        if catalog is None or not self._parameter_catalog_buffer:
            return
        buffered, self._parameter_catalog_buffer = self._parameter_catalog_buffer, []
        outcome_count = sum(len(outcomes) for outcomes, _context in buffered)
        groups: list[list[object]] = []
        for outcomes, context in buffered:
            if groups and groups[-1][0] == context:
                groups[-1][1].extend(outcomes)
            else:
                groups.append([context, list(outcomes)])

        def persist():
            inserted = 0
            for context, outcomes in groups:
                inserted += catalog.add_many(tuple(outcomes), **context)
            return inserted, catalog.rows() if inserted else None

        task = _CatalogTask(outcome_count, persist)
        task.signals.completed.connect(self._parameter_catalog_write_completed)
        task.signals.failed.connect(self._parameter_catalog_write_failed)
        self._start_retained_task(self._catalog_pool, task)

    @Slot(object)
    def _parameter_catalog_write_completed(self, payload: object) -> None:
        outcome_count, result = payload
        inserted, rows = result
        self._parameter_catalog_pending_outcomes = max(
            0, self._parameter_catalog_pending_outcomes - int(outcome_count)
        )
        self._parameter_catalog_pending_inserted += int(inserted)
        if rows is not None:
            self._parameter_catalog_latest_rows = list(rows)
        if self._parameter_catalog_pending_outcomes:
            return
        if self._parameter_catalog_latest_rows is not None:
            self._automatic_parameter_rows = self._parameter_catalog_latest_rows
        if self._parameter_catalog_pending_inserted:
            self._add_log(
                "Otomatik parametre",
                f"{self._parameter_catalog_pending_inserted} sonuç kalıcı kataloğa eklendi.",
            )
        self._parameter_catalog_pending_inserted = 0
        self._parameter_catalog_latest_rows = None
        self.parameterCatalogChanged.emit()

    @Slot(int, str)
    def _parameter_catalog_write_failed(self, outcome_count: int, detail: str) -> None:
        self._parameter_catalog_pending_outcomes = max(
            0, self._parameter_catalog_pending_outcomes - outcome_count
        )
        self._automatic_parameter_status = (
            f"Kayıt hatası · sonuç kataloğa yazılamadı: {detail}"
        )
        self._add_log("Parametre kataloğu", self._automatic_parameter_status)
        if not self._parameter_catalog_pending_outcomes:
            self._parameter_catalog_pending_inserted = 0
            self._parameter_catalog_latest_rows = None
            self.parameterCatalogChanged.emit()

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
        session = self._live_session
        automatic_status = str(
            getattr(session, "automatic_parameter_status", self._automatic_parameter_status)
        )
        if self._parameter_catalog is not None and automatic_status != self._automatic_parameter_status:
            self._automatic_parameter_status = automatic_status
            self.parameterCatalogChanged.emit()
        if snapshot.automatic_parameter_outcomes:
            configuration = getattr(session, "configuration", None)
            channelizer = getattr(session, "measurement_channelizer", None) or {}
            profile = channelizer.get("profile", {}) if isinstance(channelizer, dict) else {}
            scale = float(profile.get("output_amplitude_scale", 1.0))
            self._queue_parameter_catalog_write(
                generation,
                snapshot.automatic_parameter_outcomes,
                configuration,
                scale,
            )
        self._status_message = (
            f"Canlı FPGA karesi {snapshot.sequence_number + 1}/{self._frame_count} doğrulandı."
        )
        if (
            self._measurement_requested
            and self._pending_live_measurement is None
            and self._active_task_kind == "live"
        ):
            self._request_live_measurement()
        if first_response:
            self.pipelineChanged.emit()
            self.stateChanged.emit()

    @Slot(int, object, float)
    def _live_completed(self, generation: int, result: object, elapsed: float) -> None:
        del elapsed
        if generation != self._generation or not isinstance(result, LiveEDSessionResult):
            return
        self.cancelDirectionMeasurement()
        self._live_health_timer.stop()
        if self._live_presentation_error is not None:
            self._live_failed(generation, *self._live_presentation_error)
            return
        if self._parameter_catalog is not None:
            self._automatic_parameter_status = str(
                getattr(
                    self._live_session,
                    "automatic_parameter_status",
                    self._automatic_parameter_status,
                )
            )
        self.parameterCatalogChanged.emit()
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
        if self._pending_listening_frequency_hz is not None:
            self._pending_listening_frequency_hz = None
            self._clear_listening_parameter_basis()
            self._status_message = "Ölçülen sinyal dinleme için yeniden bulunamadı."
            self._add_log("Dinleme", self._status_message)
        self.pipelineChanged.emit()
        self.stateChanged.emit()
        self._start_pending_live_task()

    @Slot(int, str, str)
    def _live_failed(self, generation: int, code: str, detail: str) -> None:
        if generation != self._generation:
            return
        self.cancelDirectionMeasurement()
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
            self._pending_listening_frequency_hz = None
            self._clear_listening_parameter_basis()
            self._measurement_requested = False
            if code in READINESS_INVALIDATING_LIVE_ERRORS:
                self._revoke_receiver_readiness()
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
        portapack_error: str = "",
    ) -> None:
        selected_receiver = self._selected_configured_receiver(device)
        serial = selected_receiver.serial if selected_receiver is not None else None
        transfer = inventory.get("hackrf_transfer")
        discovered_serials = {
            item.serial.casefold() for item in device.devices
        } if device.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"} else set()
        receiver_rows: list[dict[str, str]] = []
        for receiver in self._device_config.configured_receivers:
            found = receiver.serial.casefold() in discovered_serials
            if found and inventory.receive_available:
                if serial is not None and receiver.serial.casefold() == serial.casefold():
                    state = (
                        "Tanındı · etkin ana RX yolu"
                        if receiver.role == "ED_RX_PRIMARY"
                        else "Tanındı · etkin yedek RX yolu"
                    )
                else:
                    state = "Tanındı · hazır yedek"
                state_key = "found"
            elif found:
                state, state_key = "Tanındı · RX aracı hazır değil", "unavailable"
            else:
                state, state_key = "Bulunamadı", "missing"
            receiver_rows.append(
                {
                    "role": receiver.role,
                    "roleLabel": "Birincil alıcı" if receiver.role == "ED_RX_PRIMARY" else "İkinci alıcı",
                    "serial": receiver.serial,
                    "serialShort": f"…{receiver.serial[-8:]}",
                    "purpose": receiver.purpose,
                    "state": state,
                    "stateKey": state_key,
                }
            )
        self._receiver_rows = receiver_rows
        self._hackrf_transfer_executable = ""
        self._error_title = ""
        self._error_message = ""
        hackrf_error = ""
        hackrf_detail = device.reason_code
        if not inventory.receive_available or device.state == "TOOLCHAIN_UNAVAILABLE":
            hackrf_error = "tools_unavailable"
        elif device.state == "NO_DEVICE":
            hackrf_error = "device_not_found"
        elif not self._device_config.configured_receivers:
            hackrf_error = "device_serial_unassigned"
            hackrf_detail = "device_serial_unassigned"
        elif serial is None:
            hackrf_error = "configured_serial_not_found"
            hackrf_detail = "configured_serial_not_found"
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
            self._revoke_receiver_readiness()
            if hackrf_error and not fpga_ready:
                code = "receiver_and_fpga_unavailable"
                detail = f"hackrf={hackrf_detail or hackrf_error}; fpga={fpga_reason or 'connection_failed'}"
            elif hackrf_error:
                code = portapack_error or hackrf_error
                detail = portapack_error or hackrf_detail or hackrf_error
            else:
                code = "connection_failed"
                detail = fpga_reason or "connection_failed"
            self._show_transient_probe_error(code, detail)
            self.pipelineChanged.emit()
            return

        self._hackrf_ready = True
        self._active_receiver_serial = serial
        self._known_spurs_hz = load_known_spurs(serial)
        self._source_state = "Hazır"
        found_receivers = sum(row["stateKey"] == "found" for row in self._receiver_rows)
        active_label = (
            "Birincil alıcı"
            if selected_receiver is not None and selected_receiver.role == "ED_RX_PRIMARY"
            else "İkinci alıcı (yedek)"
        )
        self._source_name = (
            f"{active_label} ve FPGA bağlı · {found_receivers}/"
            f"{len(self._receiver_rows)} HackRF tanındı"
        )
        self._status_message = f"{active_label} ve FPGA hazır; tarama başlatılabilir."
        self._add_log("Alıcı", self._status_message)
        self._receiver_health_timer.start()
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
        self._error_message = (
            detail
            if code == "candidate_drop" and detail
            else ERROR_TEXT.get(code, f"İşlem tamamlanamadı ({code}).")
        )
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
            "uncertain": "Tekrar ölçülmeli",
        }.get(state, "Ölçülemedi")


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
