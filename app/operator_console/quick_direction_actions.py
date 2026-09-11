"""Manual direction-measurement actions for the Qt Quick view model."""

from __future__ import annotations

import math

from PySide6.QtCore import Slot

from algorithms.p0.df import DFEstimate, DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE
from algorithms.p0.direction_client import estimate_on_board
from algorithms.p0.field_df import AntennaReference, geographic_bearing_from_manual_reference
from algorithms.parameters import AnalysisSpan


class QuickDirectionActionsMixin:
    """Keep manual DF measurement state separate from RF detection control."""

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
        selected = self._selected_detection_item()
        if self._source_mode == "hackrf" and selected is not None:
            frequency_hz = float(selected["frequencyHz"])
            bandwidth_hz = (
                (int(selected["endBin"]) - int(selected["startBin"]) + 1)
                * self.sampleRateHz / 4096.0
            )
        if frequency_hz is None or bandwidth_hz is None or (
            self._source_mode != "hackrf" and relative_power_db is None
        ):
            self._status_message = "Seçili hedef kanalının geçerli dBFS gücü bulunamadı; ölçüm kaydedilmedi."
            self.stateChanged.emit()
            return
        if self._source_mode == "hackrf":
            if self._parameter_capability is None or self._parameter_estimator is None:
                self._status_message = "Kartın çok kareli kanal gücü ölçüm profili kullanılamıyor."
                self.stateChanged.emit()
                return
            if self._analysis_span_draft is None or selected is None:
                self._status_message = "Seçili hedef için geçerli kanal ölçüm aralığı oluşturulamadı."
                self.stateChanged.emit()
                return
            if self._df_channel_span is None:
                self._df_channel_span = self._analysis_span_draft
                self._df_target_frequency_hz = float(frequency_hz)
            lower, upper = self._df_channel_span
            peak_bin = int(selected["peakBin"])
            if not lower <= peak_bin <= upper:
                self._status_message = "Seçili tespit, yön oturumunda sabitlenen hedef kanalın dışında."
                self.stateChanged.emit()
                return
            frequency_hz = float(self._df_target_frequency_hz)
            try:
                self._span_revision += 1
                self._analysis_span = AnalysisSpan(lower, upper, "auto_suggested", self._span_revision)
            except ValueError as exc:
                self._status_message = str(exc)
                self.stateChanged.emit()
                return
            session = self._live_session
            configuration = getattr(session, "configuration", None)
            if configuration is None:
                self._status_message = "Kart kanal gücü ölçümü için canlı alıcı bağlamı bulunamadı."
                self.stateChanged.emit()
                return
            receiver_binding = (
                f"hackrf|{float(configuration.output_center_frequency_hz):.6f}|"
                f"{float(self.sampleRateHz):.6f}|{lower}:{upper}|"
                f"{configuration.lna_gain_db}:{configuration.vga_gain_db}"
            )
            self._pending_direction_measurement = {
                "antenna_angle_deg": float(antenna_angle_deg),
                "reference": reference,
                "reference_deg": float(reference_deg),
                "frequency_hz": float(frequency_hz),
                "bandwidth_hz": float((upper - lower + 1) * self.sampleRateHz / 4096.0),
                "receiver_binding": receiver_binding,
                # A live-session frame counter restarts at zero after each angle.
                # Prefix it with the session generation so one physical frame can
                # never satisfy two antenna-angle records.
                "frame_id": (int(self._generation) << 32) | int(selected["lastObservedFrame"]),
                "board_endpoint": (configuration.board_host, configuration.board_port),
                "resume_settings": {
                    "center_hz": configuration.output_center_frequency_hz,
                    "lna_db": configuration.lna_gain_db,
                    "vga_db": configuration.vga_gain_db,
                    "frame_count": configuration.frame_count,
                },
            }
            self._request_live_measurement()
            if self._pending_live_measurement is None:
                self._pending_direction_measurement = None
                return
            self._status_message = (
                "Dört ardışık FPGA karesi sabitlendi; kart PL/ARM kanal gücü ölçülüyor."
            )
            self._add_log(
                "Yön Bulma",
                f"{antenna_angle_deg:.1f}° için çok kareli kart güç ölçümü istendi",
            )
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

    @Slot()
    def clearDirectionMeasurements(self) -> None:
        if (self._busy and self._active_task_kind != "live") or self._pending_live_measurement is not None:
            return
        self._reset_direction()

    def _reset_direction(self) -> None:
        self._pending_direction_measurement = None
        self._df_channel_span = None
        self._df_target_frequency_hz = None
        self._df.clear()
        self._df_points = []
        self._df_status = "15° adımlı 24 farklı anten açısında kanal gücü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self._df_reference_key = None
        self.directionChanged.emit()
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
