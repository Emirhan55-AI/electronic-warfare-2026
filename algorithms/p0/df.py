"""Manual, non-coherent amplitude direction finding for P0."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from statistics import median


@dataclass(frozen=True)
class DFProfile:
    """Acceptance limits for one amplitude-DF measurement session.

    The historical estimator remains available for frozen training evidence.
    ``FIELD_AMPLITUDE_DF_PROFILE`` is the product profile: it requires a
    substantially complete circular sweep and keeps the reported bearing at an
    actually measured antenna angle.
    """

    profile_id: str
    minimum_distinct_angles: int
    maximum_angular_gap_deg: float
    minimum_peak_prominence_db: float
    minimum_front_to_back_db: float | None
    minimum_measurements_per_angle: int
    average_in_linear_power: bool


LEGACY_AMPLITUDE_DF_PROFILE = DFProfile(
    profile_id="P0_AMPLITUDE_DF_LEGACY_V1",
    minimum_distinct_angles=3,
    maximum_angular_gap_deg=360.0,
    minimum_peak_prominence_db=1.0,
    minimum_front_to_back_db=None,
    minimum_measurements_per_angle=1,
    average_in_linear_power=False,
)

FIELD_AMPLITUDE_DF_PROFILE = DFProfile(
    profile_id="P0_AMPLITUDE_DF_FIELD_V1",
    minimum_distinct_angles=24,
    maximum_angular_gap_deg=15.0,
    minimum_peak_prominence_db=3.0,
    minimum_front_to_back_db=3.0,
    minimum_measurements_per_angle=1,
    average_in_linear_power=True,
)


@dataclass(frozen=True)
class DFMeasurement:
    angle_deg: float
    relative_power_db: float
    frequency_hz: float
    timestamp_utc: str
    confidence: float
    source: str = "REPLAY"
    geographic_bearing_deg: float | None = None
    power_spread_db: float = 0.0
    observation_count: int = 1
    channel_bandwidth_hz: float | None = None
    receiver_binding: str = ""
    frame_id: int | None = None

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
        power_spread_db: float = 0.0,
        observation_count: int = 1,
        channel_bandwidth_hz: float | None = None,
        receiver_binding: str = "",
        frame_id: int | None = None,
    ) -> "DFMeasurement":
        values = (angle_deg, relative_power_db, frequency_hz, confidence, power_spread_db)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("DF measurement values must be finite")
        if (
            frequency_hz <= 0
            or not 0.0 <= confidence <= 1.0
            or power_spread_db < 0.0
            or observation_count < 1
            or (channel_bandwidth_hz is not None and (not math.isfinite(channel_bandwidth_hz) or channel_bandwidth_hz <= 0.0))
            or (frame_id is not None and frame_id < 0)
        ):
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
            power_spread_db,
            observation_count,
            channel_bandwidth_hz,
            receiver_binding.strip(),
            frame_id,
        )


@dataclass(frozen=True)
class DFEstimate:
    raw_maximum_angle_deg: float
    estimated_angle_deg: float
    peak_power_db: float
    confidence: float
    measurement_count: int
    status: str
    distinct_angle_count: int = 0
    maximum_angular_gap_deg: float = 360.0
    peak_prominence_db: float = 0.0
    front_to_back_db: float | None = None
    angular_sampling_rms_deg: float | None = None
    profile_id: str = LEGACY_AMPLITUDE_DF_PROFILE.profile_id


class ManualAmplitudeDF:
    def __init__(self, profile: DFProfile = LEGACY_AMPLITUDE_DF_PROFILE) -> None:
        self.profile = profile
        self._measurements: list[DFMeasurement] = []

    @property
    def measurements(self) -> tuple[DFMeasurement, ...]:
        return tuple(sorted(self._measurements, key=lambda item: (item.angle_deg, item.timestamp_utc)))

    def add(self, measurement: DFMeasurement) -> None:
        if measurement.frame_id is not None and any(
            item.frame_id == measurement.frame_id and item.receiver_binding == measurement.receiver_binding
            for item in self._measurements
            if item.frame_id is not None
        ):
            raise ValueError("aynı kaynak karesi yön ölçümüne ikinci kez eklenemez")
        self._measurements.append(measurement)

    def clear(self) -> None:
        self._measurements.clear()

    def estimate(self) -> DFEstimate:
        if not self._measurements:
            raise ValueError("at least one measurement is required")
        aggregated: dict[float, list[DFMeasurement]] = {}
        for measurement in self._measurements:
            aggregated.setdefault(measurement.angle_deg, []).append(measurement)
        points: list[tuple[float, float, float, float, int]] = []
        for angle, items in aggregated.items():
            weights = [max(item.confidence, 0.01) * item.observation_count for item in items]
            weight = sum(weights)
            if self.profile.average_in_linear_power:
                linear_power = sum(
                    (10.0 ** (item.relative_power_db / 10.0)) * item_weight
                    for item, item_weight in zip(items, weights)
                ) / weight
                power = 10.0 * math.log10(max(linear_power, 1e-300))
            else:
                power = sum(item.relative_power_db * item_weight for item, item_weight in zip(items, weights)) / weight
            confidence = sum(item.confidence for item in items) / len(items)
            repeated_powers = [item.relative_power_db for item in items]
            centre = median(repeated_powers)
            between_repeat_spread = 1.4826 * median(abs(value - centre) for value in repeated_powers)
            stated_spread = math.sqrt(sum(item.power_spread_db ** 2 for item in items) / len(items))
            points.append((angle, power, confidence, math.hypot(between_repeat_spread, stated_spread), len(items)))
        points.sort(key=lambda item: (-item[1], item[0]))
        peak = points[0]
        angles = sorted(point[0] for point in points)
        gaps = [
            (angles[(index + 1) % len(angles)] - angle) % 360.0
            for index, angle in enumerate(angles)
        ]
        maximum_gap = max(gaps) if len(angles) > 1 else 360.0
        nominal_step = median(gaps) if len(gaps) > 1 else 360.0
        if self.profile.profile_id == LEGACY_AMPLITUDE_DF_PROFILE.profile_id:
            second_power = points[1][1] if len(points) > 1 else peak[1]
            prominence = max(0.0, peak[1] - second_power)
        else:
            separated = [
                point for point in points[1:]
                if self.angular_error_deg(point[0], peak[0]) > max(15.0, nominal_step * 1.5)
            ]
            competitor_power = max((point[1] for point in separated), default=points[1][1] if len(points) > 1 else peak[1])
            prominence = max(0.0, peak[1] - competitor_power)

        opposite_target = (peak[0] + 180.0) % 360.0
        opposite = min(points, key=lambda point: self.angular_error_deg(point[0], opposite_target))
        front_to_back = None
        if self.angular_error_deg(opposite[0], opposite_target) <= max(7.5, nominal_step / 2.0 + 1e-9):
            front_to_back = peak[1] - opposite[1]

        coverage_confidence = min(1.0, self.profile.maximum_angular_gap_deg / maximum_gap)
        stability_confidence = 1.0 / (1.0 + peak[3])
        prominence_confidence = min(1.0, prominence / max(6.0, self.profile.minimum_peak_prominence_db))
        confidence = peak[2] * coverage_confidence * stability_confidence * prominence_confidence
        if len(points) < self.profile.minimum_distinct_angles:
            status = "YETERSİZ AÇI"
        elif maximum_gap > self.profile.maximum_angular_gap_deg + 1e-9:
            status = "YETERSİZ AÇI KAPSAMI"
        elif any(point[4] < self.profile.minimum_measurements_per_angle for point in points):
            status = "YETERSİZ TEKRAR"
        elif len({item.receiver_binding for item in self._measurements if item.receiver_binding}) > 1:
            status = "ALICI AYARI DEĞİŞTİ"
        elif self._target_frequency_changed():
            status = "HEDEF FREKANSI DEĞİŞTİ"
        elif (
            self.profile.minimum_front_to_back_db is not None
            and (front_to_back is None or front_to_back < self.profile.minimum_front_to_back_db)
        ):
            status = "ÖN/ARKA BELİRSİZ"
        elif prominence < max(self.profile.minimum_peak_prominence_db, 2.0 * peak[3]) or confidence < 0.15:
            status = "BELİRSİZ MAKSİMUM"
        else:
            status = "LOB HAZIR"
        uniform_grid = max(gaps) - min(gaps) <= 1e-6 if gaps else False
        sampling_rms = nominal_step / math.sqrt(12.0) if uniform_grid else None
        return DFEstimate(
            peak[0], peak[0], peak[1], confidence, len(self._measurements), status,
            len(points), maximum_gap, prominence, front_to_back, sampling_rms,
            self.profile.profile_id,
        )

    def _target_frequency_changed(self) -> bool:
        if len(self._measurements) < 2:
            return False
        frequencies = [item.frequency_hz for item in self._measurements]
        bandwidths = [item.channel_bandwidth_hz for item in self._measurements if item.channel_bandwidth_hz is not None]
        if not bandwidths:
            return False
        return max(frequencies) - min(frequencies) > min(bandwidths) / 2.0

    @staticmethod
    def angular_error_deg(estimated_deg: float, ground_truth_deg: float) -> float:
        return abs((estimated_deg - ground_truth_deg + 180.0) % 360.0 - 180.0)

    @classmethod
    def rms_error_deg(cls, estimates: list[float], ground_truths: list[float]) -> float:
        if not estimates or len(estimates) != len(ground_truths):
            raise ValueError("equal non-empty estimate and truth sequences are required")
        errors = [cls.angular_error_deg(estimated, truth) for estimated, truth in zip(estimates, ground_truths)]
        return math.sqrt(sum(error * error for error in errors) / len(errors))
