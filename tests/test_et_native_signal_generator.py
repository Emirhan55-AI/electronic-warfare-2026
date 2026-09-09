"""Yayın bağlantısı bulunmayan C++ ET sinyal üreteci kabul testleri."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np

from algorithms.et import NativeSignalConfig, NativeSignalGenerator, NativeWaveform


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "algorithms" / "et" / "native"


class NativeSignalGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        compiler = shutil.which("g++")
        if compiler is None:
            raise unittest.SkipTest("C++ derleyicisi bulunamadı")
        cls.temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        output = Path(cls.temporary_directory.name) / "et_signal_generator.dll"
        process = subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-shared",
                "-static",
                "-DET_SIGNAL_GENERATOR_EXPORTS",
                str(NATIVE / "signal_generator.cpp"),
                "-o",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if process.returncode != 0:
            raise AssertionError(process.stdout + process.stderr)
        cls.generator = NativeSignalGenerator(output)
        if hasattr(cls.generator, "transmit"):
            raise AssertionError("Yerel üreteç TX arayüzü sunamaz")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.generator = None
        cls.temporary_directory.cleanup()

    def test_all_waveforms_are_bounded_and_finite(self) -> None:
        for waveform in NativeWaveform:
            with self.subTest(waveform=waveform):
                result = self.generator.generate(
                    NativeSignalConfig(
                        waveform=waveform,
                        sample_rate_hz=48_000,
                        duration_seconds=0.02,
                        frequency_hz=1_000.0,
                        amplitude=0.7,
                    )
                )
                self.assertEqual((960,), result.samples.shape)
                self.assertEqual((960, 2), result.raw_iq.shape)
                self.assertTrue(np.all(np.isfinite(result.samples)))
                self.assertLessEqual(int(np.max(np.abs(result.raw_iq.astype(np.int16)))), 89)
                self.assertLessEqual(float(np.max(np.abs(result.samples))), 0.7 + np.sqrt(2.0) / 127.0)
                self.assertEqual("KİLİTLİ", result.tx_state)

    def test_tone_frequency_matches_configuration(self) -> None:
        result = self.generator.generate(
            NativeSignalConfig(
                waveform=NativeWaveform.TONE,
                sample_rate_hz=48_000,
                duration_seconds=0.1,
                frequency_hz=3_000.0,
            )
        )
        phase_step = np.angle(result.samples[1:] * np.conj(result.samples[:-1]))
        measured_hz = float(np.median(phase_step) * result.sample_rate_hz / (2.0 * np.pi))
        self.assertAlmostEqual(3_000.0, measured_hz, delta=25.0)

    def test_real_shapes_are_bipolar_and_dc_is_constant(self) -> None:
        for waveform in (
            NativeWaveform.SINE,
            NativeWaveform.SQUARE,
            NativeWaveform.SAWTOOTH,
            NativeWaveform.TRIANGLE,
        ):
            with self.subTest(waveform=waveform):
                result = self.generator.generate(
                    NativeSignalConfig(waveform=waveform, duration_seconds=0.02)
                )
                self.assertLess(int(np.min(result.raw_iq[:, 0])), -20)
                self.assertGreater(int(np.max(result.raw_iq[:, 0])), 20)
                self.assertTrue(np.all(result.raw_iq[:, 1] == 0))
        dc = self.generator.generate(
            NativeSignalConfig(waveform=NativeWaveform.DC_OFFSET, duration_seconds=0.01)
        )
        self.assertTrue(np.all(dc.raw_iq[:, 0] == dc.raw_iq[0, 0]))
        self.assertTrue(np.all(dc.raw_iq[:, 1] == 0))

    def test_seeded_noise_is_reproducible(self) -> None:
        config = NativeSignalConfig(
            waveform=NativeWaveform.AWGN,
            duration_seconds=0.01,
            seed=1337,
        )
        first = self.generator.generate(config)
        second = self.generator.generate(config)
        np.testing.assert_array_equal(first.raw_iq, second.raw_iq)

    def test_invalid_configuration_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "reddetti"):
            self.generator.generate(NativeSignalConfig(amplitude=1.0, duration_seconds=0.01))

    def test_native_source_has_no_device_or_transmit_backend(self) -> None:
        source = (NATIVE / "signal_generator.cpp").read_text(encoding="utf-8").casefold()
        header = (NATIVE / "signal_generator.hpp").read_text(encoding="utf-8").casefold()
        combined = source + header
        for forbidden in ("hackrf", "portapack", "libusb", "basebandthread", "direction::transmit"):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
