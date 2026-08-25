"""Qt Quick presentation boundary for the release operator application."""

from __future__ import annotations

import math
import os
from pathlib import Path
import time
from typing import Callable, Literal

import numpy as np
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from algorithms.monitoring import (
    AnalogMonitor,
    AnalogMonitorConfig,
    AnalogMonitorResult,
    MonitoringError,
    write_wav,
)
from algorithms.p0.df import DFMeasurement, ManualAmplitudeDF
from algorithms.p0.field_df import AntennaReference, geographic_bearing_from_manual_reference
from algorithms.parameters import (
    AnalysisSpan,
    F1ParameterResult,
    F5ParameterEstimator,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
    suggest_analysis_span,
)
from algorithms.pipeline import (
    RuntimeFrameResult,
    RuntimePipeline,
    load_phase04f5_capability,
    resolve_default_operation_profile,
)
from algorithms.spectrum import SigMFFrameSource
from platforms.acquisition import (
    BoundedCI8FrameSource,
    CaptureResult,
    DeviceStatus,
    HackRFBackend,
    RXConfig,
    RealHackRFBackend,
    ToolInventory,
    load_ed_rx_config,
)

from .audio_playback import AudioPlayback


ERROR_TEXT = {
    "invalid_sigmf_contract": "SigMF sözleşmesi geçerli değil.",
    "source_open_failed": "Kayıt açılamadı.",
    "processing_failed": "İşleme tamamlanamadı.",
    "tools_unavailable": "HackRF komut satırı araçları bulunamadı.",
    "device_not_found": "Yapılandırılmış HackRF bulunamadı.",
    "operation_timeout": "Donanım yanıt süresi aşıldı.",
    "operation_cancelled": "İşlem durduruldu.",
    "insufficient_iq": "Dinleme için kaynakta yeterli kesintisiz I/Q örneği yok.",
    "insufficient_audio": "Seçili kanaldan kullanılabilir ses üretilemedi.",
    "invalid_channel_bandwidth": "Kanal bant genişliği kaynak sınırlarıyla uyumlu değil.",
    "nyquist_limit": "Seçili kanal kaynak Nyquist sınırını aşıyor.",
    "invalid_volume": "Ses düzeyi 0 ile 100 arasında olmalıdır.",
    "wav_write_failed": "WAV dosyası kaydedilemedi.",
}


PIPELINE_COMPONENTS = (
    {
        "id": "source",
        "name": "I/Q Kaynağı",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "SigMF sözleşmesini doğrular veya sınırlandırılmış HackRF RX alımını kaynak zincirine bağlar.",
        "hostPath": "algorithms/spectrum/source.py",
        "rtlPath": "",
    },
    {
        "id": "preprocess",
        "name": "Ön İşleme",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "Kareleme ve periyodik Hann penceresini doğrulanmış spektrum sözleşmesiyle uygular.",
        "hostPath": "algorithms/spectrum/dsp.py",
        "rtlPath": "algorithms/fpga/phase06b/rtl/axis_hann_window.sv",
    },
    {
        "id": "fft_power",
        "name": "FFT ve Lineer Güç",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "4096 nokta FFT ve güç hesabını yürütür; PL uygulaması donanım kabulü değildir.",
        "hostPath": "algorithms/spectrum/dsp.py",
        "rtlPath": "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    },
    {
        "id": "regional",
        "name": "Bölgesel Eşik",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "Doğrulanmış Bölgesel Eşik profiliyle kaba spektral adayları üretir.",
        "hostPath": "algorithms/detection/pipeline.py",
        "rtlPath": "algorithms/fpga/phase06g/rtl/axis_regional_detector.sv",
    },
    {
        "id": "temporal",
        "name": "Zamansal Doğrulama",
        "runtime": "HOST",
        "implementation": "Python · taşınabilir C karşılığı",
        "description": "Adayları kareler arasında ilişkilendirir ve 2/3 gözlem kuralıyla tespiti doğrular.",
        "hostPath": "algorithms/detection/pipeline.py",
        "rtlPath": "platforms/embedded/phase06j/src/phase06j_temporal.c",
    },
    {
        "id": "parameters",
        "name": "Parametre Ölçümü",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "Operatör onaylı analiz aralığında yalnız doğrulanmış parametre alanlarını ölçer.",
        "hostPath": "algorithms/parameters/f5_estimator.py",
        "rtlPath": "",
    },
    {
        "id": "monitoring",
        "name": "Analog Dinleme",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "Operatör seçimli AM/NFM kanalını 48 kHz mono PCM16 ses zincirine dönüştürür.",
        "hostPath": "algorithms/monitoring/dsp.py",
        "rtlPath": "",
    },
)


class _TaskSignals(QObject):
    completed = Signal(int, str, object, float)
    failed = Signal(int, str, str)


class _Task(QRunnable):
    """Run one bounded operation outside the GUI thread."""

    def __init__(self, generation: int, kind: str, operation: Callable[[], object]) -> None:
        super().__init__()
        self.generation = generation
        self.kind = kind
        self.operation = operation
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        started = time.perf_counter()
        try:
            result = self.operation()
        except Exception as exc:
            code = str(getattr(exc, "code", f"{self.kind}_failed"))
            self.signals.failed.emit(self.generation, code, type(exc).__name__)
            return
        self.signals.completed.emit(
            self.generation,
            self.kind,
            result,
            time.perf_counter() - started,
        )


class OperatorViewModel(QObject):
    """Bounded product state exposed to QML; it never manufactures RF data."""

    stateChanged = Signal()
    spectrumChanged = Signal()
    detectionsChanged = Signal()
    directionChanged = Signal()
    logChanged = Signal()
    listeningChanged = Signal()
    pipelineChanged = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        acquisition_backend: HackRFBackend | None = None,
        source_factory: Callable[..., SigMFFrameSource] = SigMFFrameSource,
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
        self._backend = acquisition_backend or RealHackRFBackend()
        self._device_config = load_ed_rx_config()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._advance)

        self._generation = 0
        self._closed = False
        self._busy = False
        self._pending_frame = False
        self._playing = False
        self._source: object | None = None
        self._source_mode: Literal["sigmf", "hackrf"] = "sigmf"
        self._source_name = "Kaynak seçilmedi"
        self._source_state = "Kullanılmıyor"
        self._status_message = "Gerçek bir SigMF kaydı seçin veya HackRF durumunu denetleyin."
        self._error_message = ""
        self._frame_index = 0
        self._frame_count = 0
        self._last_result: RuntimeFrameResult | None = None
        self._spectrum_values: list[float] = []
        self._spectrum_min_db = -120.0
        self._spectrum_max_db = 0.0
        self._viewport_points = 900
        self._detections: list[dict[str, object]] = []
        self._selected_detection_id = -1
        self._measurement_requested = False
        self._parameter_rows: list[dict[str, str]] = []
        self._analysis_span: AnalysisSpan | None = None
        self._analysis_span_draft: tuple[int, int] | None = None
        self._span_revision = 0
        self._event_observation_history: dict[int, list[tuple[int, bool]]] = {}
        self._reduced_motion = False
        self._hackrf_ready = False
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

        self._df = ManualAmplitudeDF()
        self._df_points: list[dict[str, str]] = []
        self._df_status = "En az üç farklı anten açısında gerçek güç ölçümü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
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

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=stateChanged)
    def sourceReady(self) -> bool:
        return self._source is not None

    @Property(bool, notify=stateChanged)
    def playing(self) -> bool:
        return self._playing

    @Property(int, notify=stateChanged)
    def frameIndex(self) -> int:
        return self._frame_index + 1 if self._frame_count else 0

    @Property(int, notify=stateChanged)
    def frameCount(self) -> int:
        return self._frame_count

    @Property(str, notify=stateChanged)
    def centerFrequencyText(self) -> str:
        if self._source is None:
            return "—"
        return self._format_frequency(float(getattr(self._source, "center_frequency_hz")))

    @Property(str, notify=stateChanged)
    def sampleRateText(self) -> str:
        if self._source is None:
            return "—"
        return self._format_rate(float(getattr(self._source, "sample_rate_hz")))

    @Property(float, notify=stateChanged)
    def centerFrequencyHz(self) -> float:
        return float(getattr(self._source, "center_frequency_hz", 0.0))

    @Property(float, notify=stateChanged)
    def sampleRateHz(self) -> float:
        return float(getattr(self._source, "sample_rate_hz", 0.0))

    @Property(str, notify=stateChanged)
    def calibrationText(self) -> str:
        return "Kalibrasyonsuz · dBFS" if self._source is not None else "—"

    @Property(str, constant=True)
    def profileSummary(self) -> str:
        return self._profile_summary

    @Property("QVariantList", notify=spectrumChanged)
    def spectrumValues(self) -> list[float]:
        return self._spectrum_values

    @Property(float, notify=spectrumChanged)
    def spectrumMinDb(self) -> float:
        return self._spectrum_min_db

    @Property(float, notify=spectrumChanged)
    def spectrumMaxDb(self) -> float:
        return self._spectrum_max_db

    @Property("QVariantList", notify=detectionsChanged)
    def detections(self) -> list[dict[str, object]]:
        return self._detections

    @Property(int, notify=detectionsChanged)
    def selectedDetectionId(self) -> int:
        return self._selected_detection_id

    @Property(bool, notify=detectionsChanged)
    def selectedDetectionReady(self) -> bool:
        return any(
            int(item["eventId"]) == self._selected_detection_id and item["stateKey"] == "confirmed"
            for item in self._detections
        )

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
        return self._normalized_shifted_bin(bins[0]) if bins is not None else -1.0

    @Property(float, notify=detectionsChanged)
    def analysisSpanEndNormalized(self) -> float:
        bins = self._analysis_span_bins()
        return self._normalized_shifted_bin(bins[1]) if bins is not None else -1.0

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
        return (
            self.parameterCapabilityReady
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
        source = "Hata" if self._error_message and self._source is None else self._source_state
        processing = (
            "Çalışıyor"
            if (self._playing or self._busy) and self._source is not None
            else "Hazır" if self._source is not None else "Kullanılmıyor"
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
                else "Bekliyor" if self._source is not None
                else "Kullanılmıyor"
            ),
        }
        return [dict(component, state=states[str(component["id"])]) for component in PIPELINE_COMPONENTS]

    @Slot(str, str, result=bool)
    def openImplementationLocation(self, component_id: str, target: str) -> bool:
        if not self._developer_mode or target not in {"host", "rtl"}:
            return False
        component = next((item for item in PIPELINE_COMPONENTS if item["id"] == component_id), None)
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
    def relativeArrivalText(self) -> str:
        return self._df_relative

    @Property(str, notify=directionChanged)
    def bearingText(self) -> str:
        return self._df_bearing

    @Property(str, notify=detectionsChanged)
    def listeningDetectionTitle(self) -> str:
        selected = next(
            (item for item in self._detections if int(item["eventId"]) == self._selected_detection_id),
            None,
        )
        return str(selected["title"]) if selected is not None else "Tespit seçilmedi"

    @Property(str, notify=detectionsChanged)
    def listeningDetectionFrequencyText(self) -> str:
        selected = next(
            (item for item in self._detections if int(item["eventId"]) == self._selected_detection_id),
            None,
        )
        return str(selected["frequency"]) if selected is not None else "—"

    @Property(float, notify=detectionsChanged)
    def selectedDetectionOffsetKHz(self) -> float:
        selected = next(
            (item for item in self._detections if int(item["eventId"]) == self._selected_detection_id),
            None,
        )
        return float(selected["offsetKHz"]) if selected is not None else 0.0

    @Property(bool, notify=listeningChanged)
    def listeningReady(self) -> bool:
        return self._listening_result is not None

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

    @Property(str, notify=stateChanged)
    def sourceDurationText(self) -> str:
        if self._source is None:
            return "—"
        duration = self._frame_count * int(getattr(self._source, "frame_length")) / self.sampleRateHz
        return f"{duration:.3f} s"

    @Slot(str)
    def setSourceMode(self, mode: str) -> None:
        if self._busy or mode not in {"sigmf", "hackrf"} or mode == self._source_mode:
            return
        self.stop()
        self._generation += 1
        self._close_source()
        self._source_mode = mode  # type: ignore[assignment]
        self._source_name = "Kaynak seçilmedi"
        self._source_state = "Kullanılmıyor"
        self._error_message = ""
        self._hackrf_ready = False
        self._status_message = (
            "Standart bir .sigmf-meta kaydı seçin."
            if mode == "sigmf"
            else "Önce yapılandırılmış ED_RX HackRF cihazını denetleyin."
        )
        self._clear_results()
        self.stateChanged.emit()

    @Slot(str)
    def openSigmf(self, value: str) -> None:
        if self._source_mode != "sigmf" or self._busy:
            return
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
        self._generation += 1
        generation = self._generation
        self._set_busy(True, "HackRF araçları ve ED_RX cihazı denetleniyor…")

        def operation() -> tuple[ToolInventory, DeviceStatus]:
            inventory = self._backend.discover_tools(inspect_help=True)
            if not inventory.receive_available:
                return inventory, DeviceStatus("TOOLCHAIN_UNAVAILABLE", reason_code="tools_unavailable")
            return inventory, self._backend.discover_device()

        self._submit(generation, "probe", operation)

    @Slot(float, float, int, int, int)
    def startHackrfCapture(
        self,
        center_frequency_hz: float,
        sample_rate_hz: float,
        lna_gain_db: int,
        vga_gain_db: int,
        sample_count: int,
    ) -> None:
        if self._source_mode != "hackrf" or not self._hackrf_ready or self._busy:
            return
        try:
            config = RXConfig(
                center_frequency_hz=int(center_frequency_hz),
                sample_rate_hz=int(sample_rate_hz),
                sample_count=sample_count,
                lna_gain_db=lna_gain_db,
                vga_gain_db=vga_gain_db,
                device_serial=self._device_config.serial,
            )
        except Exception as exc:
            self._show_error(str(getattr(exc, "code", "invalid_rx_config")), str(exc))
            return
        self.stop()
        self._generation += 1
        generation = self._generation
        self._set_busy(True, "Bounded HackRF RX alımı başlatılıyor…")
        self._submit(generation, "capture", lambda: self._backend.capture(config))

    @Slot()
    def startScan(self) -> None:
        if self._source is None or self._busy:
            return
        was_playing = self._playing
        if self._measurement_requested:
            self._measurement_requested = False
            self._parameter_rows = []
            self.detectionsChanged.emit()
        self._playing = True
        self._status_message = "Sinyal taraması çalışıyor."
        self._timer.start()
        self._request_frame()
        if not was_playing:
            self._add_log("İşleme", "Sinyal taraması başlatıldı")
            self.pipelineChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def pause(self) -> None:
        was_playing = self._playing
        self._playing = False
        self._timer.stop()
        if self._source is not None:
            self._status_message = "Tarama duraklatıldı."
            if was_playing:
                self._add_log("İşleme", "Sinyal taraması duraklatıldı")
                self.pipelineChanged.emit()
            self.stateChanged.emit()

    @Slot()
    def stop(self) -> None:
        self._playing = False
        self._timer.stop()

    @Slot(int)
    def selectDetection(self, event_id: int) -> None:
        if not any(int(item["eventId"]) == event_id for item in self._detections):
            return
        if event_id != self._selected_detection_id:
            self._clear_listening("Seçili kanal değişti; dinlemeyi yeniden hazırlayın.")
        self._selected_detection_id = event_id
        self._measurement_requested = False
        self._parameter_rows = []
        self._analysis_span = None
        self._prepare_analysis_span_draft(event_id)
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot(float, float)
    def setAnalysisSpanDraftNormalized(self, start: float, end: float) -> None:
        if not self.selectedDetectionReady or self._last_result is None:
            self._status_message = "Analiz aralığı için önce doğrulanmış bir tespit seçin."
            self.stateChanged.emit()
            return
        if not math.isfinite(start) or not math.isfinite(end):
            return
        lower = max(56, min(4039, int(round(min(start, end) * 4095.0))))
        upper = max(56, min(4039, int(round(max(start, end) * 4095.0))))
        event = next(
            (
                item for item in self._last_result.detection.active_events
                if item.event_id == self._selected_detection_id and item.state == "confirmed"
            ),
            None,
        )
        if event is None or not lower <= event.region.peak_bin <= upper:
            self._status_message = "Çizilen analiz aralığı seçili tespitin tepe frekansını içermelidir."
            self.stateChanged.emit()
            return
        width = upper - lower + 1
        if not 8 <= width <= 512:
            self._status_message = "Çizilen analiz aralığı 8–512 FFT hücresi arasında olmalıdır."
            self.stateChanged.emit()
            return
        self._analysis_span = None
        self._analysis_span_draft = (lower, upper)
        self._parameter_rows = []
        self._status_message = "Analiz aralığı taslağı spektrum üzerinden güncellendi; onay bekleniyor."
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot(float, float)
    def confirmAnalysisSpan(self, lower_mhz: float, upper_mhz: float) -> None:
        if not self.selectedDetectionReady or self._last_result is None:
            return
        if not math.isfinite(lower_mhz) or not math.isfinite(upper_mhz) or lower_mhz >= upper_mhz:
            self._status_message = "Analiz aralığı geçerli iki frekansla tanımlanmalıdır."
            self.stateChanged.emit()
            return
        spectrum = self._last_result.spectrum
        spacing = float(spectrum.bin_spacing_hz)
        center = float(spectrum.center_frequency_hz)
        lower = int(round((lower_mhz * 1_000_000.0 - center) / spacing + 2048.0))
        upper = int(round((upper_mhz * 1_000_000.0 - center) / spacing + 2048.0))
        event = next(
            (item for item in self._last_result.detection.active_events if item.event_id == self._selected_detection_id),
            None,
        )
        if event is None or not (lower <= event.region.peak_bin <= upper):
            self._status_message = "Analiz aralığı seçili tespitin tepe frekansını içermelidir."
            self.stateChanged.emit()
            return
        try:
            self._span_revision += 1
            self._analysis_span = AnalysisSpan(lower, upper, "operator_adjusted", self._span_revision)
        except ValueError:
            self._analysis_span = None
            self._status_message = "Analiz aralığı 8–512 FFT hücresi arasında ve kullanılabilir bant içinde olmalıdır."
            self.stateChanged.emit()
            return
        if lower < 56 or upper > 4039:
            self._analysis_span = None
            self._status_message = "Analiz aralığının iki yanında gürültü referans hücreleri kalmalıdır."
            self.stateChanged.emit()
            return
        self._analysis_span_draft = (lower, upper)
        self._parameter_rows = []
        self._status_message = "Analiz aralığı operatör tarafından onaylandı."
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def requestMeasurement(self) -> None:
        if self._parameter_capability is None or self._parameter_estimator is None:
            self._status_message = "Doğrulanmış parametre ölçüm profili kullanılamıyor; ölçüm kapalı."
            self.stateChanged.emit()
            return
        if not self.selectedDetectionReady or self._last_result is None or self._source is None or self._busy:
            return
        if self._analysis_span is None:
            self._status_message = "Ölçümden önce analiz aralığını doğrulayın ve onaylayın."
            self.stateChanged.emit()
            return
        event = next(
            (
                item for item in self._last_result.detection.active_events
                if item.event_id == self._selected_detection_id and item.state == "confirmed"
            ),
            None,
        )
        if event is None:
            return
        if not self._has_four_observed_frames(event.event_id):
            self._status_message = "Parametre ölçümü için seçili tespitin dört ardışık karede gözlenmesi gerekir."
            self.stateChanged.emit()
            return
        self.pause()
        self._measurement_requested = True
        source = self._source
        start_frame = self._frame_index - 3
        spectrum_processor = self._pipeline.processor
        candidates = tuple(
            MeasurementCandidate(
                int(item.event_id),
                int(item.seen_count),
                int(item.region.start_bin),
                int(item.region.end_bin),
                item.state == "confirmed",
            )
            for item in self._last_result.detection.active_events
            if item.observed_this_frame
        )
        context = MeasurementContext(
            self._generation,
            self._generation,
            self._generation,
            int(event.event_id),
            int(event.seen_count),
            (True, True, True, True),
            candidates,
        )
        intent = MeasurementIntent(
            self._generation,
            self._generation,
            self._generation,
            int(event.event_id),
            int(event.seen_count),
            start_frame,
            self._analysis_span,
            context,
        )
        estimator = self._parameter_estimator

        def operation() -> F1ParameterResult:
            samples = tuple(source.read_frame(start_frame + offset) for offset in range(4))  # type: ignore[attr-defined]
            spectra = tuple(
                spectrum_processor.process(
                    frame,
                    sample_rate_hz=float(source.sample_rate_hz),  # type: ignore[attr-defined]
                    center_frequency_hz=float(source.center_frequency_hz),  # type: ignore[attr-defined]
                )
                for frame in samples
            )
            return estimator.measure(intent, samples, spectra)

        self._set_busy(True, f"Tespit #{self._selected_detection_id} parametreleri ölçülüyor…")
        self._submit(self._generation, "measurement", operation)
        self._add_log("Parametre", f"Tespit #{self._selected_detection_id} ölçümü istendi")

    @Slot(str, float, float, float)
    def requestListening(self, mode: str, center_offset_khz: float, bandwidth_khz: float, volume: float) -> None:
        if self._source is None or self._last_result is None or self._busy or not self.selectedDetectionReady:
            self._listening_state = "Dinleme için doğrulanmış bir tespit ve hazır kaynak gerekir."
            self.listeningChanged.emit()
            return
        event = next(
            (
                item for item in self._last_result.detection.active_events
                if item.event_id == self._selected_detection_id and item.state == "confirmed"
            ),
            None,
        )
        if event is None:
            self._listening_state = "Seçili tespit artık etkin değil; yeniden seçin."
            self.listeningChanged.emit()
            return
        try:
            config = AnalogMonitorConfig(
                mode,  # type: ignore[arg-type]
                self.sampleRateHz,
                center_offset_khz * 1_000.0,
                bandwidth_khz * 1_000.0,
            )
            if not math.isfinite(volume) or not 0.0 <= volume <= 1.0:
                raise MonitoringError("invalid_volume", "Ses düzeyi 0 ile 1 arasında olmalıdır.")
        except Exception as exc:
            code = str(getattr(exc, "code", "invalid_channel_bandwidth"))
            self._listening_state = ERROR_TEXT.get(code, "Dinleme ayarları geçerli değil.")
            self.listeningChanged.emit()
            return

        self.pause()
        self._clear_listening("Seçili kanal hazırlanıyor…")
        source = self._source
        frame_length = int(getattr(source, "frame_length"))
        frame_count = int(getattr(source, "frame_count"))
        total_samples = frame_length * frame_count
        sample_rate = float(getattr(source, "sample_rate_hz"))
        current_sample = self._frame_index * frame_length
        selected_id = self._selected_detection_id

        def operation() -> tuple[AnalogMonitorResult, str, float, float, float]:
            continuous_samples = int(math.ceil(5.0 * sample_rate))
            if (
                hasattr(source, "read_samples")
                and total_samples >= continuous_samples
                and continuous_samples <= 10_000_000
            ):
                start_sample = max(0, min(current_sample - continuous_samples // 2, total_samples - continuous_samples))
                block_size = max(frame_length, int(sample_rate))
                blocks = tuple(
                    source.read_samples(  # type: ignore[attr-defined]
                        start_sample + offset,
                        min(block_size, continuous_samples - offset),
                    )
                    for offset in range(0, continuous_samples, block_size)
                )
                result = AnalogMonitor().process_continuous(blocks, config, volume=volume)
                return result, "Kesintisiz kayıt", continuous_samples / sample_rate, config.center_offset_hz, config.channel_bandwidth_hz
            if frame_count < 4:
                raise MonitoringError("insufficient_iq", "Dinleme için dört ardışık I/Q karesi gerekir.")
            start_frame = max(0, min(self._frame_index - 3, frame_count - 4))
            frames = tuple(source.read_frame(start_frame + offset) for offset in range(4))  # type: ignore[attr-defined]
            result = AnalogMonitor().process(frames, config, volume=volume)
            return result, "Kısa I/Q önizlemesi", 4 * frame_length / sample_rate, config.center_offset_hz, config.channel_bandwidth_hz

        self._set_busy(True, f"Tespit #{selected_id} için {mode.upper()} kanalı hazırlanıyor…")
        self._submit(self._generation, "listening", operation)
        self._add_log("Dinleme", f"Tespit #{selected_id} · {mode.upper()} hazırlama istendi")

    @Slot()
    def playListening(self) -> None:
        if not self._audio_playback.play():
            self._listening_state = "Ses çıkış aygıtı kullanılamıyor; WAV dışa aktarımı kullanılabilir."
            self.listeningChanged.emit()

    @Slot()
    def pauseListening(self) -> None:
        self._audio_playback.pause()

    @Slot()
    def stopListening(self) -> None:
        self._audio_playback.stop()

    @Slot(str)
    def exportListeningWav(self, value: str) -> None:
        if self._listening_result is None or self._busy:
            return
        url = QUrl(value)
        path = Path(url.toLocalFile() if url.isLocalFile() else value)
        if not path.name:
            return
        if path.suffix.casefold() != ".wav":
            path = path.with_suffix(".wav")
        payload = bytes(self._listening_result.pcm16)

        def operation() -> str:
            try:
                write_wav(path, payload)
            except OSError as exc:
                raise MonitoringError("wav_write_failed", "WAV dosyası yazılamadı.") from exc
            return str(path)

        self._set_busy(True, "WAV dosyası kaydediliyor…")
        self._submit(self._generation, "wav_export", operation)

    @Slot(float, str, float)
    def addDirectionMeasurement(self, antenna_angle_deg: float, reference: str, reference_deg: float) -> None:
        if self._last_result is None or self._source is None:
            self._status_message = "Yön ölçümü için işlenmiş gerçek bir kaynak karesi gerekir."
            self.stateChanged.emit()
            return
        power = np.asarray(self._last_result.spectrum.display.bin_power_fs2, dtype=np.float64)
        finite = power[np.isfinite(power) & (power > 0.0)]
        if finite.size == 0:
            self._status_message = "Geçerli dBFS güç değeri bulunamadı; ölçüm kaydedilmedi."
            self.stateChanged.emit()
            return
        relative_power_db = float(10.0 * np.log10(np.mean(finite)))
        ref = {
            "north": AntennaReference.NORTH,
            "manual": AntennaReference.MANUAL_GEOGRAPHIC,
            "none": AntennaReference.UNAVAILABLE,
        }.get(reference, AntennaReference.UNAVAILABLE)
        bearing = geographic_bearing_from_manual_reference(
            ref,
            antenna_angle_deg,
            reference_deg if ref is AntennaReference.MANUAL_GEOGRAPHIC else None,
        )
        measurement = DFMeasurement.create(
            angle_deg=antenna_angle_deg,
            relative_power_db=relative_power_db,
            frequency_hz=float(getattr(self._source, "center_frequency_hz")),
            confidence=1.0,
            source="HackRF Canlı RX" if self._source_mode == "hackrf" else "SigMF Kaydı",
            geographic_bearing_deg=bearing,
        )
        self._df.add(measurement)
        self._df_points = [
            {
                "angle": f"{item.angle_deg:.1f}°",
                "power": f"{item.relative_power_db:.2f} dBFS",
                "bearing": "—" if item.geographic_bearing_deg is None else f"{item.geographic_bearing_deg:.1f}°",
                "source": item.source,
            }
            for item in self._df.measurements
        ]
        estimate = self._df.estimate()
        self._df_status = estimate.status
        if estimate.status == "LOB HAZIR":
            self._df_relative = f"{estimate.estimated_angle_deg:.1f}°"
            peak = next(
                item for item in self._df.measurements
                if item.angle_deg == estimate.raw_maximum_angle_deg
            )
            self._df_bearing = "—" if peak.geographic_bearing_deg is None else f"{peak.geographic_bearing_deg:.1f}°"
        else:
            self._df_relative = "—"
            self._df_bearing = "—"
        self._add_log("Yön Bulma", f"{antenna_angle_deg:.1f}° gerçek güç ölçümü kaydedildi")
        self.directionChanged.emit()

    @Slot()
    def clearDirectionMeasurements(self) -> None:
        self._df.clear()
        self._df_points = []
        self._df_status = "En az üç farklı anten açısında gerçek güç ölçümü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self.directionChanged.emit()

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
        if self._last_result is not None:
            self._update_spectrum(self._last_result)

    @Slot()
    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.stop()
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
        if kind == "open":
            self._install_source(result, Path(getattr(result, "metadata_path")).name)
        elif kind == "probe":
            inventory, device = result  # type: ignore[misc]
            self._apply_probe(inventory, device)
        elif kind == "capture":
            if not isinstance(result, CaptureResult) or result.backend_kind != "real":
                self._show_error("capture_not_real", "Ürün uygulaması yalnız gerçek HackRF alımını kabul eder.")
                return
            self._install_source(BoundedCI8FrameSource(result), "HackRF ED_RX · sınırlı alım")
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
            self._listening_short_preview = scope != "Kesintisiz kayıt"
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
        self._error_message = ""
        self._status_message = "Kaynak doğrulandı; tarama başlatılabilir."
        self._pipeline.detection.reset()
        if self._pipeline.parameters is not None:
            self._pipeline.parameters.reset()
        self._clear_results(keep_source=True)
        self._add_log("Kaynak", f"{label} doğrulandı")
        self.pipelineChanged.emit()
        self._request_frame()

    def _apply_probe(self, inventory: ToolInventory, device: DeviceStatus) -> None:
        serial = self._device_config.serial
        if not inventory.receive_available or device.state == "TOOLCHAIN_UNAVAILABLE":
            self._hackrf_ready = False
            self._source_state = "Hata"
            self._status_message = "HackRF araçları kullanılamıyor. Kurulumu doğrulayın."
        elif device.state == "NO_DEVICE":
            self._hackrf_ready = False
            self._source_state = "Kullanılmıyor"
            self._status_message = "HackRF bulunamadı. USB bağlantısını ve izinleri denetleyin."
        elif serial is None:
            self._hackrf_ready = False
            self._source_state = "Kullanılmıyor"
            self._status_message = "ED_RX seri kimliği yapılandırılmamış."
        elif device.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"} and any(
            item.serial.casefold() == serial.casefold() for item in device.devices
        ):
            self._hackrf_ready = True
            self._source_state = "Hazır"
            self._source_name = f"HackRF ED_RX · …{serial[-8:]}"
            self._status_message = "Yapılandırılmış HackRF hazır; RX ayarlarını doğrulayıp alımı başlatın."
        else:
            self._hackrf_ready = False
            self._source_state = "Hata"
            self._status_message = "Yapılandırılmış ED_RX HackRF bulunamadı."
        self._add_log("HackRF", self._status_message)
        self.pipelineChanged.emit()

    def _update_spectrum(self, result: RuntimeFrameResult) -> None:
        values = np.asarray(result.spectrum.display.bin_power_dbfs, dtype=np.float64)
        width = min(self._viewport_points, values.size)
        edges = np.linspace(0, values.size, width + 1, dtype=np.int64)
        reduced = np.asarray(
            [np.max(values[edges[i] : max(edges[i] + 1, edges[i + 1])]) for i in range(width)],
            dtype=np.float64,
        )
        finite = reduced[np.isfinite(reduced)]
        if finite.size:
            upper = min(10.0, float(np.max(finite)) + 6.0)
            lower = max(-200.0, min(-40.0, float(np.percentile(finite, 5.0)) - 8.0))
            if upper - lower < 30.0:
                lower = upper - 30.0
            self._spectrum_min_db = lower
            self._spectrum_max_db = upper
        self._spectrum_values = [float(value) for value in reduced]
        self.spectrumChanged.emit()

    def _update_detections(self, result: RuntimeFrameResult) -> None:
        for event in result.detection.active_events:
            if not event.observed_this_frame:
                continue
            history = self._event_observation_history.setdefault(int(event.event_id), [])
            record = (self._frame_index, True)
            if history and history[-1][0] == self._frame_index:
                history[-1] = record
            else:
                history.append(record)
            del history[:-8]
        visible = sorted(
            result.detection.active_events,
            key=lambda item: (item.state != "confirmed", item.event_id),
        )[:12]
        state_text = {"tentative": "İzleniyor", "confirmed": "Doğrulandı", "ended": "Sona ermiş"}
        self._detections = [
            {
                "eventId": int(item.event_id),
                "title": f"Tespit #{item.event_id}",
                "frequency": self._format_frequency(item.region.peak_frequency_hz),
                "snr": f"{item.region.peak_to_noise_db:.1f} dB",
                "state": state_text[item.state],
                "stateKey": item.state,
                "offsetKHz": (item.region.peak_frequency_hz - result.spectrum.center_frequency_hz) / 1_000.0,
                "startNormalized": self._normalized_shifted_bin(item.region.start_bin),
                "endNormalized": self._normalized_shifted_bin(item.region.end_bin),
                "peakNormalized": self._normalized_shifted_bin(item.region.peak_bin),
            }
            for item in visible
        ]
        if not any(int(item["eventId"]) == self._selected_detection_id for item in self._detections):
            if self._selected_detection_id >= 0:
                self._clear_listening("Seçili tespit sona erdi; yeni bir tespit seçin.")
            self._selected_detection_id = -1
            self._measurement_requested = False
            self._parameter_rows = []
            self._analysis_span = None
            self._analysis_span_draft = None
        self.detectionsChanged.emit()

    def _clear_results(self, *, keep_source: bool = False) -> None:
        self._last_result = None
        self._spectrum_values = []
        self._detections = []
        self._selected_detection_id = -1
        self._measurement_requested = False
        self._parameter_rows = []
        self._analysis_span = None
        self._analysis_span_draft = None
        self._event_observation_history.clear()
        self._frame_index = 0
        self._clear_listening("Doğrulanmış bir tespit seçin.")
        if not keep_source:
            self._frame_count = 0
        self.spectrumChanged.emit()
        self.detectionsChanged.emit()
        self.pipelineChanged.emit()

    def _clear_listening(self, message: str) -> None:
        self._audio_playback.stop()
        self._listening_result = None
        self._listening_rows = []
        self._listening_waveform = []
        self._listening_short_preview = False
        self._listening_state = message
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
        self._error_message = ""
        self._status_message = message
        self.pipelineChanged.emit()
        self.stateChanged.emit()

    def _show_error(self, code: str, detail: str) -> None:
        self._source_state = "Hata" if self._source is None else self._source_state
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
    def _format_rate(value: float) -> str:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.6g} MHz"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.6g} kHz"
        return f"{value:.6g} Hz"

    @staticmethod
    def _field_state(state: str) -> str:
        return {
            "not_observed": "Gözlenmedi",
            "not_applicable": "Uygulanamaz",
            "insufficient_quality": "Kalite yetersiz",
            "uncertain": "Belirsiz",
        }.get(state, "Ölçülemedi")

    def _prepare_analysis_span_draft(self, event_id: int) -> None:
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
        if bins is None or self._last_result is None:
            return ""
        spectrum = self._last_result.spectrum
        frequency_hz = spectrum.center_frequency_hz + (bins[index] - 2048.0) * spectrum.bin_spacing_hz
        return f"{frequency_hz / 1_000_000.0:.6f}"

    def _analysis_span_bins(self) -> tuple[int, int] | None:
        if self._analysis_span is not None:
            return self._analysis_span.lower_shifted_bin, self._analysis_span.upper_shifted_bin
        return self._analysis_span_draft

    def _selected_detection_coordinate(self, field: str) -> float:
        selected = next(
            (item for item in self._detections if int(item["eventId"]) == self._selected_detection_id),
            None,
        )
        return float(selected[field]) if selected is not None else -1.0

    @staticmethod
    def _normalized_shifted_bin(value: int) -> float:
        return max(0.0, min(1.0, float(value) / 4095.0))

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
