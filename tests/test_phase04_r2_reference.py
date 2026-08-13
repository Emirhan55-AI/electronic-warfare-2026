"""Analytic and bounded-state tests for the PHASE-04-R2 bandwidth method."""

from __future__ import annotations

import unittest

import numpy as np

from reference.detection import DetectionPipeline, DetectorConfig, LinearPowerDetector
from reference.parameters import (
    BandEdgeHistoryStore,
    MethodSelection,
    ParameterExtractor,
    R2_BAND_HISTORY_BYTES,
    R2_PARAMETER_HISTORY_BYTES,
    estimate_band_support,
    generate_parameter_scene,
    load_parameter_catalog,
)
from reference.spectrum import SpectrumProcessor


METHOD = "band.temporal-morphology-envelope-v1"


class Phase04R2ReferenceTests(unittest.TestCase):
    def test_grow_only_components_cannot_extend_or_bridge_support(self) -> None:
        power = np.ones(176, dtype=np.float64)
        power[80] = 12.0
        power[95] = 4.0  # grow-only, no seed and no constituent region
        power[120] = 12.0
        result = estimate_band_support(
            power, 0, 175, 80, 1.0, METHOD, ((80, 80),)
        )
        self.assertEqual(result.state, "valid")
        self.assertEqual(result.retained_component_count, 1)
        self.assertNotIn(1, result.supported_component_indices)
        self.assertEqual(result.lower_shifted_bin, 80)
        self.assertEqual(result.upper_shifted_bin, 80)

    def test_am_sides_and_two_fsk_lobes_are_retained_without_family_labels(self) -> None:
        am = np.ones(176, dtype=np.float64)
        am[[72, 80, 88]] = [12.0, 100.0, 12.0]
        am_result = estimate_band_support(am, 0, 175, 80, 1.0, METHOD, ((72, 72), (80, 80), (88, 88)))
        self.assertEqual(am_result.retained_component_count, 3)
        self.assertLessEqual(float(am_result.lower_shifted_edge), 72.5)
        self.assertGreaterEqual(float(am_result.upper_shifted_edge), 87.5)

        fsk = np.ones(176, dtype=np.float64)
        fsk[60:70] = 15.0
        fsk[82:92] = 15.0
        fsk_result = estimate_band_support(fsk, 0, 175, 64, 1.0, METHOD, ((60, 69), (82, 91)))
        self.assertEqual(fsk_result.retained_component_count, 2)
        self.assertLess(float(fsk_result.lower_shifted_edge), 61.0)
        self.assertGreater(float(fsk_result.upper_shifted_edge), 90.0)

    def test_gap_24_is_inclusive_and_gap_25_closes_frontier(self) -> None:
        for gap, expected in ((24, 2), (25, 1)):
            power = np.ones(176, dtype=np.float64)
            power[90:93] = 20.0
            left_end = 90 - gap - 1
            power[left_end - 2 : left_end + 1] = 20.0
            result = estimate_band_support(
                power,
                0,
                175,
                91,
                1.0,
                METHOD,
                ((90, 92), (left_end - 2, left_end)),
            )
            self.assertEqual(result.retained_component_count, expected)

    def test_noise_only_and_search_boundary_grow_spurs_do_not_expand_anchor(self) -> None:
        noise = np.ones(176, dtype=np.float64)
        invalid = estimate_band_support(noise, 0, 175, 88, 1.0, METHOD, ())
        self.assertEqual(invalid.invalid_reason, "anchor_not_supported")

        power = np.ones(176, dtype=np.float64)
        power[88] = 12.0
        power[174:176] = 4.0
        bounded = estimate_band_support(power, 0, 175, 88, 1.0, METHOD, ((88, 88),))
        self.assertEqual(bounded.retained_component_count, 1)
        self.assertLess(float(bounded.upper_shifted_edge), 100.0)

    def test_temporal_history_is_bounded_and_resets_on_gap(self) -> None:
        history = BandEdgeHistoryStore()
        self.assertEqual(history.payload_bytes, R2_BAND_HISTORY_BYTES)
        first = history.append(7, 1, 10.0, 20.0, 1.0, supported=True)
        self.assertEqual(first[0].size, 1)
        second = history.append(7, 2, 11.0, 21.0, 1.1, supported=True)
        self.assertEqual(second[0].size, 2)
        third = history.append(7, 4, 12.0, 22.0, 1.2, supported=True)
        self.assertEqual(third[0].size, 1)
        history.retain_observed(set())
        self.assertFalse(history.contains(7))
        self.assertEqual(R2_PARAMETER_HISTORY_BYTES, 74_368)

    def test_public_temporal_schedule_for_continuous_and_burst_frames(self) -> None:
        catalog = load_parameter_catalog()
        selection = MethodSelection(
            "noise.trimmed-mean-20-hann-calibrated-v1",
            METHOD,
            "center.excess-power-centroid",
            "carrier.peak-gated",
            "domain.explainable-rules",
            "analysis.clustered-regions-v1",
        )
        for scene_id, frames, expected_first_valid in (("am-carrier", 4, 2), ("burst-qpsk", 6, 4)):
            detector = DetectionPipeline(LinearPowerDetector(DetectorConfig(method="regional")))
            extractor = ParameterExtractor(selection)
            states: dict[int, list[str]] = {}
            for frame_index in range(frames):
                frame = generate_parameter_scene(scene_id, trial_index=0, frame_index=frame_index, snr_db=12.0, catalog=catalog)
                spectrum = SpectrumProcessor().process(
                    frame.samples,
                    sample_rate_hz=float(catalog["common"]["sample_rate_hz"]),
                    center_frequency_hz=float(catalog["common"]["center_frequency_hz"]),
                )
                detection = detector.process(spectrum, frame_index=frame_index)
                output = extractor.process(frame.samples, spectrum, detection, frame_index=frame_index)
                states[frame_index] = [event.bandwidth.bandwidth_state for event in output.events]
            valid_frames = [index for index, values in states.items() if "valid" in values]
            self.assertTrue(valid_frames)
            self.assertEqual(valid_frames[0], expected_first_valid)
            if scene_id == "am-carrier":
                self.assertIn("insufficient_quality", states[1])
                self.assertIn("valid", states[3])
            else:
                self.assertIn("insufficient_quality", states[3])
                self.assertIn("valid", states[4])
                self.assertNotIn("valid", states[5])


if __name__ == "__main__":
    unittest.main()
