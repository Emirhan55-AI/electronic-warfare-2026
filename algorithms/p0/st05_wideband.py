"""ST-05 reference model for bounded wideband emission proposals.

The model deliberately keeps the canonical narrowband OS-CFAR untouched.  It
only studies wideband support whose two spectral flanks can be observed.  A
single receiver window cannot distinguish receiver noise from a noise-like
emission that fills the whole window, so this API never claims absolute signal
absence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class ST05WidebandConfig:
    frame_bins: int = 4096
    region_bins: int = 256
    seed_integration_bins: tuple[int, ...] = (32, 64, 128, 256)
    support_integration_bins: int = 8
    seed_multiplier: float = 2.5
    support_multiplier: float = 1.5
    reference_region_rank: int = 4
    minimum_span_bins: int = 41
    flank_bins: int = 64
    maximum_flank_difference_db: float = 3.0
    minimum_frames: int = 8
    minimum_occupancy: float = 0.75
    maximum_support_gap_bins: int = 4

    def __post_init__(self) -> None:
        if self.frame_bins < 128 or self.frame_bins % self.region_bins:
            raise ValueError("frame_bins must be divisible by region_bins")
        if self.region_bins < 8:
            raise ValueError("region_bins must be at least eight")
        if not self.seed_integration_bins:
            raise ValueError("at least one seed integration scale is required")
        for width in self.seed_integration_bins:
            if width < 2 or width > self.frame_bins:
                raise ValueError("seed integration scales must fit the frame")
        if not 2 <= self.support_integration_bins <= self.frame_bins:
            raise ValueError("support integration width must fit the frame")
        if self.seed_multiplier <= 1.0 or self.support_multiplier <= 1.0:
            raise ValueError("energy multipliers must be greater than one")
        if self.support_multiplier >= self.seed_multiplier:
            raise ValueError("support multiplier must remain below seed multiplier")
        region_count = self.frame_bins // self.region_bins
        if not 1 <= self.reference_region_rank <= region_count:
            raise ValueError("reference region rank must select an existing region")
        if self.minimum_span_bins < 1 or self.flank_bins < 1:
            raise ValueError("span and flank widths must be positive")
        if self.maximum_flank_difference_db <= 0.0:
            raise ValueError("flank difference limit must be positive")
        if self.minimum_frames < 2 or not 0.0 < self.minimum_occupancy <= 1.0:
            raise ValueError("temporal evidence configuration is invalid")
        if self.maximum_support_gap_bins < 0:
            raise ValueError("maximum support gap must be non-negative")


ST05_WIDEBAND_PROFILE = ST05WidebandConfig()


@dataclass(frozen=True)
class ST05WidebandCandidate:
    start_bin: int
    end_bin: int
    peak_bin: int
    peak_power: float
    reference_power_per_bin: float
    threshold_power_per_bin: float
    observed_frames: int
    total_frames: int

    @property
    def bin_count(self) -> int:
        return self.end_bin - self.start_bin + 1

    @property
    def occupancy(self) -> float:
        return self.observed_frames / self.total_frames


@dataclass(frozen=True)
class ST05UnresolvedSupport:
    start_bin: int
    end_bin: int
    reason: str


@dataclass(frozen=True)
class ST05WidebandResult:
    decision: str
    candidates: tuple[ST05WidebandCandidate, ...]
    unresolved_supports: tuple[ST05UnresolvedSupport, ...]
    relative_reference_power_per_bin: float
    reference_scope: str = "relative_spectral_only"
    absolute_absence_supported: bool = False


class ST05WidebandDetector:
    """Propose temporally persistent emissions with observable quiet flanks."""

    def __init__(self, config: ST05WidebandConfig | None = None) -> None:
        self.config = config or ST05_WIDEBAND_PROFILE

    def process(self, frame_power: npt.ArrayLike) -> ST05WidebandResult:
        frames = np.asarray(frame_power, dtype=np.float64)
        cfg = self.config
        if frames.ndim != 2 or frames.shape[1] != cfg.frame_bins:
            raise ValueError(
                f"ST-05 wideband detector requires [frames, {cfg.frame_bins}] power"
            )
        if frames.shape[0] < cfg.minimum_frames:
            raise ValueError(f"at least {cfg.minimum_frames} frames are required")
        if not np.all(np.isfinite(frames)) or np.any(frames < 0.0):
            raise ValueError("power must contain finite non-negative values")

        mean_power = np.mean(frames, axis=0)
        region_noise = self._region_noise(frames)
        reference = float(
            np.partition(region_noise, cfg.reference_region_rank - 1)[
                cfg.reference_region_rank - 1
            ]
        )
        if not math.isfinite(reference) or reference <= 0.0:
            return ST05WidebandResult(
                "reference_unavailable", (), (), float("nan")
            )

        seed_mask = np.zeros(cfg.frame_bins, dtype=np.bool_)
        for width in cfg.seed_integration_bins:
            averaged, valid = self._centered_mean(mean_power, width)
            seed_mask |= valid & (averaged > reference * cfg.seed_multiplier)

        support_mean, support_valid = self._centered_mean(
            mean_power, cfg.support_integration_bins
        )
        support_mask = support_valid & (
            support_mean > reference * cfg.support_multiplier
        )
        supports = self._seeded_supports(seed_mask, support_mask)

        accepted: list[ST05WidebandCandidate] = []
        unresolved: list[ST05UnresolvedSupport] = []
        for start, end in supports:
            if end - start + 1 < cfg.minimum_span_bins:
                continue
            left_start = start - cfg.flank_bins
            right_stop = end + 1 + cfg.flank_bins
            if left_start < 0 or right_stop > cfg.frame_bins:
                unresolved.append(
                    ST05UnresolvedSupport(start, end, "independent_flanks_unavailable")
                )
                continue

            left_frames = frames[:, left_start:start]
            right_frames = frames[:, end + 1:right_stop]
            left_noise_by_frame = np.median(left_frames, axis=1) / np.log(2.0)
            right_noise_by_frame = np.median(right_frames, axis=1) / np.log(2.0)
            left_noise = float(np.mean(left_noise_by_frame))
            right_noise = float(np.mean(right_noise_by_frame))
            flank_difference_db = abs(10.0 * math.log10(left_noise / right_noise))
            if flank_difference_db > cfg.maximum_flank_difference_db:
                unresolved.append(
                    ST05UnresolvedSupport(start, end, "nonhomogeneous_flanks")
                )
                continue

            candidate_noise = max(left_noise, right_noise)
            candidate_threshold = candidate_noise * cfg.seed_multiplier
            support_power_by_frame = np.mean(frames[:, start:end + 1], axis=1)
            frame_thresholds = (
                np.maximum(left_noise_by_frame, right_noise_by_frame)
                * cfg.seed_multiplier
            )
            observed = int(np.count_nonzero(support_power_by_frame > frame_thresholds))
            required = math.ceil(cfg.minimum_occupancy * frames.shape[0])
            if observed < required:
                continue
            mean_support_power = float(np.mean(mean_power[start:end + 1]))
            if mean_support_power <= candidate_threshold:
                continue
            peak = start + int(np.argmax(mean_power[start:end + 1]))
            accepted.append(
                ST05WidebandCandidate(
                    start,
                    end,
                    peak,
                    float(mean_power[peak]),
                    candidate_noise,
                    candidate_threshold,
                    observed,
                    int(frames.shape[0]),
                )
            )

        accepted.sort(key=lambda item: (item.start_bin, item.end_bin, item.peak_bin))
        unresolved.sort(key=lambda item: (item.start_bin, item.end_bin, item.reason))
        if accepted:
            decision = "bounded_candidates"
        elif unresolved:
            decision = "retune_required"
        else:
            decision = "no_bounded_emission"
        return ST05WidebandResult(
            decision,
            tuple(accepted),
            tuple(unresolved),
            reference,
        )

    def _region_noise(self, frames: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        cfg = self.config
        shaped = frames.reshape(
            frames.shape[0], cfg.frame_bins // cfg.region_bins, cfg.region_bins
        )
        per_frame = np.median(shaped, axis=2) / np.log(2.0)
        return np.mean(per_frame, axis=0)

    @staticmethod
    def _centered_mean(
        values: npt.NDArray[np.float64], width: int
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.bool_]]:
        left = (width - 1) // 2
        right = width - left - 1
        prefix = np.concatenate(([0.0], np.cumsum(values, dtype=np.float64)))
        centers = np.arange(left, values.size - right, dtype=np.int64)
        averaged = np.zeros(values.size, dtype=np.float64)
        averaged[centers] = (
            prefix[centers + right + 1] - prefix[centers - left]
        ) / width
        valid = np.zeros(values.size, dtype=np.bool_)
        valid[centers] = True
        return averaged, valid

    def _seeded_supports(
        self,
        seeds: npt.NDArray[np.bool_],
        support: npt.NDArray[np.bool_],
    ) -> tuple[tuple[int, int], ...]:
        bins = np.flatnonzero(support)
        if bins.size == 0:
            return ()
        cfg = self.config
        groups = np.split(
            bins,
            np.flatnonzero(
                np.diff(bins) > cfg.maximum_support_gap_bins + 1
            ) + 1,
        )
        retained = []
        for group in groups:
            start, end = int(group[0]), int(group[-1])
            if np.any(seeds[start:end + 1]):
                retained.append((start, end))
        return tuple(retained)
