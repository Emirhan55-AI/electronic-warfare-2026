"""Operator-confirmed parameter measurement actions for Qt Quick."""

from __future__ import annotations

import math

from PySide6.QtCore import Slot

from algorithms.parameters import (
    AnalysisSpan,
    F1ParameterResult,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
)
from platforms.acquisition import decode_ci8


class QuickMeasurementActionsMixin:
    """Build source-bound measurement intents without owning detector state."""

    @Slot(float, float)
    def setAnalysisSpanDraftNormalized(self, start: float, end: float) -> None:
        if not self.measurementSelectionReady or (self._last_result is None and self._source_mode != "hackrf"):
            self._status_message = "Analiz aralığı için önce doğrulanmış bir tespit seçin."
            self.stateChanged.emit()
            return
        if not math.isfinite(start) or not math.isfinite(end):
            return
        lower = max(56, min(4039, int(round(min(start, end) * 4096.0))))
        upper = max(56, min(4039, int(round(max(start, end) * 4096.0))))
        peak_bin = self._selected_detection_bin("peakBin")
        if peak_bin is None or not lower <= peak_bin <= upper:
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
        if not self.measurementSelectionReady or (self._last_result is None and self._source_mode != "hackrf"):
            return
        if not math.isfinite(lower_mhz) or not math.isfinite(upper_mhz) or lower_mhz >= upper_mhz:
            self._status_message = "Analiz aralığı geçerli iki frekansla tanımlanmalıdır."
            self.stateChanged.emit()
            return
        if self._source_mode == "hackrf":
            spacing = float(self.sampleRateHz / 4096.0)
            center = float(self.centerFrequencyHz)
        else:
            assert self._last_result is not None
            spacing = float(self._last_result.spectrum.bin_spacing_hz)
            center = float(self._last_result.spectrum.center_frequency_hz)
        lower = int(round((lower_mhz * 1_000_000.0 - center) / spacing + 2048.0))
        upper = int(round((upper_mhz * 1_000_000.0 - center) / spacing + 2048.0))
        peak_bin = self._selected_detection_bin("peakBin")
        if peak_bin is None or not (lower <= peak_bin <= upper):
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
        if self._source_mode == "hackrf":
            self._request_live_measurement()
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

    def _request_live_measurement(self) -> None:
        session = self._live_session
        if (
            session is None
            or self._pending_live_listening is not None
            or self._pending_live_measurement is not None
            or not self.measurementSelectionReady
            or self._analysis_span is None
            or self._parameter_estimator is None
            or not hasattr(session, "measurement_window")
        ):
            return
        window = self._live_measurement_window()
        if len(window) != 4:
            self._status_message = "Canlı parametre ölçümü için aynı tespitin dört ardışık FPGA karesi bekleniyor."
            self.stateChanged.emit()
            return
        sequences = tuple(item.sequence_number for item in window)
        if sequences != tuple(range(sequences[0], sequences[0] + 4)):
            self._status_message = "Canlı ölçüm penceresi ardışık değil; yeni gözlem bekleniyor."
            self.stateChanged.emit()
            return
        owner_events = []
        for snapshot in window:
            owner = next(
                (
                    event for event in snapshot.response.active
                    if event.event_id == self._selected_detection_id
                    and event.state == "confirmed"
                    and event.observed_this_frame
                ),
                None,
            )
            if owner is None:
                self._status_message = "Canlı ölçüm penceresinde tespit sürekliliği doğrulanamadı."
                self.stateChanged.emit()
                return
            owner_events.append(owner)
        owner = owner_events[-1]
        candidates = tuple(
            MeasurementCandidate(
                int(event.event_id),
                int(event.seen_count),
                int(event.start_shifted_bin),
                int(event.end_shifted_bin),
                event.state == "confirmed",
            )
            for event in window[-1].response.active
            if event.observed_this_frame
        )
        context = MeasurementContext(
            self._generation,
            self._generation,
            self._generation,
            int(owner.event_id),
            int(owner.seen_count),
            (True, True, True, True),
            candidates,
        )
        intent = MeasurementIntent(
            self._generation,
            self._generation,
            self._generation,
            int(owner.event_id),
            int(owner.seen_count),
            sequences[0],
            self._analysis_span,
            context,
        )
        estimator = self._parameter_estimator
        spectrum_processor = self._pipeline.processor

        def operation() -> F1ParameterResult:
            samples = tuple(
                decode_ci8(snapshot.output_frame.payload, expected_complex_samples=4096)
                for snapshot in window
            )
            spectra = tuple(
                spectrum_processor.process(
                    sample,
                    sample_rate_hz=float(snapshot.output_frame.sample_rate_hz),
                    center_frequency_hz=float(snapshot.output_frame.center_frequency_hz),
                )
                for sample, snapshot in zip(samples, window, strict=True)
            )
            return estimator.measure(intent, samples, spectra)

        self._pending_live_measurement = operation
        self._measurement_requested = True
        self._status_message = "Dört ardışık FPGA karesi sabitlendi; alım durdurulup parametreler ölçülüyor."
        self._add_log("Parametre", f"Tespit #{self._selected_detection_id} canlı ölçüm penceresi sabitlendi")
        session.cancel()
        self.stateChanged.emit()

    def _start_pending_live_measurement(self) -> bool:
        operation, self._pending_live_measurement = self._pending_live_measurement, None
        if operation is None:
            return False
        self._set_busy(True, f"Tespit #{self._selected_detection_id} canlı parametreleri ölçülüyor…")
        self._submit(self._generation, "measurement", operation)
        return True

    def _start_pending_live_task(self) -> bool:
        if self._start_pending_live_measurement():
            return True
        return self._start_pending_live_listening()
