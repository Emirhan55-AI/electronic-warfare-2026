"""PHASE-04-F2 parameter estimator with bounded v3 recovery changes."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from algorithms.spectrum import SpectrumResult

from .f1_estimator import F1ParameterEstimator, F1ParameterResult, _fractional_edge, _invalid
from .f2_domain import classify_domain_v3, extract_domain_vector_v3
from .models import FieldState
from .operator_assisted import FieldMeasurement, MeasurementIntent


PERSISTENT_PAYLOAD_BYTES = 50_788


def _corrected_detection_significance(
    intent: MeasurementIntent,
    spectra: tuple[SpectrumResult, ...],
) -> tuple[float, float] | None:
    """Return reference disagreement and excess-power z score including reference uncertainty."""
    if len(spectra) != 4 or any(item.frame_length != 4096 for item in spectra):
        return None
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    left_start, left_end = lower - 36, lower - 5
    right_start, right_end = upper + 5, upper + 36
    if left_start < 20 or right_end > 4075:
        return None
    psd_frames = np.stack([np.asarray(item.display.psd_fs2_per_hz) for item in spectra])
    if not np.all(np.isfinite(psd_frames)):
        return None
    averaged = np.mean(psd_frames, axis=0)
    left_noise = float(np.mean(averaged[left_start : left_end + 1]))
    right_noise = float(np.mean(averaged[right_start : right_end + 1]))
    if min(left_noise, right_noise) <= 0.0:
        return None
    reference_difference = abs(10.0 * math.log10(left_noise / right_noise))
    noise = 0.5 * (left_noise + right_noise)
    span = averaged[lower : upper + 1]
    total = float(np.sum(span - noise))
    span_cells = span.size
    reference_cells = (left_end - left_start + 1) + (right_end - right_start + 1)
    variance_cells = span_cells / 4.0 + span_cells**2 / (4.0 * reference_cells)
    standard_error = noise * math.sqrt(variance_cells)
    significance = total / max(standard_error, np.finfo(float).tiny)
    return reference_difference, significance


def carrier_evidence(
    intent: MeasurementIntent,
    spectra: tuple[SpectrumResult, ...],
    emission_frequency_hz: float,
) -> tuple[float, float, float] | None:
    """Return average prominence, excess-power share, and minimum frame prominence."""
    if len(spectra) != 4:
        return None
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    left_start, left_end = lower - 36, lower - 5
    right_start, right_end = upper + 5, upper + 36
    average_psd = np.mean(np.stack([item.display.psd_fs2_per_hz for item in spectra]), axis=0)
    noise = 0.5 * (
        float(np.mean(average_psd[left_start : left_end + 1]))
        + float(np.mean(average_psd[right_start : right_end + 1]))
    )
    total = float(np.sum(average_psd[lower : upper + 1] - noise))
    average_bin_power = np.mean(np.stack([item.display.bin_power_fs2 for item in spectra]), axis=0)
    spacing = spectra[0].bin_spacing_hz
    emission_bin = (emission_frequency_hz - spectra[0].center_frequency_hz) / spacing + 2048.0
    peak = int(np.clip(round(emission_bin), lower + 1, upper - 1))
    background_values = np.concatenate((
        average_bin_power[max(lower, peak - 8) : max(lower, peak - 2)],
        average_bin_power[min(upper + 1, peak + 3) : min(upper + 1, peak + 9)],
    ))
    if not background_values.size or total <= 0.0:
        return None
    background = float(np.median(background_values))
    prominence = 10.0 * math.log10(float(average_bin_power[peak]) / max(background, np.finfo(float).tiny))
    frame_prominences: list[float] = []
    for item in spectra:
        frame_power = np.asarray(item.display.bin_power_fs2, dtype=np.float64)
        frame_background_values = np.concatenate((
            frame_power[max(lower, peak - 8) : max(lower, peak - 2)],
            frame_power[min(upper + 1, peak + 3) : min(upper + 1, peak + 9)],
        ))
        frame_background = float(np.median(frame_background_values))
        frame_prominences.append(
            10.0 * math.log10(float(frame_power[peak]) / max(frame_background, np.finfo(float).tiny))
        )
    local = average_bin_power[peak - 1 : peak + 2]
    share = float(
        np.sum(np.maximum(local - noise * spacing, 0.0))
        / max(total * spacing, np.finfo(float).tiny)
    )
    return prominence, share, min(frame_prominences)


def _recover_obw(
    result: F1ParameterResult,
    intent: MeasurementIntent,
    spectra: tuple[SpectrumResult, ...],
    maximum_temporal_range_bins: float,
) -> F1ParameterResult:
    if (
        result.occupied_bandwidth.reason != "obw_temporal_instability"
        or result.quality.temporal_edge_range_bins is None
        or result.quality.temporal_edge_range_bins > maximum_temporal_range_bins
    ):
        return result
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    left_start, left_end = lower - 36, lower - 5
    right_start, right_end = upper + 5, upper + 36
    averaged = np.mean(np.stack([item.display.psd_fs2_per_hz for item in spectra]), axis=0)
    noise = 0.5 * (
        float(np.mean(averaged[left_start : left_end + 1]))
        + float(np.mean(averaged[right_start : right_end + 1]))
    )
    kernel = np.asarray([0.25, 0.5, 0.25], dtype=np.float64)
    smoothed_sigma = noise * 0.5 * math.sqrt(float(np.sum(kernel**2)))
    weights = np.maximum(
        np.convolve(averaged[lower : upper + 1] - noise, kernel, mode="same")
        - F1ParameterEstimator.OBW_SHRINK_SIGMA * smoothed_sigma,
        0.0,
    )
    if float(np.sum(weights)) <= 0.0:
        return result
    lower_edge = _fractional_edge(weights, lower, 0.005)
    upper_edge = _fractional_edge(weights, lower, 0.995)
    if lower_edge <= lower + 0.5 or upper_edge >= upper - 0.5:
        return result
    spacing = spectra[0].bin_spacing_hz
    center = spectra[0].center_frequency_hz
    bin_to_hz = lambda value: center + (value - 2048.0) * spacing
    return replace(
        result,
        lower_band_edge=FieldMeasurement("valid", bin_to_hz(lower_edge), "Hz"),
        upper_band_edge=FieldMeasurement("valid", bin_to_hz(upper_edge), "Hz"),
        occupied_bandwidth=FieldMeasurement("valid", (upper_edge - lower_edge) * spacing, "Hz"),
    )


class F2ParameterEstimator(F1ParameterEstimator):
    """Apply the locked F2 recovery method without changing immutable F1 sources."""

    METHOD_IDS = {
        "emission_center_frequency": "frequency.excess-centroid-shrink-v3",
        "carrier_line_frequency": "frequency.carrier-prominence-abstain-v3",
        "occupied_bandwidth": "band.debiased-obw99-temporal-v3",
        "uncalibrated_channel_power_dbfs": "power.reference-uncertainty-gated-v3",
        "snr_estimate_db": "snr.reference-uncertainty-gated-v3",
        "signal_domain": "domain.family-prototype-rejection-v3",
    }
    CORRECTED_DETECTION_SIGNIFICANCE_MINIMUM = 6.0
    LOW_SNR_ABSTENTION_DB = 3.0
    OBW_TEMPORAL_RANGE_MAXIMUM = 3.0
    CARRIER_PROMINENCE_DB_MINIMUM_V3 = 5.25
    CARRIER_SHARE_MINIMUM_V3 = 0.235
    CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V3 = 2.5

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ) -> F1ParameterResult:
        result = super().measure(intent, samples, spectra)
        statistics = _corrected_detection_significance(intent, spectra)
        if statistics is None:
            return replace(result, persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES)
        reference_difference, significance = statistics
        if not math.isfinite(significance) or significance < self.CORRECTED_DETECTION_SIGNIFICANCE_MINIMUM:
            invalid = _invalid(
                intent,
                "insufficient_quality",
                "insufficient_excess_power",
                len(spectra),
                reference_difference_db=reference_difference,
                detection_significance=significance,
            )
            return replace(invalid, persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES)
        result = replace(
            result,
            quality=replace(
                result.quality,
                detection_significance=significance,
                reference_difference_db=reference_difference,
            ),
            persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES,
        )
        if result.snr_estimate_db.state != "valid":
            return result
        snr_db = float(result.snr_estimate_db.value)
        carrier = result.carrier_line_frequency
        if snr_db < self.LOW_SNR_ABSTENTION_DB:
            carrier = FieldMeasurement("not_observed", reason="quality_below_carrier_threshold")
        elif carrier.state == "valid" and result.emission_center_frequency.state == "valid":
            evidence = carrier_evidence(
                intent,
                spectra,
                float(result.emission_center_frequency.value),
            )
            if evidence is None or (
                evidence[0] < self.CARRIER_PROMINENCE_DB_MINIMUM_V3
                or evidence[1] < self.CARRIER_SHARE_MINIMUM_V3
                or evidence[2] < self.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V3
            ):
                carrier = FieldMeasurement("not_observed", reason="carrier_line_below_threshold")
        decision = classify_domain_v3(
            extract_domain_vector_v3(samples, intent.span.lower_shifted_bin, intent.span.upper_shifted_bin),
            snr_db=snr_db,
        )
        domain_state: FieldState = decision.state
        result = replace(
            result,
            carrier_line_frequency=carrier,
            signal_domain=FieldMeasurement(domain_state, decision.value, reason=decision.reason),
        )
        return _recover_obw(result, intent, spectra, self.OBW_TEMPORAL_RANGE_MAXIMUM)
