"""Bit-true PHASE-06H detector-cell grouping reference model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .regional_detector import DetectorCell, FRAME_LENGTH, POWER_MAX


MAX_GAP_BINS = 1
MAX_INDEX_DELTA = MAX_GAP_BINS + 1
HALF_MAX_CANDIDATES = 676
MAX_CANDIDATES = 2 * HALF_MAX_CANDIDATES
PEAK_POWER_WIDTH = 58
NOISE_WIDTH = 58
THRESHOLD_WIDTH = 62
INDEX_WIDTH = 12


@dataclass(frozen=True)
class CandidateRecord:
    """One coarse shifted-bin candidate; this is not a precise bandwidth."""

    start_shifted_bin: int
    end_shifted_bin: int
    peak_shifted_bin: int
    peak_power: int
    regional_noise: int
    threshold: int
    pfa_select: int
    evaluate_center: bool

    @property
    def coarse_span_bins(self) -> int:
        return self.end_shifted_bin - self.start_shifted_bin + 1

    @property
    def peak_natural_bin(self) -> int:
        return self.peak_shifted_bin ^ 0x800


@dataclass(frozen=True)
class AxisCandidateRecord:
    """AXI packet record, including the explicit empty-frame sentinel."""

    candidate_valid: bool
    candidate: CandidateRecord | None
    tlast: bool


def _validate_cells(cells: Iterable[DetectorCell]) -> tuple[DetectorCell, ...]:
    frame = tuple(cells)
    if len(frame) != FRAME_LENGTH:
        raise ValueError("PHASE-06H tam 4096 PHASE-06G hücresi gerektirir.")
    first = frame[0]
    if first.pfa_select not in (0, 1, 2):
        raise ValueError("Pfa selector geçersizdir.")
    for natural_index, cell in enumerate(frame):
        if cell.natural_index != natural_index or cell.shifted_index != (natural_index ^ 0x800):
            raise ValueError("PHASE-06G hücre sırası veya index eşlemesi geçersizdir.")
        if cell.pfa_select != first.pfa_select or cell.evaluate_center != first.evaluate_center:
            raise ValueError("Frame metadata'sı frame boyunca sabit olmalıdır.")
        if cell.detected and not cell.evaluated:
            raise ValueError("Değerlendirilmemiş hücre detected olamaz.")
        if not 0 <= cell.input_power <= POWER_MAX:
            raise ValueError("Peak power 58 bit erişilebilir aralığı aşamaz.")
        if not 0 <= cell.noise_power < (1 << NOISE_WIDTH):
            raise ValueError("Regional noise 58 bit unsigned olmalıdır.")
        if not 0 <= cell.threshold_power < (1 << THRESHOLD_WIDTH):
            raise ValueError("Threshold 62 bit unsigned olmalıdır.")
    return frame


def _group_ordered(cells: list[DetectorCell]) -> tuple[CandidateRecord, ...]:
    detected = [cell for cell in cells if cell.detected]
    if not detected:
        return ()
    groups: list[list[DetectorCell]] = [[detected[0]]]
    for cell in detected[1:]:
        if cell.shifted_index - groups[-1][-1].shifted_index <= MAX_INDEX_DELTA:
            groups[-1].append(cell)
        else:
            groups.append([cell])

    records: list[CandidateRecord] = []
    for group in groups:
        peak = group[0]
        for cell in group[1:]:
            if cell.input_power > peak.input_power:
                peak = cell
        records.append(
            CandidateRecord(
                start_shifted_bin=group[0].shifted_index,
                end_shifted_bin=group[-1].shifted_index,
                peak_shifted_bin=peak.shifted_index,
                peak_power=peak.input_power,
                regional_noise=peak.noise_power,
                threshold=peak.threshold_power,
                pfa_select=peak.pfa_select,
                evaluate_center=peak.evaluate_center,
            )
        )
    return tuple(records)


def group_detector_cells(cells: Iterable[DetectorCell]) -> tuple[CandidateRecord, ...]:
    """Group a natural-order PHASE-06G stream and return shifted-order candidates."""
    frame = _validate_cells(cells)
    high_half = [cell for cell in frame if cell.shifted_index >= FRAME_LENGTH // 2]
    low_half = [cell for cell in frame if cell.shifted_index < FRAME_LENGTH // 2]
    high = _group_ordered(high_half)
    low = _group_ordered(low_half)
    if len(low) > HALF_MAX_CANDIDATES or len(high) > HALF_MAX_CANDIDATES:
        raise ArithmeticError("Aday sayısı kanıtlanmış half-frame sınırını aştı.")
    if low and high and high[0].start_shifted_bin - low[-1].end_shifted_bin <= MAX_INDEX_DELTA:
        low_peak = low[-1]
        high_peak = high[0]
        peak = high_peak if high_peak.peak_power > low_peak.peak_power else low_peak
        merged = CandidateRecord(
            start_shifted_bin=low_peak.start_shifted_bin,
            end_shifted_bin=high_peak.end_shifted_bin,
            peak_shifted_bin=peak.peak_shifted_bin,
            peak_power=peak.peak_power,
            regional_noise=peak.regional_noise,
            threshold=peak.threshold,
            pfa_select=peak.pfa_select,
            evaluate_center=peak.evaluate_center,
        )
        return low[:-1] + (merged,) + high[1:]
    return low + high


def axis_candidate_records(candidates: Iterable[CandidateRecord]) -> tuple[AxisCandidateRecord, ...]:
    """Packetize semantic candidates and preserve an explicit empty frame."""
    records = tuple(candidates)
    if len(records) > MAX_CANDIDATES:
        raise ValueError("Frame aday kapasitesini aştı.")
    if not records:
        return (AxisCandidateRecord(False, None, True),)
    return tuple(
        AxisCandidateRecord(True, candidate, index == len(records) - 1)
        for index, candidate in enumerate(records)
    )


def architecture_study() -> dict[str, object]:
    return {
        "selected": "natural-order single-pass grouping with two bounded half-frame candidate RAMs",
        "authoritative_order": "shifted ascending; low-half candidates precede high-half candidates",
        "input_order": "PHASE-06G natural ascending; shifted order is high half then low half",
        "new_cell_frame_ram": False,
        "candidate_ram_depth_per_half": HALF_MAX_CANDIDATES,
        "maximum_candidates_per_frame": MAX_CANDIDATES,
        "maximum_derivation": "ceil(2028 evaluated bins / 3) per half for max_gap_bins=1",
        "semantic_empty_frame": "zero candidates",
        "axis_empty_frame": "one candidate_valid=0 TLAST=1 sentinel",
        "continuous_input_while_outputting": False,
        "upstream_continuous_frame_support": False,
    }
