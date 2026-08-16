"""Deterministic P0 ED fixtures; all values are synthetic and non-RF."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


FRAME_LENGTH = 4096
SAMPLE_RATE_HZ = 1_024_000.0
CENTER_FREQUENCY_HZ = 100_000_000.0


@dataclass(frozen=True)
class P0Fixture:
    fixture_id: str
    iq: npt.NDArray[np.complex128]
    target_frequencies_hz: tuple[float, ...]
    expected_bandwidth_hz: float | None
    expected_domain: str | None
    parameter_mode: str = "detected"
    known_region_bins: tuple[int, int] | None = None


def build_fixtures() -> tuple[P0Fixture, ...]:
    count = FRAME_LENGTH
    sample_rate = SAMPLE_RATE_HZ
    center = CENTER_FREQUENCY_HZ
    time = np.arange(count, dtype=np.float64) / sample_rate

    def noise(seed: int, scale: float = 0.003) -> npt.NDArray[np.complex128]:
        rng = np.random.default_rng(seed)
        return scale * (rng.normal(size=count) + 1j * rng.normal(size=count))

    tone = 0.45 * np.exp(2j * np.pi * 40_000.0 * time) + noise(1)
    am = 0.35 * (1.0 + 0.6 * np.sin(2.0 * np.pi * 1_000.0 * time)) * np.exp(2j * np.pi * 60_000.0 * time) + noise(2)
    audio = np.sin(2.0 * np.pi * 700.0 * time)
    nfm_phase = 2.0 * np.pi * 90_000.0 * time + 2.0 * np.pi * 500.0 * np.cumsum(audio) / sample_rate
    nfm = 0.6 * np.exp(1j * nfm_phase) + noise(3)
    ook_gate = np.repeat(np.asarray([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.float64), count // 8)
    digital = 0.6 * ook_gate * np.exp(-2j * np.pi * 80_000.0 * time) + noise(4)

    rng = np.random.default_rng(5)
    wide_spectrum = np.zeros(count, dtype=np.complex128)
    wide_bins = np.arange(count // 2 + 300, count // 2 + 381)
    wide_spectrum[wide_bins] = rng.normal(size=wide_bins.size) + 1j * rng.normal(size=wide_bins.size)
    wide_frequencies = center + (wide_bins - count // 2) * sample_rate / count
    wide_truth_centroid = float(np.sum(wide_frequencies * np.abs(wide_spectrum[wide_bins]) ** 2) / np.sum(np.abs(wide_spectrum[wide_bins]) ** 2))
    wide = np.fft.ifft(np.fft.ifftshift(wide_spectrum)) * count * 0.04 + noise(6, 0.001)

    rectangular_spectrum = np.zeros(count, dtype=np.complex128)
    rectangular_bins = np.arange(count // 2 - 10, count // 2 + 11)
    rectangular_spectrum[rectangular_bins] = np.exp(1j * np.linspace(0.0, np.pi, rectangular_bins.size))
    rectangular = np.fft.ifft(np.fft.ifftshift(rectangular_spectrum)) * count * 0.08 + noise(8, 0.001)

    adjacent = (
        0.45 * np.exp(-2j * np.pi * 30_000.0 * time)
        + 0.32 * np.exp(-2j * np.pi * 24_000.0 * time)
        + noise(7)
    )
    weak_rng = np.random.default_rng(99)
    weak = 0.00066 * np.exp(2j * np.pi * 20_000.0 * time) + 0.008 * (
        weak_rng.normal(size=count) + 1j * weak_rng.normal(size=count)
    )
    fixtures = (
        P0Fixture("single-tone", tone, (center + 40_000.0,), 750.0, None),
        P0Fixture("am-like", am, (center + 60_000.0,), 2_000.0, "Analog"),
        P0Fixture("nfm-like", nfm, (center + 90_000.0,), 2_400.0, "Analog"),
        P0Fixture("digital-ook-burst", digital, (center - 80_000.0,), 2_000.0, "Sayısal"),
        P0Fixture("wideband-noise-like", wide, (wide_truth_centroid,), 20_250.0, "Belirsiz", "known_region", (count // 2 + 300, count // 2 + 380)),
        P0Fixture("digital-rectangular-spectrum", rectangular, (center,), 5_250.0, None, "known_region", (int(rectangular_bins[0]), int(rectangular_bins[-1]))),
        P0Fixture("two-adjacent-signals", adjacent, (center - 30_000.0, center - 24_000.0), 750.0, None),
        P0Fixture("weak-near-threshold", weak, (center + 20_000.0,), 750.0, None),
    )
    for fixture in fixtures:
        fixture.iq.setflags(write=False)
    return fixtures


def build_judge_demo_engine() -> "P0SearchEngine":
    """Build the deterministic two-frame replay backend used by all three demos."""

    from .search import P0SearchEngine, ReplaySearchBackend, TuningWindow

    fixture = next(item for item in build_fixtures() if item.fixture_id == "nfm-like")
    rng = np.random.default_rng(77)
    second = fixture.iq + 0.004 * (rng.normal(size=fixture.iq.size) + 1j * rng.normal(size=fixture.iq.size))
    second = np.asarray(second, dtype=np.complex128)
    second.setflags(write=False)
    window = TuningWindow(
        "p0-nfm-replay-window",
        CENTER_FREQUENCY_HZ,
        SAMPLE_RATE_HZ,
        (fixture.iq, second),
    )
    return P0SearchEngine(ReplaySearchBackend((window,)))
