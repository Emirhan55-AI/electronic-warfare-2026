import numpy as np
import pytest

from algorithms.p0.detection import OSCFARDetector
from algorithms.p0.st05_wideband import (
    ST05_WIDEBAND_PROFILE,
    ST05WidebandDetector,
)


def _frames(profile: np.ndarray, *, seed: int, count: int = 8) -> np.ndarray:
    return np.random.default_rng(seed).exponential(
        scale=profile,
        size=(count, profile.size),
    )


def _profile(*supports: tuple[int, int, float]) -> np.ndarray:
    values = np.ones(4096, dtype=np.float64)
    for start, stop, excess in supports:
        values[start:stop] += excess
    return values


def _coverage(start: int, stop: int, observed_start: int, observed_end: int) -> float:
    return max(0, min(stop, observed_end + 1) - max(start, observed_start)) / (stop - start)


def test_profile_keeps_existing_threshold_and_adds_temporal_flank_evidence() -> None:
    assert ST05_WIDEBAND_PROFILE.seed_multiplier == 2.5
    assert ST05_WIDEBAND_PROFILE.minimum_frames == 8
    assert ST05_WIDEBAND_PROFILE.minimum_occupancy == 0.75
    assert ST05_WIDEBAND_PROFILE.flank_bins == 64


@pytest.mark.parametrize("width", (96, 512, 1024, 2048))
def test_bounded_wide_emissions_are_recovered_with_useful_boundaries(width: int) -> None:
    start = (4096 - width) // 2
    result = ST05WidebandDetector().process(
        _frames(_profile((start, start + width, 12.0)), seed=1100 + width)
    )

    matching = [
        item for item in result.candidates
        if _coverage(start, start + width, item.start_bin, item.end_bin) >= 0.85
    ]
    assert result.decision == "bounded_candidates"
    assert len(matching) == 1
    assert matching[0].occupancy >= 0.75


@pytest.mark.parametrize("family", ("flat", "slope", "step"))
def test_colored_noise_does_not_become_a_confirmed_bounded_emission(family: str) -> None:
    if family == "flat":
        profile = np.ones(4096, dtype=np.float64)
    elif family == "slope":
        profile = np.power(10.0, np.linspace(-6.0, 6.0, 4096) / 10.0)
    else:
        profile = np.ones(4096, dtype=np.float64)
        profile[2048:] = 10.0 ** 1.2

    result = ST05WidebandDetector().process(_frames(profile, seed=2200))

    assert result.candidates == ()
    assert result.absolute_absence_supported is False
    assert result.reference_scope == "relative_spectral_only"


def test_edge_support_requests_a_retune_instead_of_claiming_absence() -> None:
    result = ST05WidebandDetector().process(
        _frames(_profile((0, 512, 12.0)), seed=3300)
    )

    assert result.decision == "retune_required"
    assert result.candidates == ()
    assert result.unresolved_supports
    assert {item.reason for item in result.unresolved_supports} == {
        "independent_flanks_unavailable"
    }


def test_full_window_noise_like_emission_never_produces_an_absolute_absence_claim() -> None:
    result = ST05WidebandDetector().process(
        _frames(np.full(4096, 16.0, dtype=np.float64), seed=4400)
    )

    assert result.candidates == ()
    assert result.absolute_absence_supported is False
    assert result.reference_scope == "relative_spectral_only"


def test_persistent_strong_and_weak_emissions_are_kept_separate() -> None:
    truth = ((900, 1100, 20.0), (2700, 2900, 7.0))
    result = ST05WidebandDetector().process(_frames(_profile(*truth), seed=5500))

    assert len(result.candidates) == 2
    assert all(
        any(_coverage(start, stop, item.start_bin, item.end_bin) >= 0.85 for item in result.candidates)
        for start, stop, _ in truth
    )


def test_close_supports_below_the_resolution_gap_are_merged() -> None:
    result = ST05WidebandDetector().process(
        _frames(_profile((1700, 1900, 12.0), (1903, 2103, 12.0)), seed=6600)
    )

    assert len(result.candidates) == 1
    assert _coverage(1700, 2103, result.candidates[0].start_bin, result.candidates[0].end_bin) >= 0.85


def test_short_transient_does_not_pass_the_occupancy_gate() -> None:
    frames = _frames(_profile(), seed=7700)
    transient = _frames(_profile((1800, 2300, 20.0)), seed=7701, count=2)
    frames[:2] = transient

    result = ST05WidebandDetector().process(frames)

    assert result.candidates == ()


def test_narrowband_os_cfar_remains_the_owner_of_a_single_line() -> None:
    profile = _profile((2048, 2049, 100.0))
    frames = _frames(profile, seed=8800)

    wide = ST05WidebandDetector().process(frames)
    narrow = OSCFARDetector().process(np.mean(frames, axis=0), frame_id=0)

    assert wide.candidates == ()
    assert any(item.start_bin <= 2048 <= item.end_bin for item in narrow.candidates)


@pytest.mark.parametrize(
    "frames",
    (
        np.ones((7, 4096), dtype=np.float64),
        np.ones((8, 4095), dtype=np.float64),
        np.full((8, 4096), np.nan, dtype=np.float64),
        np.full((8, 4096), -1.0, dtype=np.float64),
    ),
)
def test_invalid_or_insufficient_power_is_rejected(frames: np.ndarray) -> None:
    with pytest.raises(ValueError):
        ST05WidebandDetector().process(frames)
