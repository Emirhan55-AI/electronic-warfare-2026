"""PHASE-04-F4 estimator with NFM-conditioned domain rejection."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from algorithms.spectrum import SpectrumResult

from .f4_domain import classify_domain_v5, extract_domain_vector_v5
from .f2_estimator import F2ParameterEstimator
from .f3_estimator import F3ParameterEstimator, carrier_evidence_v4
from .models import FieldState
from .operator_assisted import FieldMeasurement, MeasurementIntent


PERSISTENT_PAYLOAD_BYTES = 52_972


class F4ParameterEstimator(F3ParameterEstimator):
    """Preserve v4 measurements and apply the separately calibrated v5 domain decision."""

    METHOD_IDS = {
        **F3ParameterEstimator.METHOD_IDS,
        "carrier_line_frequency": "frequency.carrier-temporal-artifact-rejection-v5",
        "signal_domain": "domain.family-conditioned-prototype-rejection-v5",
    }
    CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4 = 0.98
    CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4 = 0.32
    CORRECTED_DETECTION_SIGNIFICANCE_MINIMUM = 6.25

    def measure(
        self,
        intent: MeasurementIntent,
        samples: tuple[np.ndarray, ...],
        spectra: tuple[SpectrumResult, ...],
    ):
        result = F2ParameterEstimator.measure(self, intent, samples, spectra)
        result = replace(result, persistent_payload_bytes=PERSISTENT_PAYLOAD_BYTES)
        if (
            result.emission_center_frequency.state != "valid"
            or result.snr_estimate_db.state != "valid"
        ):
            return result
        snr_db = float(result.snr_estimate_db.value)
        vector = extract_domain_vector_v5(
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
        decision = classify_domain_v5(vector, snr_db=snr_db)
        domain_state: FieldState = decision.state
        return replace(
            result,
            carrier_line_frequency=carrier,
            signal_domain=FieldMeasurement(domain_state, decision.value, reason=decision.reason),
        )
