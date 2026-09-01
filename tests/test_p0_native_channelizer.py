"""Native real-time channelizer equivalence against the NumPy reference."""

from __future__ import annotations

import numpy as np
import pytest

from algorithms.p0 import (
    NativeP0Channelizer,
    P0Channelizer,
    find_native_channelizer_library,
)


@pytest.mark.skipif(find_native_channelizer_library() is None, reason="Yerel kanal seçici derlenmemiş.")
def test_native_channelizer_is_ci8_exact_across_stream_boundaries_and_offsets() -> None:
    rng = np.random.default_rng(20260831)
    for offset_hz in (1_250_000, 1_300_000, 1_500_000, 2_750_000, -1_500_000):
        reference = P0Channelizer()
        native = NativeP0Channelizer()
        for sequence in range(8):
            payload = rng.integers(-64, 65, 32_768, dtype=np.int8).tobytes()
            arguments = dict(
                sequence_number=sequence,
                frame_id=sequence,
                input_sample_rate_hz=8_000_000,
                input_center_frequency_hz=100_000_000,
                output_center_frequency_hz=100_000_000 + offset_hz,
            )
            expected, expected_input_saturated = reference.process_ci8(payload, **arguments)
            observed, observed_input_saturated = native.process_ci8(payload, **arguments)
            assert observed.frame.payload == expected.frame.payload
            assert observed.saturated_components == expected.saturated_components
            assert observed_input_saturated == expected_input_saturated == 0


@pytest.mark.skipif(find_native_channelizer_library() is None, reason="Yerel kanal seçici derlenmemiş.")
def test_native_channelizer_counts_clipped_input_and_resets_binding() -> None:
    native = NativeP0Channelizer()
    payload = bytes([127, 128]) * 16_384
    result, input_saturated = native.process_ci8(
        payload,
        sequence_number=0,
        frame_id=0,
        input_sample_rate_hz=8_000_000,
        input_center_frequency_hz=100_000_000,
        output_center_frequency_hz=101_500_000,
    )
    assert input_saturated == 32_768
    assert result.frame.payload == bytes(8_192)
    native.reset()
    native.process_ci8(
        bytes(32_768),
        sequence_number=1,
        frame_id=1,
        input_sample_rate_hz=8_000_000,
        input_center_frequency_hz=100_000_000,
        output_center_frequency_hz=98_500_000,
    )
