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


@pytest.mark.parametrize("size", [True, 8192.0, 2048, 32768, 65536])
def test_unsupported_display_fft_is_rejected(size):
    with pytest.raises(AcquisitionError):
        replace(LiveEDConfiguration(100_000_000, "0" * 32), display_fft_size=size)
