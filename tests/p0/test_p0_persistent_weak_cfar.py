from __future__ import annotations

import math
import random

import pytest

from algorithms.ps.persistent_weak_cfar import (
    MAXIMUM_TRACKED_WEAK_NOMINATIONS,
    MAXIMUM_WEAK_NOMINATIONS,
    PERSISTENCE_REQUIRED,
    PERSISTENCE_WINDOW,
    WEAK_ALPHA_Q32,
    PersistentWeakTracker,
    WeakNomination,
    architecture_study,
    ideal_exponential_false_nomination_probability,
    nominate_weak_frame,
    select_tracked_weak_nominations,
    weak_fixed_decision,
)
from algorithms.rtl.p0_os_cfar import COEFFICIENT_FRACTION_BITS, FRAME_LENGTH


def _flat_frame(*, peak_natural_bin: int | None = None, peak_power: int = 0) -> list[int]:
    frame = [1 << 30] * FRAME_LENGTH
    if peak_natural_bin is not None:
        frame[peak_natural_bin] = peak_power
    return frame


def test_weak_fixed_point_boundary_is_strict() -> None:
    reference = 1 << 30
    floor = (reference * WEAK_ALPHA_Q32) >> COEFFICIENT_FRACTION_BITS
    assert not weak_fixed_decision(floor, reference)
    assert weak_fixed_decision(floor + 1, reference)


@pytest.mark.parametrize("natural_bin", [123, 997, 2000, 3077, 3970])
def test_nomination_is_independent_of_absolute_rf_frequency(natural_bin: int) -> None:
    nominations = nominate_weak_frame(
        _flat_frame(peak_natural_bin=natural_bin, peak_power=5 << 30)
    )
    assert len(nominations) == 1
    assert nominations[0].peak_shifted_bin == natural_bin ^ 0x800


def test_arm_model_requires_24_of_32_and_tolerates_one_bin_peak_motion() -> None:
    tracker = PersistentWeakTracker()
    center = 1700
    result = ()
    for frame in range(PERSISTENCE_WINDOW):
        nominations = ()
        if frame < PERSISTENCE_REQUIRED:
            peak = center + (frame % 3) - 1
            nominations = (
                WeakNomination(peak, peak, peak, 5 << 30, 1 << 30),
            )
        result = tracker.update(nominations)
    assert len(result) == 1
    assert abs(result[0].peak_shifted_bin - center) <= 1
    assert result[0].observed_frames >= PERSISTENCE_REQUIRED
    assert result[0].mean_peak_to_os_db == pytest.approx(10.0 * math.log10(5.0), abs=0.02)


def test_transient_and_random_noise_nominations_do_not_confirm() -> None:
    tracker = PersistentWeakTracker()
    rng = random.Random(20260902)
    result = ()
    for frame in range(PERSISTENCE_WINDOW):
        nominations = []
        if frame < PERSISTENCE_REQUIRED - 4:
            peak = 1800
            nominations.append(WeakNomination(peak, peak, peak, 5 << 30, 1 << 30))
        for _ in range(35):
            peak = rng.randrange(20, FRAME_LENGTH - 20)
            nominations.append(WeakNomination(peak, peak, peak, 4 << 30, 1 << 30))
        result = tracker.update(nominations)
    assert result == ()


def test_ideal_noise_load_fits_the_bounded_sparse_contract() -> None:
    per_cell = ideal_exponential_false_nomination_probability()
    expected_cells = per_cell * (FRAME_LENGTH - 40)
    assert 0.008 < per_cell < 0.009
    assert 34.0 < expected_cells < 36.0
    assert MAXIMUM_WEAK_NOMINATIONS > expected_cells * 7


def test_tracker_admission_keeps_exactly_the_strongest_eight_ratios() -> None:
    nominations = tuple(
        WeakNomination(
            start_shifted_bin=100 + index * 10,
            end_shifted_bin=100 + index * 10,
            peak_shifted_bin=100 + index * 10,
            peak_power=(index + 2) * (1 << 30),
            order_statistic=1 << 30,
        )
        for index in range(20)
    )

    selected = select_tracked_weak_nominations(reversed(nominations))

    assert len(selected) == MAXIMUM_TRACKED_WEAK_NOMINATIONS
    assert [item.peak_shifted_bin for item in selected] == [
        220,
        230,
        240,
        250,
        260,
        270,
        280,
        290,
    ]


def test_tracker_admission_uses_exact_cross_product_and_deterministic_ties() -> None:
    nominations = (
        WeakNomination(300, 300, 300, 9, 3),
        WeakNomination(200, 200, 200, 6, 2),
        WeakNomination(400, 400, 400, 0, 0),
        WeakNomination(100, 100, 100, 1, 0),
    )

    selected = select_tracked_weak_nominations(nominations)

    assert [item.peak_shifted_bin for item in selected] == [100, 200, 300, 400]


def test_architecture_does_not_claim_unbuilt_hardware() -> None:
    study = architecture_study()
    assert study["frequency_specific_constants"] is False
    assert study["host_decision_owner"] is False
    assert study["maximum_tracked_nominations_per_frame"] == 8
    assert "digital board acceptance passed" in study["status"]
