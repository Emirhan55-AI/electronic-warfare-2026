"""Bit-true model for FPGA weak nomination and ARM long persistence.

The existing P0 OS-CFAR decision remains the high-confidence, single-frame
path.  This module models a second threshold against the *same* rank-24/32
reference statistic.  Only sparse peak locations cross the PL/PS boundary;
the PS confirms that a location is present in at least 24 of 32 frames.

This is a target architecture model.  It is not evidence that the bitstream or
the board service already implements the path.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import cmp_to_key
import math
from typing import Iterable

from algorithms.rtl.p0_os_cfar import (
    COEFFICIENT_FRACTION_BITS,
    FRAME_LENGTH,
    POWER_WIDTH,
    RADIUS,
    detect_frame,
    shifted_to_natural,
)


WEAK_THRESHOLD_DB = 6.0
WEAK_ALPHA_Q32 = round((10.0 ** (WEAK_THRESHOLD_DB / 10.0)) * (1 << 32))
PERSISTENCE_WINDOW = 32
PERSISTENCE_REQUIRED = 24
PEAK_TOLERANCE_BINS = 2
MAXIMUM_WEAK_NOMINATIONS = 1352
MAXIMUM_TRACKED_WEAK_NOMINATIONS = 8
MAXIMUM_EMITTED_WEAK_CANDIDATES = 8


@dataclass(frozen=True)
class WeakNomination:
    """One per-frame weak OS-CFAR peak in shifted FFT order."""

    start_shifted_bin: int
    end_shifted_bin: int
    peak_shifted_bin: int
    peak_power: int
    order_statistic: int

    @property
    def ratio_q8(self) -> int:
        if self.order_statistic == 0:
            return 0xFFFF if self.peak_power > 0 else 0
        return min(0xFFFF, (self.peak_power << 8) // self.order_statistic)


@dataclass(frozen=True)
class PersistentWeakCandidate:
    """A narrowband location confirmed by the 24-of-32 PS rule."""

    start_shifted_bin: int
    end_shifted_bin: int
    peak_shifted_bin: int
    observed_frames: int
    total_frames: int
    mean_peak_to_os_db: float


def _compare_nomination_strength(left: WeakNomination, right: WeakNomination) -> int:
    """Order nominations by the exact peak/reference ratio used by the ARM code."""

    left_infinite = left.peak_power != 0 and left.order_statistic == 0
    right_infinite = right.peak_power != 0 and right.order_statistic == 0
    if left_infinite != right_infinite:
        return -1 if left_infinite else 1
    left_product = left.peak_power * right.order_statistic
    right_product = right.peak_power * left.order_statistic
    if left_product != right_product:
        return -1 if left_product > right_product else 1
    if left.peak_shifted_bin != right.peak_shifted_bin:
        return -1 if left.peak_shifted_bin < right.peak_shifted_bin else 1
    if left.start_shifted_bin != right.start_shifted_bin:
        return -1 if left.start_shifted_bin < right.start_shifted_bin else 1
    return 0


def select_tracked_weak_nominations(
    nominations: Iterable[WeakNomination],
) -> tuple[WeakNomination, ...]:
    """Keep the eight strongest weak-only nominations, then restore bin order."""

    materialized = tuple(nominations)
    if len(materialized) > MAXIMUM_WEAK_NOMINATIONS:
        raise ArithmeticError("Zayıf aday sayısı ürün paket sınırını aştı.")
    strongest = sorted(materialized, key=cmp_to_key(_compare_nomination_strength))[
        :MAXIMUM_TRACKED_WEAK_NOMINATIONS
    ]
    return tuple(
        sorted(strongest, key=lambda item: (item.start_shifted_bin, item.end_shifted_bin))
    )


def weak_fixed_decision(cut_power: int, order_statistic: int) -> bool:
    """Apply the proposed 6 dB PL threshold with strict integer comparison."""

    for value in (cut_power, order_statistic):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Zayıf OS-CFAR gücü unsigned 58-bit olmalıdır.")
        if not 0 <= value < (1 << POWER_WIDTH):
            raise ValueError("Zayıf OS-CFAR gücü unsigned 58-bit olmalıdır.")
    return (cut_power << COEFFICIENT_FRACTION_BITS) > order_statistic * WEAK_ALPHA_Q32


def _groups(indices: list[int]) -> tuple[tuple[int, int], ...]:
    if not indices:
        return ()
    result: list[tuple[int, int]] = []
    start = end = indices[0]
    for index in indices[1:]:
        if index - end <= 2:
            end = index
        else:
            result.append((start, end))
            start = end = index
    result.append((start, end))
    return tuple(result)


def nominate_weak_frame(natural_power: Iterable[int]) -> tuple[WeakNomination, ...]:
    """Return sparse 6 dB nominations using the current PL OS reference."""

    frame = detect_frame(natural_power)
    shifted_power = tuple(
        frame.natural_power[shifted_to_natural(index)] for index in range(FRAME_LENGTH)
    )
    detected = [
        index
        for index in range(RADIUS, FRAME_LENGTH - RADIUS)
        if weak_fixed_decision(
            shifted_power[index], frame.order_statistic_shifted[index]
        )
    ]
    nominations: list[WeakNomination] = []
    for start, end in _groups(detected):
        peak = max(range(start, end + 1), key=shifted_power.__getitem__)
        nominations.append(
            WeakNomination(
                start_shifted_bin=start,
                end_shifted_bin=end,
                peak_shifted_bin=peak,
                peak_power=shifted_power[peak],
                order_statistic=frame.order_statistic_shifted[peak],
            )
        )
    if len(nominations) > MAXIMUM_WEAK_NOMINATIONS:
        raise ArithmeticError("Zayıf aday sayısı ürün paket sınırını aştı.")
    return tuple(nominations)


class PersistentWeakTracker:
    """Bounded ring-buffer model for the proposed ARM 24-of-32 decision."""

    def __init__(self) -> None:
        self._hits: deque[tuple[tuple[int, int], ...]] = deque()
        self._exact_hits: deque[tuple[tuple[int, int], ...]] = deque()
        self._counts = [0] * FRAME_LENGTH
        self._ratio_sums = [0] * FRAME_LENGTH
        self._exact_counts = [0] * FRAME_LENGTH
        self._exact_ratio_sums = [0] * FRAME_LENGTH

    @property
    def frame_count(self) -> int:
        return len(self._hits)

    def reset(self) -> None:
        self._hits.clear()
        self._exact_hits.clear()
        self._counts[:] = [0] * FRAME_LENGTH
        self._ratio_sums[:] = [0] * FRAME_LENGTH
        self._exact_counts[:] = [0] * FRAME_LENGTH
        self._exact_ratio_sums[:] = [0] * FRAME_LENGTH

    def update(
        self, nominations: Iterable[WeakNomination]
    ) -> tuple[PersistentWeakCandidate, ...]:
        frame_values: dict[int, int] = {}
        exact_values: dict[int, int] = {}
        for nomination in select_tracked_weak_nominations(nominations):
            if not (
                RADIUS <= nomination.start_shifted_bin
                <= nomination.peak_shifted_bin
                <= nomination.end_shifted_bin
                < FRAME_LENGTH - RADIUS
            ):
                raise ValueError("Zayıf aday FFT sınırları geçersizdir.")
            start = max(RADIUS, nomination.peak_shifted_bin - PEAK_TOLERANCE_BINS)
            end = min(
                FRAME_LENGTH - RADIUS - 1,
                nomination.peak_shifted_bin + PEAK_TOLERANCE_BINS,
            )
            ratio = nomination.ratio_q8
            exact_values[nomination.peak_shifted_bin] = max(
                exact_values.get(nomination.peak_shifted_bin, 0), ratio
            )
            for index in range(start, end + 1):
                frame_values[index] = max(frame_values.get(index, 0), ratio)

        packed = tuple(sorted(frame_values.items()))
        exact_packed = tuple(sorted(exact_values.items()))
        self._hits.append(packed)
        self._exact_hits.append(exact_packed)
        for index, ratio in packed:
            self._counts[index] += 1
            self._ratio_sums[index] += ratio
        for index, ratio in exact_packed:
            self._exact_counts[index] += 1
            self._exact_ratio_sums[index] += ratio
        if len(self._hits) > PERSISTENCE_WINDOW:
            for index, ratio in self._hits.popleft():
                self._counts[index] -= 1
                self._ratio_sums[index] -= ratio
            for index, ratio in self._exact_hits.popleft():
                self._exact_counts[index] -= 1
                self._exact_ratio_sums[index] -= ratio

        if len(self._hits) < PERSISTENCE_WINDOW:
            return ()
        persistent = [
            index
            for index in range(RADIUS, FRAME_LENGTH - RADIUS)
            if self._counts[index] >= PERSISTENCE_REQUIRED
        ]
        result: list[PersistentWeakCandidate] = []
        for start, end in _groups(persistent):
            peak = max(
                range(start, end + 1),
                key=lambda index: (
                    self._exact_counts[index],
                    self._exact_ratio_sums[index] / max(self._exact_counts[index], 1),
                    self._counts[index],
                    -index,
                ),
            )
            mean_ratio = (
                self._exact_ratio_sums[peak]
                / max(self._exact_counts[peak], 1)
                / 256.0
            )
            result.append(
                PersistentWeakCandidate(
                    start_shifted_bin=start,
                    end_shifted_bin=end,
                    peak_shifted_bin=peak,
                    observed_frames=self._counts[peak],
                    total_frames=PERSISTENCE_WINDOW,
                    mean_peak_to_os_db=(
                        10.0 * math.log10(mean_ratio)
                        if mean_ratio > 0.0
                        else math.inf
                    ),
                )
            )
        return tuple(result)


def ideal_exponential_false_nomination_probability() -> float:
    """Return P(CUT > alpha*rank24) for 32 independent exponential references."""

    alpha = WEAK_ALPHA_Q32 / float(1 << COEFFICIENT_FRACTION_BITS)
    return math.prod(index / (index + alpha) for index in range(9, 33))


def architecture_study() -> dict[str, object]:
    return {
        "status": "implemented in RTL and ARM; digital board acceptance passed",
        "pl": "rank-24/32 OS reference plus sparse strict 6 dB nomination",
        "ps": "exact-ratio top-8 admission; peak +/-2-bin occupancy ring; 24 of 32 confirmation",
        "weak_alpha_q32": WEAK_ALPHA_Q32,
        "maximum_nominations_per_frame": MAXIMUM_WEAK_NOMINATIONS,
        "maximum_tracked_nominations_per_frame": MAXIMUM_TRACKED_WEAK_NOMINATIONS,
        "maximum_emitted_weak_candidates": MAXIMUM_EMITTED_WEAK_CANDIDATES,
        "frequency_specific_constants": False,
        "host_decision_owner": False,
    }
