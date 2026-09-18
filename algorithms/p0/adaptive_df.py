"""Adaptive manual sweep planning for a directional antenna.

The operator starts with the antenna's current direction as 0 degrees.  The
planner first brackets the antenna lobe on both sides with 15-degree steps,
then samples the strongest coarse region at 5-degree spacing and finally asks
for one opposite-direction measurement to retain the front/back ambiguity
gate.  A channel-power sample for which the locked target was not detected is
still a valid lobe-boundary observation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


COARSE_STEP_DEG = 15.0
REFINEMENT_STEP_DEG = 5.0
REFINEMENT_RADIUS_DEG = 10.0


@dataclass(frozen=True)
class AdaptiveDFObservation:
    angle_deg: float
    power_db: float
    target_observed: bool


class AdaptiveDirectionSweep:
    """Plan a bounded sector search without requiring a full 360-degree grid."""

    def __init__(self) -> None:
        self._observations: dict[float, AdaptiveDFObservation] = {}

    @staticmethod
    def _key(angle_deg: float) -> float:
        return round(angle_deg % 360.0, 6)

    @property
    def observations(self) -> tuple[AdaptiveDFObservation, ...]:
        return tuple(self._observations.values())

    def clear(self) -> None:
        self._observations.clear()

    def record(self, angle_deg: float, power_db: float, target_observed: bool) -> None:
        if not math.isfinite(angle_deg) or not math.isfinite(power_db):
            raise ValueError("Uyarlamalı yön gözlemi sonlu açı ve güç içermelidir.")
        key = self._key(angle_deg)
        if key in self._observations:
            raise ValueError("Bu anten açısı uyarlamalı taramada zaten ölçüldü.")
        if not self._observations and (key != 0.0 or not target_observed):
            raise ValueError("Uyarlamalı yön taraması 0° doğrulanmış hedef ölçümüyle başlamalıdır.")
        self._observations[key] = AdaptiveDFObservation(
            key, float(power_db), bool(target_observed)
        )

    def target_observed_at(self, angle_deg: float) -> bool | None:
        item = self._observations.get(self._key(angle_deg))
        return None if item is None else item.target_observed

    def _clockwise_boundary(self) -> tuple[float, float] | None:
        last_observed = 0.0
        for index in range(1, 24):
            angle = index * COARSE_STEP_DEG
            item = self._observations.get(self._key(angle))
            if item is None:
                return None
            if not item.target_observed:
                return last_observed, angle
            last_observed = angle
        return None

    def _counterclockwise_boundary(self) -> tuple[float, float] | None:
        last_observed = 0.0
        for index in range(1, 24):
            angle = 360.0 - index * COARSE_STEP_DEG
            item = self._observations.get(self._key(angle))
            if item is None:
                return None
            if not item.target_observed:
                return last_observed, angle
            last_observed = angle
        return None

    def _next_clockwise_coarse(self) -> float | None:
        for index in range(1, 24):
            angle = index * COARSE_STEP_DEG
            item = self._observations.get(self._key(angle))
            if item is None:
                return angle
            if not item.target_observed:
                return None
        return None

    def _next_counterclockwise_coarse(self) -> float | None:
        for index in range(1, 24):
            angle = 360.0 - index * COARSE_STEP_DEG
            item = self._observations.get(self._key(angle))
            if item is None:
                return angle
            if not item.target_observed:
                return None
        return None

    @staticmethod
    def _signed_from_zero(angle_deg: float) -> float:
        normalized = angle_deg % 360.0
        return normalized - 360.0 if normalized > 180.0 else normalized

    def _sector_observations(self) -> tuple[AdaptiveDFObservation, ...]:
        clockwise = self._clockwise_boundary()
        counterclockwise = self._counterclockwise_boundary()
        if clockwise is None or counterclockwise is None:
            return ()
        right_limit = clockwise[1]
        left_limit = self._signed_from_zero(counterclockwise[1])
        return tuple(
            item
            for item in self._observations.values()
            if left_limit <= self._signed_from_zero(item.angle_deg) <= right_limit
        )

    def _best_sector_observation(self) -> AdaptiveDFObservation | None:
        observed = [item for item in self._sector_observations() if item.target_observed]
        if not observed:
            return None
        return max(observed, key=lambda item: (item.power_db, -item.angle_deg))

    def _refinement_angles(self) -> tuple[float, ...]:
        clockwise = self._clockwise_boundary()
        counterclockwise = self._counterclockwise_boundary()
        best = self._best_sector_observation()
        if clockwise is None or counterclockwise is None or best is None:
            return ()
        right_limit = clockwise[1]
        left_limit = self._signed_from_zero(counterclockwise[1])
        best_signed = self._signed_from_zero(best.angle_deg)
        candidates = []
        for offset in (-REFINEMENT_RADIUS_DEG, -REFINEMENT_STEP_DEG,
                       REFINEMENT_STEP_DEG, REFINEMENT_RADIUS_DEG):
            signed = best_signed + offset
            if left_limit < signed < right_limit:
                candidates.append(self._key(signed))
        return tuple(dict.fromkeys(candidates))

    @property
    def phase(self) -> str:
        if not self._observations:
            return "initial"
        if self._clockwise_boundary() is None:
            if all(
                self._key(index * COARSE_STEP_DEG) in self._observations
                for index in range(1, 24)
            ):
                return "boundary_not_found"
            return "clockwise_boundary"
        if self._counterclockwise_boundary() is None:
            return "counterclockwise_boundary"
        if any(self._key(angle) not in self._observations for angle in self._refinement_angles()):
            return "refinement"
        best = self._best_sector_observation()
        if best is None:
            return "invalid"
        opposite = self._key(best.angle_deg + 180.0)
        if opposite not in self._observations:
            return "opposite_check"
        return "complete"

    @property
    def complete(self) -> bool:
        return self.phase == "complete"

    def next_angle(self) -> float | None:
        phase = self.phase
        if phase == "initial":
            return 0.0
        if phase == "clockwise_boundary":
            return self._next_clockwise_coarse()
        if phase == "counterclockwise_boundary":
            return self._next_counterclockwise_coarse()
        if phase == "refinement":
            return next(
                angle
                for angle in self._refinement_angles()
                if self._key(angle) not in self._observations
            )
        if phase == "opposite_check":
            best = self._best_sector_observation()
            return None if best is None else self._key(best.angle_deg + 180.0)
        return None

    @property
    def progress(self) -> float:
        phase = self.phase
        if phase == "initial":
            return 0.0
        if phase == "clockwise_boundary":
            return min(0.35, 0.08 + 0.05 * len(self._observations))
        if phase == "counterclockwise_boundary":
            return min(0.6, 0.4 + 0.04 * len(self._observations))
        if phase == "refinement":
            refinements = self._refinement_angles()
            completed = sum(self._key(angle) in self._observations for angle in refinements)
            return 0.65 + 0.2 * completed / max(1, len(refinements))
        if phase == "opposite_check":
            return 0.9
        if phase == "complete":
            return 1.0
        return 0.0

    @property
    def status_text(self) -> str:
        return {
            "initial": "Başlangıç hedef ölçümü bekleniyor.",
            "clockwise_boundary": "Ana lobun saat yönündeki sınırı aranıyor.",
            "counterclockwise_boundary": "Ana lobun ters yöndeki sınırı aranıyor.",
            "refinement": "En güçlü bölge 5° adımlarla daraltılıyor.",
            "opposite_check": "Ön/arka belirsizliği için karşı yön denetleniyor.",
            "complete": "Uyarlamalı anten taraması tamamlandı.",
            "boundary_not_found": (
                "Saat yönünde lob dışı sınır bulunamadı; anten yönlülüğünü ve "
                "tespit eşiğini denetleyin."
            ),
            "invalid": "Uyarlamalı tarama geçerli bir hedef bölgesi oluşturamadı.",
        }[self.phase]

    @property
    def instruction_text(self) -> str:
        angle = self.next_angle()
        if angle is None:
            return self.status_text
        if self.phase == "initial":
            return "Antenin başlangıç yönünü 0° kabul edin ve ilk ölçümü alın."
        if self.phase == "clockwise_boundary":
            return (
                f"Anteni başlangıç yönünden saat yönünde {angle:.0f}° konumuna "
                "çevirin; lob dışına çıkana kadar ölçün."
            )
        if self.phase == "counterclockwise_boundary":
            return (
                "Anteni önce 0° başlangıç yönüne geri alın; ardından saat yönünün "
                f"tersine {360.0 - angle:.0f}° çevirip ölçün."
            )
        if self.phase == "refinement":
            signed = self._signed_from_zero(angle)
            direction = "saat yönünde" if signed >= 0.0 else "saat yönünün tersine"
            return (
                f"Hassaslaştırma için anteni 0° başlangıcından {direction} "
                f"{abs(signed):.0f}° konumuna çevirip ölçün."
            )
        signed = self._signed_from_zero(angle)
        direction = "saat yönünde" if signed >= 0.0 else "saat yönünün tersine"
        return (
            "Ön/arka ayrımı için anteni 0° başlangıcından "
            f"{direction} {abs(signed):.0f}° konumuna çevirip ölçün."
        )
