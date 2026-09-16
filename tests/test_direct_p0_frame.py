from __future__ import annotations

import numpy as np
import pytest

from algorithms.p0.direct_frame import DirectP0FrameAdapter, DirectP0Profile


def test_direct_adapter_preserves_exact_10msps_ci8_payload_and_metadata() -> None:
    raw = np.arange(8192, dtype=np.uint8).tobytes()
    adapter = DirectP0FrameAdapter()

    result, saturated = adapter.process_ci8(
        raw,
        sequence_number=7,
        frame_id=11,
        input_sample_rate_hz=10_000_000,
        input_center_frequency_hz=820_000_000,
        output_center_frequency_hz=820_000_000,
    )

    assert result.frame.payload == raw
    assert result.frame.sample_rate_hz == 10_000_000
    assert result.frame.center_frequency_hz == 820_000_000
    assert result.frame.complex_sample_count == 4096
    assert saturated == 64
    assert result.saturated_components == 0


def test_direct_adapter_rejects_frequency_conversion_and_wrong_profile() -> None:
    adapter = DirectP0FrameAdapter()
    with pytest.raises(ValueError, match="aynı"):
        adapter.process_ci8(
            bytes(8192), sequence_number=0, frame_id=0,
            input_sample_rate_hz=10_000_000,
            input_center_frequency_hz=820_000_000,
            output_center_frequency_hz=821_000_000,
        )
    with pytest.raises(ValueError, match="10 MS/s"):
        DirectP0Profile(input_sample_rate_hz=8_000_000)
