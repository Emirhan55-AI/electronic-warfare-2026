"""Noise-referenced deterministic bandwidth estimation for mandatory P0 output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

from .detection import P0_DETECTOR_PROFILE, order_statistic_expected_ratio
from .models import CandidateRegion


BandwidthMethod = Literal["threshold_edges", "occupied_power_fallback"]


@dataclass(frozen=True)
class BandwidthProfile:
    edge_snr_db: float = 6.0
    occupied_power_fraction: float = 0.98
    search_margin_bins: int = 64
    maximum_bridge_gap_bins: int = 2
    smoothing_kernel: tuple[float, ...] = (0.25, 0.50, 0.25)
    threshold_to_occupied_maximum_ratio: float = 1.15


@dataclass(frozen=True)
class BandwidthEstimate:
    lower_frequency_hz: float
    upper_frequency_hz: float
    bandwidth_hz: float
    method: BandwidthMethod
    threshold_lower_frequency_hz: float
    threshold_upper_frequency_hz: float
    threshold_bandwidth_hz: float
    occupied_lower_frequency_hz: float
    occupied_upper_frequency_hz: float
    occupied_bandwidth_hz: float
    coarse_lower_frequency_hz: float
    coarse_upper_frequency_hz: float
    coarse_bandwidth_hz: float
    local_noise_mean_power: float
    edge_threshold_power: float


class BandwidthEstimator:
    """Refine a coarse detector ROI with local-noise edges and explicit fallback."""

    def __init__(self, profile: BandwidthProfile | None = None) -> None:
        self.profile = profile or BandwidthProfile()

    def estimate(
        self,
        *,
        shifted_power: npt.ArrayLike,
        sample_rate_hz: float,
        center_frequency_hz: float,
        candidate: CandidateRegion,
        neighboring_candidates: tuple[CandidateRegion, ...] = (),
    ) -> BandwidthEstimate:
        power = np.asarray(shifted_power, dtype=np.float64)
        if power.ndim != 1 or power.size < 64 or not np.all(np.isfinite(power)) or np.any(power < 0):
            raise ValueError("shifted_power is invalid")
        if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be finite and positive")
        if not 0 <= candidate.start_bin <= candidate.peak_bin <= candidate.end_bin < power.size:
            raise ValueError("candidate bounds are invalid")

        profile = self.profile
        bin_width = sample_rate_hz / power.size
        search_start = max(0, candidate.start_bin - profile.search_margin_bins)
        search_end = min(power.size - 1, candidate.end_bin + profile.search_margin_bins)
        for neighbor in neighboring_candidates:
            if neighbor.end_bin < candidate.start_bin:
                search_start = max(search_start, (neighbor.end_bin + candidate.start_bin + 1) // 2)
            elif neighbor.start_bin > candidate.end_bin:
                search_end = min(search_end, (candidate.end_bin + neighbor.start_bin) // 2)
        if search_start > candidate.peak_bin or search_end < candidate.peak_bin:
            raise ValueError("neighbor bounds exclude the candidate peak")

        expected_ratio = order_statistic_expected_ratio(
            P0_DETECTOR_PROFILE.reference_count,
            P0_DETECTOR_PROFILE.order_statistic_rank,
        )
        local_noise = candidate.noise_power_per_bin / expected_ratio
        local_noise = max(float(local_noise), np.finfo(np.float64).tiny)
        edge_threshold = local_noise * 10.0 ** (profile.edge_snr_db / 10.0)
        kernel = np.asarray(profile.smoothing_kernel, dtype=np.float64)
        kernel /= np.sum(kernel)
        smoothed = np.convolve(power, kernel, mode="same")
        active = smoothed[search_start : search_end + 1] > edge_threshold
        active_bins = np.flatnonzero(active) + search_start
        groups: list[list[int]] = []
        maximum_step = profile.maximum_bridge_gap_bins + 1
        for raw_bin in active_bins:
            bin_index = int(raw_bin)
            if not groups or bin_index - groups[-1][-1] > maximum_step:
                groups.append([bin_index])
            else:
                groups[-1].append(bin_index)
        selected = next((group for group in groups if group[0] <= candidate.peak_bin <= group[-1]), None)
        if selected is None:
            threshold_start = candidate.start_bin
            threshold_end = candidate.end_bin
        else:
            threshold_start = min(selected[0], candidate.start_bin)
            threshold_end = max(selected[-1], candidate.end_bin)

        # The detector candidate is the bounded coarse ROI.  Threshold edges
        # may refine beyond it, but occupied-power fallback must not absorb a
        # neighboring emitter or unrelated noise outside that ROI.
        support_start = candidate.start_bin
        support_end = candidate.end_bin
        support_power = np.maximum(power[support_start : support_end + 1] - local_noise, 0.0)
        total_excess = float(np.sum(support_power))
        if total_excess <= 0:
            occupied_start, occupied_end = candidate.start_bin, candidate.end_bin
        else:
            cumulative = np.cumsum(support_power)
            tail = (1.0 - profile.occupied_power_fraction) / 2.0
            occupied_start = support_start + int(np.searchsorted(cumulative, tail * total_excess, side="left"))
            occupied_end = support_start + int(np.searchsorted(cumulative, (1.0 - tail) * total_excess, side="left"))
            occupied_end = min(occupied_end, support_end)

        threshold_width = threshold_end - threshold_start + 1
        occupied_width = occupied_end - occupied_start + 1
        fragmented = selected is None or len(selected) / threshold_width < 0.60
        threshold_unstable = (
            fragmented
            or threshold_start == search_start
            or threshold_end == search_end
            or threshold_width > profile.threshold_to_occupied_maximum_ratio * max(occupied_width, 1)
        )
        if threshold_unstable:
            canonical_start, canonical_end = occupied_start, occupied_end
            method: BandwidthMethod = "occupied_power_fallback"
        else:
            canonical_start, canonical_end = threshold_start, threshold_end
            method = "threshold_edges"

        frequencies = center_frequency_hz + np.fft.fftshift(np.fft.fftfreq(power.size, d=1.0 / sample_rate_hz))

        def edges(start: int, end: int) -> tuple[float, float, float]:
            lower = float(frequencies[start] - bin_width / 2.0)
            upper = float(frequencies[end] + bin_width / 2.0)
            return lower, upper, upper - lower

        lower, upper, bandwidth = edges(canonical_start, canonical_end)
        threshold_lower, threshold_upper, threshold_bandwidth = edges(threshold_start, threshold_end)
        occupied_lower, occupied_upper, occupied_bandwidth = edges(occupied_start, occupied_end)
        coarse_lower, coarse_upper, coarse_bandwidth = edges(candidate.start_bin, candidate.end_bin)
        return BandwidthEstimate(
            lower,
            upper,
            bandwidth,
            method,
            threshold_lower,
            threshold_upper,
            threshold_bandwidth,
            occupied_lower,
            occupied_upper,
            occupied_bandwidth,
            coarse_lower,
            coarse_upper,
            coarse_bandwidth,
            local_noise,
            edge_threshold,
        )
