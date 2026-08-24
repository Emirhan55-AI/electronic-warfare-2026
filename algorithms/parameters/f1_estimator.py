"""Field-independent, bounded PHASE-04-F1 parameter estimator."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from algorithms.spectrum import SpectrumResult

from .f1_domain import classify_domain, extract_domain_vector
from .models import FieldState
from .operator_assisted import AnalysisSpan, FieldMeasurement, MeasurementIntent


@dataclass(frozen=True)
class F1Quality:
    state: FieldState
    reasons: tuple[str, ...]
    observed_frames: int
    reference_difference_db: float | None
    detection_significance: float | None
    center_uncertainty_bins: float | None
    temporal_edge_range_bins: float | None


@dataclass(frozen=True)
class F1ParameterResult:
    intent: MeasurementIntent
    emission_center_frequency: FieldMeasurement
    carrier_line_frequency: FieldMeasurement
    lower_band_edge: FieldMeasurement
    upper_band_edge: FieldMeasurement
    occupied_bandwidth: FieldMeasurement
    channel_power_dbfs: FieldMeasurement
    snr_estimate_db: FieldMeasurement
    signal_domain: FieldMeasurement
    quality: F1Quality
    persistent_payload_bytes: int = 34_084


def _fractional_edge(power: np.ndarray, offset: int, fraction: float) -> float:
    cumulative = np.cumsum(power)
    target = float(cumulative[-1]) * fraction
    index = min(int(np.searchsorted(cumulative, target, side="left")), power.size - 1)
    before = 0.0 if index == 0 else float(cumulative[index - 1])
    cell = max(float(power[index]), np.finfo(float).tiny)
    return float(offset + index - 0.5 + (target - before) / cell)


def _invalid(
    intent: MeasurementIntent,
    state: FieldState,
    reason: str,
    observed: int,
    *,
    reference_difference_db: float | None = None,
    detection_significance: float | None = None,
) -> F1ParameterResult:
    numeric = FieldMeasurement(state, reason=reason)
    carrier = FieldMeasurement("not_observed", reason=reason)
    domain = FieldMeasurement("uncertain", "Belirsiz", reason=reason)
    return F1ParameterResult(
        intent, numeric, carrier, numeric, numeric, numeric, numeric, numeric, domain,
        F1Quality(state, (reason,), observed, reference_difference_db, detection_significance, None, None),
    )


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
    owner = next((item for item in context.candidates if item.event_id == intent.event_id), None)
    if owner is None or not owner.confirmed or owner.event_revision != intent.event_revision:
        return "event_ownership_lost"
    if len(context.owner_observed_frames) != 4 or not all(context.owner_observed_frames):
        return "event_ownership_lost"
    guarded_lower = intent.span.lower_shifted_bin - 4
    guarded_upper = intent.span.upper_shifted_bin + 4
    for candidate in context.candidates:
        if candidate.event_id == intent.event_id or not candidate.confirmed:
            continue
        if candidate.lower_shifted_bin <= guarded_upper and candidate.upper_shifted_bin >= guarded_lower:
            return "neighbor_overlap"
    return None


class F1ParameterEstimator:
    """Measure one confirmed event over exactly four bounded frames."""

    METHOD_IDS = {
        "emission_center_frequency": "frequency.excess-centroid-shrink-v2",
        "carrier_line_frequency": "frequency.carrier-prominence-share-v2",
        "occupied_bandwidth": "band.debiased-obw99-shrink-v2",
        "uncalibrated_channel_power_dbfs": "power.signed-excess-integral-v2",
        "snr_estimate_db": "snr.spectral-rms-calibrated-v1",
        "signal_domain": "domain.fixed-development-centroid-v1",
    }
    DETECTION_SIGNIFICANCE_MINIMUM = 12.0
    CENTER_UNCERTAINTY_BINS_MAXIMUM = 4.0
    CENTER_SHRINK_SIGMA = 1.0
    BROAD_SPAN_MINIMUM_BINS = 100
    OBW_SHRINK_SIGMA = 2.5
    CARRIER_PROMINENCE_DB_MINIMUM = 5.0
    CARRIER_SHARE_MINIMUM = 0.21

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ) -> F1ParameterResult:
        context_reason = _context_reason(intent)
        if context_reason is not None:
            state: FieldState = "uncertain" if context_reason == "neighbor_overlap" else "insufficient_quality"
            return _invalid(intent, state, context_reason, 0)
        if len(samples) != 4 or len(spectra) != 4:
            return _invalid(intent, "insufficient_quality", "four_consecutive_frames_required", len(spectra))
        if any(item.frame_length != 4096 for item in spectra):
            return _invalid(intent, "insufficient_quality", "frame_length_mismatch", len(spectra))
        if any(not np.all(np.isfinite(np.asarray(frame))) for frame in samples):
            return _invalid(intent, "insufficient_quality", "nonfinite_iq", 4)

        lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
        left_start, left_end = lower - 36, lower - 5
        right_start, right_end = upper + 5, upper + 36
        if left_start < 20 or right_end > 4075:
            return _invalid(intent, "insufficient_quality", "reference_cells_unavailable", 4)
        psd_frames = np.stack([np.asarray(item.display.psd_fs2_per_hz) for item in spectra])
        if not np.all(np.isfinite(psd_frames)):
            return _invalid(intent, "insufficient_quality", "nonfinite_psd", 4)
        averaged = np.mean(psd_frames, axis=0)
        left_noise = float(np.mean(averaged[left_start : left_end + 1]))
        right_noise = float(np.mean(averaged[right_start : right_end + 1]))
        if min(left_noise, right_noise) <= 0.0:
            return _invalid(intent, "insufficient_quality", "invalid_reference_power", 4)
        reference_difference = abs(10.0 * math.log10(left_noise / right_noise))
        if reference_difference > 3.0:
            return _invalid(intent, "uncertain", "reference_power_mismatch", 4)
        noise = 0.5 * (left_noise + right_noise)
        span_psd = averaged[lower : upper + 1]
        signed_excess = span_psd - noise
        total = float(np.sum(signed_excess))
        significance = total / max(noise * math.sqrt(span_psd.size / 4.0), np.finfo(float).tiny)
        if not math.isfinite(total) or total <= 0.0 or significance < self.DETECTION_SIGNIFICANCE_MINIMUM:
            return _invalid(
                intent,
                "insufficient_quality",
                "insufficient_excess_power",
                4,
                reference_difference_db=reference_difference,
                detection_significance=significance,
            )

        indices = np.arange(lower, upper + 1, dtype=np.float64)
        smoothing_kernel = np.asarray([0.25, 0.5, 0.25], dtype=np.float64)
        smoothed_noise_sigma = noise * 0.5 * math.sqrt(float(np.sum(smoothing_kernel**2)))
        center_weights = np.maximum(
            np.convolve(signed_excess, smoothing_kernel, mode="same")
            - self.CENTER_SHRINK_SIGMA * smoothed_noise_sigma,
            0.0,
        )
        center_weight_total = float(np.sum(center_weights))
        raw_emission_bin = float(np.sum(indices * center_weights) / center_weight_total)
        leave_one_out_centers: list[float] = []
        for omitted in range(4):
            subset = np.mean(np.delete(psd_frames, omitted, axis=0), axis=0)
            subset_noise = 0.5 * (
                float(np.mean(subset[left_start : left_end + 1]))
                + float(np.mean(subset[right_start : right_end + 1]))
            )
            subset_excess = subset[lower : upper + 1] - subset_noise
            subset_total = float(np.sum(subset_excess))
            if subset_total <= 0.0:
                leave_one_out_centers = []
                break
            leave_one_out_centers.append(float(np.sum(indices * subset_excess) / subset_total))
        center_uncertainty = None
        if leave_one_out_centers:
            center_mean = float(np.mean(leave_one_out_centers))
            center_uncertainty = math.sqrt(
                0.75 * sum((value - center_mean) ** 2 for value in leave_one_out_centers)
            )
        emission_bin = raw_emission_bin
        bin_spacing = spectra[0].bin_spacing_hz
        center_frequency = spectra[0].center_frequency_hz
        bin_to_hz = lambda value: center_frequency + (value - 2048.0) * bin_spacing
        emission_state: FieldState = "valid" if center_uncertainty is not None and center_uncertainty <= self.CENTER_UNCERTAINTY_BINS_MAXIMUM else "insufficient_quality"
        smoothed_excess = np.convolve(signed_excess, smoothing_kernel, mode="same")
        obw_weights = np.maximum(smoothed_excess - self.OBW_SHRINK_SIGMA * smoothed_noise_sigma, 0.0)
        obw_total = float(np.sum(obw_weights))
        lower_edge = _fractional_edge(obw_weights, lower, 0.005)
        upper_edge = _fractional_edge(obw_weights, lower, 0.995)
        if intent.span.width_bins >= self.BROAD_SPAN_MINIMUM_BINS:
            rectangular_ffts = [
                np.fft.fftshift(np.fft.fft(np.asarray(frame, dtype=np.complex128)))
                for frame in samples
            ]
            averaged_rectangular_power = np.mean(
                np.stack([np.abs(item) ** 2 for item in rectangular_ffts]), axis=0
            )
            rectangular_noise = 0.5 * (
                float(np.mean(averaged_rectangular_power[left_start : left_end + 1]))
                + float(np.mean(averaged_rectangular_power[right_start : right_end + 1]))
            )
            supported = np.flatnonzero(
                averaged_rectangular_power[lower : upper + 1] >= 6.0 * rectangular_noise
            )
            if supported.size:
                support_lower = lower + int(supported[0])
                support_upper = lower + int(supported[-1])
            else:
                support_lower = max(lower, int(math.ceil(lower_edge + 0.5)))
                support_upper = min(upper, int(math.floor(upper_edge - 0.5)))
            window_index = np.arange(4096, dtype=np.float64)
            hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * window_index / 4096.0)
            reconstructed_power: list[np.ndarray] = []
            for shifted_fft in rectangular_ffts:
                rectangular_power = np.abs(shifted_fft) ** 2
                frame_rectangular_noise = 0.5 * (
                    float(np.mean(rectangular_power[left_start : left_end + 1]))
                    + float(np.mean(rectangular_power[right_start : right_end + 1]))
                )
                selected = shifted_fft[support_lower : support_upper + 1]
                selected_power = np.abs(selected) ** 2
                signal_amplitude = math.sqrt(max(float(np.mean(selected_power)) - frame_rectangular_noise, 0.0))
                denoised = np.zeros(4096, dtype=np.complex128)
                denoised[support_lower : support_upper + 1] = (
                    signal_amplitude * selected / np.maximum(np.abs(selected), np.finfo(float).tiny)
                )
                reconstructed = np.fft.ifft(np.fft.ifftshift(denoised))
                reconstructed_power.append(np.abs(np.fft.fftshift(np.fft.fft(reconstructed * hann))) ** 2)
            broad_power = np.mean(np.stack(reconstructed_power), axis=0)[lower : upper + 1]
            broad_total = float(np.sum(broad_power))
            emission_bin = float(np.sum(indices * broad_power) / broad_total)
        emission = FieldMeasurement(
            emission_state,
            bin_to_hz(emission_bin) if emission_state == "valid" else None,
            "Hz" if emission_state == "valid" else None,
            None if emission_state == "valid" else "center_temporal_uncertainty",
        )
        clipping = lower_edge <= lower + 0.5 or upper_edge >= upper - 0.5
        temporal_edges: list[tuple[float, float]] = []
        for omitted in range(4):
            subset = np.mean(np.delete(psd_frames, omitted, axis=0), axis=0)
            subset_noise = 0.5 * (
                float(np.mean(subset[left_start : left_end + 1]))
                + float(np.mean(subset[right_start : right_end + 1]))
            )
            subset_excess = np.convolve(subset[lower : upper + 1] - subset_noise, smoothing_kernel, mode="same")
            subset_noise_sigma = subset_noise / math.sqrt(3.0) * math.sqrt(float(np.sum(smoothing_kernel**2)))
            weights = np.maximum(subset_excess - self.OBW_SHRINK_SIGMA * subset_noise_sigma, 0.0)
            if float(np.sum(weights)) <= 0.0:
                temporal_edges = []
                break
            temporal_edges.append((_fractional_edge(weights, lower, 0.005), _fractional_edge(weights, lower, 0.995)))
        temporal_range = None
        if temporal_edges:
            temporal_range = max(
                float(np.median([abs(item[0] - lower_edge) for item in temporal_edges])),
                float(np.median([abs(item[1] - upper_edge) for item in temporal_edges])),
            )
        if clipping:
            edge_state: FieldState = "uncertain"
            edge_reason = "span_edge_clipping"
        elif temporal_range is None or temporal_range > 2.0:
            edge_state = "uncertain"
            edge_reason = "obw_temporal_instability"
        else:
            edge_state = "valid"
            edge_reason = None
        lower_field = FieldMeasurement(edge_state, bin_to_hz(lower_edge) if edge_state == "valid" else None, "Hz" if edge_state == "valid" else None, edge_reason)
        upper_field = FieldMeasurement(edge_state, bin_to_hz(upper_edge) if edge_state == "valid" else None, "Hz" if edge_state == "valid" else None, edge_reason)
        bandwidth = FieldMeasurement(edge_state, (upper_edge - lower_edge) * bin_spacing if edge_state == "valid" else None, "Hz" if edge_state == "valid" else None, edge_reason)

        channel_power = total * bin_spacing
        channel_dbfs = 10.0 * math.log10(max(channel_power, np.finfo(float).tiny))
        channel = FieldMeasurement("valid", channel_dbfs, "dBFS")

        positive = np.maximum(signed_excess, 0.0)
        positive_total = float(np.sum(positive))
        positive_center = float(np.sum(indices * positive) / positive_total)
        spectral_std = math.sqrt(float(np.sum(((indices - positive_center) ** 2) * positive) / positive_total))
        equivalent_width = max(4.0 * spectral_std, 1.0)
        raw_snr = 10.0 * math.log10(max(total / (noise * equivalent_width), np.finfo(float).tiny))
        snr_db = 0.8 * raw_snr + 1.6
        snr = FieldMeasurement("valid", snr_db, "dB")

        average_bin_power = np.mean(np.stack([item.display.bin_power_fs2 for item in spectra]), axis=0)
        peak = int(np.clip(round(emission_bin), lower + 1, upper - 1))
        background_values = np.concatenate((average_bin_power[max(lower, peak - 8) : max(lower, peak - 2)], average_bin_power[min(upper + 1, peak + 3) : min(upper + 1, peak + 9)]))
        background = float(np.median(background_values)) if background_values.size else noise * bin_spacing
        prominence = 10.0 * math.log10(float(average_bin_power[peak]) / max(background, np.finfo(float).tiny))
        local = average_bin_power[peak - 1 : peak + 2]
        line_share = float(np.sum(np.maximum(local - noise * bin_spacing, 0.0)) / max(total * bin_spacing, np.finfo(float).tiny)) if local.size == 3 else 0.0
        carrier = FieldMeasurement("not_observed", reason="carrier_line_absent")
        if local.size == 3 and prominence >= self.CARRIER_PROMINENCE_DB_MINIMUM and line_share >= self.CARRIER_SHARE_MINIMUM:
            logs = np.log(np.maximum(local, np.finfo(float).tiny))
            denominator = logs[0] - 2.0 * logs[1] + logs[2]
            delta = float(np.clip(0.5 * (logs[0] - logs[2]) / denominator, -0.5, 0.5)) if abs(denominator) > 1e-15 else 0.0
            carrier = FieldMeasurement("valid", bin_to_hz(peak + delta), "Hz")

        domain_decision = classify_domain(extract_domain_vector(samples, lower, upper), snr_db=snr_db)
        domain = FieldMeasurement(domain_decision.state, domain_decision.value, reason=domain_decision.reason)
        quality = F1Quality("valid", (), 4, reference_difference, significance, center_uncertainty, temporal_range)
        return F1ParameterResult(intent, emission, carrier, lower_field, upper_field, bandwidth, channel, snr, domain, quality)
