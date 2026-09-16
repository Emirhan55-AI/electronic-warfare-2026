from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from algorithms.p0 import IQFrame
from app.operator_console.live_ed import LiveEDConfiguration, LiveEDPreview
from app.operator_console.quick_runtime import _LiveTask
from platforms.acquisition import AcquisitionError


@pytest.mark.parametrize("size", [4096, 8192, 16384])
def test_display_fft_uses_real_samples_without_changing_detection_spectrum(size):
    task = _LiveTask(1, SimpleNamespace())
    task.display_processor = SpectrumProcessor(SpectrumConfig(frame_length=size))
    samples = np.zeros(32768, dtype=np.int8)
    samples[::2] = np.rint(40 * np.cos(2 * np.pi * np.arange(16384) / 32)).astype(np.int8)
    frame = IQFrame(sequence_number=0, center_frequency_hz=100_000_000,
                    sample_rate_hz=8_000_000, payload=samples.tobytes())
    task._process_preview(LiveEDPreview(0, frame, 1.0, frame))
    _, canonical, visual, _ = task.preview_mailbox.take()
    assert canonical.frame_length == 16384
    assert visual.frame_length == size
    assert visual.bin_spacing_hz == 8_000_000 / size
    assert task.coarse_mailbox.take() is not None


@pytest.mark.parametrize("fpga_fft_size", [8192, 16384])
def test_larger_fpga_fft_preview_uses_bounded_real_presentation_window(fpga_fft_size):
    task = _LiveTask(1, SimpleNamespace())
    complex_samples = 4 * fpga_fft_size
    payload = np.zeros(complex_samples * 2, dtype=np.int8)
    payload[::2] = np.rint(
        40 * np.cos(2 * np.pi * np.arange(complex_samples) / 32)
    ).astype(np.int8)
    output = IQFrame(
        sequence_number=0,
        center_frequency_hz=100_000_000,
        sample_rate_hz=2_000_000,
        payload=bytes(fpga_fft_size * 2),
    )
    display = IQFrame(
        sequence_number=0,
        center_frequency_hz=102_000_000,
        sample_rate_hz=8_000_000,
        payload=payload.tobytes(),
    )

    task._process_preview(LiveEDPreview(0, output, 1.0, display))

    _, canonical, visual, _ = task.preview_mailbox.take()
    assert canonical.frame_length == 16384
    assert visual.frame_length == 16384
    assert canonical.sample_rate_hz == 8_000_000
    assert task.coarse_mailbox.take() is not None


@pytest.mark.parametrize("size", [True, 8192.0, 2048, 32768, 65536])
def test_unsupported_display_fft_is_rejected(size):
    with pytest.raises(AcquisitionError):
        replace(LiveEDConfiguration(100_000_000, "0" * 32), display_fft_size=size)
