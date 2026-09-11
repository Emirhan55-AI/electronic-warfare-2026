"""KTR-4.2: Replay dosyası, rastgele sembol ve analog referans doğrulaması."""
import numpy as np
import pytest
from scripts.prepare_parameter_replay import FS, RATE, make_wave, encode, inspect


def test_c16_iq_order_scale_and_little_endian():
    raw = encode(np.array([.25 - .5j, -.125 + .125j]))
    assert raw == b'\x00\x20\x00\xc0\x00\xf0\x00\x10'
    with pytest.raises(ValueError):
        encode(np.array([1 + 0j]))


@pytest.mark.parametrize('family', ['BPSK', 'QPSK', 'FSK'])
def test_random_symbols_and_bitstream_are_reproducible(family):
    x, truth = make_wave(family, 2, 1234)
    y, again = make_wave(family, 2, 1234)
    assert truth == again and np.array_equal(x, y)
    assert len(x) == 2 * FS
    assert min(truth['symbol_counts']) / sum(truth['symbol_counts']) > .20
    # Sabit kısa döngü yerine değişken sembol dizisi.
    middle = x[FS // 2:FS]
    assert np.mean(abs(middle[4 * (FS // RATE):] - middle[:-4 * (FS // RATE)])) > .05
    data = encode(x)
    stats = inspect(data)
    assert stats['first_last_zero']
    assert stats['peak_component'] < .8
    assert stats['duration_s'] == 2


def test_analog_reference_parameters_independently_demodulate():
    am, _ = make_wave('AM', 2, 1)
    fm, _ = make_wave('NFM', 2, 1)
    window = slice(FS // 2, FS)
    env = abs(am[window])
    assert abs((env.max() - env.min()) / (env.max() + env.min()) - .7) < 1e-5
    frequency = np.angle(fm[window][1:] * fm[window][:-1].conj()) * FS / (2 * np.pi)
    assert abs(np.max(frequency) - 6000) < 1
    assert abs(np.min(frequency) + 6000) < 1


def test_cw_carrier_is_not_removed_by_reference_spectrum():
    cw, _ = make_wave('CW', 2, 1)
    stats = inspect(encode(cw))
    assert np.isfinite(stats['reference_obw99_hz'])
    assert 0 < stats['reference_obw99_hz'] < 4 * stats['reference_fft_bin_hz']
    assert abs(stats['digital_power_dbfs'] - 20 * np.log10(.25)) < 1e-10
