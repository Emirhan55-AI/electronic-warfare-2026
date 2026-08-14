from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from reference.parameters import (
    AnalysisSpan,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
    OperatorMeasurementProcessor,
    project_to_simplex,
)
from reference.parameters.scenes import generate_parameter_scene
from reference.parameters.operator_evaluation import _new_stage_counters, _record_stage_counters
from reference.spectrum import SpectrumProcessor


class Phase04E1AlgorithmTests(unittest.TestCase):
    @staticmethod
    def intent(span: AnalysisSpan, *, neighbors: tuple[MeasurementCandidate, ...] = ()) -> MeasurementIntent:
        owner = MeasurementCandidate(1, 4, span.lower_shifted_bin, span.upper_shifted_bin)
        context = MeasurementContext(1, 1, 1, 1, 4, (True, True, True, True), (owner, *neighbors))
        return MeasurementIntent(1, 1, 1, 1, 4, 0, span, context)

    @staticmethod
    def synthetic_spectra(power_frames: tuple[np.ndarray, ...]) -> tuple[object, ...]:
        frequency = 100_000_000.0 + (np.arange(4096) - 2048) * (8_000_000.0 / 4096.0)
        records = []
        for psd in power_frames:
            display = SimpleNamespace(
                psd_fs2_per_hz=psd,
                bin_power_fs2=psd * (8_000_000.0 / 4096.0),
                frequency_absolute_hz=frequency,
            )
            records.append(SimpleNamespace(frame_length=4096, display=display, bin_spacing_hz=8_000_000.0 / 4096.0, center_frequency_hz=100_000_000.0))
        return tuple(records)
    def test_simplex_projection_is_deterministic_finite_and_sum_preserving(self) -> None:
        values = np.random.default_rng(20260910).normal(size=512)
        first = project_to_simplex(values, 17.25)
        second = project_to_simplex(values, 17.25)
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.all(np.isfinite(first)))
        self.assertTrue(np.all(first >= 0.0))
        self.assertAlmostEqual(float(np.sum(first)), 17.25, places=12)

    def test_zero_total_produces_no_rectification_bias(self) -> None:
        values = np.linspace(-1.0, 1.0, 176)
        projected = project_to_simplex(values, 0.0)
        self.assertEqual(float(np.sum(projected)), 0.0)
        self.assertEqual(int(np.count_nonzero(projected)), 0)

    def test_low_total_abstains_and_does_not_use_ground_truth(self) -> None:
        processor = SpectrumProcessor()
        frames = tuple(
            generate_parameter_scene("noise-only", trial_index=0, frame_index=index)
            for index in range(4)
        )
        spectra = tuple(processor.process(item.samples, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000) for item in frames)
        intent = self.intent(AnalysisSpan(1900, 2195, "operator_adjusted"))
        result = OperatorMeasurementProcessor().measure(intent, tuple(item.samples for item in frames), spectra)
        self.assertNotEqual(result.occupied_bandwidth.state, "valid")
        self.assertEqual(result.persistent_payload_bytes, 34_084)

    def test_four_frames_are_required(self) -> None:
        intent = self.intent(AnalysisSpan(1900, 2195, "operator_adjusted"))
        result = OperatorMeasurementProcessor().measure(intent, (), ())
        self.assertEqual(result.quality.state, "insufficient_quality")

    def test_obw_clipping_does_not_close_center_power_or_domain(self) -> None:
        span = AnalysisSpan(1900, 1931, "operator_adjusted")
        psd = np.ones(4096)
        psd[1900:1932] += 20.0
        samples = tuple(np.ones(4096, dtype=np.complex128) for _ in range(4))
        with patch("reference.parameters.operator_assisted.classify_domain", return_value=("Analog", 1.0, ())):
            result = OperatorMeasurementProcessor().measure(self.intent(span), samples, self.synthetic_spectra((psd,) * 4))
        self.assertEqual("uncertain", result.occupied_bandwidth.state)
        self.assertEqual("span_edge_clipping", result.occupied_bandwidth.reason)
        self.assertEqual("valid", result.emission_center_frequency.state)
        self.assertEqual("valid", result.channel_power_dbfs.state)
        self.assertEqual("valid", result.signal_domain.state)
        counters = _new_stage_counters()
        _record_stage_counters(counters, result)
        self.assertEqual(1, counters["occupied_bandwidth"]["field_math_reached"])
        self.assertEqual(1, counters["occupied_bandwidth"]["field_uncertain"])
        self.assertEqual(1, counters["occupied_bandwidth"]["reason_counts"]["span_edge_clipping"])
        self.assertEqual(1, counters["uncalibrated_power_dbfs"]["field_valid"])

    def test_obw_temporal_instability_only_closes_obw(self) -> None:
        span = AnalysisSpan(1900, 1963, "operator_adjusted")
        frames = []
        for peak in (1912, 1912, 1950, 1950):
            psd = np.ones(4096)
            psd[peak - 1 : peak + 2] += (300.0, 1000.0, 300.0)
            frames.append(psd)
        samples = tuple(np.ones(4096, dtype=np.complex128) for _ in range(4))
        result = OperatorMeasurementProcessor().measure(self.intent(span), samples, self.synthetic_spectra(tuple(frames)))
        self.assertEqual("obw_temporal_instability", result.occupied_bandwidth.reason)
        self.assertEqual("valid", result.emission_center_frequency.state)
        self.assertEqual("valid", result.channel_power_dbfs.state)

    def test_neighbor_and_owner_contracts_are_enforced(self) -> None:
        span = AnalysisSpan(1900, 1931, "operator_adjusted")
        neighbor = MeasurementCandidate(2, 4, 1935, 1940)
        result = OperatorMeasurementProcessor().measure(self.intent(span, neighbors=(neighbor,)), (), ())
        self.assertEqual("neighbor_overlap", result.quality.reasons[0])
        owner_only = self.intent(span)
        result = OperatorMeasurementProcessor().measure(owner_only, (), ())
        self.assertEqual("four_consecutive_frames_required", result.quality.reasons[0])
        broken = MeasurementContext(1, 1, 1, 1, 4, (True, True, False, True), owner_only.context.candidates)
        result = OperatorMeasurementProcessor().measure(MeasurementIntent(1, 1, 1, 1, 4, 0, span, broken), (), ())
        self.assertEqual("event_ownership_lost", result.quality.reasons[0])


if __name__ == "__main__":
    unittest.main()
