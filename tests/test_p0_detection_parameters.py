from __future__ import annotations

import unittest

import numpy as np

from reference.p0 import CandidateRegion, OSCFARConfig, OSCFARDetector, ParameterExtractor


class P0DetectionTests(unittest.TestCase):
    def test_os_cfar_uses_strict_decision_and_full_window_edges(self) -> None:
        power = np.ones(128, dtype=np.float64)
        power[64] = 7.5
        detector = OSCFARDetector(OSCFARConfig(reference_cells_per_side=8, guard_cells_per_side=2, order_statistic_rank=12, threshold_coefficient=7.5))
        result = detector.process(power, frame_id=9)
        self.assertFalse(result.detections[64])
        power[64] = np.nextafter(7.5, np.inf)
        result = detector.process(power, frame_id=10)
        self.assertTrue(result.detections[64])
        self.assertFalse(np.any(result.detections[:10]))
        self.assertTrue(np.all(np.isnan(result.noise_power[:10])))

    def test_candidate_grouping_is_phase06h_compatible(self) -> None:
        power = np.ones(128, dtype=np.float64)
        power[[60, 62, 80]] = [20.0, 16.0, 18.0]
        detector = OSCFARDetector(OSCFARConfig(reference_cells_per_side=8, guard_cells_per_side=2, order_statistic_rank=12, threshold_coefficient=7.5, maximum_gap_bins=1))
        result = detector.process(power, frame_id=1)
        self.assertEqual([(item.start_bin, item.end_bin, item.peak_bin) for item in result.candidates], [(60, 62, 60), (80, 80, 80)])


class P0ParameterTests(unittest.TestCase):
    def test_tone_parameters_share_candidate_noise(self) -> None:
        count = 4096
        sample_rate = 8_000_000.0
        center = 100_000_000.0
        offset_bins = 117
        time = np.arange(count, dtype=np.float64)
        iq = 0.5 * np.exp(2j * np.pi * offset_bins * time / count)
        periodic_hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * time / count)
        shifted_fft = np.fft.fftshift(np.fft.fft(iq * periodic_hann))
        power = np.abs(shifted_fft) ** 2
        peak = count // 2 + offset_bins
        candidate = CandidateRegion(peak - 1, peak + 1, peak, float(power[peak]), 1e-30, 7.5e-30)
        result = ParameterExtractor().extract(
            frame_id=2,
            iq=iq,
            shifted_power=power,
            sample_rate_hz=sample_rate,
            center_frequency_hz=center,
            candidate=candidate,
            confirmed=True,
            provenance="HOST REFERENCE",
            backend="p0.os_cfar",
        )
        expected = center + offset_bins * sample_rate / count
        self.assertAlmostEqual(result.carrier_frequency_hz, expected, places=6)
        self.assertAlmostEqual(result.bandwidth_hz, 3.0 * sample_rate / count, places=6)
        self.assertAlmostEqual(result.relative_power_linear, 0.25, places=12)
        self.assertAlmostEqual(result.relative_power_dbfs, 20.0 * np.log10(0.5), places=10)
        self.assertGreater(result.snr_db, 60.0)
        self.assertEqual(result.calibration_state, "KALİBRASYON BEKLİYOR")
        self.assertEqual(result.provenance, "HOST REFERENCE")


if __name__ == "__main__":
    unittest.main()
