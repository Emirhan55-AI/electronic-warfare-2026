"""PHASE-04 catalogue, seed, validity, and normalized-scene tests."""

from __future__ import annotations

import unittest

import numpy as np

from reference.parameters import generate_parameter_scene, load_parameter_catalog


class ParameterSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_parameter_catalog()

    def test_catalog_contract_is_complete_and_ordered(self) -> None:
        self.assertEqual(len(self.catalog["scenes"]), 14)
        self.assertEqual(self.catalog["validity_states"], [
            "valid", "not_observed", "not_applicable", "insufficient_quality", "uncertain"
        ])
        self.assertEqual(self.catalog["common"]["valid_feature_slice"], [1152, 2944])
        self.assertEqual(self.catalog["power_benchmark"]["family_order"], [
            "am-carrier", "nfm", "qpsk", "wideband-noise-like"
        ])

    def test_every_scene_has_eight_field_validity_matrix(self) -> None:
        for scene in self.catalog["scenes"]:
            self.assertEqual(len(scene["validity"]), 8, scene["id"])
            self.assertTrue(set(scene["validity"]) <= set(self.catalog["validity_states"]))

    def test_seeded_scene_is_reproducible(self) -> None:
        first = generate_parameter_scene("qpsk", trial_index=9, frame_index=2, catalog=self.catalog)
        second = generate_parameter_scene("qpsk", trial_index=9, frame_index=2, catalog=self.catalog)
        self.assertTrue(np.array_equal(first.samples, second.samples))
        self.assertTrue(np.array_equal(first.clean_samples, second.clean_samples))

    def test_condition_index_participates_in_the_seed_contract(self) -> None:
        first = generate_parameter_scene("qpsk", trial_index=9, condition_index=1, catalog=self.catalog)
        repeated = generate_parameter_scene("qpsk", trial_index=9, condition_index=1, catalog=self.catalog)
        other = generate_parameter_scene("qpsk", trial_index=9, condition_index=2, catalog=self.catalog)
        self.assertTrue(np.array_equal(first.samples, repeated.samples))
        self.assertFalse(np.array_equal(first.samples, other.samples))

    def test_mixed_boundary_covers_four_frames_without_changing_the_catalog(self) -> None:
        frames = [
            generate_parameter_scene("mixed-boundary", trial_index=3, frame_index=index, catalog=self.catalog)
            for index in range(4)
        ]
        for frame in frames:
            self.assertEqual(frame.samples.shape, (4096,))
            self.assertTrue(np.all(np.isfinite(frame.samples)))
        repeated = generate_parameter_scene("mixed-boundary", trial_index=3, frame_index=3, catalog=self.catalog)
        self.assertTrue(np.array_equal(frames[3].samples, repeated.samples))

    def test_frequency_domain_scene_returns_to_shifted_support(self) -> None:
        frame = generate_parameter_scene("wideband-noise-like", snr_db=60.0, catalog=self.catalog)
        power = np.abs(np.fft.fftshift(np.fft.fft(frame.clean_samples))) ** 2
        support = np.flatnonzero(power > np.max(power) * 1e-8)
        self.assertEqual((int(support[0]), int(support[-1])), (2468, 2563))

    def test_nominal_center_is_ground_truth_only(self) -> None:
        frame = generate_parameter_scene("bpsk", catalog=self.catalog)
        self.assertIn("nominal_center_frequency_hz", frame.ground_truth)
        self.assertNotIn("nominal_center_frequency_hz", frame.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
