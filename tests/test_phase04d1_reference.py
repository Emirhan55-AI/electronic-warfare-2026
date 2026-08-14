"""Clean-reference and independent noise-calibration tests for PHASE-04-D1."""

from __future__ import annotations

import math
import unittest

import numpy as np

from reference.parameters.obw99_reference import (
    build_clean_reference,
    canonical_json_bytes,
    fractional_power_edge,
    load_d1_catalog,
    nearest_rank_q95,
    noise_calibration,
    phase02_noise_equivalence,
)


class Phase04D1ReferenceTests(unittest.TestCase):
    def test_fractional_obw_edges_and_nearest_rank_q95_are_exact(self) -> None:
        uniform = np.ones(100, dtype=np.float64)
        self.assertAlmostEqual(fractional_power_edge(uniform, 0.005), 0.0, delta=1e-12)
        self.assertAlmostEqual(fractional_power_edge(uniform, 0.995), 99.0, delta=1e-12)
        self.assertEqual(nearest_rank_q95(np.arange(1.0, 21.0)), 19.0)

    def test_clean_reference_is_deterministic_and_all_families_converge(self) -> None:
        first = canonical_json_bytes(build_clean_reference())
        second = canonical_json_bytes(build_clean_reference())
        self.assertEqual(first, second)
        document = build_clean_reference()
        catalog = load_d1_catalog()
        self.assertEqual(len(document["families"]), len(catalog["supported_families"]))
        for family in document["families"]:
            self.assertEqual(family["active_frames"], 256)
            self.assertLessEqual(family["edge_convergence_native_bins"], 0.125)
            self.assertLessEqual(family["maximum_zero_padding_power_error"], 1e-10)
            self.assertGreater(family["truth"]["occupied_bandwidth_hz"], 0.0)

    def test_burst_reference_uses_only_active_frames(self) -> None:
        burst = next(item for item in build_clean_reference()["families"] if item["family_id"] == "burst_qpsk")
        self.assertEqual(burst["active_policy"], "burst_pattern_active_only")
        self.assertEqual(burst["active_frames"], 256)

    def test_phase02_psd_normalization_equivalence(self) -> None:
        rng = np.random.default_rng(20260819)
        samples = (rng.normal(size=4096) + 1j * rng.normal(size=4096)) / math.sqrt(2.0)
        self.assertLessEqual(phase02_noise_equivalence(samples, sample_rate_hz=8_000_000.0), 1e-20)

    def test_noise_calibration_is_deterministic_independent_and_passes(self) -> None:
        first = noise_calibration()
        second = noise_calibration()
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(first["status"], "passed")
        self.assertFalse(first["binding_or_oos_inputs_used"])
        self.assertFalse(first["exact_pfa_claimed"])
        self.assertLessEqual(abs(first["corrected_validation_bias"]), 0.005)
        self.assertLessEqual(first["corrected_validation_ci95_half_width"], 0.005)
        self.assertLessEqual(first["corrected_validation_ci95"][0], 1.0)
        self.assertGreaterEqual(first["corrected_validation_ci95"][1], 1.0)
        self.assertNotAlmostEqual(first["correction_factor"], 1.0, delta=1e-4)


if __name__ == "__main__":
    unittest.main()
