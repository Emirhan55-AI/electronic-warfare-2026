"""Hedef kanal, komşu reddi ve yeni modelin kaynak bağı."""
import hashlib
from pathlib import Path

import numpy as np
import pytest

from digital_analog_detection.selected_integration import classify_parameter_frames, MODEL
from digital_analog_detection.channel_features import selected_channel_features


@pytest.mark.parametrize("amplitude", [0., .5, 2., 4.])
def test_selected_am_survives_outside_neighbor(amplitude):
    fs, n = 2_000_000., 16384
    t = np.arange(n) / fs
    rng = np.random.default_rng(20260916)
    target = (1 + .65 * np.cos(2 * np.pi * 1800 * t)) * np.exp(2j * np.pi * 25000 * t)
    noise = .01 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    symbols = np.repeat(rng.choice((-1., 1.), size=(n+19)//20), 20)[:n]
    neighbor = amplitude * symbols * np.exp(2j * np.pi * 220000 * t)
    frames = (target + noise + neighbor).reshape(4,4096)
    result = classify_parameter_frames(frames, sample_rate_hz=fs, lower_shifted_bin=2030,
        upper_shifted_bin=2170, snr_db=20.)
    assert (result.state, result.value) == ('valid', 'Analog')
    assert result.filter_bandwidth_hz < 140000
    assert result.physical_acceptance is result.product_acceptance is False


def test_model_matches_preprocessing_sources():
    root = Path(__file__).resolve().parents[1]
    assert all(hashlib.sha256((root/path).read_bytes()).hexdigest() == expected
               for path, expected in MODEL['training_source_sha256'].items())


@pytest.mark.parametrize('lower,upper', [(55,100), (100,100), (300,200), (3900,4040)])
def test_invalid_channel_rejected(lower, upper):
    with pytest.raises(ValueError):
        selected_channel_features(np.ones((4,4096)), lower, upper)


def test_wrong_rate_low_snr_and_empty_channel_abstain():
    for rate, snr in ((1000000.,20.), (2000000.,3.), (2000000.,20.)):
        result=classify_parameter_frames(np.zeros((4,4096)), sample_rate_hz=rate,
            lower_shifted_bin=2030,upper_shifted_bin=2170,snr_db=snr)
        assert result.state == 'uncertain' and result.value is None


def test_outside_training_features_reject_even_with_high_model_score():
    rng = np.random.default_rng(1)
    samples = rng.normal(size=(4,4096)) + 1j * rng.normal(size=(4,4096))
    result = classify_parameter_frames(samples,sample_rate_hz=2000000.,
        lower_shifted_bin=56,upper_shifted_bin=4039,snr_db=20.)
    assert result.confidence > .99
    assert result.state == 'uncertain' and result.value is None
    assert 'eğitim kapsamının dışında' in result.reason
