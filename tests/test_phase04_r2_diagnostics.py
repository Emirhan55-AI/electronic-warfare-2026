"""Independent mathematical gates for the locked PHASE-04-R2 method."""

from __future__ import annotations

import unittest

import numpy as np

from reference.parameters.r2 import (
    HANN_CORRECTION,
    HANN_EXPECTED_CI95,
    IID_TRIMMED_MEAN_CORRECTION,
    IID_TRIMMED_MEAN_EXPECTATION,
    MORPHOLOGY_MOMENT_THRESHOLD,
    hann_complex_covariance,
    hann_covariance_calibration,
    hann_end_to_end_calibration,
    iid_trimmed_mean_expectation,
    morphology_calibration,
)


class Phase04R2DiagnosticTests(unittest.TestCase):
    def test_exact_iid_order_statistics_are_not_the_hann_correction(self) -> None:
        expectation = iid_trimmed_mean_expectation()
        self.assertAlmostEqual(expectation, IID_TRIMMED_MEAN_EXPECTATION, delta=1e-12)
        self.assertAlmostEqual(1.0 / expectation, IID_TRIMMED_MEAN_CORRECTION, delta=1e-12)
        self.assertNotAlmostEqual(IID_TRIMMED_MEAN_CORRECTION, HANN_CORRECTION, delta=1e-3)

    def test_periodic_hann_covariance_and_power_correlation(self) -> None:
        covariance = hann_complex_covariance()
        self.assertAlmostEqual(covariance[0, 0], 1.0, delta=1e-12)
        self.assertAlmostEqual(covariance[0, 1], -2.0 / 3.0, delta=1e-12)
        self.assertAlmostEqual(covariance[0, 2], 1.0 / 6.0, delta=1e-12)
        self.assertAlmostEqual(covariance[0, 3], 0.0, delta=1e-12)
        self.assertAlmostEqual(abs(covariance[0, 1]) ** 2, 4.0 / 9.0, delta=1e-12)
        self.assertAlmostEqual(abs(covariance[0, 2]) ** 2, 1.0 / 36.0, delta=1e-12)
        self.assertGreater(float(np.min(np.linalg.eigvalsh(covariance))), 0.0)

    def test_full_hann_covariance_calibration_gate(self) -> None:
        result = hann_covariance_calibration(full=True)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["trimmed_order_statistics"], [7, 26])
        self.assertLessEqual(
            0.5 * (result["batch_t_ci95"][1] - result["batch_t_ci95"][0]), 0.0006
        )
        self.assertAlmostEqual(result["locked_correction_candidate"], HANN_CORRECTION, delta=1e-15)

    def test_actual_phase02_hann_fft_chain_agrees_with_covariance_model(self) -> None:
        result = hann_end_to_end_calibration()
        self.assertEqual(result["status"], "passed")
        self.assertLessEqual(result["corrected_ci95"][0], 1.0)
        self.assertGreaterEqual(result["corrected_ci95"][1], 1.0)
        self.assertLessEqual(abs(result["corrected_mean_bias"]), 0.005)
        self.assertLessEqual(max(result["batch_t_ci95"][0], HANN_EXPECTED_CI95[0]),
                             min(result["batch_t_ci95"][1], HANN_EXPECTED_CI95[1]))

    def test_morphology_moment_is_derived_from_separated_analytic_sets(self) -> None:
        result = morphology_calibration()
        self.assertEqual(result["status"], "passed")
        self.assertGreaterEqual(
            result["separation_margin_bins2"], result["required_margin_bins2"]
        )
        self.assertAlmostEqual(result["locked_threshold_bins2"], MORPHOLOGY_MOMENT_THRESHOLD, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
