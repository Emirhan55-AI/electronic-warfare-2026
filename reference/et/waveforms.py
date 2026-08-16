"""Offline continuous-jamming baseband families; no RF backend is present."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


JammingFamily = Literal["single", "multiple", "barrage"]


@dataclass(frozen=True)
class ContinuousJammingConfig:
    family: JammingFamily
    sample_rate_hz: int
    duration_seconds: float
    offsets_hz: tuple[float, ...] = (0.0,)
    output_peak: float = 0.7
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.sample_rate_hz < 8_000 or not 0 < self.duration_seconds <= 30.0:
            raise ValueError("sample rate or bounded duration is invalid")
        if not 0 < self.output_peak <= 0.9:
            raise ValueError("output_peak must be in (0, 0.9]")
        if self.family == "single" and len(self.offsets_hz) != 1:
            raise ValueError("single requires exactly one offset")
        if self.family == "multiple" and not 2 <= len(self.offsets_hz) <= 16:
            raise ValueError("multiple requires 2..16 offsets")
        if self.family == "barrage" and self.offsets_hz != (0.0,):
            raise ValueError("barrage does not use tone offsets")
        if any(abs(offset) >= self.sample_rate_hz / 2 for offset in self.offsets_hz):
            raise ValueError("tone offset exceeds Nyquist")


@dataclass(frozen=True)
class WaveformResult:
    samples: npt.NDArray[np.complex128]
    sample_rate_hz: int
    family: JammingFamily
    duration_seconds: float
    peak_magnitude: float
    rms_magnitude: float
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
        else:
            rng = np.random.default_rng(config.seed)
            samples = rng.normal(size=count) + 1j * rng.normal(size=count)
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
        )

    @staticmethod
    def spectrum(samples: npt.ArrayLike, sample_rate_hz: float) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        values = np.asarray(samples, dtype=np.complex128)
        frequencies = np.fft.fftshift(np.fft.fftfreq(values.size, d=1.0 / sample_rate_hz))
        power = np.abs(np.fft.fftshift(np.fft.fft(values))) ** 2
        return frequencies, power
