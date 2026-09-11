"""Reference bridge from runtime FPGA FFT cells to the canonical ARM grid."""

from __future__ import annotations

from collections.abc import Sequence

CANONICAL_BINS = 4096
SUPPORTED_BINS = (4096, 8192, 16384)
POWER_MAX = (1 << 58) - 1


def collapse_runtime_cells(
    shifted_power_uq28_30: Sequence[int], shifted_decisions: Sequence[int]
) -> tuple[list[int], list[int]]:
    """Sum adjacent power cells and OR decision flags onto 4096 shifted bins."""

    count = len(shifted_power_uq28_30)
    if count not in SUPPORTED_BINS or len(shifted_decisions) != count:
        raise ValueError("Çalışma zamanı FFT dizileri 4096, 8192 veya 16384 hücre olmalıdır.")
    factor = count // CANONICAL_BINS
    power: list[int] = []
    decisions: list[int] = []
    for start in range(0, count, factor):
        cell_power = shifted_power_uq28_30[start : start + factor]
        cell_decisions = shifted_decisions[start : start + factor]
        if any(type(value) is not int or not 0 <= value <= POWER_MAX for value in cell_power):
            raise ValueError("FPGA güç hücresi 58 bit işaretsiz aralığın dışında.")
        if any(type(value) is not int or not 0 <= value <= 3 for value in cell_decisions):
            raise ValueError("FPGA karar hücresi iki bitlik biçimin dışında.")
        power.append(min(sum(cell_power), POWER_MAX))
        value = 0
        for decision in cell_decisions:
            value |= decision
        decisions.append(value)
    return power, decisions
