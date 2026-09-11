"""Bit-true Hann helpers for the ST-06 runtime FFT lengths."""

from __future__ import annotations

import math
from typing import Iterable


SUPPORTED_FFT_SIZES = (4096, 8192, 16384)
COEFFICIENT_SCALE = 1 << 15
OUTPUT_SHIFT = 7


def validate_fft_size(fft_size: int) -> int:
    value = int(fft_size)
    if value not in SUPPORTED_FFT_SIZES:
        raise ValueError("FPGA FFT boyutu 4096, 8192 veya 16384 olmalıdır.")
    return value


def quantized_coefficients(fft_size: int) -> tuple[int, ...]:
    size = validate_fft_size(fft_size)
    values = tuple(
        int(math.floor((0.5 - 0.5 * math.cos(2.0 * math.pi * index / size))
                       * COEFFICIENT_SCALE + 0.5))
        for index in range(size)
    )
    if values[0] != 0 or values[size // 2] != COEFFICIENT_SCALE:
        raise AssertionError("Hann uç/merkez katsayıları geçersiz.")
    if values[1:] != values[:0:-1]:
        raise AssertionError("Periyodik Hann simetrisi geçersiz.")
    return values


def unique_coefficients(fft_size: int) -> tuple[int, ...]:
    size = validate_fft_size(fft_size)
    return quantized_coefficients(size)[: size // 2 + 1]


def coefficient_for_index(fft_size: int, index: int) -> int:
    size = validate_fft_size(fft_size)
    if not 0 <= index < size:
        raise ValueError("Hann örnek indisi kare dışında.")
    table = unique_coefficients(size)
    return table[index if index <= size // 2 else size - index]


def _round_component(component: int, coefficient: int) -> int:
    if not -128 <= component <= 127:
        raise ValueError("CI8 bileşeni aralık dışında.")
    product = component * coefficient
    magnitude = abs(product)
    rounded = (magnitude + (1 << (OUTPUT_SHIFT - 1))) >> OUTPUT_SHIFT
    return -rounded if product < 0 else rounded


def window_words(fft_size: int, ci8_words: Iterable[int]) -> tuple[int, ...]:
    size = validate_fft_size(fft_size)
    words = tuple(int(word) for word in ci8_words)
    if len(words) != size:
        raise ValueError("CI8 kare uzunluğu FFT boyutuyla eşleşmiyor.")
    coefficients = quantized_coefficients(size)
    result = []
    for word, coefficient in zip(words, coefficients, strict=True):
        i_value = word & 0xFF
        q_value = (word >> 8) & 0xFF
        i_value = i_value - 256 if i_value >= 128 else i_value
        q_value = q_value - 256 if q_value >= 128 else q_value
        i_output = _round_component(i_value, coefficient) & 0xFFFF
        q_output = _round_component(q_value, coefficient) & 0xFFFF
        result.append((q_output << 16) | i_output)
    return tuple(result)
