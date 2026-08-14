"""Bit-true fixed-point periodic-Hann reference for PHASE-06B."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

from reference.spectrum import periodic_hann

from .frame_stats import FRAME_LENGTH, unpack_ci8_word


COEFFICIENT_FRACTION_BITS = 15
COEFFICIENT_SCALE = 1 << COEFFICIENT_FRACTION_BITS
COEFFICIENT_WIDTH = 16
OUTPUT_FRACTION_BITS = 15
OUTPUT_COMPONENT_WIDTH = 16
OUTPUT_WORD_WIDTH = 32
PRODUCT_WIDTH = 25
OUTPUT_SHIFT = COEFFICIENT_FRACTION_BITS - (OUTPUT_FRACTION_BITS - 7)
ROUNDING_OFFSET = 1 << (OUTPUT_SHIFT - 1)


def quantized_hann_coefficients(fractional_bits: int = COEFFICIENT_FRACTION_BITS) -> tuple[int, ...]:
    """Quantize the canonical PHASE-02 periodic Hann with round-half-up."""
    if fractional_bits < 8:
        raise ValueError("Hann katsayısı en az sekiz kesir biti kullanmalıdır.")
    scale = 1 << fractional_bits
    values = np.floor(periodic_hann(FRAME_LENGTH) * scale + 0.5).astype(np.int64)
    result = tuple(int(value) for value in values)
    if result[0] != 0 or result[FRAME_LENGTH // 2] != scale:
        raise AssertionError("Hann uç/merkez katsayıları sözleşmeyle uyuşmuyor.")
    if result[1:] != result[:0:-1]:
        raise AssertionError("Periyodik Hann simetrisi bozuldu.")
    return result


def unique_hann_coefficients() -> tuple[int, ...]:
    """Return the frozen 0..2048 half-ROM including both endpoints."""
    return quantized_hann_coefficients()[: FRAME_LENGTH // 2 + 1]


def coefficient_for_index(index: int, coefficients: Sequence[int] | None = None) -> int:
    if not 0 <= index < FRAME_LENGTH:
        raise ValueError("Hann örnek indisi 0..4095 aralığında olmalıdır.")
    values = coefficients if coefficients is not None else quantized_hann_coefficients()
    if len(values) == FRAME_LENGTH:
        return int(values[index])
    if len(values) != FRAME_LENGTH // 2 + 1:
        raise ValueError("Katsayı dizisi 4096 tam veya 2049 simetrik değer içermelidir.")
    symmetric_index = index if index <= FRAME_LENGTH // 2 else FRAME_LENGTH - index
    return int(values[symmetric_index])


def round_shift_away_from_zero(value: int, shift: int = OUTPUT_SHIFT) -> int:
    """Round a signed integer magnitude to nearest, resolving ties away from zero."""
    if shift <= 0:
        raise ValueError("Sağa kaydırma pozitif olmalıdır.")
    magnitude = abs(int(value))
    rounded = (magnitude + (1 << (shift - 1))) >> shift
    return -rounded if value < 0 else rounded


def window_component(component: int, coefficient: int) -> int:
    """Integer-only SQ1.7 × UQ1.15 -> SQ1.15 hardware result path."""
    if not -128 <= int(component) <= 127:
        raise ValueError("Giriş bileşeni signed ci8 aralığında olmalıdır.")
    if not 0 <= int(coefficient) <= COEFFICIENT_SCALE:
        raise ValueError("Hann katsayısı UQ1.15 aralığını aşıyor.")
    product = int(component) * int(coefficient)
    result = round_shift_away_from_zero(product)
    if not -(1 << 15) <= result < (1 << 15):
        raise ArithmeticError("Hann çıkışı SQ1.15 aralığını aştı.")
    return result


def pack_windowed_word(i_value: int, q_value: int) -> int:
    if not -(1 << 15) <= i_value < (1 << 15) or not -(1 << 15) <= q_value < (1 << 15):
        raise ValueError("Pencerelenmiş bileşen signed 16 bit olmalıdır.")
    return (i_value & 0xFFFF) | ((q_value & 0xFFFF) << 16)


def unpack_windowed_word(word: int) -> tuple[int, int]:
    if not 0 <= int(word) <= 0xFFFFFFFF:
        raise ValueError("Pencerelenmiş AXI sözcüğü 32 bit olmalıdır.")
    i_value = word & 0xFFFF
    q_value = (word >> 16) & 0xFFFF
    return (
        i_value - 0x10000 if i_value & 0x8000 else i_value,
        q_value - 0x10000 if q_value & 0x8000 else q_value,
    )


def window_word(word: int, index: int, coefficients: Sequence[int] | None = None) -> int:
    i_value, q_value = unpack_ci8_word(word)
    coefficient = coefficient_for_index(index, coefficients)
    return pack_windowed_word(
        window_component(i_value, coefficient),
        window_component(q_value, coefficient),
    )


def window_frame(words: Iterable[int], coefficients: Sequence[int] | None = None) -> tuple[int, ...]:
    values = tuple(words)
    if len(values) != FRAME_LENGTH:
        raise ValueError("PHASE-06B frame'i tam 4096 örnek içermelidir.")
    frozen = coefficients if coefficients is not None else quantized_hann_coefficients()
    return tuple(window_word(word, index, frozen) for index, word in enumerate(values))


def characterize_candidate(fractional_bits: int) -> dict[str, int | float]:
    """Compare one coefficient width against the PHASE-02 floating model."""
    if fractional_bits < 9:
        raise ValueError("Aday kesir genişliği en az dokuz olmalıdır.")
    window = periodic_hann(FRAME_LENGTH)
    scale = 1 << fractional_bits
    coefficients = np.floor(window * scale + 0.5).astype(np.int64)
    shift = fractional_bits - 8
    inputs = np.arange(-128, 128, dtype=np.int64)[:, None]
    products = inputs * coefficients[None, :]
    magnitudes = np.abs(products)
    outputs = (magnitudes + (1 << (shift - 1))) >> shift
    outputs = np.where(products < 0, -outputs, outputs)
    floating = (inputs / 128.0) * window[None, :]
    quantized = outputs / float(1 << OUTPUT_FRACTION_BITS)
    errors = quantized - floating
    signal_rms = float(np.sqrt(np.mean(floating * floating)))
    error_rms = float(np.sqrt(np.mean(errors * errors)))
    coefficient_errors = coefficients / float(scale) - window
    return {
        "fractional_bits": fractional_bits,
        "coefficient_bits": fractional_bits + 1,
        "unique_quantized_values": int(np.unique(coefficients).size),
        "zero_coefficient_count": int(np.count_nonzero(coefficients == 0)),
        "maximum_coefficient": int(np.max(coefficients)),
        "maximum_coefficient_error": float(np.max(np.abs(coefficient_errors))),
        "rms_coefficient_error": float(np.sqrt(np.mean(coefficient_errors * coefficient_errors))),
        "maximum_output_error_fs": float(np.max(np.abs(errors))),
        "rms_output_error_fs": error_rms,
        "enumerated_rms_signal_to_error_ratio_db": float(20.0 * math.log10(signal_rms / error_rms)),
    }


def build_word_length_study() -> dict[str, object]:
    coefficients = quantized_hann_coefficients()
    window = periodic_hann(FRAME_LENGTH)
    return {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "algorithm_reference": "PHASE-02 periodic_hann float64",
        "candidate_formats": [characterize_candidate(bits) for bits in (10, 12, 14, 15, 16)],
        "selected_format": "UQ1.15 coefficient, SQ1.15 output",
        "metric_definitions": {
            "enumerated_rms_signal_to_error_ratio_db": (
                "20*log10(rms(PHASE-02 float64 outputs)/rms(SQ1.15 error)) over all "
                "256 signed ci8 component values and all 4096 Hann indices; this is not a measured SNR, "
                "SINAD, SQNR or ENOB claim"
            ),
            "output_error_fs": "SQ1.15 result minus PHASE-02 float64 result, normalized to full scale",
        },
        "selection_reason": (
            "16 bit katsayı ROM'u ve 16 bit FFT-facing bileşenle 3.04e-5 FS altında maksimum hata; "
            "17 bit UQ1.16 yalnız sınırlı ek doğruluk sağlar."
        ),
        "selected_characterization": characterize_candidate(COEFFICIENT_FRACTION_BITS),
        "periodic_hann": {
            "equation": "0.5-0.5*cos(2*pi*n/4096)",
            "full_coefficient_count": FRAME_LENGTH,
            "symmetric_rom_count": FRAME_LENGTH // 2 + 1,
            "floating_first": float(window[0]),
            "floating_second": float(window[1]),
            "floating_center": float(window[FRAME_LENGTH // 2]),
            "floating_last": float(window[-1]),
            "quantized_first": coefficients[0],
            "quantized_second": coefficients[1],
            "quantized_center": coefficients[FRAME_LENGTH // 2],
            "quantized_last": coefficients[-1],
            "floating_coherent_gain": float(np.mean(window)),
            "quantized_coherent_gain": float(np.mean(coefficients) / COEFFICIENT_SCALE),
            "floating_mean_square": float(np.mean(window * window)),
            "quantized_mean_square": float(np.mean((np.asarray(coefficients) / COEFFICIENT_SCALE) ** 2)),
        },
    }
