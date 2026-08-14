"""Qt-independent operator-assisted PHASE-04-E1 measurement reference."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from reference.detection import DetectionEvent
from reference.spectrum import SpectrumResult

from .models import FieldState
from .operator_classification import classify_domain, extract_domain_features


SpanProvenance = Literal["auto_suggested", "operator_adjusted"]
E1Field = Literal[
    "emission_center_frequency",
    "carrier_line_frequency",
    "occupied_bandwidth",
    "uncalibrated_power_dbfs",
    "signal_domain",
]


@dataclass(frozen=True)
class MeasurementCandidate:
    """One confirmed candidate identity supplied by orchestration, never ground truth."""

    event_id: int
    event_revision: int
    lower_shifted_bin: int
    upper_shifted_bin: int
    confirmed: bool = True


@dataclass(frozen=True)
class MeasurementContext:
    """Owner, generation and four-frame observation contract for one measurement."""

    source_generation: int
    pipeline_generation: int
    configuration_generation: int
    owner_event_id: int
    owner_event_revision: int
    owner_observed_frames: tuple[bool, bool, bool, bool]
    candidates: tuple[MeasurementCandidate, ...]


@dataclass(frozen=True)
class AnalysisSpan:
    lower_shifted_bin: int
    upper_shifted_bin: int
    provenance: SpanProvenance
    revision: int = 0

    @property
    def width_bins(self) -> int:
        return self.upper_shifted_bin - self.lower_shifted_bin + 1

    def __post_init__(self) -> None:
        if not 20 <= self.lower_shifted_bin <= self.upper_shifted_bin <= 4075:
            raise ValueError("analysis span is outside the usable shifted FFT range")
        if not 8 <= self.width_bins <= 512:
            raise ValueError("analysis span width must be in [8, 512]")


@dataclass(frozen=True)
class MeasurementIntent:
    source_generation: int
    pipeline_generation: int
    configuration_generation: int
    event_id: int
    event_revision: int
    start_frame: int
    span: AnalysisSpan
    context: MeasurementContext | None = None

    @property
    def generation_key(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.source_generation,
            self.pipeline_generation,
            self.configuration_generation,
            self.event_id,
            self.event_revision,
            self.span.revision,
        )


@dataclass(frozen=True)
class FieldMeasurement:
    state: FieldState
    value: float | str | None = None
    unit: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class MeasurementQuality:
    state: FieldState
    reasons: tuple[str, ...]
    reference_difference_db: float | None
    integrated_snr_db: float | None
    observed_frames: int
    edge_share_left: float | None
    edge_share_right: float | None
    temporal_edge_range_bins: float | None = None


@dataclass(frozen=True)
class OperatorAssistedParameterResult:
    intent: MeasurementIntent
    emission_center_frequency: FieldMeasurement
    carrier_line_frequency: FieldMeasurement
    lower_band_edge: FieldMeasurement
    upper_band_edge: FieldMeasurement
    occupied_bandwidth: FieldMeasurement
    peak_power_dbfs_per_bin: FieldMeasurement
    channel_power_dbfs: FieldMeasurement
    signal_domain: FieldMeasurement
    quality: MeasurementQuality
    persistent_payload_bytes: int = 34_084


def project_to_simplex(values: np.ndarray, total: float) -> np.ndarray:
    """Project a finite vector onto {x >= 0, sum(x) == total}."""
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or not np.all(np.isfinite(vector)):
        raise ValueError("simplex input must be a finite vector")
    if not math.isfinite(total) or total < 0.0:
        raise ValueError("simplex total must be finite and non-negative")
    if total == 0.0:
        return np.zeros_like(vector)
    ordered = np.sort(vector)[::-1]
    cssv = np.cumsum(ordered) - total
    indices = np.arange(1, vector.size + 1, dtype=np.float64)
    positive = ordered - cssv / indices > 0.0
    rho = int(np.flatnonzero(positive)[-1])
    theta = float(cssv[rho] / (rho + 1))
    projected = np.maximum(vector - theta, 0.0)
    correction = total - float(np.sum(projected))
    if abs(correction) > 0.0:
        projected[int(np.argmax(projected))] += correction
    projected[np.abs(projected) < np.finfo(np.float64).eps * max(total, 1.0)] = 0.0
    return projected


def suggest_analysis_span(event: DetectionEvent, others: tuple[DetectionEvent, ...], *, revision: int = 0) -> AnalysisSpan | None:
    if event.state != "confirmed" or not event.observed_this_frame:
        return None
    width = event.region.end_bin - event.region.start_bin + 1
    margin = min(64, max(8, math.ceil(width / 2.0)))
    lower = max(20, event.region.start_bin - margin)
    upper = min(4075, event.region.end_bin + margin)
    for other in others:
        if other.event_id == event.event_id or not other.observed_this_frame:
            continue
        midpoint = 0.5 * (event.region.peak_bin + other.region.peak_bin)
        if other.region.peak_bin < event.region.peak_bin:
            lower = max(lower, int(math.ceil(midpoint)) + 4)
        else:
            upper = min(upper, int(math.floor(midpoint)) - 4)
    if upper - lower + 1 < 8:
        return None
    return AnalysisSpan(lower, upper, "auto_suggested", revision)


def _fractional_edge(power: np.ndarray, offset: int, fraction: float) -> float:
    total = float(np.sum(power))
    target = total * fraction
    cumulative = np.cumsum(power)
    index = min(int(np.searchsorted(cumulative, target, side="left")), power.size - 1)
    before = 0.0 if index == 0 else float(cumulative[index - 1])
    cell = max(float(power[index]), np.finfo(np.float64).tiny)
    return float(offset + index - 0.5 + (target - before) / cell)


def _invalid(intent: MeasurementIntent, state: FieldState, reason: str, *, observed: int) -> OperatorAssistedParameterResult:
    field = FieldMeasurement(state=state, reason=reason)
    return OperatorAssistedParameterResult(
        intent, field, FieldMeasurement("not_observed", reason=reason), field, field, field, field, field,
        FieldMeasurement("uncertain", value="Belirsiz", reason=reason),
        MeasurementQuality(state, (reason,), None, None, observed, None, None),
    )


def _field(state: FieldState, reason: str) -> FieldMeasurement:
    return FieldMeasurement(state=state, reason=reason)


def _context_reason(intent: MeasurementIntent) -> str | None:
    context = intent.context
    if context is None:
        return "event_ownership_lost"
    if (
        context.source_generation != intent.source_generation
        or context.pipeline_generation != intent.pipeline_generation
        or context.configuration_generation != intent.configuration_generation
    ):
        return "stale_generation"
    if context.owner_event_id != intent.event_id or context.owner_event_revision != intent.event_revision:
        return "event_ownership_lost"
    owner = next(
        (
            item
            for item in context.candidates
            if item.event_id == intent.event_id and item.event_revision == intent.event_revision and item.confirmed
        ),
        None,
    )
    if owner is None or len(context.owner_observed_frames) != 4 or not all(context.owner_observed_frames):
        return "event_ownership_lost"
    guarded_lower = intent.span.lower_shifted_bin - 4
    guarded_upper = intent.span.upper_shifted_bin + 4
    for candidate in context.candidates:
        if candidate.event_id == intent.event_id or not candidate.confirmed:
            continue
        if candidate.lower_shifted_bin <= guarded_upper and candidate.upper_shifted_bin >= guarded_lower:
            return "neighbor_overlap"
    return None


class OperatorMeasurementProcessor:
    """Measure one explicitly approved span over four bounded consecutive frames."""

    METHOD_IDS = {
        "emission_center_frequency": "frequency.emission-center-v1",
        "carrier_line_frequency": "frequency.carrier-line-parabolic-v1",
        "occupied_bandwidth": "band.operator-span-debiased-obw99-v1",
        "uncalibrated_power_dbfs": "power.operator-span-psd-v1",
        "signal_domain": "domain.operator-span-rules-v1",
    }

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ) -> OperatorAssistedParameterResult:
        context_reason = _context_reason(intent)
        if context_reason is not None:
            state: FieldState = "uncertain" if context_reason == "neighbor_overlap" else "insufficient_quality"
            return _invalid(intent, state, context_reason, observed=0)
        if len(samples) != 4 or len(spectra) != 4:
            return _invalid(intent, "insufficient_quality", "four_consecutive_frames_required", observed=len(spectra))
        if any(item.frame_length != 4096 for item in spectra):
            return _invalid(intent, "insufficient_quality", "frame_length_mismatch", observed=len(spectra))
        if any(not np.all(np.isfinite(np.asarray(frame))) for frame in samples):
            return _invalid(intent, "insufficient_quality", "nonfinite_iq", observed=4)
        lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
        left_start, left_end = lower - 36, lower - 5
        right_start, right_end = upper + 5, upper + 36
        if left_start < 20 or right_end > 4075:
            return _invalid(intent, "insufficient_quality", "reference_cells_unavailable", observed=4)
        psd_frames = np.stack([np.asarray(item.display.psd_fs2_per_hz, dtype=np.float64) for item in spectra])
        if not np.all(np.isfinite(psd_frames)):
            return _invalid(intent, "insufficient_quality", "nonfinite_psd", observed=4)
        averaged = np.mean(psd_frames, axis=0)
        left = averaged[left_start : left_end + 1]
        right = averaged[right_start : right_end + 1]
        left_noise, right_noise = float(np.mean(left)), float(np.mean(right))
        if min(left_noise, right_noise) <= 0.0:
            return _invalid(intent, "insufficient_quality", "invalid_reference_power", observed=4)
        reference_difference = abs(10.0 * math.log10(left_noise / right_noise))
        if reference_difference > 3.0:
            return _invalid(intent, "uncertain", "reference_power_mismatch", observed=4)
        noise = 0.5 * (left_noise + right_noise)
        span_psd = averaged[lower : upper + 1]
        debiased = span_psd - noise
        total = float(np.sum(debiased))
        noise_total = noise * debiased.size
        snr_db = 10.0 * math.log10(total / noise_total) if total > 0.0 and noise_total > 0.0 else -math.inf
        if not math.isfinite(total) or total <= 0.0 or snr_db < 6.0:
            return _invalid(intent, "insufficient_quality", "insufficient_excess_power", observed=4)
        projected = project_to_simplex(debiased, total)
        bin_spacing = spectra[0].bin_spacing_hz
        center_frequency = spectra[0].center_frequency_hz
        bin_to_hz = lambda value: center_frequency + (value - 2048.0) * bin_spacing

        # The common contract ends here. Every following gate owns only its field.
        emission = _field("insufficient_quality", "center_not_finite")
        emission_bin = float(np.sum((np.arange(projected.size) + lower) * projected) / total)
        if math.isfinite(emission_bin) and lower <= emission_bin <= upper:
            emission = FieldMeasurement("valid", bin_to_hz(emission_bin), "Hz")

        average_bin_power = np.mean(np.stack([item.display.bin_power_fs2 for item in spectra]), axis=0)
        carrier = FieldMeasurement("not_observed", reason="carrier_line_absent")
        local_peak = int(np.argmax(average_bin_power[lower : upper + 1])) + lower
        local = average_bin_power[local_peak - 1 : local_peak + 2]
        if local.size == 3 and np.all(local > 0.0):
            logs = np.log(local)
            denominator = logs[0] - 2.0 * logs[1] + logs[2]
            delta = float(np.clip(0.5 * (logs[0] - logs[2]) / denominator, -0.5, 0.5)) if abs(denominator) > 1e-15 else 0.0
            peak_to_noise = 10.0 * math.log10(float(average_bin_power[local_peak]) / max(noise * bin_spacing, np.finfo(float).tiny))
            line_share = float(np.sum(np.maximum(local - noise * bin_spacing, 0.0)) / max(total * bin_spacing, np.finfo(float).tiny))
            frame_peaks = [int(np.argmax(item.display.bin_power_fs2[lower : upper + 1])) + lower for item in spectra]
            if peak_to_noise >= 10.0 and line_share >= 0.35 and max(frame_peaks) - min(frame_peaks) <= 1:
                carrier = FieldMeasurement("valid", bin_to_hz(local_peak + delta), "Hz")

        peak_dbfs = 10.0 * math.log10(max(float(np.max(average_bin_power[lower : upper + 1])), np.finfo(float).tiny))
        channel_power = total * bin_spacing
        channel_dbfs = 10.0 * math.log10(max(channel_power, np.finfo(float).tiny))
        peak_power = FieldMeasurement("valid", peak_dbfs, "dBFS/bin")
        channel_field = FieldMeasurement("valid", channel_dbfs, "dBFS")

        features = tuple(extract_domain_features(np.asarray(frame), lower, upper) for frame in samples)
        domain, _confidence, reasons = classify_domain(features, snr_db=snr_db)
        domain_state: FieldState = "valid" if domain in {"Analog", "Sayısal"} else "uncertain"
        domain_field = FieldMeasurement(domain_state, domain, None, ",".join(reasons) if reasons else ("classification_ambiguous" if domain_state != "valid" else None))

        # OBW-only edge, per-frame edge and temporal stability gates.
        left_share = float(np.sum(projected[:4]) / total)
        right_share = float(np.sum(projected[-4:]) / total)
        lower_field = _field("uncertain", "span_edge_clipping")
        upper_field = _field("uncertain", "span_edge_clipping")
        bandwidth_field = _field("uncertain", "span_edge_clipping")
        temporal_edge_range: float | None = None
        if left_share > 0.005 or right_share > 0.005:
            obw_reason = "span_edge_clipping"
        else:
            frame_edges: list[tuple[float, float]] = []
            obw_reason = None
            for frame_psd in psd_frames:
                frame_delta = frame_psd[lower : upper + 1] - noise
                frame_total = float(np.sum(frame_delta))
                if frame_total <= 0.0:
                    obw_reason = "temporal_excess_missing"
                    break
                frame_projected = project_to_simplex(frame_delta, frame_total)
                frame_edges.append((_fractional_edge(frame_projected, lower, 0.005), _fractional_edge(frame_projected, lower, 0.995)))
            if obw_reason is None:
                lower_edges = np.asarray([item[0] for item in frame_edges])
                upper_edges = np.asarray([item[1] for item in frame_edges])
                temporal_edge_range = max(float(np.ptp(lower_edges)), float(np.ptp(upper_edges)))
                if temporal_edge_range > 2.0:
                    obw_reason = "obw_temporal_instability"
            if obw_reason is None:
                lower_edge = _fractional_edge(projected, lower, 0.005)
                upper_edge = _fractional_edge(projected, lower, 0.995)
                lower_field = FieldMeasurement("valid", bin_to_hz(lower_edge), "Hz")
                upper_field = FieldMeasurement("valid", bin_to_hz(upper_edge), "Hz")
                bandwidth_field = FieldMeasurement("valid", (upper_edge - lower_edge) * bin_spacing, "Hz")
            else:
                obw_state: FieldState = "insufficient_quality" if obw_reason == "temporal_excess_missing" else "uncertain"
                lower_field = _field(obw_state, obw_reason)
                upper_field = _field(obw_state, obw_reason)
                bandwidth_field = _field(obw_state, obw_reason)

        quality = MeasurementQuality(
            "valid", (), reference_difference, snr_db, 4, left_share, right_share, temporal_edge_range
        )
        return OperatorAssistedParameterResult(
            intent=intent,
            emission_center_frequency=emission,
            carrier_line_frequency=carrier,
            lower_band_edge=lower_field,
            upper_band_edge=upper_field,
            occupied_bandwidth=bandwidth_field,
            peak_power_dbfs_per_bin=peak_power,
            channel_power_dbfs=channel_field,
            signal_domain=domain_field,
            quality=quality,
        )
