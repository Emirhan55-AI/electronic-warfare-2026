"""Integer-only golden model for AXI-stream ci8 frame statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


FRAME_LENGTH = 4096
POWER_WIDTH = 16
ENERGY_WIDTH = 28
INDEX_WIDTH = 12
SAMPLE_COUNT_WIDTH = 13
ERROR_NONE = 0
ERROR_EARLY_TLAST = 1
ERROR_MISSING_TLAST = 2


def _signed_ci8(value: int) -> int:
    value &= 0xFF
    return value - 256 if value & 0x80 else value


def unpack_ci8_word(word: int) -> tuple[int, int]:
    """Unpack tdata[7:0]=I and tdata[15:8]=Q."""
    if not 0 <= int(word) <= 0xFFFF:
        raise ValueError("AXI ci8 sözcüğü 16 bit olmalıdır.")
    return _signed_ci8(word), _signed_ci8(word >> 8)


def pack_ci8_bytes(data: bytes) -> tuple[int, ...]:
    """Convert interleaved signed [I,Q] bytes to AXI tdata words."""
    if len(data) % 2:
        raise ValueError("ci8 verisi tek byte ile bitemez.")
    return tuple(data[index] | (data[index + 1] << 8) for index in range(0, len(data), 2))


def sample_power(word: int) -> int:
    i_value, q_value = unpack_ci8_word(word)
    power = i_value * i_value + q_value * q_value
    if not 0 <= power < (1 << POWER_WIDTH):
        raise ArithmeticError("Kompleks güç bit genişliğini aştı.")
    return power


@dataclass(frozen=True)
class FrameStatsResult:
    total_energy: int
    peak_power: int
    peak_index: int
    sample_count: int
    protocol_error: bool
    error_code: int

    def __post_init__(self) -> None:
        limits = (
            (self.total_energy, ENERGY_WIDTH, "total_energy"),
            (self.peak_power, POWER_WIDTH, "peak_power"),
            (self.peak_index, INDEX_WIDTH, "peak_index"),
            (self.sample_count, SAMPLE_COUNT_WIDTH, "sample_count"),
        )
        for value, width, name in limits:
            if not 0 <= value < (1 << width):
                raise ArithmeticError(f"{name} {width} bit sınırını aştı.")
        if self.error_code not in (ERROR_NONE, ERROR_EARLY_TLAST, ERROR_MISSING_TLAST):
            raise ValueError("Bilinmeyen protokol hata kodu.")
        if self.protocol_error != (self.error_code != ERROR_NONE):
            raise ValueError("Protokol hata bayrağı ve kodu tutarsız.")

    def packed72(self) -> int:
        value = self.total_energy
        value = (value << POWER_WIDTH) | self.peak_power
        value = (value << INDEX_WIDTH) | self.peak_index
        value = (value << SAMPLE_COUNT_WIDTH) | self.sample_count
        value = (value << 1) | int(self.protocol_error)
        return (value << 2) | self.error_code

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "total_energy": self.total_energy,
            "peak_power": self.peak_power,
            "peak_index": self.peak_index,
            "sample_count": self.sample_count,
            "protocol_error": self.protocol_error,
            "error_code": self.error_code,
        }


class AxisFrameStatsModel:
    """Accepted-transfer model with deterministic late-TLAST recovery."""

    def __init__(self, frame_length: int = FRAME_LENGTH) -> None:
        if frame_length != FRAME_LENGTH:
            raise ValueError("PHASE-06A frame uzunluğu tam 4096 olmalıdır.")
        self.frame_length = frame_length
        self.late_tlast_recoveries = 0
        self.reset()

    def reset(self) -> None:
        self.sample_index = 0
        self.total_energy = 0
        self.peak_power = 0
        self.peak_index = 0
        self.dropping_late_frame = False

    def _clear_frame(self) -> None:
        self.sample_index = 0
        self.total_energy = 0
        self.peak_power = 0
        self.peak_index = 0

    def accept(self, word: int, *, tlast: bool) -> FrameStatsResult | None:
        """Apply one `tvalid && tready` transfer."""
        if self.dropping_late_frame:
            if tlast:
                self.dropping_late_frame = False
                self.late_tlast_recoveries += 1
                self._clear_frame()
            return None

        power = sample_power(word)
        next_energy = self.total_energy + power
        if next_energy >= (1 << ENERGY_WIDTH):
            raise ArithmeticError("Frame enerjisi sessizce taşamaz.")
        next_peak = self.peak_power
        next_peak_index = self.peak_index
        if power > self.peak_power:
            next_peak = power
            next_peak_index = self.sample_index
        next_count = self.sample_index + 1
        expected_last = next_count == self.frame_length

        error_code = ERROR_NONE
        if tlast and not expected_last:
            error_code = ERROR_EARLY_TLAST
        elif expected_last and not tlast:
            error_code = ERROR_MISSING_TLAST

        if expected_last or tlast:
            result = FrameStatsResult(
                next_energy,
                next_peak,
                next_peak_index,
                next_count,
                error_code != ERROR_NONE,
                error_code,
            )
            self._clear_frame()
            if error_code == ERROR_MISSING_TLAST:
                self.dropping_late_frame = True
            return result

        self.total_energy = next_energy
        self.peak_power = next_peak
        self.peak_index = next_peak_index
        self.sample_index = next_count
        return None


def frame_stats(words: Iterable[int]) -> FrameStatsResult:
    values = tuple(words)
    if len(values) != FRAME_LENGTH:
        raise ValueError("Golden frame tam 4096 örnek içermelidir.")
    model = AxisFrameStatsModel()
    result: FrameStatsResult | None = None
    for index, word in enumerate(values):
        result = model.accept(word, tlast=index == FRAME_LENGTH - 1)
    if result is None:
        raise AssertionError("Tam frame sonuç üretmedi.")
    return result
