"""Independent bit-true PHASE-06G regional-detector reference model."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


FRAME_LENGTH = 4096
REGION_SIZE = 256
REGION_COUNT = 16
POWER_WIDTH = 58
POWER_FRACTION_BITS = 30
POWER_MAX = 1 << 57
EDGE_CELLS = 20

COEFFICIENT_FRACTION_BITS = 24
COEFFICIENT_SCALE = 1 << COEFFICIENT_FRACTION_BITS
NOISE_COEFFICIENT = 24_204_406
NOISE_COEFFICIENT_WIDTH = 26
THRESHOLD_COEFFICIENTS = (115_892_902, 154_523_870, 193_154_837)
THRESHOLD_COEFFICIENT_WIDTH = 28
COMBINED_COEFFICIENTS = (167_198_116, 222_930_821, 278_663_526)
COMBINED_COEFFICIENT_WIDTH = 29
PFA_VALUES = (1e-3, 1e-4, 1e-5)

MEDIAN_TWICE_WIDTH = 59
NOISE_WIDTH = 58
THRESHOLD_WIDTH = 62


def quantize_unsigned(value: float, fractional_bits: int = COEFFICIENT_FRACTION_BITS) -> int:
    """Round a non-negative coefficient to nearest, with exact half ties upward."""
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("Katsayı sonlu ve negatif olmayan bir değer olmalıdır.")
    return int(math.floor(value * (1 << fractional_bits) + 0.5))


def round_shift_ties_up(value: int, shift: int) -> int:
    """Unsigned round-to-nearest right shift; an exact half rounds upward."""
    if value < 0 or shift <= 0:
        raise ValueError("Unsigned yuvarlama pozitif shift gerektirir.")
    return (value + (1 << (shift - 1))) >> shift


def natural_to_shifted(natural_index: int) -> int:
    if not 0 <= natural_index < FRAME_LENGTH:
        raise ValueError("Natural FFT index 0..4095 aralığında olmalıdır.")
    return natural_index ^ 0x800


def shifted_to_natural(shifted_index: int) -> int:
    if not 0 <= shifted_index < FRAME_LENGTH:
        raise ValueError("Shifted FFT index 0..4095 aralığında olmalıdır.")
    return shifted_index ^ 0x800


def is_evaluated(shifted_index: int, evaluate_center: bool) -> bool:
    if not isinstance(evaluate_center, bool):
        raise TypeError("evaluate_center boolean olmalıdır.")
    return EDGE_CELLS <= shifted_index < FRAME_LENGTH - EDGE_CELLS and (
        evaluate_center or shifted_index != FRAME_LENGTH // 2
    )


def _validate_power_frame(natural_power: Iterable[int]) -> tuple[int, ...]:
    frame = tuple(natural_power)
    if len(frame) != FRAME_LENGTH:
        raise ValueError("Detector frame'i tam 4096 power hücresi içermelidir.")
    for value in frame:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= POWER_MAX:
            raise ValueError("Power hücresi erişilebilir unsigned UQ28.30 aralığında olmalıdır.")
    return frame


def median_twice_exact(values: Iterable[int]) -> int:
    ordered = sorted(values)
    if len(ordered) != REGION_SIZE:
        raise ValueError("Bölgesel median tam 256 değer gerektirir.")
    result = ordered[127] + ordered[128]
    if not 0 <= result < (1 << MEDIAN_TWICE_WIDTH):
        raise ArithmeticError("median_twice 59 bit sözleşmesini aştı.")
    return result


def regional_fixed_values(median_twice: int, pfa_select: int) -> tuple[int, int]:
    """Return rounded integer noise and threshold from the exact doubled median."""
    if not 0 <= median_twice < (1 << MEDIAN_TWICE_WIDTH):
        raise ValueError("median_twice unsigned 59 bit olmalıdır.")
    if pfa_select not in (0, 1, 2):
        raise ValueError("Pfa selector yalnız doğrulanmış 1e-3/1e-4/1e-5 değerlerini seçebilir.")
    shift = COEFFICIENT_FRACTION_BITS + 1
    noise = round_shift_ties_up(median_twice * NOISE_COEFFICIENT, shift)
    threshold = round_shift_ties_up(median_twice * COMBINED_COEFFICIENTS[pfa_select], shift)
    if noise >= (1 << NOISE_WIDTH) or threshold >= (1 << THRESHOLD_WIDTH):
        raise ArithmeticError("Detector ara sonucu dondurulmuş çıkış genişliğini aştı.")
    return noise, threshold


@dataclass(frozen=True)
class DetectorCell:
    natural_index: int
    shifted_index: int
    region_index: int
    input_power: int
    median_twice: int
    noise_power: int
    threshold_power: int
    evaluated: bool
    detected: bool
    pfa_select: int
    evaluate_center: bool


@dataclass(frozen=True)
class DetectorFrame:
    cells: tuple[DetectorCell, ...]
    region_medians_twice: tuple[int, ...]
    region_noise: tuple[int, ...]
    region_threshold: tuple[int, ...]


def detect_frame(
    natural_power: Iterable[int],
    *,
    pfa_select: int = 1,
    evaluate_center: bool = True,
) -> DetectorFrame:
    """Evaluate one natural-order PHASE-06F frame with exact integer arithmetic."""
    frame = _validate_power_frame(natural_power)
    if pfa_select not in (0, 1, 2):
        raise ValueError("Geçersiz Pfa selector.")
    if not isinstance(evaluate_center, bool):
        raise TypeError("evaluate_center boolean olmalıdır.")

    shifted = tuple(frame[shifted_to_natural(index)] for index in range(FRAME_LENGTH))
    medians_twice = tuple(
        median_twice_exact(shifted[offset : offset + REGION_SIZE])
        for offset in range(0, FRAME_LENGTH, REGION_SIZE)
    )
    fixed = tuple(regional_fixed_values(value, pfa_select) for value in medians_twice)
    region_noise = tuple(value[0] for value in fixed)
    region_threshold = tuple(value[1] for value in fixed)

    cells: list[DetectorCell] = []
    for natural_index, power in enumerate(frame):
        shifted_index = natural_to_shifted(natural_index)
        region_index = shifted_index // REGION_SIZE
        evaluated = is_evaluated(shifted_index, evaluate_center)
        threshold = region_threshold[region_index] if evaluated else 0
        noise = region_noise[region_index] if evaluated else 0
        cells.append(
            DetectorCell(
                natural_index=natural_index,
                shifted_index=shifted_index,
                region_index=region_index,
                input_power=power,
                median_twice=medians_twice[region_index],
                noise_power=noise,
                threshold_power=threshold,
                evaluated=evaluated,
                detected=evaluated and power > threshold,
                pfa_select=pfa_select,
                evaluate_center=evaluate_center,
            )
        )
    return DetectorFrame(
        cells=tuple(cells),
        region_medians_twice=medians_twice,
        region_noise=region_noise,
        region_threshold=region_threshold,
    )


def coefficient_study() -> dict[str, object]:
    candidates = (12, 16, 20, 24, 28, 32)
    exact_noise = 1.0 / math.log(2.0)
    rows: list[dict[str, object]] = []
    for fractional_bits in candidates:
        scale = 1 << fractional_bits
        noise_q = quantize_unsigned(exact_noise, fractional_bits)
        pfa_rows = []
        for pfa in PFA_VALUES:
            threshold_exact = -math.log(pfa)
            combined_exact = threshold_exact / math.log(2.0)
            threshold_q = quantize_unsigned(threshold_exact, fractional_bits)
            combined_q = quantize_unsigned(combined_exact, fractional_bits)
            pfa_rows.append(
                {
                    "pfa": pfa,
                    "threshold_integer": threshold_q,
                    "threshold_absolute_error": threshold_q / scale - threshold_exact,
                    "combined_integer": combined_q,
                    "combined_absolute_error": combined_q / scale - combined_exact,
                }
            )
        rows.append(
            {
                "fractional_bits": fractional_bits,
                "noise_integer": noise_q,
                "noise_absolute_error": noise_q / scale - exact_noise,
                "pfa": pfa_rows,
            }
        )
    return {
        "candidates": rows,
        "selected_fractional_bits": COEFFICIENT_FRACTION_BITS,
        "selection_policy": (
            "Smallest candidate with combined-threshold relative error below 3e-9, noise relative "
            "error below 2e-8, zero non-boundary decision mismatches on the frozen detector fixture, "
            "and bit-exact RTL equivalence."
        ),
        "rounding": "unsigned round-to-nearest, exact half upward",
        "implementation": "single combined median-to-threshold coefficient; noise computed separately",
    }


def architecture_study() -> dict[str, object]:
    return {
        "selected": "dual-rank binary radix selection over one 4096x58 frame buffer",
        "candidates": [
            {"name": "full_sorting_network", "exact": True, "selected": False, "reason": "prohibitive compare/exchange and routing pressure"},
            {"name": "sequential_in_place_sort", "exact": True, "selected": False, "reason": "larger write traffic and quadratic worst-case latency for simple implementations"},
            {"name": "histogram_binning", "exact": False, "selected": False, "reason": "cannot preserve the PHASE-03 median contract"},
            {"name": "comparison_selection_partial_sort", "exact": True, "selected": False, "reason": "variable-control or larger comparator structure than radix selection"},
            {"name": "dual_rank_binary_radix_selection", "exact": True, "selected": True, "reason": "bounded exact ranks 127 and 128 with one read-only scan datapath"},
        ],
        "buffering": "one complete frame; processing and replay occur while input TREADY is low",
        "continuous_frames": False,
        "ping_pong": False,
        "frame_gap_required": True,
        "radix_passes_per_region": POWER_WIDTH,
        "stored_bins": FRAME_LENGTH,
    }
