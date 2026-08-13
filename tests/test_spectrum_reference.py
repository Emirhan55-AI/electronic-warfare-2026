"""Mathematical contract tests for the PHASE-02 reference spectrum."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from reference.spectrum import (
    ExponentialPowerAverager,
    SigMFFrameSource,
    SpectrumConfig,
    SpectrumError,
    SpectrumProcessor,
    periodic_hann,
)


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
MANIFEST = ROOT / "results" / "evidence" / "phase01" / "fixture-manifest.json"


class SpectrumReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SigMFFrameSource(METADATA)
        self.processor = SpectrumProcessor()

    def process_fixture_frame(self, index: int = 0):
        return self.processor.process(
            self.source.read_frame(index),
            sample_rate_hz=self.source.sample_rate_hz,
            center_frequency_hz=self.source.center_frequency_hz,
        )

    def test_fixture_hashes_and_four_frames_are_golden(self) -> None:
        payload = DATA.read_bytes()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(manifest["sha512"], hashlib.sha512(payload).hexdigest())

        results = [self.process_fixture_frame(index) for index in range(4)]
        for result in results:
            display = result.display
            self.assertEqual(4096, display.frequency_offset_hz.size)
            self.assertEqual(256, int(np.argmax(result.fft_power_unshifted)))
            self.assertEqual(2304, int(np.argmax(display.bin_power_fs2)))
            self.assertAlmostEqual(-4_000_000.0, display.frequency_offset_hz[0], delta=1e-9)
            self.assertAlmostEqual(3_998_046.875, display.frequency_offset_hz[-1], delta=1e-9)
            self.assertAlmostEqual(96_000_000.0, display.frequency_absolute_hz[0], delta=1e-9)
            self.assertAlmostEqual(103_998_046.875, display.frequency_absolute_hz[-1], delta=1e-9)
            self.assertAlmostEqual(500_000.0, display.frequency_offset_hz[2304], delta=1e-9)
            self.assertAlmostEqual(100_500_000.0, display.frequency_absolute_hz[2304], delta=1e-9)
            self.assertAlmostEqual(0.7802479253326433, display.amplitude_fs[2304], delta=1e-12)
            self.assertAlmostEqual(-2.1553475488702216, display.bin_power_dbfs[2304], delta=1e-8)
            self.assertAlmostEqual(-36.823560529668725, display.psd_dbfs_per_hz[2304], delta=1e-8)
            for array in (
                result.fft_unshifted.real,
                result.fft_unshifted.imag,
                result.fft_power_unshifted,
                display.frequency_offset_hz,
                display.frequency_absolute_hz,
                display.amplitude_fs,
                display.bin_power_fs2,
                display.bin_power_dbfs,
                display.psd_fs2_per_hz,
                display.psd_dbfs_per_hz,
            ):
                self.assertTrue(np.all(np.isfinite(array)))

        for result in results[1:]:
            np.testing.assert_allclose(results[0].fft_unshifted, result.fft_unshifted, rtol=1e-10, atol=1e-12)
        non_peak = results[0].display.bin_power_fs2.copy()
        non_peak[2304] = 0.0
        self.assertGreater(np.count_nonzero(non_peak), 0, "quantized lookup/window spectrum is not single-bin")
        self.assertGreater(results[0].display.bin_power_fs2[2304], float(np.max(non_peak)))

    def test_periodic_hann_normalization(self) -> None:
        window = periodic_hann(4096)
        self.assertAlmostEqual(0.5, float(np.sum(window) / window.size), delta=1e-15)
        self.assertAlmostEqual(0.375, float(np.sum(window * window) / window.size), delta=1e-15)
        enbw_bins = window.size * float(np.sum(window * window)) / float(np.sum(window) ** 2)
        self.assertAlmostEqual(1.5, enbw_bins, delta=1e-14)

    def test_dynamic_sample_rate_and_axis_contract(self) -> None:
        processor = SpectrumProcessor(SpectrumConfig(frame_length=8))
        frame = np.zeros(8, dtype=np.complex128)
        result = processor.process(frame, sample_rate_hz=10_000_000, center_frequency_hz=915_000_000)
        self.assertEqual(1_250_000.0, result.bin_spacing_hz)
        np.testing.assert_array_equal(
            np.array([-5_000_000, -3_750_000, -2_500_000, -1_250_000, 0, 1_250_000, 2_500_000, 3_750_000]),
            result.display.frequency_offset_hz,
        )
        self.assertTrue(np.all(result.display.bin_power_dbfs == -200.0))
        self.assertTrue(np.all(result.display.psd_dbfs_per_hz == -200.0))

    def test_optional_dc_removal_is_explicit(self) -> None:
        frame = np.full(4096, 0.5 + 0.25j, dtype=np.complex128)
        retained = SpectrumProcessor(SpectrumConfig(remove_dc=False)).process(
            frame, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000
        )
        removed = SpectrumProcessor(SpectrumConfig(remove_dc=True)).process(
            frame, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000
        )
        self.assertGreater(retained.display.bin_power_dbfs[2048], -10.0)
        self.assertTrue(np.all(removed.display.bin_power_dbfs == -200.0))

    def test_exponential_average_is_linear_and_bounded(self) -> None:
        average = ExponentialPowerAverager(alpha=0.2)
        first = average.update(np.array([1.0, 3.0]))
        second = average.update(np.array([6.0, 8.0]))
        np.testing.assert_allclose(first, np.array([1.0, 3.0]), rtol=0.0, atol=0.0)
        np.testing.assert_allclose(second, np.array([2.0, 4.0]), rtol=0.0, atol=1e-15)
        average.reset()
        np.testing.assert_array_equal(np.array([6.0, 8.0]), average.update(np.array([6.0, 8.0])))

    def test_invalid_frames_and_values_are_rejected(self) -> None:
        with self.assertRaises(SpectrumError):
            self.processor.process(np.zeros(2), sample_rate_hz=8_000_000, center_frequency_hz=0)
        frame = np.zeros(4096, dtype=np.complex128)
        frame[0] = complex(float("nan"), 0.0)
        with self.assertRaises(SpectrumError):
            self.processor.process(frame, sample_rate_hz=8_000_000, center_frequency_hz=0)
        with self.assertRaises(SpectrumError):
            self.processor.process(np.zeros(4096), sample_rate_hz=0, center_frequency_hz=0)


if __name__ == "__main__":
    unittest.main()
