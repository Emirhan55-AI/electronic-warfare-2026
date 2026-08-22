"""Independent deterministic amplitude-angle fixtures for host DF training."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SyntheticDFScene:
    scene_id: str
    truth_bearing_deg: float
    measurements: tuple[tuple[float, float, float], ...]


def circular_delta_deg(angle_deg: float, truth_deg: float) -> float:
    """Signed shortest angular separation, independent of the estimator."""
    return (angle_deg - truth_deg + 180.0) % 360.0 - 180.0


def build_synthetic_df_scene(
    truth_bearing_deg: float = 75.0,
    *,
    angular_step_deg: int = 15,
) -> SyntheticDFScene:
    """Generate a plausible directional pattern without calling the DF estimator."""
    if angular_step_deg <= 0 or 360 % angular_step_deg:
        raise ValueError("angular step must divide 360")
    truth = float(truth_bearing_deg) % 360.0
    points: list[tuple[float, float, float]] = []
    for angle in range(0, 360, angular_step_deg):
        delta = math.radians(circular_delta_deg(float(angle), truth))
        forward = max(math.cos(delta), 0.0) ** 4
        back = max(-math.cos(delta), 0.0) ** 2
        deterministic_variation = 0.22 * math.sin(math.radians(7.0 * angle + 13.0))
        power_dbfs = -38.0 + 25.0 * forward + 3.0 * back + deterministic_variation
        confidence = 0.92 if abs(math.degrees(delta)) <= 90.0 else 0.82
        points.append((float(angle), float(power_dbfs), confidence))
    return SyntheticDFScene(
        f"host-synthetic-bearing-{truth:g}",
        truth,
        tuple(points),
    )


def build_df_acceptance_scenes() -> tuple[SyntheticDFScene, ...]:
    return tuple(build_synthetic_df_scene(truth) for truth in (75.0, 210.0, 355.0))
