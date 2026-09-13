"""Manual direction-measurement actions for the Qt Quick view model."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import Slot

from algorithms.p0.df import DFEstimate, DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE
from algorithms.p0.direction_client import estimate_on_board
from algorithms.p0.field_df import AntennaReference, geographic_bearing_from_manual_reference
from algorithms.p0.parameter_client import BoardAnalysisSpan, MAXIMUM_BOARD_SPAN_BINS


CLOCKWISE_DIRECTION_ANGLE_COUNT = FIELD_AMPLITUDE_DF_PROFILE.minimum_distinct_angles
CLOCKWISE_DIRECTION_STEP_DEG = 360.0 / CLOCKWISE_DIRECTION_ANGLE_COUNT


class QuickDirectionActionsMixin:
    """Keep manual DF measurement state separate from RF detection control."""

    def _next_clockwise_direction_angle(self) -> float | None:
        measured_angles = {
            round(item.angle_deg % 360.0, 6)
            for item in self._df.measurements
        }
        for index in range(CLOCKWISE_DIRECTION_ANGLE_COUNT):
            angle = index * CLOCKWISE_DIRECTION_STEP_DEG
            if round(angle, 6) not in measured_angles:
                return angle
        return None

    @Slot()
    def addNextClockwiseDirectionMeasurement(self) -> None:
        """Record the next 15-degree clockwise point from the operator's zero."""
        angle = self._next_clockwise_direction_angle()
        if angle is None:
            self._df_capture_message = "360° saat yönü taraması tamamlandı."
            self.stateChanged.emit()
            return
        self.addDirectionMeasurement(angle, "none", 0.0)

    @Slot(float, str, float)
    def addDirectionMeasurement(self, antenna_angle_deg: float, reference: str, reference_deg: float) -> None:
        if self._busy and self._active_task_kind != "live":
            self._status_message = "Devam eden kart işlemi tamamlanmadan yeni yön ölçümü alınamaz."
            self.stateChanged.emit()
            return
        if (
            (self._source_mode == "hackrf" and self._live_session is None)
            or (self._source_mode != "hackrf" and (self._last_result is None or self._source is None))
        ):
            self._status_message = "Yön ölçümü için işlenmiş gerçek bir kaynak karesi gerekir."
            self.stateChanged.emit()
            return
        if self._source_mode == "hackrf":
            self._begin_direction_measurement(antenna_angle_deg, reference, reference_deg)
            return
        if not self.selectedDetectionReady:
            self._status_message = "Yön ölçümü için önce doğrulanmış hedef sinyali seçin."
            self.stateChanged.emit()
            return
        if not math.isfinite(antenna_angle_deg) or not 0.0 <= antenna_angle_deg < 360.0:
            self._status_message = "Anten açısı 0° ile 359° arasında olmalıdır."
            self.stateChanged.emit()
            return
        if reference == "manual" and not math.isfinite(reference_deg):
            self._status_message = "Anten 0° gerçek kerterizi geçerli olmalıdır."
            self.stateChanged.emit()
            return
        relative_power_db = self._direction_frame_power_dbfs
        frequency_hz = self._direction_frame_frequency_hz
        bandwidth_hz = self._direction_frame_bandwidth_hz
        if frequency_hz is None or bandwidth_hz is None or relative_power_db is None:
            self._status_message = "Seçili hedef kanalının geçerli dBFS gücü bulunamadı; ölçüm kaydedilmedi."
            self.stateChanged.emit()
            return
        self._commit_direction_measurement(
            antenna_angle_deg=antenna_angle_deg,
            reference=reference,
            reference_deg=reference_deg,
            relative_power_db=relative_power_db,
            frequency_hz=frequency_hz,
            bandwidth_hz=bandwidth_hz,
            receiver_binding=self._direction_receiver_binding,
            frame_id=self._direction_frame_id,
        )

    def _commit_direction_measurement(
        self,
        *,
        antenna_angle_deg: float,
        reference: str,
        reference_deg: float,
        relative_power_db: float,
        frequency_hz: float,
        bandwidth_hz: float,
        receiver_binding: str,
        frame_id: int | None,
        board_endpoint: tuple[str, int] | None = None,
    ) -> None:
        ref = {
            "north": AntennaReference.NORTH,
            "manual": AntennaReference.MANUAL_GEOGRAPHIC,
            "none": AntennaReference.UNAVAILABLE,
        }.get(reference, AntennaReference.UNAVAILABLE)
        if ref is AntennaReference.MANUAL_GEOGRAPHIC:
            reference_key = ("manual", round(reference_deg % 360.0, 6))
        else:
            reference_mode = reference if reference in {"north", "none"} else "none"
            reference_key = (reference_mode, None)
        if self._df_reference_key is not None and self._df_reference_key != reference_key:
            self._status_message = "Ölçüm oturumunun anten referansı değiştirilemez; önce ölçümleri temizleyin."
            self.stateChanged.emit()
            return
        bearing = geographic_bearing_from_manual_reference(
            ref,
            antenna_angle_deg,
            reference_deg if ref is AntennaReference.MANUAL_GEOGRAPHIC else None,
        )
        try:
            measurement = DFMeasurement.create(
                angle_deg=antenna_angle_deg,
                relative_power_db=relative_power_db,
                frequency_hz=frequency_hz,
                confidence=1.0,
                source=self._source_name,
                geographic_bearing_deg=bearing,
                channel_bandwidth_hz=bandwidth_hz,
                receiver_binding=receiver_binding,
                frame_id=frame_id,
            )
            self._df.add(measurement)
        except ValueError as exc:
            self._status_message = str(exc)
            self.stateChanged.emit()
            return
        self._df_reference_key = reference_key
        self._df_points = [
            {
                "angle": f"{item.angle_deg:.1f}°",
                "power": f"{item.relative_power_db:.2f} dBFS",
                "bearing": "—" if item.geographic_bearing_deg is None else f"{item.geographic_bearing_deg:.1f}°",
                "frequency": self._format_frequency(item.frequency_hz),
                "source": item.source,
            }
            for item in self._df.measurements
        ]
        estimate = self._df.estimate()
        self._apply_direction_estimate(estimate)
        self._add_log(
            "Yön Bulma",
            f"{antenna_angle_deg:.1f}° seçili kanal gücü kaydedildi · {frequency_hz / 1_000_000.0:.6f} MHz",
        )
        self.directionChanged.emit()
        distinct_angle_count = len({item.angle_deg for item in self._df.measurements})
        if distinct_angle_count >= FIELD_AMPLITUDE_DF_PROFILE.minimum_distinct_angles and self._source_mode == "hackrf":
            session = self._live_session
            configuration = getattr(session, "configuration", None)
            endpoint = board_endpoint or (
                (configuration.board_host, configuration.board_port)
                if configuration is not None else None
            )
            if endpoint is None:
                self._df_status = "Kart ARM yön hesabı için canlı alıcı bağlamı bulunamadı."
                self._df_relative = "—"
                self._df_bearing = "—"
                self.directionChanged.emit()
                return
            measurements = self._df.measurements
            host, port = endpoint

            def operation():
                return estimate_on_board(host, port, measurements)

            self._df_status = "Kart ARM yön hesabı doğrulanıyor…"
            self._df_relative = "—"
            self._df_bearing = "—"
            self._set_busy(True, "Kart ARM yön hesabı doğrulanıyor…")
            self._submit(self._generation, "direction", operation)
            self.directionChanged.emit()

    def _direction_binding(self):
        config = getattr(self._live_session, "configuration", None)
        if config is None:
            return None
        return (config.device_serial, config.output_center_frequency_hz,
                config.input_center_frequency_hz, config.lna_gain_db,
                config.vga_gain_db, config.fpga_fft_size)

    def _direction_unavailable_reason(self) -> str:
        if self._pending_direction_measurement is not None:
            return "Ölçüm sürüyor; anteni sabit tutun."
        if self._live_session is None:
            return "Ölçüm için canlı alımı başlatın."
        if self._live_fpga_fft_size() != 4096:
            return "Yön ölçümü için FPGA FFT 4096 gerekir; kartı yeniden başlatın."
        if self._parameter_capability is None or self._parameter_estimator is None:
            return "Kartın kanal gücü ölçüm profili kullanılamıyor."
        if self._pending_live_measurement is not None or self._pending_live_listening is not None:
            return "Diğer ölçüm işleminin tamamlanmasını bekleyin."
        if not hasattr(self._live_session, "begin_direction_capture"):
            return "Alım bileşeni yeni yön ölçüm akışını desteklemiyor."
        if self._df_channel_span is not None:
            if self._df_capture_binding != self._direction_binding():
                return "Alıcı ayarları değişti; ölçümleri temizleyip hedefi yeniden seçin."
            span = self._df_channel_span
        else:
            selected = self._selected_detection_item()
            if selected is None or not selected.get("confirmed", selected.get("stateKey") == "confirmed"):
                return "Tespit ekranından ölçülecek sinyali seçin."
            if self._analysis_span_draft is None:
                return "Seçili sinyalin kanal aralığı uygun değil; izole bir hedef seçin."
            span = self._analysis_span_draft
        lower, upper = span
        if (
            not 56 <= lower <= upper <= 4039
            or not 8 <= upper - lower + 1 <= MAXIMUM_BOARD_SPAN_BINS
        ):
            return (
                "Seçili sinyalin kanal aralığı kartın 8–3984 FFT hücre sınırına "
                "uygun değil; hedefi yeniden seçin."
            )
        return ""

    def _begin_direction_measurement(self, angle, reference, reference_deg) -> None:
        reason = self._direction_unavailable_reason()
        if reason:
            self._df_capture_message = reason
            self.stateChanged.emit()
            return
        if not math.isfinite(angle) or not 0 <= angle < 360 or reference not in {"north", "manual", "none"} or not math.isfinite(reference_deg):
            self._df_capture_message = "Anten açısı ve yön referansı geçerli olmalıdır."
            self.stateChanged.emit()
            return
        reference_key = (reference, round(reference_deg % 360, 6) if reference == "manual" else None)
        if self._df_reference_key is not None and reference_key != self._df_reference_key:
            self._df_capture_message = "Oturumun anten referansı değiştirilemez; önce ölçümleri temizleyin."
            self.stateChanged.emit()
            return
        session = self._live_session
        config = session.configuration
        new_channel_lock = self._df_channel_span is None
        channel_span = self._analysis_span_draft if new_channel_lock else self._df_channel_span
        assert channel_span is not None
        lower, upper = channel_span
        try:
            session.begin_direction_capture(lower, upper)
        except ValueError as exc:
            self._df_capture_message = f"Yön ölçümü başlatılamadı: {exc}"
            self.stateChanged.emit()
            return
        if new_channel_lock:
            self._df_channel_span = channel_span
            self._df_target_frequency_hz = float(self._selected_detection_item()["frequencyHz"])
            self._df_capture_binding = self._direction_binding()
        self._pending_direction_measurement = {
            "antenna_angle_deg": float(angle), "reference": reference,
            "reference_deg": float(reference_deg),
            "frequency_hz": self._df_target_frequency_hz,
            "bandwidth_hz": (upper - lower + 1) * self.sampleRateHz / 4096,
            "receiver_binding": repr((self._df_capture_binding, self._df_channel_span)),
            "frame_id": None, "board_endpoint": (config.board_host, config.board_port),
            "resume_settings": {"center_hz": config.output_center_frequency_hz,
                                "lna_db": config.lna_gain_db, "vga_db": config.vga_gain_db,
                                "frame_count": config.frame_count},
            "capture_session": session, "capture_generation": self._generation,
            "deadline": time.monotonic() + 5.0,
        }
        self._df_capture_message = "Yeni ölçüm verisi toplanıyor; anteni sabit tutun."
        self.stateChanged.emit()

    def _poll_direction_capture(self) -> None:
        pending = self._pending_direction_measurement
        if pending is None or "deadline" not in pending:
            return
        session = pending["capture_session"]
        if (session is not self._live_session or pending["capture_generation"] != self._generation
                or self._direction_binding() != self._df_capture_binding):
            self.cancelDirectionMeasurement()
            return
        window, reason = session.direction_capture()
        if time.monotonic() >= pending["deadline"]:
            self.cancelDirectionMeasurement()
            self._df_capture_message = "5 saniyede ölçüm alınamadı. " + reason
            self.stateChanged.emit()
            return
        if len(window) != 4:
            self._df_capture_message = reason
            return
        self._span_revision += 1
        self._analysis_span = BoardAnalysisSpan(
            *self._df_channel_span, "auto_suggested", self._span_revision
        )
        pending["frame_id"] = (int(self._generation) << 32) | window[0].sequence_number
        self._request_live_measurement(direction_window=window)
        if self._pending_live_measurement is None:
            message = self._status_message
            self.cancelDirectionMeasurement()
            self._df_capture_message = message
        else:
            del pending["deadline"]
            session.cancel_direction_capture()
            self._df_capture_message = "Kanal gücü kartta ölçülüyor; anteni sabit tutun."
        self.stateChanged.emit()

    @Slot()
    def cancelDirectionMeasurement(self) -> None:
        pending = self._pending_direction_measurement
        if pending is None or "deadline" not in pending:
            return
        pending["capture_session"].cancel_direction_capture()
        self._pending_direction_measurement = None
        self._df_capture_message = "Ölçüm iptal edildi; bu açı kaydedilmedi."
        self.stateChanged.emit()

    @Slot()
    def clearDirectionMeasurements(self) -> None:
        if (self._busy and self._active_task_kind != "live") or self._pending_live_measurement is not None:
            return
        self._reset_direction()

    def _reset_direction(self) -> None:
        self.cancelDirectionMeasurement()
        self._pending_direction_measurement = None
        self._df_capture_binding = None
        self._df_capture_message = ""
        self._df_channel_span = None
        self._df_target_frequency_hz = None
        self._df.clear()
        self._df_points = []
        self._df_status = "15° adımlı 24 farklı anten açısında kanal gücü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self._df_reference_key = None
        self.directionChanged.emit()
        self.stateChanged.emit()
    def _apply_direction_estimate(self, estimate: DFEstimate) -> None:
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
