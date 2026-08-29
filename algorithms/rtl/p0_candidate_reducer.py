"""Bit-true P0 OS-CFAR and wideband candidate-reduction reference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .candidate_grouping import CandidateRecord, MAX_CANDIDATES
from .p0_os_cfar import (
    FRAME_LENGTH,
    POWER_WIDTH,
    RADIUS,
    detect_frame,
    shifted_to_natural,
)


REGION_SIZE = 256
REGION_COUNT = FRAME_LENGTH // REGION_SIZE
INTEGRATION_BINS = 32
INTEGRATION_LEFT = 15
INTEGRATION_RIGHT = 16
MINIMUM_RECOVERY_SPAN = 41
MAXIMUM_GAP_BINS = 1
PFA_SELECT = 1
FIXED_COEFFICIENT_BITS = 48
OS_THRESHOLD_Q48 = 2_415_095_562_554_865
NOISE_Q48 = 203_041_276_517_400
REGIONAL_THRESHOLD_Q48 = 507_603_191_293_500
INTEGRATED_THRESHOLD_Q48 = 16_243_302_121_391_996


@dataclass(frozen=True)
class CandidateReductionFrame:
    """Final candidates and intermediate wideband decisions for one frame."""

    candidates: tuple[CandidateRecord, ...]
    os_candidates: tuple[CandidateRecord, ...]
    recovery_candidates: tuple[CandidateRecord, ...]
    integrated_detections: tuple[bool, ...]
    region_median_twice: tuple[int, ...]


def _validated_natural_power(values: Iterable[int]) -> tuple[int, ...]:
    frame = tuple(values)
    if len(frame) != FRAME_LENGTH:
        raise ValueError("P0 aday azaltıcı tam 4096 güç hücresi gerektirir.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < (1 << POWER_WIDTH)
        for value in frame
    ):
        raise ValueError("Güç hücreleri unsigned 58-bit olmalıdır.")
    return frame


def _round_fixed(value: int, coefficient: int) -> int:
    return (value * coefficient + (1 << (FIXED_COEFFICIENT_BITS - 1))) >> FIXED_COEFFICIENT_BITS


def _candidate(
    start: int,
    end: int,
    peak: int,
    power: tuple[int, ...],
    noise: int,
    threshold: int,
) -> CandidateRecord:
    return CandidateRecord(
        start_shifted_bin=start,
        end_shifted_bin=end,
        peak_shifted_bin=peak,
        peak_power=power[peak],
        regional_noise=noise,
        threshold=threshold,
        pfa_select=PFA_SELECT,
        evaluate_center=False,
    )


def _groups(detected: tuple[bool, ...], start: int, stop: int) -> tuple[tuple[int, int], ...]:
    bins = [index for index in range(start, stop) if detected[index]]
    if not bins:
        return ()
    groups: list[tuple[int, int]] = []
    group_start = bins[0]
    group_end = bins[0]
    for index in bins[1:]:
        if index - group_end <= MAXIMUM_GAP_BINS + 1:
            group_end = index
        else:
            groups.append((group_start, group_end))
            group_start = group_end = index
    groups.append((group_start, group_end))
    return tuple(groups)


def _peak(power: tuple[int, ...], start: int, end: int) -> int:
    peak = start
    for index in range(start + 1, end + 1):
        if power[index] > power[peak]:
            peak = index
    return peak


def _os_candidates(
    power: tuple[int, ...],
    detected: tuple[bool, ...],
    order_statistics: tuple[int, ...],
) -> tuple[CandidateRecord, ...]:
    candidates = []
    for start, end in _groups(detected, RADIUS, FRAME_LENGTH - RADIUS):
        peak = _peak(power, start, end)
        noise = order_statistics[peak]
        threshold = _round_fixed(noise, OS_THRESHOLD_Q48)
        candidates.append(_candidate(start, end, peak, power, noise, threshold))
    return tuple(candidates)


def _regional_medians(power: tuple[int, ...]) -> tuple[int, ...]:
    medians = []
    for region in range(REGION_COUNT):
        base = region * REGION_SIZE
        ordered = sorted(power[base : base + REGION_SIZE])
        medians.append(ordered[REGION_SIZE // 2 - 1] + ordered[REGION_SIZE // 2])
    return tuple(medians)


def _integrated_detections(
    power: tuple[int, ...], region_median_twice: tuple[int, ...]
) -> tuple[bool, ...]:
    detected = [False] * FRAME_LENGTH
    evaluated_start = max(RADIUS, INTEGRATION_LEFT)
    evaluated_stop = FRAME_LENGTH - max(RADIUS, INTEGRATION_RIGHT)
    window_sum = sum(
        power[evaluated_start - INTEGRATION_LEFT : evaluated_start + INTEGRATION_RIGHT + 1]
    )
    for center in range(evaluated_start, evaluated_stop):
        median_twice = region_median_twice[center // REGION_SIZE]
        detected[center] = (
            window_sum << FIXED_COEFFICIENT_BITS
        ) > median_twice * INTEGRATED_THRESHOLD_Q48
        if center + 1 < evaluated_stop:
            window_sum -= power[center - INTEGRATION_LEFT]
            window_sum += power[center + INTEGRATION_RIGHT + 1]
    return tuple(detected)


def _recovery_candidates(
    power: tuple[int, ...],
    detected: tuple[bool, ...],
    region_median_twice: tuple[int, ...],
) -> tuple[CandidateRecord, ...]:
    recoveries = []
    for group_start, group_end in _groups(detected, RADIUS, FRAME_LENGTH - RADIUS):
        start = group_start + INTEGRATION_LEFT
        end = group_end - INTEGRATION_RIGHT
        if end < start or end - start + 1 < MINIMUM_RECOVERY_SPAN:
            continue
        peak = _peak(power, start, end)
        median_twice = region_median_twice[peak // REGION_SIZE]
        noise = _round_fixed(median_twice, NOISE_Q48)
        threshold = _round_fixed(median_twice, REGIONAL_THRESHOLD_Q48)
        recoveries.append(_candidate(start, end, peak, power, noise, threshold))
    return tuple(recoveries)


def reduce_candidates(natural_power: Iterable[int]) -> CandidateReductionFrame:
    """Return the lossless P0 sparse-candidate contract for one natural-order frame."""
    natural = _validated_natural_power(natural_power)
    shifted = tuple(natural[shifted_to_natural(index)] for index in range(FRAME_LENGTH))
    os_frame = detect_frame(natural)
    os_candidates = _os_candidates(
        shifted, os_frame.detected_shifted, os_frame.order_statistic_shifted
    )
    medians = _regional_medians(shifted)
    integrated = _integrated_detections(shifted, medians)
    recoveries = _recovery_candidates(shifted, integrated, medians)
    retained = tuple(
        candidate
        for candidate in os_candidates
        if not any(
            candidate.start_shifted_bin <= recovery.end_shifted_bin
            and recovery.start_shifted_bin <= candidate.end_shifted_bin
            for recovery in recoveries
        )
    )
    candidates = tuple(
        sorted(
            (*retained, *recoveries),
            key=lambda item: (
                item.start_shifted_bin,
                item.end_shifted_bin,
                item.peak_shifted_bin,
            ),
        )
    )
    if len(candidates) > MAX_CANDIDATES:
        raise ArithmeticError("Aday sayısı kanıtlanmış çerçeve sınırını aştı.")
    return CandidateReductionFrame(
        candidates=candidates,
        os_candidates=os_candidates,
        recovery_candidates=recoveries,
        integrated_detections=integrated,
        region_median_twice=medians,
    )


def architecture_study() -> dict[str, object]:
    return {
        "selected": "sparse final-candidate packet for detection frames",
        "full_power_policy": "retained only for explicit parameter-measurement frames",
        "local_detector": "P0 OS-CFAR rank-24/32 strict decision",
        "wideband_detector": "32-bin integrated energy against 16 regional medians",
        "fusion": "wideband recovery suppresses overlapping OS fragments",
        "fixed_coefficient_bits": FIXED_COEFFICIENT_BITS,
        "maximum_candidates": MAX_CANDIDATES,
        "requires_dma_overlap": True,
        "physical_acceptance": False,
    }
