"""Deterministic, transmit-disabled continuous ET baseband models.

The functions in this module create bounded local I/Q buffers only.  They do
not open a device, configure a transmitter, or contain an RF-output path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


JammingFamily = Literal["single", "multiple", "barrage", "sweep"]


@dataclass(frozen=True)
class ContinuousJammingConfig:
    family: JammingFamily
    sample_rate_hz: int
    duration_seconds: float
    offsets_hz: tuple[float, ...] = (0.0,)
    output_peak: float = 0.7
    seed: int = 2026
    barrage_bandwidth_hz: float = 16_000.0
    sweep_start_hz: float = -10_000.0
    sweep_stop_hz: float = 10_000.0

    def __post_init__(self) -> None:
        if self.sample_rate_hz < 8_000 or not 0 < self.duration_seconds <= 30.0:
            raise ValueError("sample rate or bounded duration is invalid")
        if not 0 < self.output_peak <= 0.9:
            raise ValueError("output_peak must be in (0, 0.9]")
        if self.family == "single" and len(self.offsets_hz) != 1:
            raise ValueError("single requires exactly one offset")
        if self.family == "multiple" and not 2 <= len(self.offsets_hz) <= 16:
            raise ValueError("multiple requires 2..16 offsets")
        if self.family in {"barrage", "sweep"} and self.offsets_hz != (0.0,):
            raise ValueError(f"{self.family} does not use tone offsets")
        if any(abs(offset) >= self.sample_rate_hz / 2 for offset in self.offsets_hz):
            raise ValueError("tone offset exceeds Nyquist")
        if not 0 < self.barrage_bandwidth_hz <= self.sample_rate_hz:
            raise ValueError("barrage bandwidth is outside the offline frame")
        if not (-self.sample_rate_hz / 2 < self.sweep_start_hz < self.sample_rate_hz / 2):
            raise ValueError("sweep start is outside Nyquist")
        if not (-self.sample_rate_hz / 2 < self.sweep_stop_hz < self.sample_rate_hz / 2):
            raise ValueError("sweep stop is outside Nyquist")
        if self.family == "sweep" and self.sweep_start_hz == self.sweep_stop_hz:
            raise ValueError("sweep endpoints must differ")


@dataclass(frozen=True)
class WaveformResult:
    samples: npt.NDArray[np.complex128]
    sample_rate_hz: int
    family: JammingFamily
    duration_seconds: float
    peak_magnitude: float
    rms_magnitude: float
    occupied_bandwidth_hz: float
    sweep_sub_bands_hz: tuple[tuple[float, float], ...] = ()
    provenance: str = "OFFLINE BASEBAND"


class ContinuousJammingEngine:
    def generate(self, config: ContinuousJammingConfig) -> WaveformResult:
        count = int(round(config.sample_rate_hz * config.duration_seconds))
        if count < 1 or count > 5_000_000:
            raise ValueError("waveform sample count exceeds the offline bound")
        if config.family in {"single", "multiple"}:
            time = np.arange(count, dtype=np.float64) / config.sample_rate_hz
            samples = np.zeros(count, dtype=np.complex128)
            for offset in config.offsets_hz:
                samples += np.exp(2j * np.pi * offset * time)
            samples /= max(len(config.offsets_hz), 1)
        elif config.family == "barrage":
            samples = self._band_limited_noise(count, config)
        else:
            samples = self._linear_sweep(count, config)
        peak = float(np.max(np.abs(samples)))
        if peak <= 0:
            raise ValueError("generated waveform has no energy")
        samples = samples * (config.output_peak / peak)
        samples = np.asarray(samples, dtype=np.complex128)
        samples.setflags(write=False)
        return WaveformResult(
            samples,
            config.sample_rate_hz,
            config.family,
            count / config.sample_rate_hz,
            float(np.max(np.abs(samples))),
            float(np.sqrt(np.mean(np.abs(samples) ** 2))),
            self._occupied_bandwidth(samples, config.sample_rate_hz),
            self._sweep_sub_bands(config) if config.family == "sweep" else (),
        )

    @staticmethod
    def _band_limited_noise(count: int, config: ContinuousJammingConfig) -> npt.NDArray[np.complex128]:
        """Create seeded complex noise restricted to the requested local band."""

        rng = np.random.default_rng(config.seed)
        frequencies = np.fft.fftfreq(count, d=1.0 / config.sample_rate_hz)
        mask = np.abs(frequencies) <= config.barrage_bandwidth_hz / 2.0
        spectrum = np.zeros(count, dtype=np.complex128)
        spectrum[mask] = rng.normal(size=int(np.count_nonzero(mask))) + 1j * rng.normal(size=int(np.count_nonzero(mask)))
        return np.fft.ifft(spectrum)

    @staticmethod
    def _linear_sweep(count: int, config: ContinuousJammingConfig) -> npt.NDArray[np.complex128]:
        time = np.arange(count, dtype=np.float64) / config.sample_rate_hz
        rate_hz_per_second = (config.sweep_stop_hz - config.sweep_start_hz) / config.duration_seconds
        phase = 2.0 * np.pi * (config.sweep_start_hz * time + 0.5 * rate_hz_per_second * time**2)
        return np.exp(1j * phase)

    @staticmethod
    def _occupied_bandwidth(samples: npt.ArrayLike, sample_rate_hz: float) -> float:
        """Return deterministic 99 %-power width; it is a baseband-only summary."""

        frequencies, power = ContinuousJammingEngine.spectrum(samples, sample_rate_hz)
        total = float(np.sum(power))
        if not np.isfinite(total) or total <= 0:
            raise ValueError("generated waveform has no finite spectral energy")
        order = np.argsort(power)[::-1]
        included = np.zeros(power.size, dtype=bool)
        cumulative = 0.0
        for index in order:
            included[index] = True
            cumulative += float(power[index])
            if cumulative >= total * 0.99:
                break
        selected = frequencies[included]
        return float(np.max(selected) - np.min(selected)) if selected.size > 1 else 0.0

    @staticmethod
    def _sweep_sub_bands(config: ContinuousJammingConfig) -> tuple[tuple[float, float], ...]:
        edges = np.linspace(config.sweep_start_hz, config.sweep_stop_hz, 9, dtype=np.float64)
        return tuple((float(start), float(stop)) for start, stop in zip(edges[:-1], edges[1:]))

    @staticmethod
    def spectrum(samples: npt.ArrayLike, sample_rate_hz: float) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        values = np.asarray(samples, dtype=np.complex128)
        frequencies = np.fft.fftshift(np.fft.fftfreq(values.size, d=1.0 / sample_rate_hz))
        power = np.abs(np.fft.fftshift(np.fft.fft(values))) ** 2
        # The inverse FFT used for a band-limited barrage leaves machine-scale
        # residue outside the explicit support.  Remove only that numerical
        # residue so offline spectrum summaries do not mistake it for energy.
        floor = float(np.max(power)) * 1e-12
        power = np.where(power >= floor, power, 0.0)
        return frequencies, power
