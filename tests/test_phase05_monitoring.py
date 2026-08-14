"""Reference DSP and bounded-state tests for PHASE-05 analog monitoring."""

from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from reference.monitoring import (
    AUDIO_SAMPLE_RATE_HZ,
    AnalogMonitor,
    AnalogMonitorConfig,
    AudioRingBuffer,
    FIXTURE_SPECS,
    MonitoringError,
    aligned_correlation,
    dominant_tone_hz,
    generate_iq,
    pcm16_bytes,
    wav_bytes,
    write_wav,
)


class Phase05MonitoringTests(unittest.TestCase):
    def _result(self, mode: str, snr_db: float | None = None):
        spec = next(item for item in FIXTURE_SPECS if item.mode == mode)
        iq = generate_iq(spec, snr_db=snr_db)
        frames = tuple(iq[index : index + 4096] for index in range(0, 16_384, 4096))
        result = AnalogMonitor().process(
            frames,
            AnalogMonitorConfig(mode, 192_000.0, spec.carrier_offset_hz, spec.channel_bandwidth_hz),
        )
        reference = np.sin(2.0 * np.pi * float(spec.audio_tone_hz) * np.arange(result.audio.size) / 48_000.0)
        return spec, result, aligned_correlation(reference, result.audio)

    def test_am_and_nfm_clean_recovery(self) -> None:
        for mode in ("am", "nfm"):
            with self.subTest(mode=mode):
                spec, result, correlation = self._result(mode)
                self.assertEqual(AUDIO_SAMPLE_RATE_HZ, result.sample_rate_hz)
                self.assertTrue(np.all(np.isfinite(result.audio)))
                self.assertEqual(0, result.clipping_count)
                self.assertGreaterEqual(correlation, 0.95)
                self.assertLessEqual(abs(result.dominant_tone_hz - float(spec.audio_tone_hz)), 48_000 / 4096)

    def test_am_and_nfm_twenty_db_recovery(self) -> None:
        for mode in ("am", "nfm"):
            with self.subTest(mode=mode):
                spec, result, correlation = self._result(mode, 20.0)
                self.assertGreaterEqual(correlation, 0.80)
                self.assertLessEqual(abs(result.dominant_tone_hz - float(spec.audio_tone_hz)), 2 * 48_000 / 4096)

    def test_nfm_is_continuous_across_input_frame_boundaries(self) -> None:
        spec, result, _ = self._result("nfm")
        iq = generate_iq(spec)
        joined = AnalogMonitor().process(
            tuple(iq[index : index + 4096] for index in range(0, 16_384, 4096)),
            AnalogMonitorConfig("nfm", 192_000.0, spec.carrier_offset_hz, spec.channel_bandwidth_hz),
        )
        self.assertEqual(result.pcm16, joined.pcm16)

    def test_invalid_inputs_are_rejected(self) -> None:
        spec = FIXTURE_SPECS[0]
        good = generate_iq(spec)[:4096]
        with self.assertRaisesRegex(MonitoringError, "dört ardışık"):
            AnalogMonitor().process((good,), AnalogMonitorConfig("am", 192_000.0, 24_000.0, 16_000.0))
        with self.assertRaisesRegex(MonitoringError, "Nyquist"):
            AnalogMonitorConfig("am", 192_000.0, 94_000.0, 16_000.0)
        bad = good.copy()
        bad[0] = complex(float("nan"), 0.0)
        with self.assertRaisesRegex(MonitoringError, "NaN"):
            AnalogMonitor().process((bad, good, good, good), AnalogMonitorConfig("am", 192_000.0, 24_000.0, 16_000.0))

    def test_pcm_wav_and_ring_buffer_are_deterministic_and_bounded(self) -> None:
        tone = np.sin(2.0 * np.pi * 1000.0 * np.arange(4800) / 48_000.0)
        pcm, clipping = pcm16_bytes(tone)
        self.assertEqual(0, clipping)
        self.assertEqual(pcm, pcm16_bytes(tone)[0])
        payload = wav_bytes(pcm)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.wav"
            write_wav(path, pcm)
            self.assertEqual(payload, path.read_bytes())
            with wave.open(str(path), "rb") as stream:
                self.assertEqual((1, 2, 48_000), (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()))
        ring = AudioRingBuffer(maximum_samples=100)
        ring.append(bytes(160))
        ring.append(bytes(160))
        self.assertLessEqual(ring.sample_count, 100)

    def test_dominant_tone_and_correlation_helpers(self) -> None:
        tone = np.sin(2.0 * np.pi * 1500.0 * np.arange(4096) / 48_000.0)
        shifted = np.concatenate((np.zeros(31), tone[:-31]))
        self.assertLessEqual(abs(dominant_tone_hz(tone) - 1500.0), 48_000 / 4096)
        self.assertGreaterEqual(aligned_correlation(tone, shifted), 0.999)


if __name__ == "__main__":
    unittest.main()
