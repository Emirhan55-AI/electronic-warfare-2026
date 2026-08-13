"""Deterministic mathematical tests for the PHASE-03 reference detector."""

from __future__ import annotations

import math
import unittest

import numpy as np

from reference.detection import (
    CellDetectionResult,
    DetectionPipeline,
    DetectorConfig,
    LinearPowerDetector,
    ca_threshold_multiplier,
    os_threshold_multiplier,
)
from reference.detection.scenes import generate_scene, load_scene_catalog
from reference.spectrum import SpectrumProcessor


class DetectionReferenceTests(unittest.TestCase):
    def test_independently_known_cfar_constants(self) -> None:
        self.assertAlmostEqual(10.6726858292, ca_threshold_multiplier(1e-4), places=10)
        self.assertAlmostEqual(8.5801430407, os_threshold_multiplier(1e-4), places=10)

    def test_center_policy_has_exact_cut_denominators(self) -> None:
        power = np.ones(4096, dtype=np.float64)
        included = LinearPowerDetector(DetectorConfig(method="ca_cfar", evaluate_center=True)).detect(power)
        excluded = LinearPowerDetector(DetectorConfig(method="ca_cfar", evaluate_center=False)).detect(power)
        self.assertEqual(4056, included.evaluated_count)
        self.assertEqual(4055, excluded.evaluated_count)
        self.assertTrue(included.evaluated_mask[2048])
        self.assertFalse(excluded.evaluated_mask[2048])
        self.assertEqual(4055, int(np.count_nonzero(excluded.evaluated_mask)))

    def test_shifted_frequency_scenes_round_trip_through_real_spectrum_chain(self) -> None:
        catalog = load_scene_catalog()
        processor = SpectrumProcessor()
        for scene_id in ("wideband-noise-like", "sloped-noise", "stepped-noise"):
            first = generate_scene(scene_id, trial_index=0, catalog=catalog)
            second = generate_scene(scene_id, trial_index=0, catalog=catalog)
            self.assertTrue(np.array_equal(first.samples, second.samples), scene_id)
            result = processor.process(
                first.samples,
                sample_rate_hz=catalog["common"]["sample_rate_hz"],
                center_frequency_hz=catalog["common"]["center_frequency_hz"],
            )
            self.assertTrue(np.all(np.isfinite(result.display.bin_power_fs2)), scene_id)
        wide = generate_scene("wideband-noise-like", trial_index=0, catalog=catalog)
        truth = wide.ground_truth[0]
        result = processor.process(
            wide.samples,
            sample_rate_hz=catalog["common"]["sample_rate_hz"],
            center_frequency_hz=catalog["common"]["center_frequency_hz"],
        )
        expected = np.arange(truth["shifted_start_bin"], truth["shifted_end_bin"] + 1)
        strongest = np.argpartition(result.display.bin_power_fs2, -expected.size)[-expected.size :]
        self.assertGreaterEqual(np.intersect1d(strongest, expected).size / expected.size, 0.95)

    def test_all_detectors_reject_invalid_power(self) -> None:
        for method in ("regional", "ca_cfar", "os_cfar"):
            detector = LinearPowerDetector(DetectorConfig(method=method))
            with self.assertRaisesRegex(ValueError, "finite"):
                detector.detect(np.full(4096, math.nan))
            with self.assertRaisesRegex(ValueError, "negative"):
                detector.detect(np.full(4096, -1.0))

    def test_split_merge_identity_and_memory_limits_are_deterministic(self) -> None:
        class SequenceDetector:
            def __init__(self, masks: list[np.ndarray]) -> None:
                self.masks = iter(masks)

            def detect(self, _: object) -> CellDetectionResult:
                mask = next(self.masks)
                evaluated = np.zeros(4096, dtype=np.bool_)
                evaluated[20:-20] = True
                noise = np.ones(4096, dtype=np.float64)
                threshold = np.ones(4096, dtype=np.float64)
                return CellDetectionResult(
                    method="regional",
                    pfa=1e-4,
                    evaluated_mask=evaluated,
                    detected_mask=mask,
                    noise_power=noise,
                    threshold_power=threshold,
                    evaluated_count=4056,
                )

        def mask(*ranges: tuple[int, int]) -> np.ndarray:
            result = np.zeros(4096, dtype=np.bool_)
            for start, end in ranges:
                result[start : end + 1] = True
            return result

        spectrum = SpectrumProcessor().process(
            np.zeros(4096, dtype=np.complex128),
            sample_rate_hz=8_000_000,
            center_frequency_hz=100_000_000,
        )
        pipeline = DetectionPipeline(  # type: ignore[arg-type]
            SequenceDetector(
                [
                    mask((100, 102), (108, 110)),
                    mask((100, 110)),
                    mask((100, 102), (108, 110)),
                ]
            )
        )
        first = pipeline.process(spectrum, frame_index=0)
        second = pipeline.process(spectrum, frame_index=1)
        third = pipeline.process(spectrum, frame_index=2)
        self.assertEqual([1, 2], [event.event_id for event in first.active_events])
        self.assertEqual(1, sum(event.observed_this_frame for event in second.active_events))
        self.assertEqual([1, 2], [event.event_id for event in third.active_events])
        self.assertTrue(all(event.state == "confirmed" for event in third.active_events))

        many = mask(*[(20 + index * 3, 20 + index * 3) for index in range(100)])
        empty = mask()
        bounded = DetectionPipeline(SequenceDetector([many, empty, empty] * 3))  # type: ignore[arg-type]
        final = None
        dropped_total = 0
        for frame_index in range(9):
            final = bounded.process(spectrum, frame_index=frame_index)
            dropped_total += final.dropped_candidates
            self.assertLessEqual(len(final.active_events), 64)
            self.assertLessEqual(len(final.ended_history), 128)
        assert final is not None
        self.assertGreater(final.evicted_history_count, 0)
        self.assertGreater(dropped_total, 0)


if __name__ == "__main__":
    unittest.main()
