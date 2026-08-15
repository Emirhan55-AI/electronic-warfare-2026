"""Bit-true PHASE-06F FFT-output linear-power reference model."""

from __future__ import annotations


COMPONENT_WIDTH = 29
COMPONENT_FRACTION_BITS = 15
COMPONENT_MIN = -(1 << (COMPONENT_WIDTH - 1))
COMPONENT_MAX = (1 << (COMPONENT_WIDTH - 1)) - 1
SQUARE_WIDTH = 57
POWER_WIDTH = 58
POWER_FRACTION_BITS = 30
POWER_MAX_REACHABLE = 1 << 57


def _signed(value: int, width: int) -> int:
    mask = (1 << width) - 1
    value &= mask
    return value - (1 << width) if value & (1 << (width - 1)) else value


def _validate_component(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("FFT bileşeni integer olmalıdır.")
    if value < COMPONENT_MIN or value > COMPONENT_MAX:
        raise ValueError("FFT bileşeni signed 29 bit aralığını aşıyor.")
    return value


def unpack_fft_word(word: int, *, require_canonical_padding: bool = True) -> tuple[int, int]:
    """Extract signed 29-bit I/Q from the frozen 64-bit external FFT payload."""
    if not isinstance(word, int) or isinstance(word, bool) or word < 0 or word >= (1 << 64):
        raise ValueError("FFT sözcüğü unsigned 64 bit olmalıdır.")
    i_value = _signed(word & ((1 << COMPONENT_WIDTH) - 1), COMPONENT_WIDTH)
    q_value = _signed((word >> 32) & ((1 << COMPONENT_WIDTH) - 1), COMPONENT_WIDTH)
    if require_canonical_padding:
        i_lane = _signed(word & 0xFFFFFFFF, 32)
        q_lane = _signed((word >> 32) & 0xFFFFFFFF, 32)
        if i_lane != i_value or q_lane != q_value:
            raise ValueError("FFT lane padding'i signed 29 bit sign-extension ile uyumlu değil.")
    return i_value, q_value


def pack_fft_word(i_value: int, q_value: int) -> int:
    """Pack signed 29-bit values into canonical sign-extended 32-bit lanes."""
    i_value = _validate_component(i_value)
    q_value = _validate_component(q_value)
    return ((q_value & 0xFFFFFFFF) << 32) | (i_value & 0xFFFFFFFF)


def linear_power(i_value: int, q_value: int) -> int:
    """Return exact I_int² + Q_int² with no scaling, rounding or saturation."""
    i_value = _validate_component(i_value)
    q_value = _validate_component(q_value)
    result = i_value * i_value + q_value * q_value
    if result < 0 or result > POWER_MAX_REACHABLE:
        raise ArithmeticError("Exact power sonucu dondurulmuş 58 bit sözleşmesini aştı.")
    return result


def power_from_fft_word(word: int) -> int:
    return linear_power(*unpack_fft_word(word))


def power_real_value(power_integer: int) -> float:
    if not isinstance(power_integer, int) or power_integer < 0 or power_integer > POWER_MAX_REACHABLE:
        raise ValueError("Power integer erişilebilir UQ28.30 aralığında olmalıdır.")
    return power_integer / float(1 << POWER_FRACTION_BITS)


def width_proof() -> dict[str, object]:
    minimum_square = COMPONENT_MIN * COMPONENT_MIN
    maximum_positive_square = COMPONENT_MAX * COMPONENT_MAX
    worst_sum = minimum_square + minimum_square
    return {
        "component_integer_minimum": COMPONENT_MIN,
        "component_integer_maximum": COMPONENT_MAX,
        "minimum_negative_square": minimum_square,
        "maximum_positive_square": maximum_positive_square,
        "single_square_minimum_unsigned_width": minimum_square.bit_length(),
        "worst_case_exact_sum": worst_sum,
        "sum_minimum_unsigned_width": worst_sum.bit_length(),
        "input_format": "SQ14.15",
        "output_format": "UQ28.30",
        "rounding": "none",
        "truncation": "none",
        "saturation": "none",
        "mathematical_overflow": False,
    }
