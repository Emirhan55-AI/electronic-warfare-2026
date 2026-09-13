"""Operator-confirmed parameter measurement actions for Qt Quick."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Callable
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QStandardPaths, Slot

from algorithms.parameters import (
    AnalysisSpan,
    F1ParameterResult,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
    suggest_analysis_span,
)
from platforms.acquisition import decode_ci8
from algorithms.p0.parameter_client import BoardAnalysisSpan, MAXIMUM_BOARD_SPAN_BINS
from .measurement_record import (
    RecordedMeasurement,
    digest,
    measure_and_record,
    utc_now,
    validate_measurement_ownership,
)


class QuickMeasurementActionsMixin:
    """Build source-bound measurement intents without owning detector state."""

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
                if lower <= start <= peak <= end <= upper
                and 8 <= upper - lower + 1 <= MAXIMUM_BOARD_SPAN_BINS
                else None
            )
            if self._analysis_span_draft is None:
                self._status_message = (
                    "Otomatik analiz aralığı oluşturulamadı; Aralığı Düzenle ile "
                    "alt ve üst frekansı girin."
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

    def _initialize_measurement_recording(self, directory: Path | None) -> None:
        self._measurement_namespace = uuid4().hex
        self._measurement_record_directory = directory or (
            Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
            / "parameter-records"
        )
        self._measurement_record_path = ""
        self._measurement_info = {}

    def _live_measurement_window(self):
        if self._selected_live_measurement_window:
            return self._selected_live_measurement_window
        cached = self._visible_live_measurement_windows.get(self._selected_detection_id, ())
        if cached:
            return cached
        session = self._live_session
        return tuple(session.measurement_window(self._selected_detection_id)) if session is not None and hasattr(session, "measurement_window") else ()

    @Slot()
    def cancelParameterMeasurement(self) -> None:
        if self._pending_live_measurement is not None:
            self._pending_live_measurement = None
        elif self._measurement_requested and self._live_session is not None:
            # A one-click live request may be waiting for the next complete
            # four-frame window. Cancelling the request must not stop RX.
            if hasattr(self._live_session, "cancel_parameter_capture"):
                self._live_session.cancel_parameter_capture()
            self._measurement_requested = False
        elif self._active_task_kind == "measurement":
            # The bounded worker finishes safely; its generation can no longer publish.
            self._generation += 1
        else:
            return
        self._measurement_requested = False
        self._parameter_rows = []
        self._status_message = "Parametre ölçümü iptal edildi; sonuç yayımlanmayacak."
        self.detectionsChanged.emit()
        self.stateChanged.emit()

    @Slot(result=bool)
    def restartParameterAcquisition(self) -> bool:
        if self._busy or self._live_session is not None:
            return False
        self.clearDetectionSelection()
        if self._source_mode == "hackrf":
            settings = self._live_receive_settings
            self.startLiveEDSession(settings["center_hz"], settings["lna_db"], settings["vga_db"], 878_906)
            return self.liveSessionActive
        self.startScan()
        return self._playing

    @Slot(float, float)
    def setAnalysisSpanDraftNormalized(self, start: float, end: float) -> None:
        if self._pending_live_measurement is not None or self._active_task_kind == "measurement":
            return
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
        maximum = MAXIMUM_BOARD_SPAN_BINS if self._source_mode == "hackrf" else 512
        if not 8 <= width <= maximum:
            self._status_message = f"Çizilen analiz aralığı 8–{maximum} FFT hücresi arasında olmalıdır."
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
        if self._pending_live_measurement is not None or self._active_task_kind == "measurement":
            self._status_message = "Ölçüm sürerken analiz aralığı değiştirilemez."
            self.stateChanged.emit()
            return
        if not self.measurementSelectionReady or (self._last_result is None and self._source_mode != "hackrf"):
            self._status_message = "Analiz aralığı için güncel ve doğrulanmış bir tespit seçin."
            self.stateChanged.emit()
            return
        self._analysis_span = None
        self._parameter_rows = []
        self.detectionsChanged.emit()
        self.stateChanged.emit()
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
            span_type = BoardAnalysisSpan if self._source_mode == "hackrf" else AnalysisSpan
            self._analysis_span = span_type(lower, upper, "operator_adjusted", self._span_revision)
        except ValueError:
            self._analysis_span = None
            maximum = MAXIMUM_BOARD_SPAN_BINS if self._source_mode == "hackrf" else 512
            self._status_message = f"Analiz aralığı 8–{maximum} FFT hücresi arasında ve kullanılabilir bant içinde olmalıdır."
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
        requested_utc = utc_now()
        source_info = {
            "kind": "sigmf", "session_id": f"{self._measurement_namespace}:{self._generation}",
            "source_name": self._source_name,
            "datatype": getattr(getattr(source, "report", None), "source_datatype", None),
            "frame_indices": list(range(start_frame, start_frame + 4)),
            "receiver_settings": None, "channelizer": None,
            "upstream_amplitude_scale": None, "board_identity": None,
        }
        self._parameter_rows = []
        self._measurement_record_path = ""
        record_directory = self._measurement_record_directory

        def operation() -> RecordedMeasurement:
            samples = tuple(source.read_frame(start_frame + offset) for offset in range(4))  # type: ignore[attr-defined]
            return measure_and_record(
                intent, samples, sample_rate_hz=float(source.sample_rate_hz),
                center_frequency_hz=float(source.center_frequency_hz),
                spectrum_config=spectrum_processor.config, source=source_info,
                requested_utc=requested_utc, directory=record_directory,
            )

        self._set_busy(True, f"Tespit #{self._selected_detection_id} parametreleri ölçülüyor…")
        self._submit(self._generation, "measurement", operation)
        self._add_log("Parametre", f"Tespit #{self._selected_detection_id} ölçümü istendi")

    def _request_live_measurement(self, *, direction_window=None) -> None:
        session = self._live_session
        if session is None or self._pending_live_listening is not None or self._pending_live_measurement is not None:
            return
        if self._analysis_span is None or self._parameter_estimator is None or not hasattr(session, "current_measurement_window"):
            if direction_window is None:
                self._measurement_requested = False
                self._status_message = "Ölçümden önce geçerli analiz aralığını onaylayın."
                self.stateChanged.emit()
            return
        if direction_window is None:
            # The operator's single action remains armed across a brief event
            # presentation gap instead of requiring a frame-perfect second click.
            self._measurement_requested = True
            if not self.measurementSelectionReady:
                self._status_message = "Ölçüm istendi; seçili sinyalin dört güncel ardışık FPGA karesi otomatik bekleniyor."
                self.stateChanged.emit()
                return
        span = self._analysis_span
        assert span is not None
        channel_capture = False
        capture_reason = ""
        if (
            direction_window is None
            and hasattr(session, "begin_parameter_capture")
            and hasattr(session, "parameter_capture")
        ):
            selected = self._selected_detection_item()
            if selected is not None:
                selected_lower = int(selected["startBin"])
                selected_upper = int(selected["endBin"])
                if (
                    selected_lower < span.lower_shifted_bin
                    or selected_upper > span.upper_shifted_bin
                ):
                    try:
                        self._span_revision += 1
                        span = BoardAnalysisSpan(
                            max(56, min(span.lower_shifted_bin, selected_lower)),
                            min(4039, max(span.upper_shifted_bin, selected_upper)),
                            "automatic_live_expansion",
                            self._span_revision,
                        )
                    except ValueError:
                        self._measurement_requested = False
                        self._status_message = (
                            "Canlı aday kartın kullanılabilir analiz sınırını aşıyor; "
                            "ölçüm başlatılmadı."
                        )
                        self.stateChanged.emit()
                        return
                    self._analysis_span = span
                    self._analysis_span_draft = (
                        span.lower_shifted_bin,
                        span.upper_shifted_bin,
                    )
                    self.detectionsChanged.emit()
            try:
                session.begin_parameter_capture(
                    span.lower_shifted_bin, span.upper_shifted_bin
                )
            except ValueError as exc:
                self._measurement_requested = False
                self._status_message = str(exc)
                self.stateChanged.emit()
                return
            captured, capture_reason = session.parameter_capture()
            window = tuple(captured)
            channel_capture = True
        else:
            window = (
                tuple(direction_window)
                if direction_window is not None
                else tuple(session.current_measurement_window(self._selected_detection_id))
            )
        if len(window) != 4:
            self._status_message = (
                capture_reason
                or "Canlı parametre ölçümü için aynı tespitin dört ardışık FPGA karesi bekleniyor."
            )
            self.stateChanged.emit()
            return
        sequences = tuple(item.sequence_number for item in window)
        if sequences != tuple(range(sequences[0], sequences[0] + 4)):
            self._status_message = "Canlı ölçüm penceresi ardışık değil; yeni gözlem bekleniyor."
            self.stateChanged.emit()
            return
        owner_events = []
        for snapshot in window:
            owner_span = (
                self._df_channel_span
                if direction_window is not None
                else (span.lower_shifted_bin, span.upper_shifted_bin)
            )
            owner = (session.direction_channel_owner(snapshot, *owner_span)
                     if direction_window is not None or channel_capture else next(
                (
                    event for event in snapshot.response.active
                    if event.event_id == self._selected_detection_id
                    and event.state == "confirmed"
                    and event.observed_this_frame
                ),
                None,
            ))
            if owner is None:
                self._status_message = "Canlı ölçüm penceresinde tespit sürekliliği doğrulanamadı."
                self.stateChanged.emit()
                return
            owner_events.append(owner)
        owner = owner_events[-1]
        owner_lower = min(int(event.start_shifted_bin) for event in owner_events)
        owner_upper = max(int(event.end_shifted_bin) for event in owner_events)
        if owner_lower < span.lower_shifted_bin or owner_upper > span.upper_shifted_bin:
            expanded_lower = max(56, min(span.lower_shifted_bin, owner_lower))
            expanded_upper = min(4039, max(span.upper_shifted_bin, owner_upper))
            try:
                self._span_revision += 1
                span = BoardAnalysisSpan(
                    expanded_lower,
                    expanded_upper,
                    "automatic_live_expansion",
                    self._span_revision,
                )
            except ValueError:
                self._status_message = (
                    "Canlı aday kartın kullanılabilir analiz sınırını aşıyor; "
                    "ölçüm başlatılmadı."
                )
                self.stateChanged.emit()
                return
            self._analysis_span = span
            self._analysis_span_draft = (expanded_lower, expanded_upper)
            self.detectionsChanged.emit()
        first_frame = window[0].output_frame
        configuration = getattr(session, "configuration", None)
        if configuration is None or any(
            snapshot.output_frame.sample_rate_hz != first_frame.sample_rate_hz
            or snapshot.output_frame.center_frequency_hz != first_frame.center_frequency_hz
            or snapshot.output_frame.sample_format != "ci8"
            or len(snapshot.output_frame.payload) != 8192
            or snapshot.output_frame.sequence_number != snapshot.sequence_number
            or snapshot.output_frame.frame_id != snapshot.response.frame_id
            or snapshot.response.frame_id != snapshot.sequence_number
            or snapshot.response.dma_status_flags != 7
            or snapshot.response.dropped_candidates != 0
            for snapshot in window
        ) or first_frame.center_frequency_hz != configuration.output_center_frequency_hz:
            self._status_message = "Ölçüm karelerinin alıcı veya kart bağlamı uyuşmuyor; yeni gözlem bekleniyor."
            self.stateChanged.emit()
            return
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
            tuple(event.event_id == owner.event_id for event in owner_events),
            candidates,
        )
        intent = MeasurementIntent(
            self._generation,
            self._generation,
            self._generation,
            int(owner.event_id),
            int(owner.seen_count),
            sequences[0],
            span,
            context,
        )
        spectrum_processor = self._pipeline.processor
        requested_utc = utc_now()
        channelizer = getattr(session, "measurement_channelizer", None)
        source_info = {
            "kind": "hackrf", "session_id": f"{self._measurement_namespace}:{self._generation}",
            "receiver_settings": asdict(configuration.rx_config),
            "receiver_settings_basis": "session_configuration_not_independent_readback",
            "channelizer": channelizer,
            "upstream_amplitude_scale": (channelizer or {}).get("profile", {}).get("output_amplitude_scale"),
            "board_identity": None,
            "board_identity_reason": "running_service_and_image_hash_not_observed",
            "sequence_numbers": list(sequences),
            "frame_ids": [snapshot.response.frame_id for snapshot in window],
            "transport_iq_sha256": [digest(snapshot.output_frame.payload) for snapshot in window],
            "owner_observations": [asdict(event) for event in owner_events],
        }
        if direction_window is not None:
            source_info["direction_capture"] = {
                "binding": "operator_selected_channel_v1",
                "span": list(self._df_channel_span),
                "frequency_hz": self._df_target_frequency_hz,
                "event_ids": [int(event.event_id) for event in owner_events],
                "request_event_id_basis": "last_channel_observation",
                "emitter_identity_verified": False,
                "fresh_after_operator_request": True,
                "host_capture_sequence_floor": session._direction_after_sequence,
                "angle_deg": self._pending_direction_measurement["antenna_angle_deg"],
            }
        elif channel_capture:
            source_info["channel_capture"] = {
                "binding": "operator_selected_channel_v1",
                "span": [span.lower_shifted_bin, span.upper_shifted_bin],
                "frequency_hz": float(self._selected_detection_item()["frequencyHz"]),
                "event_ids": [int(event.event_id) for event in owner_events],
                "request_event_id_basis": "last_channel_observation",
                "emitter_identity_verified": False,
                "fresh_after_operator_request": True,
                "host_capture_sequence_floor": session._parameter_after_sequence,
            }
        try:
            validate_measurement_ownership(intent, source_info)
        except ValueError as exc:
            if direction_window is None:
                # Keep RX running and retry on the next complete live window.
                # This avoids the former stopped/blank screen when event bounds
                # changed between range confirmation and capture.
                self._status_message = f"Ölçüm istendi; {exc} Yeni FPGA gözlemi otomatik bekleniyor."
                self.stateChanged.emit()
                return
            raise
        if channel_capture:
            session.cancel_parameter_capture()
        self._parameter_rows = []
        self._measurement_record_path = ""
        record_directory = self._measurement_record_directory

        def operation() -> RecordedMeasurement:
            samples = tuple(
                decode_ci8(snapshot.output_frame.payload, expected_complex_samples=4096)
                for snapshot in window
            )
            return measure_and_record(
                intent, samples, sample_rate_hz=float(first_frame.sample_rate_hz),
                center_frequency_hz=float(first_frame.center_frequency_hz),
                spectrum_config=spectrum_processor.config, source=source_info,
                requested_utc=requested_utc, directory=record_directory,
                board_endpoint=(configuration.board_host, configuration.board_port),
            )

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
        self._set_busy(True, "Seçili kanalın gücü ölçülüyor…" if self._pending_direction_measurement is not None
                       else f"Tespit #{self._selected_detection_id} canlı parametreleri ölçülüyor…")
        self._submit(self._generation, "measurement", operation)
        return True

    def _start_pending_live_task(self) -> bool:
        if self._start_pending_live_measurement():
            return True
        return self._start_pending_live_listening()

    def _f5_parameter_rows(self, result: F1ParameterResult) -> list[dict[str, str]]:
        validated = set(self._parameter_capability.validated_fields if self._parameter_capability else ())

        reasons = {
            "reference_mismatch": "İki gürültü referansı uyuşmuyor; referans bölgesinde sinyal veya girişim olabilir.",
            "reference_power_unavailable": "Gürültü referansı hesaplanamadı.",
            "span_edge_clipping": "Sinyal analiz aralığının dışına taşıyor; aralığı genişletin.",
            "obw_temporal_instability": "Bant kenarları dört kare arasında kararlı değil.",
            "carrier_line_below_threshold": "Ayrı bir taşıyıcı çizgisi yeterince belirgin değil.",
            "quality_below_carrier_threshold": "Taşıyıcı tespiti için SNR yetersiz.",
            "excess_power_not_significant": "Gürültü üzerindeki sinyal gücü yeterince belirgin değil.",
            "center_temporal_uncertainty": "Emisyon merkezi dört kare arasında kararlı değil.",
        }

        def reason_text(values: object) -> str:
            if isinstance(values, str):
                values = (values,)
            if not isinstance(values, (tuple, list)):
                return ""
            return " ".join(reasons.get(str(value), str(value)) for value in values if value)

        def diagnostic(value: object, formatter: Callable[[float], str]) -> tuple[str, str]:
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                return formatter(float(value)), "valid"
            return "Ölçülemedi", "not_observed"

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
        rows = [
            {"label": "Emisyon merkez frekansı", "value": measured("emission_center_frequency", result.emission_center_frequency, self._format_frequency)},
            {"label": "Gözlenen taşıyıcı frekansı", "value": measured("carrier_line_frequency", result.carrier_line_frequency, self._format_frequency)},
            {"label": "Alt OBW sınırı", "value": measured("occupied_bandwidth", result.lower_band_edge, self._format_frequency)},
            {"label": "Üst OBW sınırı", "value": measured("occupied_bandwidth", result.upper_band_edge, self._format_frequency)},
            {"label": "İşgal edilen bant genişliği (OBW %99)", "value": measured("occupied_bandwidth", result.occupied_bandwidth, self._format_rate)},
            {"label": "Kanal gücü (dBFS)", "value": measured("uncalibrated_channel_power_dbfs", result.channel_power_dbfs, lambda value: f"{value:.2f} dBFS")},
            {"label": "Bant içi SNR kestirimi", "value": measured("snr_estimate_db", result.snr_estimate_db, lambda value: f"{value:.2f} dB")},
            {"label": "Sinyal türü", "value": domain},
            {"label": "Güç referansı", "value": "Kalibre edilmemiş · dBFS"},
        ]
        keys = ("emission_center_frequency", "carrier_line_frequency", "lower_band_edge",
                "upper_band_edge", "occupied_bandwidth", "channel_power_dbfs",
                "snr_estimate_db", "signal_domain", "power_reference")
        for row, key in zip(rows, keys):
            field = getattr(result, key, None)
            reason = str(getattr(field, "reason", "") or "")
            row.update(key=key, state=str(getattr(field, "state", "valid")),
                       reason=reason_text(reason))

        quality = result.quality
        quality_state = str(quality.state)
        rows.append({
            "key": "measurement_quality",
            "label": (
                "Kart ölçüm kalite kapısı"
                if self._source_mode == "hackrf"
                else "Kayıtlı I/Q kalite kapısı"
            ),
            "value": (
                f"Geçti · {int(quality.observed_frames)}/4 kare"
                if quality_state == "valid"
                else f"{self._field_state(quality_state)} · {int(quality.observed_frames)}/4 kare"
            ),
            "state": quality_state,
            "reason": reason_text(quality.reasons),
        })
        diagnostics = (
            ("reference_difference_db", "Gürültü referans farkı", quality.reference_difference_db,
             lambda value: f"{value:.3f} dB"),
            ("detection_significance", "Tespit anlamlılığı", quality.detection_significance,
             lambda value: f"{value:.3f}"),
            ("center_uncertainty_bins", "Merkez kararsızlığı", quality.center_uncertainty_bins,
             lambda value: f"{value:.3f} hücre"),
            ("temporal_edge_range_bins", "OBW kenar değişimi", quality.temporal_edge_range_bins,
             lambda value: f"{value:.3f} hücre"),
        )
        for key, label, value, formatter in diagnostics:
            text, state = diagnostic(value, formatter)
            rows.append({"key": key, "label": label, "value": text,
                         "state": state, "reason": ""})
        return rows
