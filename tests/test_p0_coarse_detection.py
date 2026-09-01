import numpy as np
import pytest

from algorithms.p0.coarse_detection import CoarseSpectrumDetector
from algorithms.p0.detection import MultiscaleDetector


SAMPLE_RATE_HZ = 8_000_000.0
CENTER_HZ = 2_401_500_000.0


def _ci8_hann_power(width_hz: float, seed: int, *, offset_hz: float = 0.0) -> np.ndarray:
    count = 16_384
    width = round(width_hz / SAMPLE_RATE_HZ * count)
    first = count // 2 + round(offset_hz / SAMPLE_RATE_HZ * count) - width // 2
    stop = first + width
    expected = np.ones(count, dtype=np.float64)
    expected[first:stop] += 25.0
    rng = np.random.default_rng(seed)
    coefficients = (
        rng.normal(size=count) + 1j * rng.normal(size=count)
    ) * np.sqrt(expected / 2.0)
    iq = np.fft.ifft(np.fft.ifftshift(coefficients))
    iq *= 0.65 / max(np.max(np.abs(iq.real)), np.max(np.abs(iq.imag)))
    packed = np.column_stack((np.rint(iq.real * 128), np.rint(iq.imag * 128))).astype(np.int8)
    decoded = (packed[:, 0].astype(float) + 1j * packed[:, 1].astype(float)) / 128.0
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(count) / count)
    return np.abs(np.fft.fftshift(np.fft.fft(decoded * window))) ** 2


@pytest.mark.parametrize("width_hz", (100_000.0, 500_000.0, 1_000_000.0, 2_000_000.0))
def test_wide_preview_produces_temporally_confirmed_host_candidate(width_hz: float) -> None:
    detector = CoarseSpectrumDetector()
    result = None
    for index in range(3):
        result = detector.process(
            _ci8_hann_power(width_hz, 20260831 + index, offset_hz=-1_500_000.0),
            center_frequency_hz=CENTER_HZ,
            sample_rate_hz=SAMPLE_RATE_HZ,
            sequence_number=index * 16,
        )
    assert result is not None
    confirmed = [item for item in result.candidates if item.state == "confirmed" and item.observed_this_frame]
    assert confirmed
    assert any(item.lower_frequency_hz <= 2_400_000_000.0 <= item.upper_frequency_hz for item in confirmed)


@pytest.mark.parametrize("family", ("flat", "slope", "step"))
def test_noise_only_families_do_not_create_coarse_candidate(family: str) -> None:
    rng = np.random.default_rng(501)
    scale = np.ones(16_384, dtype=np.float64)
    if family == "slope":
        scale = np.power(10.0, np.linspace(-6.0, 6.0, scale.size) / 10.0)
    elif family == "step":
        scale[scale.size // 2:] = 10.0 ** 1.2
    result = CoarseSpectrumDetector().process(
        rng.exponential(scale),
        center_frequency_hz=CENTER_HZ,
        sample_rate_hz=SAMPLE_RATE_HZ,
        sequence_number=0,
    )
    assert result.candidates == ()


def test_full_eight_mhz_occupancy_remains_explicitly_unresolved() -> None:
    detector = CoarseSpectrumDetector()
    result = detector.process(
        _ci8_hann_power(8_000_000.0, 703),
        center_frequency_hz=CENTER_HZ,
        sample_rate_hz=SAMPLE_RATE_HZ,
        sequence_number=0,
    )
    assert result.candidates == ()
    assert "bağımsız gürültü referansı yoktur" in result.limitation


def test_binding_change_resets_temporal_confirmation() -> None:
    detector = CoarseSpectrumDetector()
    power = _ci8_hann_power(1_000_000.0, 803, offset_hz=-1_500_000.0)
    first = detector.process(power, center_frequency_hz=CENTER_HZ,
                             sample_rate_hz=SAMPLE_RATE_HZ, sequence_number=0)
    second = detector.process(power, center_frequency_hz=CENTER_HZ + 1_000_000.0,
                              sample_rate_hz=SAMPLE_RATE_HZ, sequence_number=16)
    assert first.candidates and all(item.state == "tentative" for item in first.candidates)
    assert second.candidates and all(item.state == "tentative" for item in second.candidates)


def test_vectorized_host_stage_matches_canonical_candidate_fields() -> None:
    rng = np.random.default_rng(901)
    power = rng.exponential(1.0, 4096)
    power[1200:1700] += 20.0
    coarse = CoarseSpectrumDetector()
    actual = coarse._vectorized_candidates(power)
    expected = MultiscaleDetector().process(power, frame_id=0).candidates
    assert actual == expected


@pytest.mark.parametrize("bad", (np.ones(4096), np.full(16_384, np.nan), np.full(16_384, -1.0)))
def test_invalid_wide_power_is_rejected(bad: np.ndarray) -> None:
    with pytest.raises(ValueError):
        CoarseSpectrumDetector().process(
            bad,
            center_frequency_hz=CENTER_HZ,
            sample_rate_hz=SAMPLE_RATE_HZ,
            sequence_number=0,
        )
