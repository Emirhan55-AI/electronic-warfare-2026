"""Bit-true integer model for the P0 PL OS-CFAR cell decision."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


FRAME_LENGTH = 4096
POWER_WIDTH = 58
REFERENCE_PER_SIDE = 16
GUARD_PER_SIDE = 4
ORDER_STATISTIC_RANK = 24
RADIUS = REFERENCE_PER_SIDE + GUARD_PER_SIDE
COEFFICIENT_FRACTION_BITS = 32
ALPHA_Q32 = 36_851_433_755
WEAK_ALPHA_Q32 = 17_098_572_778
OUTPUT_MARKER = 0xC


def natural_to_shifted(index: int) -> int:
    if not 0 <= index < FRAME_LENGTH:
        raise ValueError("Natural FFT index 0..4095 aralığında olmalıdır.")
    return index ^ 0x800


def shifted_to_natural(index: int) -> int:
    if not 0 <= index < FRAME_LENGTH:
        raise ValueError("Shifted FFT index 0..4095 aralığında olmalıdır.")
    return index ^ 0x800


def _frame(values: Iterable[int]) -> tuple[int, ...]:
    result = tuple(values)
    if len(result) != FRAME_LENGTH:
        raise ValueError("OS-CFAR frame'i tam 4096 güç hücresi içermelidir.")
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value < (1 << POWER_WIDTH)
        for value in result
    ):
        raise ValueError("Güç hücreleri unsigned 58-bit olmalıdır.")
    return result


def _coefficient(value: int, width: int) -> int:
    if type(value) is not int or not (1 << 32) <= value < (1 << width):
        raise ValueError("CFAR katsayısı desteklenen Q32 aralığında olmalıdır.")
    return value


def fixed_decision(cut_power: int, order_statistic: int, alpha_q32: int = ALPHA_Q32) -> bool:
    if not 0 <= cut_power < (1 << POWER_WIDTH):
        raise ValueError("CUT unsigned 58-bit olmalıdır.")
    if not 0 <= order_statistic < (1 << POWER_WIDTH):
        raise ValueError("Sıra istatistiği unsigned 58-bit olmalıdır.")
    return (cut_power << COEFFICIENT_FRACTION_BITS) > order_statistic * _coefficient(alpha_q32, 36)


def fixed_weak_nomination(cut_power: int, order_statistic: int, alpha_q32: int = WEAK_ALPHA_Q32) -> bool:
    """Return the exact PL weak-cell decision used only by 24/32 persistence."""
    if not 0 <= cut_power < (1 << POWER_WIDTH):
        raise ValueError("CUT unsigned 58-bit olmalıdır.")
    if not 0 <= order_statistic < (1 << POWER_WIDTH):
        raise ValueError("Sıra istatistiği unsigned 58-bit olmalıdır.")
    return (cut_power << COEFFICIENT_FRACTION_BITS) > order_statistic * _coefficient(alpha_q32, 34)


@dataclass(frozen=True)
class P0OSCFARFrame:
    natural_power: tuple[int, ...]
    evaluated_shifted: tuple[bool, ...]
    detected_shifted: tuple[bool, ...]
    weak_shifted: tuple[bool, ...]
    order_statistic_shifted: tuple[int, ...]
    dma_words_natural: tuple[int, ...]


def detect_frame(natural_power: Iterable[int], *, alpha_q32: int = ALPHA_Q32,
                 weak_alpha_q32: int = WEAK_ALPHA_Q32) -> P0OSCFARFrame:
    _coefficient(alpha_q32, 36)
    _coefficient(weak_alpha_q32, 34)
    if weak_alpha_q32 > alpha_q32:
        raise ValueError("Zayıf eşik normal eşikten büyük olamaz.")
    natural = _frame(natural_power)
    shifted = tuple(natural[shifted_to_natural(index)] for index in range(FRAME_LENGTH))
    evaluated = [False] * FRAME_LENGTH
    detected = [False] * FRAME_LENGTH
    weak = [False] * FRAME_LENGTH
    order_statistics = [0] * FRAME_LENGTH

    for cut in range(RADIUS, FRAME_LENGTH - RADIUS):
        references = (
            shifted[cut - RADIUS : cut - GUARD_PER_SIDE]
            + shifted[cut + GUARD_PER_SIDE + 1 : cut + RADIUS + 1]
        )
        order_statistic = sorted(references)[ORDER_STATISTIC_RANK - 1]
        evaluated[cut] = True
        order_statistics[cut] = order_statistic
        detected[cut] = fixed_decision(shifted[cut], order_statistic, alpha_q32)
        weak[cut] = fixed_weak_nomination(shifted[cut], order_statistic, weak_alpha_q32)

    words = []
    for natural_index, power in enumerate(natural):
        shifted_index = natural_to_shifted(natural_index)
        word = power
        word |= int(evaluated[shifted_index]) << 58
        word |= int(detected[shifted_index]) << 59
        word |= OUTPUT_MARKER << 60
        word |= int(weak[shifted_index]) << 60
        words.append(word)
    return P0OSCFARFrame(
        natural_power=natural,
        evaluated_shifted=tuple(evaluated),
        detected_shifted=tuple(detected),
        weak_shifted=tuple(weak),
        order_statistic_shifted=tuple(order_statistics),
        dma_words_natural=tuple(words),
    )


def architecture_study() -> dict[str, object]:
    return {
        "selected": "sliding dual sorted 16-cell windows with fixed union rank selection",
        "alternatives": [
            {
                "name": "32-input full sorting network",
                "selected": False,
                "reason": "unnecessary comparator and routing pressure",
            },
            {
                "name": "per-CUT 58-pass radix selection",
                "selected": False,
                "reason": "exceeds the 50 MHz frame-cycle budget",
            },
            {
                "name": "quantized histogram",
                "selected": False,
                "reason": "does not preserve the exact rank-24 contract",
            },
        ],
        "stored_power_bins": FRAME_LENGTH,
        "stored_metadata_bits_per_bin": 3,
        "ping_pong": False,
        "runtime_profile": "fixed P0_OS_CFAR_EXPONENTIAL_PFA_1E4",
    }
