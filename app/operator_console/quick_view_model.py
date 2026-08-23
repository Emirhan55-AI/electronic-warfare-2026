"""Qt Quick presentation boundary for the release operator application."""

from __future__ import annotations

import math
from pathlib import Path
import time
from typing import Callable, Literal

import numpy as np
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot

from algorithms.p0.df import DFMeasurement, ManualAmplitudeDF
from algorithms.p0.field_df import AntennaReference, geographic_bearing_from_manual_reference
from algorithms.p0.models import CandidateRegion, P0ParameterResult
from algorithms.p0.parameters import ParameterExtractor as P0ParameterExtractor
from algorithms.pipeline import RuntimeFrameResult, RuntimePipeline, resolve_default_operation_profile
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


ERROR_TEXT = {
    "invalid_sigmf_contract": "SigMF sözleşmesi geçerli değil.",
    "source_open_failed": "Kayıt açılamadı.",
    "processing_failed": "İşleme tamamlanamadı.",
    "tools_unavailable": "HackRF komut satırı araçları bulunamadı.",
    "device_not_found": "Yapılandırılmış HackRF bulunamadı.",
    "operation_timeout": "Donanım yanıt süresi aşıldı.",
    "operation_cancelled": "İşlem durduruldu.",
}


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

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        acquisition_backend: HackRFBackend | None = None,
        source_factory: Callable[..., SigMFFrameSource] = SigMFFrameSource,
    ) -> None:
        super().__init__(parent)
        resolved = resolve_default_operation_profile()
        self._pipeline = RuntimePipeline(resolved.profile, verified_binding=resolved.binding)
        self._profile_summary = self._pipeline.validated_summary
        self._profile_warning = resolved.fallback_code
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
        self._reduced_motion = False
        self._hackrf_ready = False
        self._operation_samples_ms: list[float] = []
        self._event_log: list[dict[str, str]] = []

        self._df = ManualAmplitudeDF()
        self._df_points: list[dict[str, str]] = []
        self._df_status = "En az üç farklı anten açısında gerçek güç ölçümü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self._add_log("Sistem", "Operatör uygulaması hazır")
        if self._profile_warning:
            self._add_log("İşleme", "Parametre profili doğrulanamadı; güvenli tespit profili kullanılıyor")

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

    @Property("QVariantList", notify=detectionsChanged)
    def parameterRows(self) -> list[dict[str, str]]:
        return self._parameter_rows

    @Property(bool, notify=stateChanged)
    def reducedMotion(self) -> bool:
        return self._reduced_motion

    @Property("QVariantList", notify=stateChanged)
    def pipelineBlocks(self) -> list[dict[str, str]]:
        source = "Hata" if self._error_message and self._source is None else self._source_state
        processing = "Çalışıyor" if self._busy and self._source is not None else "Hazır" if self._source is not None else "Kullanılmıyor"
        selected = "Hazır" if self.selectedDetectionReady else "Kullanılmıyor"
        return [
            {"name": "Kaynak", "state": source},
            {"name": "Ön İşleme", "state": processing},
            {"name": "FFT / Güç", "state": processing},
            {"name": "OS-CFAR", "state": processing},
            {"name": "Operatör Görevleri", "state": selected},
        ]

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
        if self._measurement_requested:
            self._measurement_requested = False
            self._parameter_rows = []
            self.detectionsChanged.emit()
        self._playing = True
        self._status_message = "Sinyal taraması çalışıyor."
        self._timer.start()
        self._request_frame()
        self.stateChanged.emit()

    @Slot()
    def pause(self) -> None:
        self._playing = False
        self._timer.stop()
        if self._source is not None:
            self._status_message = "Tarama duraklatıldı."
            self.stateChanged.emit()

    @Slot()
    def stop(self) -> None:
        self._playing = False
        self._timer.stop()

    @Slot(int)
    def selectDetection(self, event_id: int) -> None:
        if not any(int(item["eventId"]) == event_id for item in self._detections):
            return
        self._selected_detection_id = event_id
        self._measurement_requested = False
        self._parameter_rows = []
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def requestMeasurement(self) -> None:
        if not self.selectedDetectionReady or self._last_result is None or self._source is None or self._busy:
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
        self.pause()
        self._measurement_requested = True
        source = self._source
        frame_index = self._frame_index
        spectrum_processor = self._pipeline.processor
        regions = tuple(
            item.region for item in self._last_result.detection.active_events
            if item.observed_this_frame
        )

        def operation() -> P0ParameterResult:
            samples = source.read_frame(frame_index)  # type: ignore[attr-defined]
            spectrum = spectrum_processor.process(
                samples,
                sample_rate_hz=float(source.sample_rate_hz),  # type: ignore[attr-defined]
                center_frequency_hz=float(source.center_frequency_hz),  # type: ignore[attr-defined]
            )
            shifted_power = np.fft.fftshift(spectrum.fft_power_unshifted)
            scale = float((spectrum.frame_length * spectrum.window_coherent_gain) ** 2)

            def candidate(region: object) -> CandidateRegion:
                return CandidateRegion(
                    int(region.start_bin),  # type: ignore[attr-defined]
                    int(region.end_bin),  # type: ignore[attr-defined]
                    int(region.peak_bin),  # type: ignore[attr-defined]
                    float(region.peak_power) * scale,  # type: ignore[attr-defined]
                    float(region.local_noise_power) * scale,  # type: ignore[attr-defined]
                    float(region.threshold_power) * scale,  # type: ignore[attr-defined]
                )

            selected = candidate(event.region)
            neighbors = tuple(candidate(region) for region in regions)
            return P0ParameterExtractor().extract(
                frame_id=frame_index,
                iq=samples,
                shifted_power=shifted_power,
                sample_rate_hz=spectrum.sample_rate_hz,
                center_frequency_hz=spectrum.center_frequency_hz,
                candidate=selected,
                confirmed=True,
                provenance="HOST REFERENCE" if self._source_mode == "hackrf" else "REPLAY",
                backend=(
                    "HackRF Canlı RX · P0 parametre referansı"
                    if self._source_mode == "hackrf"
                    else "SigMF Kaydı · PHASE-03 aday + P0 parametre referansı"
                ),
                neighboring_candidates=neighbors,
            )

        self._set_busy(True, f"Tespit #{self._selected_detection_id} parametreleri ölçülüyor…")
        self._submit(self._generation, "measurement", operation)
        self._add_log("Parametre", f"Tespit #{self._selected_detection_id} ölçümü istendi")

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
        self._close_source()
        self._backend.close()

    def _submit(self, generation: int, kind: str, operation: Callable[[], object]) -> None:
        task = _Task(generation, kind, operation)
        task.signals.completed.connect(self._task_completed)
        task.signals.failed.connect(self._task_failed)
        self._busy = True
        self.stateChanged.emit()
        self._pool.start(task)

    @Slot(int, str, object, float)
    def _task_completed(self, generation: int, kind: str, result: object, elapsed: float) -> None:
        self._busy = False
        if generation != self._generation:
            if hasattr(result, "close"):
                result.close()  # type: ignore[attr-defined]
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
            self._install_source(BoundedCI8FrameSource(result), "HackRF ED_RX · bounded alım")
        elif kind == "frame":
            if not isinstance(result, RuntimeFrameResult):
                self._show_error("processing_failed", "İşleme sonucu sözleşmeyle eşleşmedi.")
                return
            self._operation_samples_ms.append(elapsed * 1000.0)
            self._operation_samples_ms = self._operation_samples_ms[-256:]
            self._last_result = result
            self._update_spectrum(result)
            self._update_detections(result)
            if self._measurement_requested:
                self._update_parameters(result)
            self._status_message = f"Kare {self._frame_index + 1}/{self._frame_count} işlendi."
            if self._pending_frame:
                self._pending_frame = False
                self._advance()
        elif kind == "measurement":
            if not isinstance(result, P0ParameterResult):
                self._show_error("measurement_failed", "Parametre sonucu sözleşmeyle eşleşmedi.")
                return
            self._parameter_rows = [
                {"label": "Taşıyıcı", "value": self._format_frequency(result.carrier_frequency_hz)},
                {"label": "OBW", "value": self._format_rate(result.occupied_bandwidth_hz)},
                {"label": "Alt sınır", "value": self._format_frequency(result.lower_frequency_hz)},
                {"label": "Üst sınır", "value": self._format_frequency(result.upper_frequency_hz)},
                {"label": "Kanal gücü", "value": f"{result.channel_power_dbfs:.2f} dBFS"},
                {"label": "Tepe güç", "value": f"{result.peak_power_dbfs_per_bin:.2f} dBFS/bin"},
                {"label": "SNR", "value": f"{result.snr_db:.2f} dB"},
                {"label": "Sinyal alanı", "value": result.signal_domain},
                {"label": "Kalibrasyon", "value": "Bekliyor · göreli ölçüm"},
            ]
            self._status_message = f"Tespit #{self._selected_detection_id} parametre ölçümü tamamlandı."
            self._add_log("Parametre", self._status_message)
            self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot(int, str, str)
    def _task_failed(self, generation: int, code: str, detail: str) -> None:
        self._busy = False
        if generation == self._generation:
            self._show_error(code, detail)
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
        visible = sorted(
            result.detection.active_events,
            key=lambda item: (item.state != "confirmed", -item.region.peak_to_noise_db, item.event_id),
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
            }
            for item in visible
        ]
        if not any(int(item["eventId"]) == self._selected_detection_id for item in self._detections):
            self._selected_detection_id = -1
            self._measurement_requested = False
            self._parameter_rows = []
        self.detectionsChanged.emit()

    def _update_parameters(self, result: RuntimeFrameResult) -> None:
        if result.parameters is None:
            self._parameter_rows = [{"label": "Durum", "value": "Doğrulanmış parametre profili kullanılamıyor"}]
            self.detectionsChanged.emit()
            return
        estimate = next(
            (item for item in result.parameters.events if item.event_id == self._selected_detection_id),
            None,
        )
        if estimate is None:
            self._parameter_rows = [{"label": "Durum", "value": "Seçili tespit bu karede ölçülemedi"}]
        else:
            def measured(value: float | None, state: str, formatter: Callable[[float], str]) -> str:
                return formatter(value) if value is not None and state == "valid" else self._field_state(state)

            self._parameter_rows = [
                {"label": "Spektral merkez", "value": measured(estimate.frequency.spectral_center_frequency_hz, estimate.frequency.spectral_center_state, self._format_frequency)},
                {"label": "Gözlenen taşıyıcı", "value": measured(estimate.frequency.observed_carrier_frequency_hz, estimate.frequency.observed_carrier_state, self._format_frequency)},
                {"label": "OBW %99", "value": measured(estimate.bandwidth.bandwidth_hz, estimate.bandwidth.bandwidth_state, self._format_rate)},
                {"label": "Kanal gücü", "value": measured(estimate.power.signal_power_dbfs, estimate.power.relative_power_state, lambda value: f"{value:.2f} dBFS")},
                {"label": "SNR", "value": measured(estimate.power.snr_db, estimate.power.snr_state, lambda value: f"{value:.2f} dB")},
                {"label": "Sinyal alanı", "value": estimate.signal_domain.value if estimate.signal_domain.state == "valid" else self._field_state(estimate.signal_domain.state)},
            ]
        self.detectionsChanged.emit()

    def _clear_results(self, *, keep_source: bool = False) -> None:
        self._last_result = None
        self._spectrum_values = []
        self._detections = []
        self._selected_detection_id = -1
        self._measurement_requested = False
        self._parameter_rows = []
        self._frame_index = 0
        if not keep_source:
            self._frame_count = 0
        self.spectrumChanged.emit()
        self.detectionsChanged.emit()

    def _close_source(self) -> None:
        source, self._source = self._source, None
        if source is not None and hasattr(source, "close"):
            source.close()  # type: ignore[attr-defined]

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        self._error_message = ""
        self._status_message = message
        self.stateChanged.emit()

    def _show_error(self, code: str, detail: str) -> None:
        self._source_state = "Hata" if self._source is None else self._source_state
        self._error_message = ERROR_TEXT.get(code, f"İşlem tamamlanamadı ({code}).")
        self._status_message = self._error_message
        self._add_log("Hata", f"{code} · {detail}")
        self.stateChanged.emit()

    def _add_log(self, component: str, message: str) -> None:
        self._event_log.insert(
            0,
            {
                "time": time.strftime("%H:%M:%S"),
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
