"""PHASE-04-F5 estimator with calibrated OBW99 tail recovery."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from algorithms.spectrum import SpectrumResult

from .f1_estimator import _fractional_edge
from .f4_estimator import F4ParameterEstimator, PERSISTENT_PAYLOAD_BYTES
from .operator_assisted import FieldMeasurement, MeasurementIntent


def _tail_corrected_obw(
    result,
    intent: MeasurementIntent,
    spectra: tuple[SpectrumResult, ...],
    *,
    tail_fraction: float,
    edge_expansion_bins: float,
    maximum_temporal_range_bins: float,
):
    if (
        len(spectra) != 4
        or result.emission_center_frequency.state != "valid"
        or result.snr_estimate_db.state != "valid"
        or result.occupied_bandwidth.reason == "span_edge_clipping"
    ):
        return result
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    left_start, left_end = lower - 36, lower - 5
    right_start, right_end = upper + 5, upper + 36
    if left_start < 20 or right_end > 4075:
        return result
    psd_frames = np.stack([np.asarray(item.display.psd_fs2_per_hz, dtype=np.float64) for item in spectra])
    if not np.all(np.isfinite(psd_frames)):
        return result
    kernel = np.asarray([0.25, 0.5, 0.25], dtype=np.float64)

    def edges(frames: np.ndarray) -> tuple[float, float] | None:
        averaged = np.mean(frames, axis=0)
        noise = 0.5 * (
            float(np.mean(averaged[left_start : left_end + 1]))
            + float(np.mean(averaged[right_start : right_end + 1]))
        )
        sigma = noise / math.sqrt(float(frames.shape[0])) * math.sqrt(float(np.sum(kernel**2)))
        weights = np.maximum(
            np.convolve(averaged[lower : upper + 1] - noise, kernel, mode="same")
            - F4ParameterEstimator.OBW_SHRINK_SIGMA * sigma,
            0.0,
        )
        if float(np.sum(weights)) <= 0.0:
            return None
        return (
            _fractional_edge(weights, lower, tail_fraction),
            _fractional_edge(weights, lower, 1.0 - tail_fraction),
        )

    aggregate = edges(psd_frames)
    leave_one_out = [edges(np.delete(psd_frames, omitted, axis=0)) for omitted in range(4)]
    if aggregate is None or any(item is None for item in leave_one_out):
        return result
    temporal_range = max(
        float(np.median([abs(item[0] - aggregate[0]) for item in leave_one_out if item is not None])),
        float(np.median([abs(item[1] - aggregate[1]) for item in leave_one_out if item is not None])),
    )
    corrected_edges = (aggregate[0] - edge_expansion_bins, aggregate[1] + edge_expansion_bins)
    clipping = corrected_edges[0] <= lower + 0.5 or corrected_edges[1] >= upper - 0.5
    if clipping:
        state = "uncertain"
        reason = "span_edge_clipping"
    elif temporal_range > maximum_temporal_range_bins:
        state = "uncertain"
        reason = "obw_temporal_instability"
    else:
        state = "valid"
        reason = None
    spacing = spectra[0].bin_spacing_hz
    center = spectra[0].center_frequency_hz
    bin_to_hz = lambda value: center + (value - 2048.0) * spacing
    return replace(
        result,
        lower_band_edge=FieldMeasurement(state, bin_to_hz(corrected_edges[0]) if state == "valid" else None, "Hz" if state == "valid" else None, reason),
        upper_band_edge=FieldMeasurement(state, bin_to_hz(corrected_edges[1]) if state == "valid" else None, "Hz" if state == "valid" else None, reason),
        occupied_bandwidth=FieldMeasurement(state, (corrected_edges[1] - corrected_edges[0]) * spacing if state == "valid" else None, "Hz" if state == "valid" else None, reason),
        quality=replace(result.quality, temporal_edge_range_bins=temporal_range),
    )


class F5ParameterEstimator(F4ParameterEstimator):
    """Preserve v5 fields and apply calibrated, temporally gated OBW99 tails."""

    METHOD_IDS = {
        **F4ParameterEstimator.METHOD_IDS,
        "occupied_bandwidth": "band.debiased-obw99-tail-bias-correction-v6",
    }
    OBW_TAIL_FRACTION_V6 = 0.0075
    OBW_EDGE_EXPANSION_BINS_V6 = 0.375
    OBW_TEMPORAL_RANGE_MAXIMUM_V6 = 7.0

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ):
        result = super().measure(intent, samples, spectra)
        result = _tail_corrected_obw(
            result,
            intent,
            spectra,
            tail_fraction=self.OBW_TAIL_FRACTION_V6,
            edge_expansion_bins=self.OBW_EDGE_EXPANSION_BINS_V6,
            maximum_temporal_range_bins=self.OBW_TEMPORAL_RANGE_MAXIMUM_V6,
        )
        return replace(result, persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES)
