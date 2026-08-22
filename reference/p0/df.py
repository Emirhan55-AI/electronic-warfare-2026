"""Manual, non-coherent amplitude direction finding for P0."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class DFMeasurement:
    angle_deg: float
    relative_power_db: float
    frequency_hz: float
    timestamp_utc: str
    confidence: float
    source: str = "REPLAY"
    geographic_bearing_deg: float | None = None

    @classmethod
    def create(
        cls,
        *,
        angle_deg: float,
        relative_power_db: float,
        frequency_hz: float,
        confidence: float,
        timestamp_utc: str | None = None,
        source: str = "REPLAY",
        geographic_bearing_deg: float | None = None,
    ) -> "DFMeasurement":
        values = (angle_deg, relative_power_db, frequency_hz, confidence)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("DF measurement values must be finite")
        if frequency_hz <= 0 or not 0.0 <= confidence <= 1.0:
            raise ValueError("DF frequency or confidence is invalid")
        stamp = timestamp_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not source.strip():
            raise ValueError("DF measurement source is required")
        if geographic_bearing_deg is not None and not math.isfinite(geographic_bearing_deg):
            raise ValueError("DF geographic bearing must be finite when provided")
        return cls(
            angle_deg % 360.0,
            relative_power_db,
            frequency_hz,
            stamp,
            confidence,
            source.strip(),
            None if geographic_bearing_deg is None else geographic_bearing_deg % 360.0,
        )


@dataclass(frozen=True)
class DFEstimate:
    raw_maximum_angle_deg: float
    estimated_angle_deg: float
    peak_power_db: float
    confidence: float
    measurement_count: int
    status: str


class ManualAmplitudeDF:
    def __init__(self) -> None:
        self._measurements: list[DFMeasurement] = []

    @property
    def measurements(self) -> tuple[DFMeasurement, ...]:
        return tuple(sorted(self._measurements, key=lambda item: (item.angle_deg, item.timestamp_utc)))

    def add(self, measurement: DFMeasurement) -> None:
        self._measurements.append(measurement)

    def clear(self) -> None:
        self._measurements.clear()

    def estimate(self) -> DFEstimate:
        if not self._measurements:
            raise ValueError("at least one measurement is required")
        aggregated: dict[float, list[DFMeasurement]] = {}
        for measurement in self._measurements:
            aggregated.setdefault(measurement.angle_deg, []).append(measurement)
        points = []
        for angle, items in aggregated.items():
            weight = sum(max(item.confidence, 0.01) for item in items)
            power = sum(item.relative_power_db * max(item.confidence, 0.01) for item in items) / weight
            confidence = sum(item.confidence for item in items) / len(items)
            points.append((angle, power, confidence))
        points.sort(key=lambda item: (-item[1], item[0]))
        peak = points[0]
        second_power = points[1][1] if len(points) > 1 else peak[1]
        contrast = max(0.0, peak[1] - second_power)
        angular_coverage = len(points) / max(6.0, len(points))
        confidence = peak[2] * min(1.0, contrast / 6.0) * angular_coverage
        if len(points) < 3:
            status = "YETERSİZ AÇI"
        elif contrast < 1.0 or confidence < 0.15:
            status = "BELİRSİZ MAKSİMUM"
        else:
            status = "LOB HAZIR"
        return DFEstimate(peak[0], peak[0], peak[1], confidence, len(self._measurements), status)

    @staticmethod
    def angular_error_deg(estimated_deg: float, ground_truth_deg: float) -> float:
        return abs((estimated_deg - ground_truth_deg + 180.0) % 360.0 - 180.0)

    @classmethod
    def rms_error_deg(cls, estimates: list[float], ground_truths: list[float]) -> float:
        if not estimates or len(estimates) != len(ground_truths):
            raise ValueError("equal non-empty estimate and truth sequences are required")
        errors = [cls.angular_error_deg(estimated, truth) for estimated, truth in zip(estimates, ground_truths)]
        return math.sqrt(sum(error * error for error in errors) / len(errors))
