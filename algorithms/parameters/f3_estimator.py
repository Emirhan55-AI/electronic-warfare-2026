"""PHASE-04-F3 parameter estimator with separate OOK robustness changes."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

import numpy as np

from algorithms.spectrum import SpectrumResult

from .f2_estimator import F2ParameterEstimator
from .f3_domain import FEATURE_NAMES, classify_domain_v4, extract_domain_vector_v4
from .models import FieldState
from .operator_assisted import FieldMeasurement, MeasurementIntent


PERSISTENT_PAYLOAD_BYTES = 52_964


@dataclass(frozen=True)
class CarrierEvidenceV4:
    frequency_hz: float
    prominence_db: float
    share: float
    frame_prominences_db: tuple[float, ...]
    spectral_entropy: float
    envelope_skewness: float


def carrier_evidence_v4(
    intent: MeasurementIntent,
    spectra: tuple[SpectrumResult, ...],
    emission_frequency_hz: float,
    domain_vector: np.ndarray,
) -> CarrierEvidenceV4 | None:
    """Measure a fixed-center spectral line and its four-frame support."""
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
    prominence = 10.0 * math.log10(
        float(average_bin_power[peak]) / max(background, np.finfo(float).tiny)
    )
    frame_prominences: list[float] = []
    for item in spectra:
        frame_power = np.asarray(item.display.bin_power_fs2, dtype=np.float64)
        frame_background_values = np.concatenate((
            frame_power[max(lower, peak - 8) : max(lower, peak - 2)],
            frame_power[min(upper + 1, peak + 3) : min(upper + 1, peak + 9)],
        ))
        frame_background = float(np.median(frame_background_values))
        frame_prominences.append(
            10.0 * math.log10(
                float(frame_power[peak]) / max(frame_background, np.finfo(float).tiny)
            )
        )
    local = average_bin_power[peak - 1 : peak + 2]
    share = float(
        np.sum(np.maximum(local - noise * spacing, 0.0))
        / max(total * spacing, np.finfo(float).tiny)
    )
    logs = np.log(np.maximum(local, np.finfo(float).tiny))
    denominator = logs[0] - 2.0 * logs[1] + logs[2]
    delta = (
        float(np.clip(0.5 * (logs[0] - logs[2]) / denominator, -0.5, 0.5))
        if abs(denominator) > 1.0e-15 else 0.0
    )
    spectral_entropy = float(domain_vector[FEATURE_NAMES.index("spectral_entropy")])
    envelope_skewness = float(domain_vector[FEATURE_NAMES.index("envelope_skewness")])
    return CarrierEvidenceV4(
        frequency_hz=spectra[0].center_frequency_hz + (peak + delta - 2048.0) * spacing,
        prominence_db=prominence,
        share=share,
        frame_prominences_db=tuple(frame_prominences),
        spectral_entropy=spectral_entropy,
        envelope_skewness=envelope_skewness,
    )


class F3ParameterEstimator(F2ParameterEstimator):
    """Apply v4 carrier and domain decisions without changing frozen F2 sources."""

    METHOD_IDS = {
        **F2ParameterEstimator.METHOD_IDS,
        "carrier_line_frequency": "frequency.carrier-temporal-artifact-rejection-v4",
        "signal_domain": "domain.envelope-spectrum-prototype-rejection-v4",
    }
    CARRIER_PROMINENCE_DB_MINIMUM_V4 = 5.25
    CARRIER_SHARE_MINIMUM_V4 = 0.235
    CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4 = 1.0
    CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4 = 0.325
    CARRIER_ARTIFACT_ENVELOPE_SKEWNESS_MAXIMUM_V4 = -0.1

    @classmethod
    def carrier_is_valid(cls, evidence: CarrierEvidenceV4 | None) -> bool:
        if evidence is None:
            return False
        artifact_like = (
            evidence.spectral_entropy >= cls.CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4
            and evidence.envelope_skewness <= cls.CARRIER_ARTIFACT_ENVELOPE_SKEWNESS_MAXIMUM_V4
        )
        return (
            evidence.prominence_db >= cls.CARRIER_PROMINENCE_DB_MINIMUM_V4
            and evidence.share >= cls.CARRIER_SHARE_MINIMUM_V4
            and min(evidence.frame_prominences_db) >= cls.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4
            and not artifact_like
        )

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ):
        result = super().measure(intent, samples, spectra)
        result = replace(result, persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES)
        if (
            result.emission_center_frequency.state != "valid"
            or result.snr_estimate_db.state != "valid"
        ):
            return result
        snr_db = float(result.snr_estimate_db.value)
        vector = extract_domain_vector_v4(
            samples, intent.span.lower_shifted_bin, intent.span.upper_shifted_bin,
        )
        if snr_db < self.LOW_SNR_ABSTENTION_DB:
            carrier = FieldMeasurement("not_observed", reason="quality_below_carrier_threshold")
        else:
            evidence = carrier_evidence_v4(
                intent, spectra, float(result.emission_center_frequency.value), vector,
            )
            carrier = (
                FieldMeasurement("valid", evidence.frequency_hz, "Hz")
                if self.carrier_is_valid(evidence) and evidence is not None
                else FieldMeasurement("not_observed", reason="carrier_line_below_threshold")
            )
        decision = classify_domain_v4(vector, snr_db=snr_db)
        domain_state: FieldState = decision.state
        return replace(
            result,
            carrier_line_frequency=carrier,
            signal_domain=FieldMeasurement(domain_state, decision.value, reason=decision.reason),
        )
