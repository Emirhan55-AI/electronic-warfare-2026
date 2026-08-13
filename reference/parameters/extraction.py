"""Qt-independent PHASE-04 frame-local core parameter extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from reference.detection import DetectionEvent, DetectionFrameResult, DetectionRegion
from reference.spectrum import SpectrumResult

from .classification import FEATURE_HISTORY_BYTES, FeatureHistoryStore, classify_features
from .models import (
    AnalysisCandidate,
    BandSupportResult,
    BandwidthEstimate,
    EventParameterEstimate,
    FrequencyEstimate,
    ParameterFrameResult,
    ParameterInvalidReason,
    RelativePowerEstimate,
    SignalDomainEstimate,
)
from .r2 import (
    HANN_CORRECTION,
    MORPHOLOGY_MOMENT_THRESHOLD,
    NOMINAL_GROW_RATIO,
    NOMINAL_SEED_RATIO,
)


FRAME_LENGTH = 4096
TRANSIENT_GUARD = 1152
FEATURE_START = 1152
FEATURE_STOP = 2944
FEATURE_SAMPLES = 1792
MIN_VALID_BIN = 20
MAX_VALID_BIN = 4075
ANALYSIS_SEARCH_MARGIN = 32
ANALYSIS_REFERENCE_GUARD = 4
ANALYSIS_REFERENCE_CELLS_PER_SIDE = 16
ANALYSIS_CLUSTER_GAP_MAX = 24
ANALYSIS_HULL_WIDTH_MAX = 112
ANALYSIS_REGION_COUNT_MAX = 32
MULTI_COMPONENT_GAP_MAX = 16
MULTI_COMPONENT_COUNT_MAX = 32
MULTI_COMPONENT_POWER_FRACTION_MIN = 0.02
R2_COMPONENT_GAP_MAX = 24
R2_COMPONENT_COUNT_MAX = 32
R2_TEMPORAL_DEPTH = 3
R2_BAND_HISTORY_BYTES = 6_528
R2_PARAMETER_HISTORY_BYTES = FEATURE_HISTORY_BYTES + R2_BAND_HISTORY_BYTES
assert R2_PARAMETER_HISTORY_BYTES == 74_368

ANALYSIS_METHODS = (
    "analysis.single-region-v1",
    "analysis.clustered-regions-v1",
)
BANDWIDTH_METHODS = (
    "band.noise-threshold-6db",
    "band.occupied-power-99",
    "band.peak-drop-20db",
    "band.multi-component-excess-99-v1",
    "band.temporal-morphology-envelope-v1",
)
NOISE_METHODS = (
    "noise.sideband-median-ln2",
    "noise.trimmed-mean-20",
    "noise.winsorized-mean-10",
    "noise.trimmed-mean-20-hann-calibrated-v1",
)
POWER_SNR_METHODS = ("power.psd-noise-subtract-v1",)


@dataclass(frozen=True)
class MethodSelection:
    noise: str
    bandwidth: str
    spectral_center: str
    carrier: str
    signal_domain: str
    analysis_window: str = "analysis.single-region-v1"
    power_snr: str = "power.psd-noise-subtract-v1"


def compute_transient_guard(frame_length: int = FRAME_LENGTH) -> tuple[int, int, int]:
    """Recompute the fixed impulse-energy guard without benchmark observations."""
    worst = 0
    worst_width = 0
    for width in range(1, 4057):
        mask = _raised_cosine_mask(frame_length, frame_length // 2 - width // 2, frame_length // 2 - width // 2 + width - 1)
        impulse = np.fft.fftshift(np.fft.ifft(np.fft.ifftshift(mask)))
        energy = np.abs(impulse) ** 2
        total = float(np.sum(energy))
        center = frame_length // 2
        accumulated = float(energy[center])
        guard = 0
        while accumulated / total < 0.999:
            guard += 1
            accumulated += float(energy[center - guard] + energy[center + guard])
        if guard > worst:
            worst, worst_width = guard, width
    rounded = int(math.ceil(worst / 64.0) * 64)
    return worst, worst_width, rounded


def _region_key(region: DetectionRegion) -> tuple[int, int, int]:
    return region.start_bin, region.end_bin, region.peak_bin


def _select_candidate_owner(
    regions: tuple[DetectionRegion, ...],
    detection: DetectionFrameResult,
    history: FeatureHistoryStore | None,
) -> tuple[DetectionEvent | None, tuple[int, ...]]:
    keys = {_region_key(region) for region in regions}
    events = [
        event
        for event in detection.active_events
        if event.state == "confirmed"
        and event.observed_this_frame
        and _region_key(event.region) in keys
    ]
    events.sort(key=lambda event: event.event_id)
    if not events:
        return None, ()

    def owner_key(event: DetectionEvent) -> tuple[bool, int, int]:
        continuous = history is not None and history.last_frame(event.event_id) == detection.frame_index - 1
        return not continuous, event.first_frame, event.event_id

    return min(events, key=owner_key), tuple(event.event_id for event in events)


def _analysis_candidate(
    regions: tuple[DetectionRegion, ...],
    detection: DetectionFrameResult,
    history: FeatureHistoryStore | None,
) -> AnalysisCandidate | None:
    owner, source_event_ids = _select_candidate_owner(regions, detection, history)
    if owner is None:
        return None
    hull_start = min(region.start_bin for region in regions)
    hull_end = max(region.end_bin for region in regions)
    search_start = max(MIN_VALID_BIN, hull_start - ANALYSIS_SEARCH_MARGIN)
    search_end = min(MAX_VALID_BIN, hull_end + ANALYSIS_SEARCH_MARGIN)
    left_end = search_start - ANALYSIS_REFERENCE_GUARD - 1
    left_start = left_end - ANALYSIS_REFERENCE_CELLS_PER_SIDE + 1
    right_start = search_end + ANALYSIS_REFERENCE_GUARD + 1
    right_end = right_start + ANALYSIS_REFERENCE_CELLS_PER_SIDE - 1
    reason: ParameterInvalidReason | None = None
    if len(regions) > ANALYSIS_REGION_COUNT_MAX or hull_end - hull_start + 1 > ANALYSIS_HULL_WIDTH_MAX:
        reason = "analysis_candidate_overflow"
    elif left_start < MIN_VALID_BIN or right_end > MAX_VALID_BIN:
        reason = "reference_cells_unavailable"
    return AnalysisCandidate(
        owner_event_id=owner.event_id,
        source_event_ids=source_event_ids,
        source_region_count=len(regions),
        hull_start_bin=hull_start,
        hull_end_bin=hull_end,
        search_start_bin=search_start,
        search_end_bin=search_end,
        left_reference_start_bin=left_start,
        left_reference_end_bin=left_end,
        right_reference_start_bin=right_start,
        right_reference_end_bin=right_end,
        peak_bin=owner.region.peak_bin,
        state="valid" if reason is None else "insufficient_quality",
        invalid_reason=reason,
        constituent_regions=tuple((region.start_bin, region.end_bin) for region in regions),
    )


def _analysis_chains(detection: DetectionFrameResult, method: str) -> tuple[tuple[DetectionRegion, ...], ...]:
    if method not in ANALYSIS_METHODS:
        raise ValueError(f"unsupported analysis-window method: {method}")
    regions = tuple(sorted(detection.regions, key=lambda item: (item.start_bin, item.end_bin, item.peak_bin)))
    if method == "analysis.single-region-v1":
        return tuple((region,) for region in regions)
    chains: list[tuple[DetectionRegion, ...]] = []
    current: list[DetectionRegion] = []
    for region in regions:
        if current and region.start_bin - current[-1].end_bin - 1 > ANALYSIS_CLUSTER_GAP_MAX:
            chains.append(tuple(current))
            current = []
        current.append(region)
    if current:
        chains.append(tuple(current))
    return tuple(chains)


def _build_analysis_candidates_and_drops(
    detection: DetectionFrameResult,
    method: str,
    history: FeatureHistoryStore | None,
) -> tuple[tuple[AnalysisCandidate, ...], int]:
    candidates: list[AnalysisCandidate] = []
    dropped = 0
    for chain in _analysis_chains(detection, method):
        candidate = _analysis_candidate(chain, detection, history)
        if candidate is None:
            dropped += 1
        else:
            candidates.append(candidate)
    candidates.sort(key=lambda item: (item.hull_start_bin, item.hull_end_bin, item.owner_event_id))
    return tuple(candidates), dropped


def build_analysis_candidates(
    detection: DetectionFrameResult,
    method: str,
    history: FeatureHistoryStore | None = None,
) -> tuple[AnalysisCandidate, ...]:
    """Build deterministic, bounded windows without consulting ground truth."""
    candidates, _ = _build_analysis_candidates_and_drops(detection, method, history)
    return candidates


def _raised_cosine_mask(length: int, lower: int, upper: int) -> np.ndarray:
    mask = np.zeros(length, dtype=np.float64)
    lo = max(0, min(length - 1, int(lower)))
    hi = max(lo, min(length - 1, int(upper)))
    mask[lo : hi + 1] = 1.0
    for distance in range(1, 5):
        value = 0.5 * (1.0 + math.cos(math.pi * distance / 4.0))
        if lo - distance >= 0:
            mask[lo - distance] = value
        if hi + distance < length:
            mask[hi + distance] = value
    return mask


def _noise_density(psd: np.ndarray, candidate: AnalysisCandidate, method: str) -> float:
    left = psd[candidate.left_reference_start_bin : candidate.left_reference_end_bin + 1]
    right = psd[candidate.right_reference_start_bin : candidate.right_reference_end_bin + 1]
    if left.size != ANALYSIS_REFERENCE_CELLS_PER_SIDE or right.size != ANALYSIS_REFERENCE_CELLS_PER_SIDE:
        return 0.0
    references = np.concatenate((left, right))
    references = references[np.isfinite(references)]
    if references.size == 0:
        return 0.0
    ordered = np.sort(references)
    if method == "noise.sideband-median-ln2":
        return float(np.median(ordered) / math.log(2.0))
    if method in {"noise.trimmed-mean-20", "noise.trimmed-mean-20-hann-calibrated-v1"}:
        cut = int(math.floor(0.2 * ordered.size))
        body = ordered[cut : ordered.size - cut] if ordered.size - 2 * cut else ordered
        estimate = float(np.mean(body))
        return estimate * HANN_CORRECTION if method.endswith("hann-calibrated-v1") else estimate
    if method == "noise.winsorized-mean-10":
        cut = int(math.floor(0.1 * ordered.size))
        if cut:
            ordered = np.clip(ordered, ordered[cut], ordered[-cut - 1])
        return float(np.mean(ordered))
    raise ValueError(f"unsupported noise method: {method}")


def _bridge(mask: np.ndarray) -> np.ndarray:
    result = mask.copy()
    if result.size >= 3:
        result[1:-1] |= result[:-2] & result[2:]
    return result


def _invalid_support(reason: ParameterInvalidReason, *, component_count: int = 0) -> BandSupportResult:
    return BandSupportResult(None, None, "insufficient_quality", reason, component_count)


def _connected_components(mask: np.ndarray) -> tuple[tuple[int, int], ...]:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return ()
    components: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for raw in indices[1:]:
        index = int(raw)
        if index != previous + 1:
            components.append((start, previous))
            start = index
        previous = index
    components.append((start, previous))
    return tuple(components)


def _multi_component_support(
    smoothed: np.ndarray,
    *,
    lower: int,
    local_peak: int,
    noise: float,
) -> BandSupportResult:
    threshold = max(noise * (10.0 ** 0.6), np.finfo(np.float64).tiny)
    significant = _bridge(smoothed >= threshold)
    components = _connected_components(significant)
    if len(components) > MULTI_COMPONENT_COUNT_MAX:
        return _invalid_support("support_component_overflow", component_count=len(components))
    anchor_index = next(
        (index for index, (start, end) in enumerate(components) if start <= local_peak <= end),
        None,
    )
    if anchor_index is None:
        return _invalid_support("anchor_not_significant", component_count=len(components))
    excess = np.maximum(smoothed - noise, 0.0)
    powers = np.asarray([np.sum(excess[start : end + 1]) for start, end in components], dtype=np.float64)
    total = float(np.sum(powers))
    if not math.isfinite(total) or total <= 0.0:
        return _invalid_support("support_empty", component_count=len(components))

    retained = {anchor_index}
    expansion_order = ["anchor"]
    left_index = anchor_index - 1
    right_index = anchor_index + 1
    left_open = left_index >= 0
    right_open = right_index < len(components)
    hull_start, hull_end = components[anchor_index]
    while left_open or right_open:
        eligible: list[tuple[int, float, int, str, int]] = []
        if left_open:
            start, end = components[left_index]
            gap = hull_start - end - 1
            fraction = float(powers[left_index] / total)
            if gap <= MULTI_COMPONENT_GAP_MAX and fraction >= MULTI_COMPONENT_POWER_FRACTION_MIN:
                eligible.append((gap, -float(powers[left_index]), 0, "left", left_index))
            else:
                left_open = False
        if right_open:
            start, end = components[right_index]
            gap = start - hull_end - 1
            fraction = float(powers[right_index] / total)
            if gap <= MULTI_COMPONENT_GAP_MAX and fraction >= MULTI_COMPONENT_POWER_FRACTION_MIN:
                eligible.append((gap, -float(powers[right_index]), 1, "right", right_index))
            else:
                right_open = False
        if not eligible:
            continue
        _, _, _, side, selected = min(eligible)
        retained.add(selected)
        expansion_order.append(side)
        if side == "left":
            hull_start = components[selected][0]
            left_index -= 1
            left_open = left_index >= 0
        else:
            hull_end = components[selected][1]
            right_index += 1
            right_open = right_index < len(components)

    retained_excess = np.zeros_like(excess)
    for index in sorted(retained):
        start, end = components[index]
        retained_excess[start : end + 1] = excess[start : end + 1]
    retained_total = float(np.sum(retained_excess))
    if retained_total <= 0.0:
        return _invalid_support("support_empty", component_count=len(components))
    cumulative = np.cumsum(retained_excess) / retained_total
    lo = int(np.searchsorted(cumulative, 0.005, side="left"))
    hi = int(np.searchsorted(cumulative, 0.995, side="left"))
    lo = max(0, lo - 1)
    hi = min(smoothed.size - 1, hi + 1)
    return BandSupportResult(
        lower + lo,
        lower + hi,
        "valid",
        component_count=len(components),
        retained_component_count=len(retained),
        expansion_order=tuple(expansion_order),
        retained_component_indices=tuple(sorted(retained)),
    )


def _component_intersects_regions(
    component: tuple[int, int], lower: int, constituent_regions: tuple[tuple[int, int], ...],
) -> bool:
    absolute_start = lower + component[0]
    absolute_end = lower + component[1]
    return any(absolute_start <= region_end and absolute_end >= region_start for region_start, region_end in constituent_regions)


def _weighted_moment_and_centroid(
    excess: np.ndarray, component: tuple[int, int], lower: int,
) -> tuple[float, float]:
    start, end = component
    weights = excess[start : end + 1]
    total = float(np.sum(weights))
    if total <= 0.0:
        return math.inf, float(lower + 0.5 * (start + end))
    bins = lower + np.arange(start, end + 1, dtype=np.float64)
    centroid = float(np.sum(weights * bins) / total)
    moment = float(np.sum(weights * (bins - centroid) ** 2) / total)
    return moment, centroid


def _fractional_power_edge(
    excess: np.ndarray, component: tuple[int, int], lower: int, quantile: float,
) -> float:
    start, end = component
    weights = excess[start : end + 1]
    total = float(np.sum(weights))
    if total <= 0.0:
        return float(lower + start if quantile <= 0.5 else lower + end)
    target = quantile * total
    cumulative = np.cumsum(weights)
    relative = int(np.searchsorted(cumulative, target, side="left"))
    relative = min(relative, weights.size - 1)
    before = 0.0 if relative == 0 else float(cumulative[relative - 1])
    fraction = (target - before) / max(float(weights[relative]), np.finfo(np.float64).tiny)
    # Treat each PSD cell as uniform across its physical half-bin boundaries.
    return float(lower + start + relative - 0.5 + np.clip(fraction, 0.0, 1.0))


def _temporal_morphology_support(
    raw: np.ndarray,
    smoothed: np.ndarray,
    *,
    lower: int,
    local_peak: int,
    noise: float,
    constituent_regions: tuple[tuple[int, int], ...],
) -> BandSupportResult:
    seed = raw >= noise * NOMINAL_SEED_RATIO
    grow = _bridge(raw >= noise * NOMINAL_GROW_RATIO)
    components = _connected_components(grow)
    if len(components) > R2_COMPONENT_COUNT_MAX:
        return _invalid_support("support_component_overflow", component_count=len(components))
    anchor = next((index for index, (start, end) in enumerate(components) if start <= local_peak <= end), None)
    if anchor is None:
        return _invalid_support("anchor_not_supported", component_count=len(components))
    seed_backed = [bool(np.any(seed[start : end + 1])) for start, end in components]
    region_backed = [
        _component_intersects_regions(component, lower, constituent_regions) for component in components
    ]
    supported = [left or right for left, right in zip(seed_backed, region_backed)]
    if not supported[anchor]:
        return _invalid_support("anchor_not_supported", component_count=len(components))

    retained = {anchor}
    hull_start, hull_end = components[anchor]
    # Grow-only components are ignored and never shorten the physical gap.
    for index in reversed([item for item in range(anchor) if supported[item]]):
        gap = hull_start - components[index][1] - 1
        if gap > R2_COMPONENT_GAP_MAX:
            break
        retained.add(index)
        hull_start = components[index][0]
    for index in [item for item in range(anchor + 1, len(components)) if supported[item]]:
        gap = components[index][0] - hull_end - 1
        if gap > R2_COMPONENT_GAP_MAX:
            break
        retained.add(index)
        hull_end = components[index][1]

    excess = np.maximum(smoothed - noise, 0.0)
    ordered = sorted(retained)
    moments: list[float] = []
    centroids: dict[int, float] = {}
    for index in ordered:
        moment, centroid = _weighted_moment_and_centroid(excess, components[index], lower)
        moments.append(moment)
        centroids[index] = centroid
    first, last = ordered[0], ordered[-1]
    first_is_line = seed_backed[first] and moments[0] <= MORPHOLOGY_MOMENT_THRESHOLD
    last_is_line = seed_backed[last] and moments[-1] <= MORPHOLOGY_MOMENT_THRESHOLD
    lower_edge = (
        centroids[first]
        if first_is_line
        else _fractional_power_edge(excess, components[first], lower, 0.005)
    )
    upper_edge = (
        centroids[last]
        if last_is_line
        else _fractional_power_edge(excess, components[last], lower, 0.995)
    )
    if upper_edge < lower_edge:
        return _invalid_support("support_empty", component_count=len(components))
    return BandSupportResult(
        lower_shifted_bin=lower + components[first][0],
        upper_shifted_bin=lower + components[last][1],
        state="valid",
        component_count=len(components),
        retained_component_count=len(retained),
        expansion_order=("anchor", "left", "right"),
        retained_component_indices=tuple(ordered),
        lower_shifted_edge=lower_edge,
        upper_shifted_edge=upper_edge,
        component_moments=tuple(moments),
        supported_component_indices=tuple(index for index, value in enumerate(supported) if value),
    )


def estimate_band_support(
    psd: npt.ArrayLike,
    lower: int,
    upper: int,
    peak: int,
    noise: float,
    method: str,
    constituent_regions: tuple[tuple[int, int], ...] = (),
) -> BandSupportResult:
    """Estimate inclusive shifted-bin support inside one bounded search window."""
    values = np.asarray(psd, dtype=np.float64)
    if method not in BANDWIDTH_METHODS:
        raise ValueError(f"unsupported bandwidth method: {method}")
    if not math.isfinite(noise) or noise <= 0.0:
        return _invalid_support("invalid_noise")
    if not 0 <= lower <= peak <= upper < values.size:
        return _invalid_support("support_empty")
    window = values[lower : upper + 1]
    smoothed = np.convolve(window, np.asarray([0.25, 0.5, 0.25]), mode="same")
    local_peak = int(np.clip(peak - lower, 0, window.size - 1))
    if method == "band.temporal-morphology-envelope-v1":
        return _temporal_morphology_support(
            window,
            smoothed,
            lower=lower,
            local_peak=local_peak,
            noise=noise,
            constituent_regions=constituent_regions,
        )
    if method == "band.multi-component-excess-99-v1":
        return _multi_component_support(smoothed, lower=lower, local_peak=local_peak, noise=noise)
    if method == "band.noise-threshold-6db":
        mask = _bridge(smoothed >= max(noise * (10.0 ** 0.6), np.finfo(np.float64).tiny))
        if not mask[local_peak]:
            return _invalid_support("anchor_not_significant")
        lo = local_peak
        hi = local_peak
        while lo > 0 and mask[lo - 1]:
            lo -= 1
        while hi + 1 < mask.size and mask[hi + 1]:
            hi += 1
        return BandSupportResult(lower + lo, lower + hi, "valid")
    excess = np.maximum(smoothed - noise, 0.0)
    total = float(np.sum(excess))
    if total <= 0.0:
        return _invalid_support("support_empty")
    if method == "band.occupied-power-99":
        excess = np.where(smoothed >= 10.0 * noise, excess, 0.0)
        total = float(np.sum(excess))
        if total <= 0.0:
            return _invalid_support("support_empty")
        cumulative = np.cumsum(excess) / total
        lo = int(np.searchsorted(cumulative, 0.005, side="left"))
        hi = int(np.searchsorted(cumulative, 0.995, side="left"))
        # A continuous occupied spectrum uses one deterministic outer-bin
        # correction for finite-bin integration. Sparse carrier/sideband lines
        # deliberately do not receive this correction.
        if float(np.mean(excess > 0.0)) > 0.5:
            lo = max(0, lo - 1)
            hi = min(window.size - 1, hi + 1)
        return BandSupportResult(lower + lo, lower + min(hi, window.size - 1), "valid")
    if method == "band.peak-drop-20db":
        threshold = noise + max(0.0, float(smoothed[local_peak]) - noise) * 0.01
        mask = _bridge(smoothed >= threshold)
        lo = local_peak
        hi = local_peak
        while lo > 0 and mask[lo - 1]:
            lo -= 1
        while hi + 1 < mask.size and mask[hi + 1]:
            hi += 1
        return BandSupportResult(lower + lo, lower + hi, "valid")
    raise AssertionError("bandwidth method allowlist is incomplete")


def _spectral_center(psd: np.ndarray, lo: int, hi: int, noise: float, method: str) -> float:
    if method == "center.band-midpoint":
        return 0.5 * (lo + hi)
    weights = np.maximum(psd[lo : hi + 1] - noise, 0.0)
    bins = np.arange(lo, hi + 1, dtype=np.float64)
    if method == "center.half-power-midpoint":
        threshold = 0.5 * float(np.max(weights))
        selected = bins[weights >= threshold]
        return float(0.5 * (selected[0] + selected[-1])) if selected.size else float(0.5 * (lo + hi))
    if method == "center.excess-power-centroid":
        return float(np.sum(bins * weights) / np.sum(weights)) if np.sum(weights) > 0.0 else float(0.5 * (lo + hi))
    raise ValueError(f"unsupported center method: {method}")


def _parabolic_peak(psd: np.ndarray, peak: int) -> float:
    if peak <= 0 or peak >= psd.size - 1:
        return float(peak)
    values = np.log(np.maximum(psd[peak - 1 : peak + 2], np.finfo(np.float64).tiny))
    denominator = values[0] - 2.0 * values[1] + values[2]
    delta = 0.0 if abs(denominator) < 1e-15 else 0.5 * (values[0] - values[2]) / denominator
    return float(peak + np.clip(delta, -0.5, 0.5))


def _carrier_bin(
    samples: np.ndarray,
    psd: np.ndarray,
    lo: int,
    hi: int,
    noise: float,
    center_bin: float,
    sample_rate_hz: float,
    method: str,
) -> float | None:
    peak = lo + int(np.argmax(psd[lo : hi + 1]))
    band_excess = float(np.sum(np.maximum(psd[lo : hi + 1] - noise, 0.0)))
    line_excess = float(np.sum(np.maximum(psd[max(lo, peak - 1) : min(hi + 1, peak + 2)] - noise, 0.0)))
    ratio = line_excess / band_excess if band_excess > 0.0 else 0.0
    peak_to_noise = float(psd[peak] / noise) if noise > 0.0 else math.inf
    filtered = _frame_local_channel(samples, lo, hi, center_bin, sample_rate_hz, 0)
    valid = filtered[FEATURE_START:FEATURE_STOP]
    phase = np.angle(valid[1:] * np.conj(valid[:-1]))
    weights = np.abs(valid[1:] * valid[:-1])
    coherence = float(np.abs(np.sum(weights * np.exp(1j * phase))) / max(np.sum(weights), np.finfo(float).tiny))
    phase_bin = center_bin + float(np.angle(np.sum(weights * np.exp(1j * phase))) * FRAME_LENGTH / (2.0 * np.pi))
    if method == "carrier.centroid-only":
        centered_phase = phase - float(np.mean(phase))
        phase_spectrum = np.abs(np.fft.fft(centered_phase)) ** 2
        periodicity = (
            float(np.max(phase_spectrum[1:]) / np.sum(phase_spectrum[1:]))
            if phase_spectrum.size > 1 and np.sum(phase_spectrum[1:]) > 0.0
            else 0.0
        )
        center_index = int(np.clip(round(center_bin), lo, hi))
        center_peak_ratio = float(psd[center_index] / max(psd[peak], np.finfo(np.float64).tiny))
        phase_evidence = coherence >= 0.80 and periodicity >= 0.30 and center_peak_ratio >= 0.80
        bandwidth_hz = max((hi - lo + 1) * sample_rate_hz / FRAME_LENGTH, sample_rate_hz / FRAME_LENGTH)
        stride = int(np.clip(math.floor(sample_rate_hz / (4.0 * bandwidth_hz)), 1, 256))
        reduced = valid[::stride]
        reduced_steps = np.angle(reduced[1:] * np.conj(reduced[:-1])) if reduced.size > 1 else np.zeros(0)
        reduced_envelope = np.abs(reduced)
        active_pairs = (
            (reduced_envelope[1:] >= 0.25 * np.sqrt(np.mean(reduced_envelope**2)))
            & (reduced_envelope[:-1] >= 0.25 * np.sqrt(np.mean(reduced_envelope**2)))
            if reduced.size > 1
            else np.zeros(0, dtype=np.bool_)
        )
        jump_mask = (np.abs(reduced_steps) >= np.pi / 3.0) & active_pairs
        jump_events = int(np.count_nonzero(jump_mask & np.r_[True, ~jump_mask[:-1]])) if jump_mask.size else 0
        jump_rate = jump_events / max(1, int(np.count_nonzero(active_pairs)))
        line_evidence = ratio >= 0.35 and abs(peak - center_bin) <= 0.75 and jump_rate < 0.005
        return center_bin if peak_to_noise >= 10.0 and (line_evidence or phase_evidence) else None
    if peak_to_noise < 10.0 or ratio < 0.35:
        return None
    interpolated = _parabolic_peak(psd, peak)
    if method == "carrier.peak-gated":
        return interpolated
    if method != "carrier.agreement-gated":
        raise ValueError(f"unsupported carrier method: {method}")
    if coherence < 0.80 or abs(phase_bin - interpolated) > 0.75:
        return None
    return interpolated


def _frame_local_channel(samples: np.ndarray, lo: int, hi: int, center_bin: float, sample_rate_hz: float, frame_index: int) -> np.ndarray:
    shifted = np.fft.fftshift(np.fft.fft(samples))
    mask = _raised_cosine_mask(samples.size, lo, hi)
    filtered = np.fft.ifft(np.fft.ifftshift(shifted * mask))
    signed_center = center_bin - samples.size / 2.0
    global_index = frame_index * samples.size + np.arange(samples.size, dtype=np.float64)
    oscillator = np.exp(-1j * 2.0 * np.pi * signed_center * global_index / samples.size)
    return np.asarray(filtered * oscillator, dtype=np.complex128)


def extract_frame_features(
    samples: npt.ArrayLike,
    *,
    lower_bin: int,
    upper_bin: int,
    center_bin: float,
    sample_rate_hz: float,
    frame_index: int,
    snr_db: float,
) -> np.ndarray:
    frame = np.asarray(samples, dtype=np.complex128)
    channel = _frame_local_channel(frame, lower_bin, upper_bin, center_bin, sample_rate_hz, frame_index)
    valid = channel[FEATURE_START:FEATURE_STOP]
    envelope = np.abs(valid)
    rms = float(np.sqrt(np.mean(envelope**2)))
    mean = float(np.mean(envelope))
    std = float(np.std(envelope))
    cv = std / mean if mean > 0.0 else 0.0
    off = float(np.mean(envelope <= 0.25 * rms)) if rms > 0.0 else 1.0
    sorted_env = np.sort(envelope)
    otsu = float(sorted_env[len(sorted_env) // 2]) if sorted_env.size else 0.0
    below = envelope[envelope <= otsu]
    above = envelope[envelope > otsu]
    separation = abs(float(np.mean(above)) - float(np.mean(below))) / max(mean, 1e-15) if below.size and above.size else 0.0
    modulus_dispersion = cv
    bandwidth_hz = max((upper_bin - lower_bin + 1) * sample_rate_hz / frame.size, sample_rate_hz / frame.size)
    stride = int(np.clip(math.floor(sample_rate_hz / (4.0 * bandwidth_hz)), 1, 256))
    reduced = valid[::stride]
    phase_steps = np.angle(reduced[1:] * np.conj(reduced[:-1])) if reduced.size > 1 else np.zeros(0)
    jump_mask = np.abs(phase_steps) >= (np.pi / 3.0)
    events = int(np.count_nonzero(jump_mask & np.r_[True, ~jump_mask[:-1]])) if jump_mask.size else 0
    comparisons = int(jump_mask.size)
    jump_rate = events / comparisons if comparisons else 0.0
    instantaneous = np.angle(valid[1:] * np.conj(valid[:-1])) * frame.size / (2.0 * np.pi)
    histogram, _ = np.histogram(instantaneous, bins=32)
    peaks = np.argsort(histogram)[-2:]
    peaks.sort()
    primary = float(histogram[peaks[-1]] / max(1, np.sum(histogram)))
    secondary = float(histogram[peaks[0]] / max(1, np.sum(histogram)))
    separation_bins = float(abs(int(peaks[-1]) - int(peaks[0])))
    valley = float(np.min(histogram[peaks[0] : peaks[-1] + 1]) / max(1, min(histogram[peaks[0]], histogram[peaks[-1]]))) if peaks[-1] > peaks[0] else 1.0
    shifted_power = np.abs(np.fft.fftshift(np.fft.fft(valid))) ** 2
    positive = np.maximum(shifted_power, np.finfo(np.float64).tiny)
    flatness = float(np.exp(np.mean(np.log(positive))) / np.mean(positive))
    freq_bins = np.arange(shifted_power.size, dtype=np.float64)
    spectral_center = float(np.sum(freq_bins * shifted_power) / max(np.sum(shifted_power), 1e-15))
    centered = freq_bins - spectral_center
    spread = float(np.sqrt(np.sum(centered**2 * shifted_power) / max(np.sum(shifted_power), 1e-15)))
    skew = float(np.sum(centered**3 * shifted_power) / max(np.sum(shifted_power) * spread**3, 1e-15))
    kurt = float(np.sum(centered**4 * shifted_power) / max(np.sum(shifted_power) * spread**4, 1e-15))
    edge_count = max(1, shifted_power.size // 10)
    edge_ratio = float((np.sum(shifted_power[:edge_count]) + np.sum(shifted_power[-edge_count:])) / max(np.sum(shifted_power), 1e-15))
    occupied = float(np.mean(shifted_power >= 0.01 * np.max(shifted_power)))
    activity = float(np.mean(envelope >= 0.5 * rms)) if rms > 0.0 else 0.0
    result = np.asarray(
        [
            valid.size, rms, mean, std, cv, off, otsu, separation, modulus_dispersion,
            events, comparisons, jump_rate,
            float(np.mean(np.abs(phase_steps))) if phase_steps.size else 0.0,
            float(np.quantile(np.abs(phase_steps), 0.95)) if phase_steps.size else 0.0,
            float(np.mean(instantaneous)) if instantaneous.size else 0.0,
            float(np.std(instantaneous)) if instantaneous.size else 0.0,
            float(np.quantile(instantaneous, 0.05)) if instantaneous.size else 0.0,
            float(np.quantile(instantaneous, 0.95)) if instantaneous.size else 0.0,
            primary, secondary, separation_bins, valley, flatness,
            spectral_center - shifted_power.size / 2.0, spread, skew, kurt, edge_ratio, occupied, activity,
            float(np.mean(np.abs(valid) ** 2)), float(snr_db),
        ],
        dtype=np.float64,
    )
    if result.shape != (32,) or not np.all(np.isfinite(result)):
        raise ValueError("non-finite frame-local feature vector")
    return result


def _invalid_event(
    event: DetectionEvent,
    frame_index: int,
    reason: ParameterInvalidReason,
    state: str = "insufficient_quality",
) -> EventParameterEstimate:
    return EventParameterEstimate(
        event.event_id,
        frame_index,
        FrequencyEstimate(None, state, None, state),  # type: ignore[arg-type]
        BandwidthEstimate(None, state, None, state, None, state, None, None, reason),  # type: ignore[arg-type]
        RelativePowerEstimate(None, None, None, None, state, state),  # type: ignore[arg-type]
        SignalDomainEstimate("Belirsiz", "uncertain", 0),
        reason,
    )


@dataclass
class _BandSlot:
    row: int
    last_frame: int


class BandEdgeHistoryStore:
    """Bounded three-frame edge history; no raw I/Q or full PSD is retained."""

    MAX_TRACKS = 64

    def __init__(self) -> None:
        shape = (self.MAX_TRACKS, R2_TEMPORAL_DEPTH)
        self.lower = np.zeros(shape, dtype=np.float64)
        self.upper = np.zeros(shape, dtype=np.float64)
        self.noise = np.zeros(shape, dtype=np.float64)
        self.frame_indices = np.full(shape, -1, dtype=np.int64)
        self.valid = np.zeros(shape, dtype=np.bool_)
        self.supported = np.zeros(shape, dtype=np.bool_)
        self._slots: dict[int, _BandSlot] = {}
        assert self.payload_bytes == R2_BAND_HISTORY_BYTES

    @property
    def payload_bytes(self) -> int:
        return sum(
            item.nbytes
            for item in (self.lower, self.upper, self.noise, self.frame_indices, self.valid, self.supported)
        )

    def reset(self) -> None:
        self.lower.fill(0.0)
        self.upper.fill(0.0)
        self.noise.fill(0.0)
        self.frame_indices.fill(-1)
        self.valid.fill(False)
        self.supported.fill(False)
        self._slots.clear()

    def contains(self, event_id: int) -> bool:
        return event_id in self._slots

    def last_frame(self, event_id: int) -> int | None:
        slot = self._slots.get(event_id)
        return None if slot is None else slot.last_frame

    def discard(self, event_id: int) -> None:
        slot = self._slots.pop(event_id, None)
        if slot is not None:
            self._clear_row(slot.row)

    def retain_observed(self, observed_event_ids: set[int]) -> None:
        """A first miss immediately invalidates continuity for the R2 edge median."""
        for event_id in sorted(set(self._slots) - observed_event_ids):
            self.discard(event_id)

    def append(
        self,
        event_id: int,
        frame_index: int,
        lower: float,
        upper: float,
        noise: float,
        *,
        supported: bool,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not all(math.isfinite(value) for value in (lower, upper, noise)) or upper < lower or noise <= 0.0:
            raise ValueError("band history requires finite ordered edges and positive noise")
        slot = self._slots.get(event_id)
        if slot is None:
            occupied = {item.row for item in self._slots.values()}
            free = next((row for row in range(self.MAX_TRACKS) if row not in occupied), None)
            if free is None:
                raise ValueError("band history track capacity exceeded")
            slot = _BandSlot(free, frame_index - 1)
            self._slots[event_id] = slot
        if frame_index != slot.last_frame + 1:
            self._clear_row(slot.row)
        row = slot.row
        for array in (self.lower, self.upper, self.noise, self.frame_indices, self.valid, self.supported):
            array[row, :-1] = array[row, 1:]
        self.lower[row, -1] = lower
        self.upper[row, -1] = upper
        self.noise[row, -1] = noise
        self.frame_indices[row, -1] = frame_index
        self.valid[row, -1] = True
        self.supported[row, -1] = supported
        slot.last_frame = frame_index
        mask = self.valid[row]
        return self.lower[row, mask].copy(), self.upper[row, mask].copy(), self.noise[row, mask].copy()

    def _clear_row(self, row: int) -> None:
        self.lower[row].fill(0.0)
        self.upper[row].fill(0.0)
        self.noise[row].fill(0.0)
        self.frame_indices[row].fill(-1)
        self.valid[row].fill(False)
        self.supported[row].fill(False)


class ParameterExtractor:
    """Stateful only for bounded per-event feature records, never raw I/Q."""

    def __init__(self, selection: MethodSelection) -> None:
        if selection.analysis_window not in ANALYSIS_METHODS:
            raise ValueError(f"unsupported analysis-window method: {selection.analysis_window}")
        if selection.bandwidth not in BANDWIDTH_METHODS:
            raise ValueError(f"unsupported bandwidth method: {selection.bandwidth}")
        if selection.noise not in NOISE_METHODS:
            raise ValueError(f"unsupported noise method: {selection.noise}")
        if selection.power_snr not in POWER_SNR_METHODS:
            raise ValueError(f"unsupported power/SNR method: {selection.power_snr}")
        self.selection = selection
        self.history = FeatureHistoryStore()
        self.band_history = BandEdgeHistoryStore()

    def reset(self) -> None:
        self.history.reset()
        self.band_history.reset()

    def process(
        self,
        samples: npt.ArrayLike,
        spectrum: SpectrumResult,
        detection: DetectionFrameResult,
        *,
        frame_index: int,
    ) -> ParameterFrameResult:
        if detection.frame_index != frame_index:
            raise ValueError("detection and parameter frame indices differ")
        frame = np.asarray(samples, dtype=np.complex128)
        active = {event.event_id for event in detection.active_events}
        observed = {
            event.event_id
            for event in detection.active_events
            if event.state == "confirmed" and event.observed_this_frame
        }
        self.history.remove_missing(active)
        self.band_history.retain_observed(observed)
        owner_history = (
            self.band_history
            if self.selection.bandwidth == "band.temporal-morphology-envelope-v1"
            else self.history
        )
        candidates, dropped_owner_count = _build_analysis_candidates_and_drops(
            detection,
            self.selection.analysis_window,
            owner_history,  # type: ignore[arg-type]
        )
        owner_ids = {candidate.owner_event_id for candidate in candidates}
        for event in detection.active_events:
            if event.state == "confirmed" and event.observed_this_frame and event.event_id not in owner_ids:
                self.history.discard(event.event_id)
                self.band_history.discard(event.event_id)
        events = {event.event_id: event for event in detection.active_events}
        estimates: list[EventParameterEstimate] = []
        for candidate in candidates:
            event = events[candidate.owner_event_id]
            if candidate.state != "valid":
                assert candidate.invalid_reason is not None
                self.band_history.discard(event.event_id)
                estimates.append(_invalid_event(event, frame_index, candidate.invalid_reason))
            else:
                estimates.append(self._event(frame, spectrum, event, candidate, frame_index))
        return ParameterFrameResult(
            frame_index,
            tuple(estimates),
            R2_PARAMETER_HISTORY_BYTES
            if self.selection.bandwidth == "band.temporal-morphology-envelope-v1"
            else FEATURE_HISTORY_BYTES,
            TRANSIENT_GUARD,
            FEATURE_SAMPLES,
            analysis_candidates=candidates,
            dropped_owner_candidate_count=dropped_owner_count,
        )

    def _event(
        self,
        samples: np.ndarray,
        spectrum: SpectrumResult,
        event: DetectionEvent,
        candidate: AnalysisCandidate,
        frame_index: int,
    ) -> EventParameterEstimate:
        psd = spectrum.display.psd_fs2_per_hz
        noise = _noise_density(psd, candidate, self.selection.noise)
        support = estimate_band_support(
            psd,
            candidate.search_start_bin,
            candidate.search_end_bin,
            candidate.peak_bin,
            noise,
            self.selection.bandwidth,
            candidate.constituent_regions,
        )
        if support.state != "valid":
            assert support.invalid_reason is not None
            self.band_history.discard(event.event_id)
            return _invalid_event(event, frame_index, support.invalid_reason)
        assert support.lower_shifted_bin is not None and support.upper_shifted_bin is not None
        lo, hi = support.lower_shifted_bin, support.upper_shifted_bin
        lower_edge = float(lo)
        upper_edge = float(hi + 1)
        temporal_ready = True
        if self.selection.bandwidth == "band.temporal-morphology-envelope-v1":
            assert support.lower_shifted_edge is not None and support.upper_shifted_edge is not None
            lower_history, upper_history, noise_history = self.band_history.append(
                event.event_id,
                frame_index,
                support.lower_shifted_edge,
                support.upper_shifted_edge,
                noise,
                supported=True,
            )
            temporal_ready = lower_history.size >= 2
            lower_edge = float(np.median(lower_history))
            upper_edge = float(np.median(upper_history))
            noise = float(np.median(noise_history))
            temporal_lo = int(math.ceil(lower_edge))
            temporal_hi = int(math.floor(upper_edge))
            if temporal_lo <= temporal_hi:
                lo = max(candidate.search_start_bin, temporal_lo)
                hi = min(candidate.search_end_bin, temporal_hi)
        center_bin = _spectral_center(psd, lo, hi, noise, self.selection.spectral_center)
        carrier_bin = _carrier_bin(samples, psd, lo, hi, noise, center_bin, spectrum.sample_rate_hz, self.selection.carrier)
        df = spectrum.bin_spacing_hz
        lower_frequency = spectrum.center_frequency_hz + (lower_edge - FRAME_LENGTH / 2.0) * df
        upper_frequency = spectrum.center_frequency_hz + (upper_edge - FRAME_LENGTH / 2.0) * df
        bandwidth_hz = (upper_edge - lower_edge) * df
        center_frequency = spectrum.center_frequency_hz + (center_bin - FRAME_LENGTH / 2.0) * df
        carrier_frequency = None if carrier_bin is None else spectrum.center_frequency_hz + (carrier_bin - FRAME_LENGTH / 2.0) * df
        total = float(np.sum(psd[lo : hi + 1]) * df)
        noise_total = float(noise * (hi - lo + 1) * df)
        signal = total - noise_total
        if signal <= 0.0 or noise_total <= 0.0:
            power = RelativePowerEstimate(None, None, noise_total if noise_total > 0.0 else None, None, "insufficient_quality", "insufficient_quality")
            domain = SignalDomainEstimate("Belirsiz", "uncertain", 0)
        else:
            snr_db = 10.0 * math.log10(signal / noise_total)
            power = RelativePowerEstimate(signal, 10.0 * math.log10(signal), noise_total, snr_db, "valid", "valid")
            features = extract_frame_features(
                samples,
                lower_bin=lo,
                upper_bin=hi,
                center_bin=center_bin,
                sample_rate_hz=spectrum.sample_rate_hz,
                frame_index=frame_index,
                snr_db=snr_db,
            )
            history = self.history.append(event.event_id, frame_index, features)
            domain = classify_features(self.selection.signal_domain, history)
        if not temporal_ready:
            return _invalid_event(event, frame_index, "temporal_warmup")
        return EventParameterEstimate(
            event.event_id,
            frame_index,
            FrequencyEstimate(center_frequency, "valid", carrier_frequency, "valid" if carrier_frequency is not None else "not_observed"),
            BandwidthEstimate(
                lower_frequency,
                "valid",
                upper_frequency,
                "valid",
                bandwidth_hz,
                "valid",
                lo,
                hi,
                None,
                lower_edge,
                upper_edge,
            ),
            power,
            domain,
        )
