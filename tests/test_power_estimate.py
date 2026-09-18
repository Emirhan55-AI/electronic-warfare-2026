import math

from app.operator_console.power_estimate import estimate_hackrf_input_power_dbm


def test_nominal_gain_and_scale_are_removed_from_uncalibrated_estimate():
    estimate = estimate_hackrf_input_power_dbm(
        -31.5,
        frequency_hz=820_000_000.0,
        lna_gain_db=16,
        vga_gain_db=16,
        rf_amplifier=False,
        output_amplitude_scale=1.0,
    )
    assert estimate is not None
    assert estimate.power_dbm == -68.5
    assert estimate.uncertainty_db == 15.0

    scaled = estimate_hackrf_input_power_dbm(
        -31.5,
        frequency_hz=820_000_000.0,
        lna_gain_db=16,
        vga_gain_db=16,
        rf_amplifier=True,
        output_amplitude_scale=2.0,
    )
    assert scaled is not None
    assert math.isclose(scaled.power_dbm, -85.520599913, abs_tol=1e-9)
    assert scaled.uncertainty_db == 18.0


def test_invalid_or_unknown_context_does_not_create_estimated_dbm():
    common = dict(
        frequency_hz=820_000_000.0,
        lna_gain_db=16,
        vga_gain_db=16,
        rf_amplifier=False,
        output_amplitude_scale=1.0,
    )
    assert estimate_hackrf_input_power_dbm(float("nan"), **common) is None
    assert estimate_hackrf_input_power_dbm(-31.5, **{**common, "lna_gain_db": 12}) is None
    assert estimate_hackrf_input_power_dbm(-31.5, **{**common, "output_amplitude_scale": None}) is None
