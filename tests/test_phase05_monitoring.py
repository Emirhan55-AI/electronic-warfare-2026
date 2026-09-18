"""Reference DSP and bounded-state tests for PHASE-05 analog monitoring."""

from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from algorithms.monitoring import (
    AUDIO_SAMPLE_RATE_HZ,
    AnalogMonitor,
    AnalogMonitorConfig,
    AudioRingBuffer,
    FIXTURE_SPECS,
    MonitoringError,
    StreamingAnalogMonitor,
    aligned_correlation,
    dominant_tone_hz,
    decode_dtmf,
    generate_iq,
    nfm_deemphasis,
    pcm16_bytes,
    wav_bytes,
    write_wav,
)
from algorithms.monitoring.dsp import _resample_linear, _resample_voice


class Phase05MonitoringTests(unittest.TestCase):
    def test_voice_defaults_are_clear_and_bandwidth_is_bounded(self) -> None:
        config = AnalogMonitorConfig("nfm", 192_000.0, 24_000.0, 16_000.0)
        self.assertEqual(0.0, config.nfm_deemphasis_us)
        with self.assertRaisesRegex(MonitoringError, "2–25 kHz"):
            AnalogMonitorConfig("nfm", 192_000.0, 0.0, 200_000.0)

    def test_voice_resampling_rejects_high_frequency_alias(self) -> None:
        source_rate = 192_000.0
        time_axis = np.arange(int(source_rate), dtype=np.float64) / source_rate
        high_frequency = np.sin(2.0 * np.pi * 47_000.0 * time_axis)
        unfiltered = _resample_linear(high_frequency, source_rate)
        filtered = _resample_voice(high_frequency, source_rate, 3_000.0)
        self.assertGreater(float(np.sqrt(np.mean(unfiltered**2))), 0.6)
        self.assertLess(float(np.sqrt(np.mean(filtered**2))), 0.01)

    def test_deemphasis_selection_is_applied_and_recorded_in_both_paths(self):
        spec = next(item for item in FIXTURE_SPECS if item.mode == "nfm")
        iq = generate_iq(spec)
        frames = tuple(iq[index:index + 4096] for index in range(0, 16384, 4096))
        t = np.arange(5 * 192000, dtype=np.float64) / 192000
        continuous_iq = 0.7 * np.exp(2j * np.pi * spec.carrier_offset_hz * t
                                    - 1j * spec.modulation_index * np.cos(2 * np.pi * spec.audio_tone_hz * t))
        monitor = AnalogMonitor()
        for continuous in (False, True):
            results = []
            for tau in (0.0, 750.0):
                config = AnalogMonitorConfig("nfm", 192000.0, spec.carrier_offset_hz,
                                             spec.channel_bandwidth_hz, nfm_deemphasis_us=tau)
                result = (monitor.process_continuous(continuous_iq, config) if continuous
                          else monitor.process(frames, config))
                self.assertEqual(tau, result.nfm_deemphasis_us)
                self.assertEqual(0, result.clipping_count)
                results.append(result.audio)
            self.assertFalse(np.allclose(results[0], results[1]))

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

    def test_continuous_nfm_retains_state_across_long_read_blocks(self) -> None:
        spec = next(item for item in FIXTURE_SPECS if item.mode == "nfm")
        source = np.resize(generate_iq(spec), int(192_000 * 5.1))
        config = AnalogMonitorConfig("nfm", 192_000.0, spec.carrier_offset_hz, spec.channel_bandwidth_hz)
        monitor = AnalogMonitor()
        whole = monitor.process_continuous(source, config)
        chunked = monitor.process_continuous(tuple(source[index : index + 4096] for index in range(0, source.size, 4096)), config)
        self.assertEqual(whole.pcm16, chunked.pcm16)
        self.assertGreaterEqual(whole.audio.size / whole.sample_rate_hz, 5.0)
        self.assertGreaterEqual(len(chunked.observation_times_s), 19)
        self.assertEqual(len(chunked.observation_times_s), len(chunked.channel_power_dbfs_trace))
        self.assertEqual(len(chunked.observation_times_s), len(chunked.residual_frequency_hz_trace))
        np.testing.assert_allclose(whole.channel_power_dbfs_trace, chunked.channel_power_dbfs_trace, atol=1e-12)
        np.testing.assert_allclose(whole.residual_frequency_hz_trace, chunked.residual_frequency_hz_trace, atol=1e-12)
        self.assertLess(max(abs(value) for value in chunked.residual_frequency_hz_trace), 10.0)

    def test_streaming_nfm_is_pcm_identical_across_worker_chunk_boundaries(self) -> None:
        sample_rate = 192_000.0
        duration = 6.0
        time_axis = np.arange(int(sample_rate * duration), dtype=np.float64) / sample_rate
        source = 0.7 * np.exp(
            2j * np.pi * 24_000.0 * time_axis
            - 2.2j * np.cos(2.0 * np.pi * 1_000.0 * time_axis)
        )
        config = AnalogMonitorConfig("nfm", sample_rate, 24_000.0, 16_000.0, voice_filter=True)
        whole = StreamingAnalogMonitor(config).process(source, volume=0.8)
        chunked_monitor = StreamingAnalogMonitor(config)
        chunks = tuple(
            chunked_monitor.process(source[index:index + 96_000], volume=0.8)
            for index in range(0, source.size, 96_000)
        )
        self.assertEqual(whole.pcm16, b"".join(chunk.pcm16 for chunk in chunks))
        self.assertTrue(all(chunk.quality_code == "streaming" for chunk in chunks))
        self.assertTrue(all(chunk.clipping_count == 0 for chunk in chunks))
        self.assertLessEqual(abs(chunks[-1].dominant_tone_hz - 1_000.0), 1.0)

    def test_channel_observation_tracks_known_frequency_drift(self) -> None:
        sample_rate = 192_000.0
        duration = 5.0
        count = int(sample_rate * duration)
        time_axis = np.arange(count, dtype=np.float64) / sample_rate
        injected_drift = -200.0 + 400.0 * time_axis / duration
        phase = 2.0 * np.pi * (
            24_000.0 * time_axis + np.cumsum(injected_drift) / sample_rate
        )
        audio = np.sin(2.0 * np.pi * 1_000.0 * time_axis)
        iq = 0.55 * (1.0 + 0.4 * audio) * np.exp(1j * phase)
        result = AnalogMonitor().process_continuous(
            tuple(iq[index:index + 4096] for index in range(0, iq.size, 4096)),
            AnalogMonitorConfig("am", sample_rate, 24_000.0, 16_000.0),
        )

        self.assertEqual(20, len(result.observation_times_s))
        self.assertAlmostEqual(-190.0, result.residual_frequency_hz_trace[0], delta=2.0)
        self.assertAlmostEqual(190.0, result.residual_frequency_hz_trace[-1], delta=2.0)
        self.assertLess(max(result.channel_power_dbfs_trace) - min(result.channel_power_dbfs_trace), 0.02)

    def test_nfm_deemphasis_has_expected_six_db_per_octave_slope(self) -> None:
        sample_rate = 48_000.0
        time_axis = np.arange(int(sample_rate), dtype=np.float64) / sample_rate
        source = np.sin(2.0 * np.pi * 300.0 * time_axis) + np.sin(2.0 * np.pi * 3_000.0 * time_axis)
        filtered = nfm_deemphasis(source, 750.0)

        def amplitude(values: np.ndarray, frequency_hz: float) -> float:
            reference = np.exp(-2j * np.pi * frequency_hz * time_axis)
            return 2.0 * abs(np.vdot(reference, values)) / values.size

        attenuation_db = 20.0 * np.log10(amplitude(filtered, 3_000.0) / amplitude(filtered, 300.0))
        self.assertAlmostEqual(-18.3, attenuation_db, delta=0.4)
        np.testing.assert_array_equal(nfm_deemphasis(source, 0.0), source)

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

    def test_dtmf_decoder_accepts_sustained_symbols_and_rejects_speech_tone(self) -> None:
        rate = 48_000
        tone_time = np.arange(int(0.12 * rate), dtype=np.float64) / rate
        silence = np.zeros(int(0.08 * rate), dtype=np.float64)

        def symbol(low: float, high: float) -> np.ndarray:
            return 0.35 * np.sin(2 * np.pi * low * tone_time) + 0.35 * np.sin(2 * np.pi * high * tone_time)

        payload = np.concatenate((symbol(770, 1336), silence, symbol(941, 1477)))
        self.assertEqual(("5", "#"), decode_dtmf(payload, rate))
        repeated = np.concatenate((symbol(770, 1336), silence, symbol(770, 1336)))
        self.assertEqual(("5", "5"), decode_dtmf(repeated, rate))
        speech_tone = np.sin(2 * np.pi * 1_000 * np.arange(rate) / rate)
        self.assertEqual((), decode_dtmf(speech_tone, rate))


if __name__ == "__main__":
    unittest.main()
