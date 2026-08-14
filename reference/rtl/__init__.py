"""Bit-exact integer references for synthesizable PHASE-06 RTL."""

from .frame_stats import (
    ENERGY_WIDTH,
    ERROR_EARLY_TLAST,
    ERROR_MISSING_TLAST,
    ERROR_NONE,
    FRAME_LENGTH,
    INDEX_WIDTH,
    POWER_WIDTH,
    SAMPLE_COUNT_WIDTH,
    AxisFrameStatsModel,
    FrameStatsResult,
    frame_stats,
    pack_ci8_bytes,
    sample_power,
    unpack_ci8_word,
)

__all__ = [
    "ENERGY_WIDTH",
    "ERROR_EARLY_TLAST",
    "ERROR_MISSING_TLAST",
    "ERROR_NONE",
    "FRAME_LENGTH",
    "INDEX_WIDTH",
    "POWER_WIDTH",
    "SAMPLE_COUNT_WIDTH",
    "AxisFrameStatsModel",
    "FrameStatsResult",
    "frame_stats",
    "pack_ci8_bytes",
    "sample_power",
    "unpack_ci8_word",
]
