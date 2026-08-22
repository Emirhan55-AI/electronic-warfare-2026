"""Offline AM/FM/NFM baseband generation and local loopback verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class AnalogDeceptionConfig:
    mode: Literal["AM", "FM", "NFM"] = "NFM"
    sample_rate_hz: int = 192_000
    audio_sample_rate_hz: int = 48_000
    duration_seconds: float = 2.0
    output_peak: float = 0.7
    audio_bandwidth_hz: float = 3_000.0

    def __post_init__(self) -> None:
        if self.mode not in {"AM", "FM", "NFM"}:
            raise ValueError("only AM, FM, and NFM offline modes are supported")
        if self.sample_rate_hz < 8_000 or self.audio_sample_rate_hz < 8_000:
            raise ValueError("sample rates are outside the offline bound")
        if not 0 < self.audio_bandwidth_hz < self.audio_sample_rate_hz / 2:
            raise ValueError("voice-band filter cutoff is invalid")

    @property
    def deviation_hz(self) -> float:
        return 2_500.0 if self.mode == "NFM" else 15_000.0


@dataclass(frozen=True)
class AnalogDeceptionResult:
    samples: npt.NDArray[np.complex128]
    normalized_audio: npt.NDArray[np.float64]
    sample_rate_hz: int
    duration_seconds: float
    mode: str
    peak_magnitude: float
    loopback_correlation: float
    audio_bandwidth_hz: float
    provenance: str = "OFFLINE BASEBAND"


class AnalogDeceptionEngine:
    def generate(self, audio: npt.ArrayLike, config: AnalogDeceptionConfig) -> AnalogDeceptionResult:
        source = np.asarray(audio, dtype=np.float64)
        if source.ndim != 1 or source.size < 32 or not np.all(np.isfinite(source)):
            raise ValueError("audio must be a finite mono sequence")
        if not 0 < config.duration_seconds <= 30.0 or not 0 < config.output_peak <= 0.9:
            raise ValueError("bounded duration or output level is invalid")
        target_audio_count = int(round(config.audio_sample_rate_hz * config.duration_seconds))
        if target_audio_count > source.size:
            repeats = int(np.ceil(target_audio_count / source.size))
            source = np.tile(source, repeats)
        source = source[:target_audio_count]
        source = source - np.mean(source)
        peak = float(np.max(np.abs(source)))
        if peak <= np.finfo(np.float64).eps:
            raise ValueError("audio has no usable energy")
        normalized = source / peak
        normalized = self._lowpass(normalized, config.audio_sample_rate_hz, config.audio_bandwidth_hz)
        normalized /= max(float(np.max(np.abs(normalized))), np.finfo(np.float64).eps)

        count = int(round(config.sample_rate_hz * config.duration_seconds))
        source_axis = np.arange(normalized.size, dtype=np.float64) / config.audio_sample_rate_hz
        target_axis = np.arange(count, dtype=np.float64) / config.sample_rate_hz
        audio_up = np.interp(target_axis, source_axis, normalized, left=0.0, right=0.0)
        if config.mode == "AM":
            # A 50 % modulation index keeps the generated envelope bounded and
            # intentionally does not represent an RF output power setting.
            samples = config.output_peak * (0.5 + 0.5 * audio_up).astype(np.complex128)
            demod = (np.abs(samples) / config.output_peak - 0.5) * 2.0
            correlation = float(np.corrcoef(audio_up, demod)[0, 1])
        else:
            phase = 2.0 * np.pi * config.deviation_hz * np.cumsum(audio_up) / config.sample_rate_hz
            samples = config.output_peak * np.exp(1j * phase)
            demod = np.angle(samples[1:] * np.conj(samples[:-1])) * config.sample_rate_hz / (2.0 * np.pi * config.deviation_hz)
            correlation = float(np.corrcoef(audio_up[1:], demod)[0, 1])
        samples = np.asarray(samples, dtype=np.complex128)
        normalized = np.asarray(normalized, dtype=np.float64)
        samples.setflags(write=False)
        normalized.setflags(write=False)
        return AnalogDeceptionResult(
            samples,
            normalized,
            config.sample_rate_hz,
            count / config.sample_rate_hz,
            config.mode,
            float(np.max(np.abs(samples))),
            correlation,
            config.audio_bandwidth_hz,
        )

    @staticmethod
    def _lowpass(audio: npt.NDArray[np.float64], sample_rate_hz: float, cutoff_hz: float) -> npt.NDArray[np.float64]:
        taps = 129
        index = np.arange(taps, dtype=np.float64) - (taps - 1) / 2
        normalized_cutoff = cutoff_hz / sample_rate_hz
        kernel = 2 * normalized_cutoff * np.sinc(2 * normalized_cutoff * index)
        kernel *= np.hanning(taps)
        kernel /= np.sum(kernel)
        return np.convolve(audio, kernel, mode="same")
