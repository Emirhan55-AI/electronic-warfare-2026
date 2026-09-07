import numpy as np
import pytest
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor, SpectrumError


@pytest.mark.parametrize("remove_dc", [False, True])
@pytest.mark.parametrize("size", [4096, 16384])
def test_detection_power_exactly_matches_full_reference(size, remove_dc):
    processor = SpectrumProcessor(SpectrumConfig(frame_length=size, remove_dc=remove_dc))
    rng = np.random.default_rng(20260907)
    for samples in [np.zeros(size), np.ones(size),
                    np.exp(2j * np.pi * np.arange(size) * .137),
                    rng.integers(-128, 128, size) / 128 + 1j * rng.integers(-128, 128, size) / 128]:
        expected = processor.process(samples, sample_rate_hz=8e6,
                                     center_frequency_hz=826e6).display.bin_power_fs2
        actual = processor.detection_power(samples)
        np.testing.assert_array_equal(actual, expected)
        assert not actual.flags.writeable


@pytest.mark.parametrize("samples,code", [([1], "frame_size_mismatch"),
    ([complex(float('nan'), 0)] * 4096, "nonfinite_input")])
def test_detection_power_rejects_invalid_frames(samples, code):
    with pytest.raises(SpectrumError) as error:
        SpectrumProcessor().detection_power(samples)
    assert error.value.code == code
