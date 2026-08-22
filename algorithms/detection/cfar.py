"""Adaptive detector implementations operating on shifted linear FFT power."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]
DetectorMethod = Literal["regional", "ca_cfar", "os_cfar", "os_regional_cap"]

ALLOWED_PFA_VALUES = (1e-3, 1e-4, 1e-5)
OS_EXPECTED_RATIO = 1.3406380525793773


class DetectionError(ValueError):
    """Raised when the PHASE-03 detector contract is violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DetectorCost:
    """Deterministic streaming-reference cost used only as a final tie-break."""

    selection_inputs_per_frame: int
    stream_state_slots: int
    maximum_selection_width: int
    basic_arithmetic_ops: int

    @property
    def key(self) -> tuple[int, int, int, int]:
        return (
            self.selection_inputs_per_frame,
            self.stream_state_slots,
            self.maximum_selection_width,
            self.basic_arithmetic_ops,
        )


COST_MODELS: dict[DetectorMethod, DetectorCost] = {
    "ca_cfar": DetectorCost(0, 41, 0, 24_363),
    "regional": DetectorCost(4_096, 256, 256, 32),
    "os_cfar": DetectorCost(129_792, 41, 32, 8_112),
    "os_regional_cap": DetectorCost(133_888, 297, 256, 8_144),
}


def regional_threshold_multiplier(pfa: float) -> float:
    """Return the exponential-noise multiplier for a known mean."""
    _validate_pfa(pfa)
    return -math.log(float(pfa))


def ca_threshold_multiplier(pfa: float, training_count: int = 32) -> float:
    """Return the classic square-law CA-CFAR threshold multiplier."""
    _validate_pfa(pfa)
    if training_count <= 0:
        raise DetectionError("invalid_training_count", "training_count must be positive")
    return training_count * (float(pfa) ** (-1.0 / training_count) - 1.0)


def os_threshold_multiplier(
    pfa: float,
    training_count: int = 32,
    rank: int = 24,
) -> float:
    """Solve the exponential OS-CFAR Pfa equation by deterministic bisection."""
    _validate_pfa(pfa)
    if training_count <= 0 or not 1 <= rank <= training_count:
        raise DetectionError("invalid_order_statistic", "rank must be within the training set")

    def probability(alpha: float) -> float:
        value = 1.0
        for index in range(rank):
            value *= (training_count - index) / (training_count - index + alpha)
        return value

    low = 0.0
    high = 1.0
    while probability(high) > pfa:
        high *= 2.0
    for _ in range(160):
        midpoint = (low + high) / 2.0
        if probability(midpoint) > pfa:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def _validate_pfa(pfa: float) -> None:
    if not math.isfinite(float(pfa)) or not 0.0 < float(pfa) < 1.0:
        raise DetectionError("invalid_pfa", "Pfa must be finite and in the interval (0, 1)")


def _readonly(array: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class DetectorConfig:
    """Immutable PHASE-03 detector configuration."""

    method: DetectorMethod
    pfa: float = 1e-4
    frame_length: int = 4096
    training_cells_per_side: int = 16
    guard_cells_per_side: int = 4
    os_rank: int = 24
    region_size: int = 256
    evaluate_center: bool = True

    def __post_init__(self) -> None:
        if self.method not in COST_MODELS:
            raise DetectionError("unsupported_detector", f"unsupported detector: {self.method}")
        if self.pfa not in ALLOWED_PFA_VALUES:
            raise DetectionError("pfa_outside_validated_envelope", "Pfa is outside the validated profile envelope")
        if self.frame_length != 4096:
            raise DetectionError("unsupported_frame_length", "PHASE-03 requires 4096 power cells")
        if self.training_cells_per_side != 16 or self.guard_cells_per_side != 4:
            raise DetectionError("unsupported_cfar_window", "PHASE-03 uses fixed T=16 and G=4")
        if self.os_rank != 24:
            raise DetectionError("unsupported_os_rank", "PHASE-03 uses the 24th order statistic")
        if self.region_size != 256 or self.frame_length % self.region_size:
            raise DetectionError("unsupported_region_size", "PHASE-03 uses sixteen 256-cell regions")
        if not isinstance(self.evaluate_center, bool):
            raise DetectionError("invalid_center_policy", "evaluate_center must be boolean")

    @property
    def edge_cells(self) -> int:
        return self.training_cells_per_side + self.guard_cells_per_side

    @property
    def evaluated_count(self) -> int:
        return 4056 if self.evaluate_center else 4055


@dataclass(frozen=True)
class CellDetectionResult:
    """One detector decision vector with explicit evaluation coverage."""

    method: DetectorMethod
    pfa: float
    evaluated_mask: BoolArray
    detected_mask: BoolArray
    noise_power: FloatArray
    threshold_power: FloatArray
    evaluated_count: int


class LinearPowerDetector:
    """Evaluate one shifted linear-power frame with a selected reference method."""

    def __init__(self, config: DetectorConfig) -> None:
        self.config = config

    def detect(self, shifted_power: npt.ArrayLike) -> CellDetectionResult:
        power = np.asarray(shifted_power, dtype=np.float64)
        if power.ndim != 1 or power.size != self.config.frame_length:
            raise DetectionError("power_size_mismatch", "power must contain exactly 4096 cells")
        if not np.all(np.isfinite(power)):
            raise DetectionError("nonfinite_power", "power contains a non-finite value")
        if np.any(power < 0.0):
            raise DetectionError("negative_power", "power must be non-negative")

        evaluated = np.zeros(power.size, dtype=np.bool_)
        edge = self.config.edge_cells
        evaluated[edge : power.size - edge] = True
        if not self.config.evaluate_center:
            evaluated[power.size // 2] = False

        if self.config.method == "regional":
            noise, threshold = self._regional(power)
        elif self.config.method == "ca_cfar":
            noise, threshold = self._ca(power)
        elif self.config.method == "os_cfar":
            noise, threshold = self._os(power)
        else:
            regional_noise, regional_threshold = self._regional(power)
            os_noise, os_threshold = self._os(power)
            choose_regional = regional_threshold < os_threshold
            noise = np.where(choose_regional, regional_noise, os_noise)
            threshold = np.minimum(regional_threshold, os_threshold)

        detected = evaluated & (power > threshold)
        noise = np.where(evaluated, noise, 0.0).astype(np.float64, copy=False)
        threshold = np.where(evaluated, threshold, 0.0).astype(np.float64, copy=False)
        if int(np.count_nonzero(evaluated)) != self.config.evaluated_count:
            raise DetectionError("evaluation_mask_mismatch", "evaluated CUT count violates the contract")
        return CellDetectionResult(
            method=self.config.method,
            pfa=self.config.pfa,
            evaluated_mask=_readonly(evaluated),
            detected_mask=_readonly(detected),
            noise_power=_readonly(noise),
            threshold_power=_readonly(threshold),
            evaluated_count=self.config.evaluated_count,
        )

    def _regional(self, power: FloatArray) -> tuple[FloatArray, FloatArray]:
        shaped = power.reshape(-1, self.config.region_size)
        medians = np.median(shaped, axis=1)
        region_noise = medians / math.log(2.0)
        noise = np.repeat(region_noise, self.config.region_size).astype(np.float64, copy=False)
        threshold = noise * regional_threshold_multiplier(self.config.pfa)
        return noise, threshold

    def _reference_windows(self, power: FloatArray) -> tuple[FloatArray, FloatArray]:
        total_window = 2 * (self.config.training_cells_per_side + self.config.guard_cells_per_side) + 1
        windows = np.lib.stride_tricks.sliding_window_view(power, total_window)
        training = self.config.training_cells_per_side
        references = np.concatenate((windows[:, :training], windows[:, -training:]), axis=1)
        return windows[:, total_window // 2], references

    def _ca(self, power: FloatArray) -> tuple[FloatArray, FloatArray]:
        _, references = self._reference_windows(power)
        local = references.mean(axis=1)
        noise = np.zeros(power.size, dtype=np.float64)
        edge = self.config.edge_cells
        noise[edge : power.size - edge] = local
        threshold = noise * ca_threshold_multiplier(self.config.pfa, references.shape[1])
        return noise, threshold

    def _os(self, power: FloatArray) -> tuple[FloatArray, FloatArray]:
        _, references = self._reference_windows(power)
        statistic = np.partition(references, self.config.os_rank - 1, axis=1)[:, self.config.os_rank - 1]
        edge = self.config.edge_cells
        noise = np.zeros(power.size, dtype=np.float64)
        threshold = np.zeros(power.size, dtype=np.float64)
        noise[edge : power.size - edge] = statistic / OS_EXPECTED_RATIO
        threshold[edge : power.size - edge] = statistic * os_threshold_multiplier(
            self.config.pfa,
            references.shape[1],
            self.config.os_rank,
        )
        return noise, threshold
