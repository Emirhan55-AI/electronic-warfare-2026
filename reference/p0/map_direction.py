"""Presentation-only geographic direction contracts for the P0 operator console.

This module deliberately converts a known sensor heading and an existing
amplitude-DF result into a finite Line Of Bearing (LOB) presentation. It does
not estimate a transmitter position or perform any form of localization.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .df import DFEstimate, DFMeasurement


def normalize_bearing_deg(value: float) -> float:
    """Normalize a finite geographic or relative angle to ``[0, 360)``."""
    if not math.isfinite(value):
        raise ValueError("bearing must be finite")
    return value % 360.0


@dataclass(frozen=True)
class SensorPosition:
    """A known sensor position and optional geographic heading reference."""

    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_m: float | None
    heading_deg: float | None
    source: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.source.strip():
            raise ValueError("sensor name and source are required")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude must be within [-90, 90]")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude must be within [-180, 180]")
        if self.altitude_m is not None and not math.isfinite(self.altitude_m):
            raise ValueError("altitude must be finite when provided")
        if self.heading_deg is not None:
            object.__setattr__(self, "heading_deg", normalize_bearing_deg(self.heading_deg))


@dataclass(frozen=True)
class DirectionPresentation:
    """A display contract built from a canonical DF estimate, never an estimator."""

    sensor: SensorPosition
    frequency_hz: float
    relative_antenna_angle_deg: float
    geographic_azimuth_deg: float | None
    confidence: float
    peak_power_db: float
    measurement_timestamp_utc: str
    backend: str
    source: str

    def __post_init__(self) -> None:
        values = (self.frequency_hz, self.relative_antenna_angle_deg, self.confidence, self.peak_power_db)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("direction presentation values must be finite")
        if self.frequency_hz <= 0.0 or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("direction presentation frequency or confidence is invalid")
        if self.geographic_azimuth_deg is not None:
            object.__setattr__(self, "geographic_azimuth_deg", normalize_bearing_deg(self.geographic_azimuth_deg))

    @property
    def has_geographic_lob(self) -> bool:
        return self.geographic_azimuth_deg is not None

    @property
    def geographic_status(self) -> str:
        return "Coğrafi yön hesaplandı" if self.has_geographic_lob else "Bağıl yön — coğrafi azimut referansı yok"


@dataclass(frozen=True)
class GeographicLOB:
    """Finite geographic geometry used only to render a direction line.

    ``render_endpoint`` is not a transmitter or target estimate. It is a
    geodesic endpoint selected solely to make an LOB visible on a map.
    """

    start_latitude_deg: float
    start_longitude_deg: float
    render_endpoint_latitude_deg: float
    render_endpoint_longitude_deg: float
    bearing_deg: float
    display_distance_m: float
    arrowhead_coordinates: tuple[tuple[float, float], ...]


def destination_point(
    latitude_deg: float,
    longitude_deg: float,
    bearing_deg: float,
    distance_m: float,
) -> tuple[float, float]:
    """Return a WGS-84-like spherical destination point for display geometry."""
    values = (latitude_deg, longitude_deg, bearing_deg, distance_m)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("geographic destination values must be finite")
    if not -90.0 <= latitude_deg <= 90.0 or not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("geographic origin is invalid")
    if distance_m < 0.0:
        raise ValueError("display distance must not be negative")
    radius_m = 6_371_008.8
    angular_distance = distance_m / radius_m
    latitude = math.radians(latitude_deg)
    longitude = math.radians(longitude_deg)
    bearing = math.radians(normalize_bearing_deg(bearing_deg))
    destination_latitude = math.asin(
        math.sin(latitude) * math.cos(angular_distance)
        + math.cos(latitude) * math.sin(angular_distance) * math.cos(bearing)
    )
    destination_longitude = longitude + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(latitude),
        math.cos(angular_distance) - math.sin(latitude) * math.sin(destination_latitude),
    )
    return math.degrees(destination_latitude), (math.degrees(destination_longitude) + 540.0) % 360.0 - 180.0


def geographic_lob_geometry(
    presentation: DirectionPresentation,
    *,
    display_distance_m: float = 2_500.0,
) -> GeographicLOB | None:
    """Create a finite geodesic LOB and arrowhead only when azimuth is valid."""
    if not presentation.has_geographic_lob:
        return None
    assert presentation.geographic_azimuth_deg is not None
    end_latitude, end_longitude = destination_point(
        presentation.sensor.latitude_deg,
        presentation.sensor.longitude_deg,
        presentation.geographic_azimuth_deg,
        display_distance_m,
    )
    arrow_size_m = min(180.0, max(45.0, display_distance_m * 0.09))
    left_latitude, left_longitude = destination_point(
        end_latitude,
        end_longitude,
        presentation.geographic_azimuth_deg + 150.0,
        arrow_size_m,
    )
    right_latitude, right_longitude = destination_point(
        end_latitude,
        end_longitude,
        presentation.geographic_azimuth_deg - 150.0,
        arrow_size_m,
    )
    return GeographicLOB(
        start_latitude_deg=presentation.sensor.latitude_deg,
        start_longitude_deg=presentation.sensor.longitude_deg,
        render_endpoint_latitude_deg=end_latitude,
        render_endpoint_longitude_deg=end_longitude,
        bearing_deg=presentation.geographic_azimuth_deg,
        display_distance_m=display_distance_m,
        arrowhead_coordinates=(
            (end_longitude, end_latitude),
            (left_longitude, left_latitude),
            (right_longitude, right_latitude),
            (end_longitude, end_latitude),
        ),
    )


def build_direction_presentation(
    *,
    sensor: SensorPosition,
    estimate: DFEstimate,
    peak_measurement: DFMeasurement,
    backend: str,
    source: str,
) -> DirectionPresentation:
    """Bind an existing DF result to geographic display metadata only."""
    relative_angle = normalize_bearing_deg(estimate.estimated_angle_deg)
    geographic = None if sensor.heading_deg is None else normalize_bearing_deg(sensor.heading_deg + relative_angle)
    return DirectionPresentation(
        sensor=sensor,
        frequency_hz=peak_measurement.frequency_hz,
        relative_antenna_angle_deg=relative_angle,
        geographic_azimuth_deg=geographic,
        confidence=estimate.confidence,
        peak_power_db=estimate.peak_power_db,
        measurement_timestamp_utc=peak_measurement.timestamp_utc,
        backend=backend,
        source=source,
    )
