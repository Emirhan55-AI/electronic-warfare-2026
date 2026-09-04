import numpy as np
import pytest

from app.operator_console.integrated_spectrum import (
    integrated_candidate_near,
    integrated_spectrum_candidates,
)


def _spectra(*, occupied_frames=80, total_frames=80):
    rng = np.random.default_rng(417)
    frequencies = 955_000_000.0 + np.arange(2048) * 488.28125
    power = rng.exponential(1.0, size=(total_frames, frequencies.size))
    target = int(np.argmin(np.abs(frequencies - 955_700_000.0)))
    power[:occupied_frames, target] += 9.0
    return frequencies, power, target


def test_persistent_unknown_tone_is_nominated_without_frequency_truth():
    frequencies, power, target = _spectra()
    candidates = integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=955_400_000.0,
        upper_hz=956_000_000.0,
    )

    assert len(candidates) == 1
    assert candidates[0].frequency_hz == frequencies[target]
    assert candidates[0].occupancy >= 0.75
    assert candidates[0].peak_to_noise_db >= 6.0


def test_intermittent_peak_is_not_promoted_by_mean_power_alone():
    frequencies, power, _ = _spectra(occupied_frames=40)
    assert integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=955_400_000.0,
        upper_hz=956_000_000.0,
    ) == ()


def test_noise_only_does_not_create_candidate():
    frequencies, power, _ = _spectra(occupied_frames=0)
    assert integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=955_400_000.0,
        upper_hz=956_000_000.0,
    ) == ()


def test_known_target_helper_only_selects_nearby_persistent_peak():
    frequencies, power, target = _spectra()
    result = integrated_candidate_near(frequencies, power, 955_700_000.0)
    assert result is not None
    assert result.frequency_hz == frequencies[target]
    assert integrated_candidate_near(frequencies, power, 956_500_000.0) is None


@pytest.mark.parametrize("center_hz", [40_000_000.0, 854_000_000.0, 2_900_000_000.0, 5_800_000_000.0])
def test_detection_math_is_invariant_across_supported_rf_centers(center_hz):
    rng = np.random.default_rng(731)
    spacing = 488.28125
    frequencies = center_hz + (np.arange(2048) - 1024) * spacing
    power = rng.exponential(1.0, size=(96, frequencies.size))
    target = 1173
    power[:, target] += 10.0

    result = integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=center_hz - 300_000.0,
        upper_hz=center_hz + 300_000.0,
    )

    assert len(result) == 1
    assert result[0].peak_frequency_hz == frequencies[target]
    assert result[0].center_method == "spectral_peak"


def test_symmetric_modulation_components_report_emission_centroid_not_strongest_line():
    rng = np.random.default_rng(919)
    spacing = 500.0
    center_hz = 1_742_345_000.0
    frequencies = center_hz + (np.arange(4096) - 2048) * spacing
    power = rng.exponential(1.0, size=(96, frequencies.size))
    # Generic 1 kHz-spaced symmetric components.  The lower outer component
    # is deliberately strongest, so peak frequency and emission centre differ.
    offsets_and_power = [(-12_000.0, 12.0), (-11_000.0, 2.0), (-10_000.0, 2.0),
                         (-9_000.0, 2.0), (-8_000.0, 2.0), (-7_000.0, 2.0),
                         (-6_000.0, 2.0), (-5_000.0, 2.0), (-4_000.0, 2.0),
                         (-3_000.0, 2.0), (-2_000.0, 2.0), (-1_000.0, 2.0),
                         (0.0, 2.0), (1_000.0, 2.0), (2_000.0, 2.0),
                         (3_000.0, 2.0), (4_000.0, 2.0), (5_000.0, 2.0),
                         (6_000.0, 2.0), (7_000.0, 2.0), (8_000.0, 2.0),
                         (9_000.0, 2.0), (10_000.0, 2.0), (11_000.0, 2.0),
                         (12_000.0, 12.0)]
    for offset_hz, added_power in offsets_and_power:
        index = int(np.argmin(np.abs(frequencies - (center_hz + offset_hz))))
        power[:, index] += added_power

    result = integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=center_hz - 100_000.0,
        upper_hz=center_hz + 100_000.0,
    )

    assert len(result) == 1
    assert result[0].component_count > 1
    assert result[0].center_method == "persistent_component_centroid"
    assert abs(result[0].frequency_hz - center_hz) <= spacing
    assert abs(result[0].peak_frequency_hz - center_hz) >= 11_000.0


def test_nearby_unrelated_carriers_are_not_averaged_into_false_center():
    rng = np.random.default_rng(1201)
    spacing = 500.0
    center_hz = 433_500_000.0
    frequencies = center_hz + (np.arange(4096) - 2048) * spacing
    power = rng.exponential(1.0, size=(96, frequencies.size))
    first = int(np.argmin(np.abs(frequencies - (center_hz - 20_000.0))))
    second = int(np.argmin(np.abs(frequencies - (center_hz + 20_000.0))))
    power[:, first] += 12.0
    power[:, second] += 11.0

    result = integrated_spectrum_candidates(
        frequencies,
        power,
        lower_hz=center_hz - 100_000.0,
        upper_hz=center_hz + 100_000.0,
    )

    assert len(result) == 2
    assert [item.peak_frequency_hz for item in result] == [frequencies[first], frequencies[second]]
    assert all(item.center_method == "spectral_peak" for item in result)
