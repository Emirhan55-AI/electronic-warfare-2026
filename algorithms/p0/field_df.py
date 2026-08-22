"""Truthful P0 field-DF input contracts.

These contracts keep a manually entered antenna angle separate from a
geographic reference.  They do not infer a physical antenna heading.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .map_direction import normalize_bearing_deg


class PositionSource(StrEnum):
    AUTO_PC = "BİLGİSAYAR"
    MANUAL = "MANUEL"
    HOST_SYNTHETIC = "HOST/SYNTHETIC"
    REPLAY = "REPLAY"
    LIVE_GNSS_RESERVED = "LIVE GNSS (REZERVE)"


class AntennaReference(StrEnum):
    NORTH = "KUZEY / 0° COĞRAFİ"
    MANUAL_GEOGRAPHIC = "MANUEL COĞRAFİ BAŞ"
    UNAVAILABLE = "REFERANS YOK"


@dataclass(frozen=True)
class LocationFix:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float | None
    accuracy_m: float | None
    source: PositionSource
    timestamp_utc: str | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("enlem -90 ile 90 arasında olmalıdır")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("boylam -180 ile 180 arasında olmalıdır")
        if self.altitude_m is not None and not math.isfinite(self.altitude_m):
            raise ValueError("yükseklik sonlu olmalıdır")
        if self.accuracy_m is not None and (not math.isfinite(self.accuracy_m) or self.accuracy_m < 0.0):
            raise ValueError("doğruluk sıfır veya pozitif sonlu olmalıdır")


def geographic_bearing_from_manual_reference(
    reference: AntennaReference,
    manual_antenna_angle_deg: float,
    manual_geographic_reference_deg: float | None = None,
) -> float | None:
    """Return geographic bearing only from an explicit operator reference."""
    angle = normalize_bearing_deg(manual_antenna_angle_deg)
    if reference is AntennaReference.NORTH:
        return angle
    if reference is AntennaReference.MANUAL_GEOGRAPHIC:
        if manual_geographic_reference_deg is None:
            return None
        return normalize_bearing_deg(manual_geographic_reference_deg + angle)
    return None
