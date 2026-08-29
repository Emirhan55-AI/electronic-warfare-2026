from __future__ import annotations

import unittest

import numpy as np

from algorithms.p0 import IQFrameCodec, P0Channelizer


INPUT_RATE_HZ = 8_000_000
INPUT_CENTER_HZ = 100_000_000
OUTPUT_CENTER_HZ = 101_500_000
INPUT_SAMPLES = 16_384


def tone(frequency_hz: float, amplitude: float = 0.5) -> np.ndarray:
    time = np.arange(INPUT_SAMPLES, dtype=np.float64) / INPUT_RATE_HZ
    return amplitude * np.exp(2j * np.pi * frequency_hz * time)


def decode_ci8(payload: bytes) -> np.ndarray:
    values = np.frombuffer(payload, dtype=np.int8).astype(np.float64) / 128.0
    return values[0::2] + 1j * values[1::2]


class P0ChannelizerTests(unittest.TestCase):
    def test_frequency_translation_and_exact_fpga_frame_contract(self) -> None:
        channelizer = P0Channelizer()
        target_offset_hz = OUTPUT_CENTER_HZ - INPUT_CENTER_HZ
        result = channelizer.process(
            tone(target_offset_hz + 300_000),
            sequence_number=7,
            frame_id=11,
            input_sample_rate_hz=INPUT_RATE_HZ,
            input_center_frequency_hz=INPUT_CENTER_HZ,
            output_center_frequency_hz=OUTPUT_CENTER_HZ,
        )

        decoded = IQFrameCodec.decode(IQFrameCodec.encode(result.frame))
        self.assertEqual(decoded.sample_rate_hz, 2_000_000)
        self.assertEqual(decoded.center_frequency_hz, OUTPUT_CENTER_HZ)
        self.assertEqual(decoded.complex_sample_count, 4096)
        self.assertEqual(len(decoded.payload), 8192)
        self.assertEqual(result.saturated_components, 0)

        output = decode_ci8(decoded.payload)[128:]
        spectrum = np.abs(np.fft.fftshift(np.fft.fft(output)))
        frequencies = np.fft.fftshift(np.fft.fftfreq(output.size, 1.0 / 2_000_000))
        measured_hz = frequencies[int(np.argmax(spectrum))]
        self.assertLessEqual(abs(measured_hz - 300_000), 600)

    def test_filter_meets_locked_passband_and_stopband_envelope(self) -> None:
        channelizer = P0Channelizer()
        response = np.abs(np.fft.rfft(channelizer.taps, 262_144))
        frequency = np.fft.rfftfreq(262_144, 1.0 / INPUT_RATE_HZ)
        passband = response[frequency <= 800_000]
        stopband = response[frequency >= 1_000_000]
        passband_ripple_db = 20.0 * np.log10(np.max(passband) / np.min(passband))
        stopband_peak_db = 20.0 * np.log10(np.max(stopband))
        self.assertLessEqual(passband_ripple_db, 0.01)
        self.assertLessEqual(stopband_peak_db, -65.0)

    def test_hackrf_dc_component_is_rejected_by_offset_tuning(self) -> None:
        channelizer = P0Channelizer()
        desired = tone(OUTPUT_CENTER_HZ - INPUT_CENTER_HZ + 200_000, 0.35)
        dc_spur = np.full(INPUT_SAMPLES, 0.35 + 0.0j)
        result = channelizer.process(
            desired + dc_spur,
            sequence_number=0,
            frame_id=0,
            input_sample_rate_hz=INPUT_RATE_HZ,
            input_center_frequency_hz=INPUT_CENTER_HZ,
            output_center_frequency_hz=OUTPUT_CENTER_HZ,
        )
        output = decode_ci8(result.frame.payload)[128:]
        spectrum = np.abs(np.fft.fftshift(np.fft.fft(output)))
        frequency = np.fft.fftshift(np.fft.fftfreq(output.size, 1.0 / 2_000_000))
        desired_bin = int(np.argmin(np.abs(frequency - 200_000)))
        residual_dc_alias = float(np.max(spectrum[np.abs(frequency) >= 900_000]))
        self.assertGreater(float(spectrum[desired_bin]), 100.0 * residual_dc_alias)

    def test_live_profile_rejects_unsafe_zero_if_center(self) -> None:
        with self.assertRaisesRegex(ValueError, "DC-güvenli"):
            P0Channelizer().process(
                np.zeros(INPUT_SAMPLES, dtype=np.complex128),
                sequence_number=0,
                frame_id=0,
                input_sample_rate_hz=INPUT_RATE_HZ,
                input_center_frequency_hz=INPUT_CENTER_HZ,
                output_center_frequency_hz=INPUT_CENTER_HZ,
            )

    def test_stream_binding_requires_reset_before_retune(self) -> None:
        channelizer = P0Channelizer()
        arguments = dict(
            samples=np.zeros(INPUT_SAMPLES, dtype=np.complex128),
            sequence_number=0,
            frame_id=0,
            input_sample_rate_hz=INPUT_RATE_HZ,
            input_center_frequency_hz=INPUT_CENTER_HZ,
            output_center_frequency_hz=OUTPUT_CENTER_HZ,
        )
        channelizer.process(**arguments)
        arguments["output_center_frequency_hz"] = OUTPUT_CENTER_HZ + 100_000
        with self.assertRaisesRegex(ValueError, "sıfırlanmalıdır"):
            channelizer.process(**arguments)
        channelizer.reset()
        channelizer.process(**arguments)


if __name__ == "__main__":
    unittest.main()
