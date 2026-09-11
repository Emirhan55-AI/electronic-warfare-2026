"""KTR-4.2: adayın fiziksel birim, girdi ve negatif kontrol kapıları."""
import numpy as np
import pytest
from algorithms.parameters.refined_candidate import measure_candidate


def tone(offset=78123., amplitude=.15):
    t=np.arange(16384)/2_000_000
    rng=np.random.default_rng(911)
    return (amplitude*np.exp(2j*np.pi*offset*t)+.0005*(rng.normal(size=len(t))+1j*rng.normal(size=len(t)))).reshape(4,4096)


def measure(x, center=700_000_000):
    return measure_candidate(x,sample_rate_hz=2_000_000,center_frequency_hz=center,lower_bin=1950,upper_bin=2440)


def test_resolved_line_is_independent_of_rf_center_and_digital_scale():
    original=measure(tone()); shifted=measure(tone(),center=900_000_000)
    scaled=measure(tone()*2)
    assert original.reason is None
    assert abs(original.line_hz-700_078123)<30
    assert abs(shifted.line_hz-original.line_hz-200_000_000)<1e-5
    assert abs(scaled.power_dbfs-original.power_dbfs-20*np.log10(2))<1e-8
    assert abs(scaled.obw99_hz-original.obw99_hz)<1e-7


def test_noise_and_clipping_never_produce_numeric_measurement():
    rng=np.random.default_rng(912)
    noise=.05*(rng.normal(size=(4,4096))+1j*rng.normal(size=(4,4096)))
    assert measure(noise).power_dbfs is None
    clipped=tone();clipped[1,300]=1+0j
    assert measure(clipped).reason=='clipped_iq'


@pytest.mark.parametrize('bad',[np.zeros((3,4096)),np.full((4,4096),np.nan)])
def test_invalid_shape_and_nonfinite_iq_rejected(bad):
    with pytest.raises(ValueError):measure(bad)


def test_line_outside_selected_span_is_not_recovered_as_target():
    result=measure(tone(offset=-400000))
    assert result.line_hz is None


def test_receiver_dc_does_not_replace_weak_offset_carrier():
    result=measure(tone(amplitude=.003)+.04+.03j)
    assert result.line_hz is not None
    assert abs(result.line_hz-700078123)<40


def test_external_emission_invalidates_only_full_emission_bandwidth():
    t=np.arange(16384)/2_000_000
    samples=tone()+(.02*np.exp(-2j*np.pi*400000*t)).reshape(4,4096)
    result=measure(samples)
    assert result.obw99_hz is None
    assert result.bandwidth_reason=='outside_energy_or_noise_uncertainty'
    assert result.line_hz is not None
    assert result.power_dbfs is not None
    assert result.features


def test_one_tail_above_half_percent_is_not_hidden_by_total_one_percent():
    t=np.arange(16384)/2_000_000
    # 0.7% of main-tone power, all on the low-frequency side: total <1%,
    # but lower 0.5% quantile cannot lie inside the selected analysis span.
    samples=tone()+(.15*np.sqrt(.007)*np.exp(-2j*np.pi*400000*t)).reshape(4,4096)
    result=measure(samples)
    assert result.obw99_hz is None
    assert result.bandwidth_reason=='outside_energy_or_noise_uncertainty'
