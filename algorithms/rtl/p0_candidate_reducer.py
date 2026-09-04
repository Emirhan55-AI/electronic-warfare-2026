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
    fixed_weak_nomination,
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
WEAK_THRESHOLD_Q48 = 1_120_572_065_598_908
NOISE_Q48 = 203_041_276_517_400
REGIONAL_THRESHOLD_Q48 = 507_603_191_293_500
INTEGRATED_THRESHOLD_Q48 = 16_243_302_121_391_996
BROAD_REFERENCE_REGION_INDEX = 3
BROAD_MINIMUM_RECOVERY_SPAN = REGION_SIZE + 1
FLANK_MEDIAN_RATIO_Q48 = 703_687_441_776_640


@dataclass(frozen=True)
class CandidateReductionFrame:
    """Final candidates and intermediate wideband decisions for one frame."""

    candidates: tuple[CandidateRecord, ...]
    os_candidates: tuple[CandidateRecord, ...]
    recovery_candidates: tuple[CandidateRecord, ...]
    integrated_detections: tuple[bool, ...]
    regional_integrated_detections: tuple[bool, ...]
    broad_integrated_detections: tuple[bool, ...]
    frame_reference_twice: int
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
    *,
    weak_evidence: bool = False,
    single_frame_confident: bool = False,
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
        weak_evidence=weak_evidence,
        single_frame_confident=single_frame_confident,
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


def _strict_os_candidates(
    power: tuple[int, ...],
    strict_detected: tuple[bool, ...],
    order_statistics: tuple[int, ...],
) -> tuple[CandidateRecord, ...]:
    candidates = []
    for start, end in _groups(strict_detected, RADIUS, FRAME_LENGTH - RADIUS):
        peak = _peak(power, start, end)
        noise = order_statistics[peak]
        threshold = _round_fixed(noise, OS_THRESHOLD_Q48)
        candidates.append(_candidate(start, end, peak, power, noise, threshold))
    return tuple(candidates)


def strict_os_candidates(natural_power: Iterable[int]) -> tuple[CandidateRecord, ...]:
    """Return the strict single-frame OS-CFAR candidates for one frame."""
    natural = _validated_natural_power(natural_power)
    shifted = tuple(natural[shifted_to_natural(index)] for index in range(FRAME_LENGTH))
    os_frame = detect_frame(natural)
    return _strict_os_candidates(
        shifted, os_frame.detected_shifted, os_frame.order_statistic_shifted
    )


def _os_candidates(
    power: tuple[int, ...],
    strict_detected: tuple[bool, ...],
    order_statistics: tuple[int, ...],
) -> tuple[CandidateRecord, ...]:
    candidates = []
    weak_detected = tuple(
        fixed_weak_nomination(power[index], order_statistics[index])
        if RADIUS <= index < FRAME_LENGTH - RADIUS else False
        for index in range(FRAME_LENGTH)
    )
    for start, end in _groups(weak_detected, RADIUS, FRAME_LENGTH - RADIUS):
        peak = _peak(power, start, end)
        noise = order_statistics[peak]
        single_frame_confident = any(strict_detected[start : end + 1])
        threshold = _round_fixed(
            noise,
            OS_THRESHOLD_Q48 if single_frame_confident else WEAK_THRESHOLD_Q48,
        )
        candidates.append(
            _candidate(
                start,
                end,
                peak,
                power,
                noise,
                threshold,
                weak_evidence=True,
                single_frame_confident=single_frame_confident,
            )
        )
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


def _broad_integrated_detections(
    power: tuple[int, ...], frame_reference_twice: int
) -> tuple[bool, ...]:
    detected = [False] * FRAME_LENGTH
    evaluated_start = max(RADIUS, INTEGRATION_LEFT)
    evaluated_stop = FRAME_LENGTH - max(RADIUS, INTEGRATION_RIGHT)
    window_sum = sum(
        power[evaluated_start - INTEGRATION_LEFT : evaluated_start + INTEGRATION_RIGHT + 1]
    )
    threshold = frame_reference_twice * INTEGRATED_THRESHOLD_Q48
    for center in range(evaluated_start, evaluated_stop):
        detected[center] = (window_sum << FIXED_COEFFICIENT_BITS) > threshold
        if center + 1 < evaluated_stop:
            window_sum -= power[center - INTEGRATION_LEFT]
            window_sum += power[center + INTEGRATION_RIGHT + 1]
    return tuple(detected)


def _recovery_candidates(
    power: tuple[int, ...],
    detected: tuple[bool, ...],
    region_median_twice: tuple[int, ...],
    *,
    require_flanks: bool = False,
) -> tuple[CandidateRecord, ...]:
    recoveries = []
    for group_start, group_end in _groups(detected, RADIUS, FRAME_LENGTH - RADIUS):
        start = group_start + INTEGRATION_LEFT
        end = group_end - INTEGRATION_RIGHT
        if end < start or end - start + 1 < MINIMUM_RECOVERY_SPAN:
            continue
        peak = _peak(power, start, end)
        median_twice = region_median_twice[peak // REGION_SIZE]
        if require_flanks:
            if end - start + 1 < BROAD_MINIMUM_RECOVERY_SPAN:
                continue
            left_region = start // REGION_SIZE - 1
            right_region = end // REGION_SIZE + 1
            if left_region < 0 or right_region >= REGION_COUNT:
                continue
            inside_start = start // REGION_SIZE
            inside_stop = end // REGION_SIZE + 1
            if inside_start >= inside_stop:
                continue
            inside_median_twice = max(region_median_twice[inside_start:inside_stop])
            flank_median_twice = max(
                region_median_twice[left_region], region_median_twice[right_region]
            )
            if (inside_median_twice << FIXED_COEFFICIENT_BITS) <= (
                flank_median_twice * FLANK_MEDIAN_RATIO_Q48
            ):
                continue
            median_twice = flank_median_twice
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
    frame_reference_twice = sorted(medians)[BROAD_REFERENCE_REGION_INDEX]
    regional_integrated = _integrated_detections(shifted, medians)
    broad_integrated = _broad_integrated_detections(shifted, frame_reference_twice)
    integrated = tuple(first or second for first, second in zip(regional_integrated, broad_integrated))
    regional_recoveries = _recovery_candidates(shifted, regional_integrated, medians)
    broad_recoveries = _recovery_candidates(
        shifted, broad_integrated, medians, require_flanks=True
    )
    recoveries = tuple(sorted(
        (*[candidate for candidate in regional_recoveries
           if not any(
               candidate.start_shifted_bin <= broad.end_shifted_bin
               and broad.start_shifted_bin <= candidate.end_shifted_bin
               for broad in broad_recoveries
           )], *broad_recoveries),
        key=lambda item: (
            item.start_shifted_bin, item.end_shifted_bin, item.peak_shifted_bin
        ),
    ))
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
        regional_integrated_detections=regional_integrated,
        broad_integrated_detections=broad_integrated,
        frame_reference_twice=frame_reference_twice,
        region_median_twice=medians,
    )


def architecture_study() -> dict[str, object]:
    return {
        "selected": "sparse final-candidate packet for detection frames",
        "full_power_policy": "retained only for explicit parameter-measurement frames",
        "local_detector": "P0 OS-CFAR rank-24/32 strict decision",
        "wideband_detector": "32-bin regional recovery plus flanked fourth-region-order broad recovery",
        "fusion": "wideband recovery suppresses overlapping OS fragments",
        "fixed_coefficient_bits": FIXED_COEFFICIENT_BITS,
        "maximum_candidates": MAX_CANDIDATES,
        "requires_dma_overlap": True,
        "physical_acceptance": False,
    }
