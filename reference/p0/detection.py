"""Ordered-statistic CFAR method and canonical P0 engineering profile."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .models import CandidateRegion


def os_cfar_false_alarm_probability(
    coefficient: float,
    reference_count: int,
    order_statistic_rank: int,
) -> float:
    """Return exponential-noise OS-CFAR Pfa for an ascending order statistic.

    The model assumes independent, identically distributed square-law power
    samples. The coefficient multiplies the kth-smallest reference sample.
    """

    if not np.isfinite(coefficient) or coefficient <= 0:
        raise ValueError("coefficient must be finite and positive")
    if reference_count < 1 or not 1 <= order_statistic_rank <= reference_count:
        raise ValueError("reference count or order-statistic rank is invalid")
    probability = 1.0
    for index in range(order_statistic_rank):
        remaining = float(reference_count - index)
        probability *= remaining / (remaining + coefficient)
    return probability


def derive_os_cfar_threshold_coefficient(
    desired_pfa: float,
    reference_count: int,
    order_statistic_rank: int,
) -> float:
    """Deterministically solve the exponential OS-CFAR Pfa equation."""

    if not np.isfinite(desired_pfa) or not 0.0 < desired_pfa < 1.0:
        raise ValueError("desired_pfa must be finite and in (0, 1)")
    if reference_count < 1 or not 1 <= order_statistic_rank <= reference_count:
        raise ValueError("reference count or order-statistic rank is invalid")
    low, high = 0.0, 1.0
    while os_cfar_false_alarm_probability(high, reference_count, order_statistic_rank) > desired_pfa:
        high *= 2.0
    for _ in range(160):
        midpoint = (low + high) / 2.0
        if os_cfar_false_alarm_probability(midpoint, reference_count, order_statistic_rank) > desired_pfa:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def order_statistic_expected_ratio(reference_count: int, order_statistic_rank: int) -> float:
    """Return E[X_(k)] / mean for iid exponential power samples."""

    if reference_count < 1 or not 1 <= order_statistic_rank <= reference_count:
        raise ValueError("reference count or order-statistic rank is invalid")
    return float(sum(1.0 / (reference_count - index) for index in range(order_statistic_rank)))


@dataclass(frozen=True)
class P0DetectorProfile:
    """Named engineering profile; only the OS-CFAR method comes from KTR intent."""

    name: str
    reference_cells_per_side: int
    guard_cells_per_side: int
    order_statistic_rank: int
    desired_pfa: float
    maximum_gap_bins: int = 1
    edge_policy: str = "require_full_window"
    comparison_rule: str = "strict_greater_than"

    @property
    def reference_count(self) -> int:
        return 2 * self.reference_cells_per_side

    @property
    def threshold_coefficient(self) -> float:
        return derive_os_cfar_threshold_coefficient(
            self.desired_pfa,
            self.reference_count,
            self.order_statistic_rank,
        )


P0_DETECTOR_PROFILE = P0DetectorProfile(
    name="P0_OS_CFAR_EXPONENTIAL_PFA_1E4",
    reference_cells_per_side=16,
    guard_cells_per_side=4,
    order_statistic_rank=24,
    desired_pfa=1e-4,
)


@dataclass(frozen=True)
class OSCFARConfig:
    """Explicit P0 engineering values; none are constants from the KTR."""

    reference_cells_per_side: int = P0_DETECTOR_PROFILE.reference_cells_per_side
    guard_cells_per_side: int = P0_DETECTOR_PROFILE.guard_cells_per_side
    order_statistic_rank: int = P0_DETECTOR_PROFILE.order_statistic_rank
    threshold_coefficient: float = P0_DETECTOR_PROFILE.threshold_coefficient
    maximum_gap_bins: int = P0_DETECTOR_PROFILE.maximum_gap_bins
    edge_policy: str = P0_DETECTOR_PROFILE.edge_policy

    def __post_init__(self) -> None:
        reference_total = 2 * self.reference_cells_per_side
        if self.reference_cells_per_side < 1:
            raise ValueError("reference_cells_per_side must be positive")
        if self.guard_cells_per_side < 0:
            raise ValueError("guard_cells_per_side must be non-negative")
        if not 1 <= self.order_statistic_rank <= reference_total:
            raise ValueError("order_statistic_rank is one-based and must fit the reference window")
        if not np.isfinite(self.threshold_coefficient) or self.threshold_coefficient <= 0:
            raise ValueError("threshold_coefficient must be finite and positive")
        if self.maximum_gap_bins < 0:
            raise ValueError("maximum_gap_bins must be non-negative")
        if self.edge_policy != "require_full_window":
            raise ValueError("only deterministic require_full_window edge handling is supported")


@dataclass(frozen=True)
class OSCFARFrameResult:
    frame_id: int
    detections: npt.NDArray[np.bool_]
    noise_power: npt.NDArray[np.float64]
    threshold_power: npt.NDArray[np.float64]
    candidates: tuple[CandidateRegion, ...]
    evaluated_start_bin: int
    evaluated_end_bin: int


class OSCFARDetector:
    """Strict `CUT > coefficient × kth(reference)` OS-CFAR implementation."""

    def __init__(self, config: OSCFARConfig | None = None) -> None:
        self.config = config or OSCFARConfig()

    def process(self, power: npt.ArrayLike, *, frame_id: int) -> OSCFARFrameResult:
        values = np.asarray(power, dtype=np.float64)
        if values.ndim != 1 or values.size < 3:
            raise ValueError("power must be a one-dimensional frame")
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError("power must contain finite non-negative values")
        if isinstance(frame_id, bool) or not isinstance(frame_id, int) or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")

        cfg = self.config
        radius = cfg.reference_cells_per_side + cfg.guard_cells_per_side
        detections = np.zeros(values.size, dtype=np.bool_)
        noise = np.full(values.size, np.nan, dtype=np.float64)
        threshold = np.full(values.size, np.nan, dtype=np.float64)
        if values.size <= 2 * radius:
            return OSCFARFrameResult(frame_id, detections, noise, threshold, (), radius, radius - 1)

        rank_index = cfg.order_statistic_rank - 1
        for cut in range(radius, values.size - radius):
            left = values[cut - radius : cut - cfg.guard_cells_per_side]
            right_start = cut + cfg.guard_cells_per_side + 1
            right = values[right_start : right_start + cfg.reference_cells_per_side]
            references = np.concatenate((left, right))
            local_noise = float(np.partition(references, rank_index)[rank_index])
            local_threshold = local_noise * cfg.threshold_coefficient
            noise[cut] = local_noise
            threshold[cut] = local_threshold
            detections[cut] = bool(values[cut] > local_threshold)

        candidates = self._group(values, detections, noise, threshold)
        detections.setflags(write=False)
        noise.setflags(write=False)
        threshold.setflags(write=False)
        return OSCFARFrameResult(
            frame_id,
            detections,
            noise,
            threshold,
            candidates,
            radius,
            values.size - radius - 1,
        )

    def _group(
        self,
        power: npt.NDArray[np.float64],
        detections: npt.NDArray[np.bool_],
        noise: npt.NDArray[np.float64],
        threshold: npt.NDArray[np.float64],
    ) -> tuple[CandidateRegion, ...]:
        bins = np.flatnonzero(detections)
        if not bins.size:
            return ()
        groups: list[list[int]] = [[int(bins[0])]]
        maximum_step = self.config.maximum_gap_bins + 1
        for raw_bin in bins[1:]:
            bin_index = int(raw_bin)
            if bin_index - groups[-1][-1] <= maximum_step:
                groups[-1].append(bin_index)
            else:
                groups.append([bin_index])
        candidates: list[CandidateRegion] = []
        for group in groups:
            start, end = group[0], group[-1]
            region_power = power[start : end + 1]
            peak = start + int(np.argmax(region_power))
            candidates.append(
                CandidateRegion(
                    start,
                    end,
                    peak,
                    float(power[peak]),
                    float(noise[peak]),
                    float(threshold[peak]),
                )
            )
        return tuple(candidates)
