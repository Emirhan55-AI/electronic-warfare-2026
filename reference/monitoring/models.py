"""Typed contracts for bounded operator-selected analog monitoring."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


DemodulationMode = Literal["am", "nfm"]
FloatArray = npt.NDArray[np.float64]


class MonitoringError(ValueError):
    """Raised when a listening request violates the bounded contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AnalogMonitorConfig:
    """One explicit AM or NFM channel selection."""

    mode: DemodulationMode
    sample_rate_hz: float
    center_offset_hz: float
    channel_bandwidth_hz: float
    output_sample_rate_hz: int = 48_000

    def __post_init__(self) -> None:
        if self.mode not in ("am", "nfm"):
            raise MonitoringError("unsupported_demodulation", "Yalnız AM ve NFM desteklenir.")
        values = (self.sample_rate_hz, self.center_offset_hz, self.channel_bandwidth_hz)
        if not all(math.isfinite(float(value)) for value in values):
            raise MonitoringError("invalid_sample_rate", "Dinleme ayarları sonlu olmalıdır.")
        if self.sample_rate_hz <= 0.0 or self.output_sample_rate_hz != 48_000:
            raise MonitoringError("invalid_sample_rate", "Çıkış örnekleme hızı 48 kHz olmalıdır.")
        if not 2_000.0 <= self.channel_bandwidth_hz <= min(200_000.0, self.sample_rate_hz):
            raise MonitoringError("invalid_channel_bandwidth", "Kanal bant genişliği desteklenen sınırın dışındadır.")
        if abs(self.center_offset_hz) + self.channel_bandwidth_hz / 2.0 > self.sample_rate_hz / 2.0:
            raise MonitoringError("nyquist_limit", "Seçilen kanal kaynak Nyquist sınırını aşıyor.")


@dataclass(frozen=True)
class ListeningIntent:
    """Generation-bound request for exactly four consecutive recorded frames."""

    source_generation: int
    pipeline_generation: int
    configuration_generation: int
    event_id: int
    event_revision: int
    start_frame: int
    mode: DemodulationMode
    center_offset_hz: float
    channel_bandwidth_hz: float
    volume: float

    @property
    def generation_key(self) -> tuple[int, int, int, int, int, int, str, float, float]:
        return (
            self.source_generation,
            self.pipeline_generation,
            self.configuration_generation,
            self.event_id,
            self.event_revision,
            self.start_frame,
            self.mode,
            float(self.center_offset_hz),
            float(self.channel_bandwidth_hz),
        )


@dataclass(frozen=True)
class AnalogMonitorResult:
    """Finite 48 kHz mono audio plus transparent quality metadata."""

    mode: DemodulationMode
    sample_rate_hz: int
    audio: FloatArray
    pcm16: bytes
    dominant_tone_hz: float
    clipping_count: int
    input_frame_count: int
    input_complex_samples: int
    transient_guard_input_samples: int
    quality_code: str

    def __post_init__(self) -> None:
        if self.sample_rate_hz != 48_000:
            raise MonitoringError("invalid_audio_rate", "Ses sonucu 48 kHz olmalıdır.")
        if self.audio.ndim != 1 or not np.all(np.isfinite(self.audio)):
            raise MonitoringError("nonfinite_audio", "Ses sonucu sonlu mono örneklerden oluşmalıdır.")
        if self.clipping_count != 0:
            raise MonitoringError("pcm_clipping", "PCM16 dönüşümünde taşma oluştu.")
