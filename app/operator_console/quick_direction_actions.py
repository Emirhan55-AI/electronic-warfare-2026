"""Manual direction-measurement actions for the Qt Quick view model."""

from __future__ import annotations

import math

from PySide6.QtCore import Slot

from algorithms.p0.df import DFMeasurement
from algorithms.p0.field_df import AntennaReference, geographic_bearing_from_manual_reference


class QuickDirectionActionsMixin:
    """Keep manual DF measurement state separate from RF detection control."""

    @Slot(float, str, float)
    def addDirectionMeasurement(self, antenna_angle_deg: float, reference: str, reference_deg: float) -> None:
        if self._last_result is None or self._source is None:
            self._status_message = "Yön ölçümü için işlenmiş gerçek bir kaynak karesi gerekir."
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
        if relative_power_db is None:
            self._status_message = "Geçerli dBFS güç değeri bulunamadı; ölçüm kaydedilmedi."
            self.stateChanged.emit()
            return
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
        measurement = DFMeasurement.create(
            angle_deg=antenna_angle_deg,
            relative_power_db=relative_power_db,
            frequency_hz=float(getattr(self._source, "center_frequency_hz")),
            confidence=1.0,
            source=self._source_name,
            geographic_bearing_deg=bearing,
        )
        self._df_reference_key = reference_key
        self._df.add(measurement)
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
        self._reset_direction()

    def _reset_direction(self) -> None:
        self._df.clear()
        self._df_points = []
        self._df_status = "En az üç farklı anten açısında gerçek güç ölçümü gerekir."
        self._df_relative = "—"
        self._df_bearing = "—"
        self._df_reference_key = None
        self.directionChanged.emit()
