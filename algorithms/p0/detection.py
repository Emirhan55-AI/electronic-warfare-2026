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


@dataclass(frozen=True)
class WidebandRecoveryConfig:
    """Bounded integrated-energy profile for emissions wider than the OS window."""

    region_size: int = 256
    integration_bins: int = 32
    noise_multiplier: float = 2.5
    broad_reference_region_rank: int = 4
    broad_minimum_span_bins: int = 257
    minimum_span_bins: int = 2 * (
        P0_DETECTOR_PROFILE.reference_cells_per_side
        + P0_DETECTOR_PROFILE.guard_cells_per_side
    ) + 1

    def __post_init__(self) -> None:
        if self.region_size <= 0 or 4096 % self.region_size:
            raise ValueError("region_size must divide the 4096-bin P0 frame")
        if self.integration_bins <= 1 or self.integration_bins % 2:
            raise ValueError("integration_bins must be an even integer greater than one")
        if not np.isfinite(self.noise_multiplier) or self.noise_multiplier <= 1.0:
            raise ValueError("noise_multiplier must be finite and greater than one")
        if not 1 <= self.broad_reference_region_rank <= 4096 // self.region_size:
            raise ValueError("broad_reference_region_rank must select an existing region")
        if self.broad_minimum_span_bins <= self.region_size:
            raise ValueError("broad_minimum_span_bins must exceed one complete region")
        if self.minimum_span_bins < 1:
            raise ValueError("minimum_span_bins must be positive")


P0_WIDEBAND_RECOVERY_PROFILE = WidebandRecoveryConfig()


@dataclass(frozen=True)
class MultiscaleFrameResult:
    """OS-CFAR result plus qualified integrated-energy recovery candidates."""

    frame_id: int
    os_cfar: OSCFARFrameResult
    recovery_candidates: tuple[CandidateRegion, ...]
    candidates: tuple[CandidateRegion, ...]


class MultiscaleDetector:
    """Preserve OS-CFAR and recover only support wider than its full window."""

    def __init__(
        self,
        os_config: OSCFARConfig | None = None,
        recovery_config: WidebandRecoveryConfig | None = None,
    ) -> None:
        self.os_detector = OSCFARDetector(os_config)
        self.recovery_config = recovery_config or P0_WIDEBAND_RECOVERY_PROFILE

    def process(self, power: npt.ArrayLike, *, frame_id: int) -> MultiscaleFrameResult:
        values = np.asarray(power, dtype=np.float64)
        os_result = self.os_detector.process(values, frame_id=frame_id)
        regional = self._regional_recoveries(values, os_result.evaluated_start_bin)
        broad = self._flanked_broad_recoveries(values, os_result.evaluated_start_bin)
        recoveries = tuple(sorted(
            (*[candidate for candidate in regional
               if not any(self._overlaps(candidate, item) for item in broad)], *broad),
            key=lambda candidate: (candidate.start_bin, candidate.end_bin, candidate.peak_bin),
        ))
        retained = tuple(
            candidate
            for candidate in os_result.candidates
            if not any(self._overlaps(candidate, recovery) for recovery in recoveries)
        )
        combined = tuple(sorted(
            (*retained, *recoveries),
            key=lambda candidate: (candidate.start_bin, candidate.end_bin, candidate.peak_bin),
        ))
        return MultiscaleFrameResult(frame_id, os_result, recoveries, combined)

    def recovery_candidates(self, power: npt.ArrayLike) -> tuple[CandidateRegion, ...]:
        """Return qualified integrated-energy proposals without running OS-CFAR."""

        values = np.asarray(power, dtype=np.float64)
        if values.ndim != 1 or values.size != 4096:
            raise ValueError("power must contain exactly 4096 cells")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("power must contain finite non-negative values")
        radius = (
            self.os_detector.config.reference_cells_per_side
            + self.os_detector.config.guard_cells_per_side
        )
        regional = self._regional_recoveries(values, radius)
        broad = self._flanked_broad_recoveries(values, radius)
        return tuple(sorted(
            (*[candidate for candidate in regional
               if not any(self._overlaps(candidate, item) for item in broad)], *broad),
            key=lambda candidate: (candidate.start_bin, candidate.end_bin, candidate.peak_bin),
        ))

    def _regional_recoveries(
        self,
        power: npt.NDArray[np.float64],
        edge_cells: int,
    ) -> tuple[CandidateRegion, ...]:
        cfg = self.recovery_config
        shaped = power.reshape(-1, cfg.region_size)
        region_noise = np.median(shaped, axis=1) / np.log(2.0)
        region_threshold = region_noise * cfg.noise_multiplier
        threshold = np.repeat(region_threshold, cfg.region_size)
        noise = np.repeat(region_noise, cfg.region_size)
        left_window = cfg.integration_bins // 2 - 1
        right_window = cfg.integration_bins // 2
        evaluated_start = max(edge_cells, left_window)
        evaluated_stop = power.size - max(edge_cells, right_window)
        prefix = np.concatenate(([0.0], np.cumsum(power, dtype=np.float64)))
        centers = np.arange(evaluated_start, evaluated_stop, dtype=np.int64)
        means = (
            prefix[centers + right_window + 1]
            - prefix[centers - left_window]
        ) / cfg.integration_bins
        detected = np.zeros(power.size, dtype=np.bool_)
        detected[centers] = means > threshold[centers]

        bins = np.flatnonzero(detected)
        if not bins.size:
            return ()
        groups: list[list[int]] = [[int(bins[0])]]
        maximum_step = self.os_detector.config.maximum_gap_bins + 1
        for raw_bin in bins[1:]:
            bin_index = int(raw_bin)
            if bin_index - groups[-1][-1] <= maximum_step:
                groups[-1].append(bin_index)
            else:
                groups.append([bin_index])

        candidates: list[CandidateRegion] = []
        for group in groups:
            start = group[0] + left_window
            end = group[-1] - right_window
            if end < start:
                continue
            if end - start + 1 < cfg.minimum_span_bins:
                continue
            peak = start + int(np.argmax(power[start : end + 1]))
            candidates.append(CandidateRegion(
                start,
                end,
                peak,
                float(power[peak]),
                float(noise[peak]),
                float(threshold[peak]),
            ))
        return tuple(candidates)

    def _flanked_broad_recoveries(
        self,
        power: npt.NDArray[np.float64],
        edge_cells: int,
    ) -> tuple[CandidateRegion, ...]:
        """Recover broad support only when independent regions exist on both sides."""
        cfg = self.recovery_config
        shaped = power.reshape(-1, cfg.region_size)
        region_medians = np.median(shaped, axis=1)
        reference_median = float(np.partition(
            region_medians, cfg.broad_reference_region_rank - 1
        )[cfg.broad_reference_region_rank - 1])
        frame_noise = reference_median / np.log(2.0)
        left_window = cfg.integration_bins // 2 - 1
        right_window = cfg.integration_bins // 2
        evaluated_start = max(edge_cells, left_window)
        evaluated_stop = power.size - max(edge_cells, right_window)
        prefix = np.concatenate(([0.0], np.cumsum(power, dtype=np.float64)))
        centers = np.arange(evaluated_start, evaluated_stop, dtype=np.int64)
        means = (
            prefix[centers + right_window + 1]
            - prefix[centers - left_window]
        ) / cfg.integration_bins
        detected_bins = centers[means > frame_noise * cfg.noise_multiplier]
        if not detected_bins.size:
            return ()
        groups = np.split(
            detected_bins,
            np.flatnonzero(np.diff(detected_bins) > self.os_detector.config.maximum_gap_bins + 1) + 1,
        )
        candidates: list[CandidateRegion] = []
        for group in groups:
            start = int(group[0]) + left_window
            end = int(group[-1]) - right_window
            if end - start + 1 < cfg.broad_minimum_span_bins:
                continue
            left_region = start // cfg.region_size - 1
            right_region = end // cfg.region_size + 1
            if left_region < 0 or right_region >= region_medians.size:
                continue
            inside_start = start // cfg.region_size
            inside_stop = end // cfg.region_size + 1
            if inside_start >= inside_stop:
                continue
            inside_median = float(np.max(region_medians[inside_start:inside_stop]))
            flank_median = float(max(region_medians[left_region], region_medians[right_region]))
            if inside_median <= cfg.noise_multiplier * flank_median:
                continue
            peak = start + int(np.argmax(power[start : end + 1]))
            flank_noise = flank_median / np.log(2.0)
            candidates.append(CandidateRegion(
                start,
                end,
                peak,
                float(power[peak]),
                flank_noise,
                flank_noise * cfg.noise_multiplier,
            ))
        return tuple(candidates)

    @staticmethod
    def _overlaps(first: CandidateRegion, second: CandidateRegion) -> bool:
        return first.start_bin <= second.end_bin and second.start_bin <= first.end_bin
