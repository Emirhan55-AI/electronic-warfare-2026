"""Variable-length bit-true model for the ST-06 runtime OS-CFAR RTL."""

from __future__ import annotations

from typing import Iterable

from .p0_os_cfar import (
    ALPHA_Q32,
    OUTPUT_MARKER,
    POWER_WIDTH,
    RADIUS,
    GUARD_PER_SIDE,
    ORDER_STATISTIC_RANK,
    WEAK_ALPHA_Q32,
    _coefficient,
    fixed_decision,
    fixed_weak_nomination,
)
from .runtime_hann import validate_fft_size


def detect_words(natural_power: Iterable[int], *, alpha_q32: int = ALPHA_Q32,
                 weak_alpha_q32: int = WEAK_ALPHA_Q32) -> tuple[int, ...]:
    _coefficient(alpha_q32, 36)
    _coefficient(weak_alpha_q32, 34)
    if weak_alpha_q32 > alpha_q32:
        raise ValueError("Zayıf eşik normal eşikten büyük olamaz.")
    natural = tuple(natural_power)
    size = validate_fft_size(len(natural))
    if any(type(value) is not int or not 0 <= value < (1 << POWER_WIDTH) for value in natural):
        raise ValueError("Güç hücreleri unsigned 58-bit olmalıdır.")
    half = size // 2
    shifted = tuple(natural[index ^ half] for index in range(size))
    evaluated = [False] * size
    detected = [False] * size
    weak = [False] * size
    for cut in range(RADIUS, size - RADIUS):
        references = (
            shifted[cut - RADIUS : cut - GUARD_PER_SIDE]
            + shifted[cut + GUARD_PER_SIDE + 1 : cut + RADIUS + 1]
        )
        order_statistic = sorted(references)[ORDER_STATISTIC_RANK - 1]
        evaluated[cut] = True
        detected[cut] = fixed_decision(shifted[cut], order_statistic, alpha_q32)
        weak[cut] = fixed_weak_nomination(shifted[cut], order_statistic, weak_alpha_q32)
    words = []
    for natural_index, power in enumerate(natural):
        shifted_index = natural_index ^ half
        word = power
        word |= int(evaluated[shifted_index]) << 58
        word |= int(detected[shifted_index]) << 59
        word |= OUTPUT_MARKER << 60
        word |= int(weak[shifted_index]) << 60
        words.append(word)
    return tuple(words)
