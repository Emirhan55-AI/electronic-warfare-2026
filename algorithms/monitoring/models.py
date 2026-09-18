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
    nfm_deemphasis_us: float = 0.0
    voice_filter: bool = False

    def __post_init__(self) -> None:
        if self.mode not in ("am", "nfm"):
            raise MonitoringError("unsupported_demodulation", "Yalnız AM ve NFM desteklenir.")
        values = (
            self.sample_rate_hz,
            self.center_offset_hz,
            self.channel_bandwidth_hz,
            self.nfm_deemphasis_us,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise MonitoringError("invalid_sample_rate", "Dinleme ayarları sonlu olmalıdır.")
        if self.sample_rate_hz <= 0.0 or self.output_sample_rate_hz != 48_000:
            raise MonitoringError("invalid_sample_rate", "Çıkış örnekleme hızı 48 kHz olmalıdır.")
        if not 2_000.0 <= self.channel_bandwidth_hz <= min(25_000.0, self.sample_rate_hz):
            raise MonitoringError(
                "invalid_channel_bandwidth",
                "Analog ses için kanal bant genişliği 2–25 kHz arasında olmalıdır.",
            )
        if abs(self.center_offset_hz) + self.channel_bandwidth_hz / 2.0 > self.sample_rate_hz / 2.0:
            raise MonitoringError("nyquist_limit", "Seçilen kanal kaynak Nyquist sınırını aşıyor.")
        if not 0.0 <= self.nfm_deemphasis_us <= 2_000.0:
            raise MonitoringError("invalid_deemphasis", "NFM de-emphasis zaman sabiti geçersizdir.")


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
    rf_power_dbfs: float = float("nan")
    observation_interval_s: float = 0.0
    observation_times_s: tuple[float, ...] = ()
    channel_power_dbfs_trace: tuple[float, ...] = ()
    residual_frequency_hz_trace: tuple[float, ...] = ()
    nfm_deemphasis_us: float = 0.0
    voice_filter: bool = False

    def __post_init__(self) -> None:
        if self.sample_rate_hz != 48_000:
            raise MonitoringError("invalid_audio_rate", "Ses sonucu 48 kHz olmalıdır.")
        if self.audio.ndim != 1 or not np.all(np.isfinite(self.audio)):
            raise MonitoringError("nonfinite_audio", "Ses sonucu sonlu mono örneklerden oluşmalıdır.")
        if self.clipping_count != 0:
            raise MonitoringError("pcm_clipping", "PCM16 dönüşümünde taşma oluştu.")
        trace_lengths = {
            len(self.observation_times_s),
            len(self.channel_power_dbfs_trace),
            len(self.residual_frequency_hz_trace),
        }
        if trace_lengths != {0} and (len(trace_lengths) != 1 or self.observation_interval_s <= 0.0):
            raise MonitoringError("invalid_observation_trace", "Kanal gözlem dizileri birbiriyle uyuşmuyor.")
        trace_values = (
            *self.observation_times_s,
            *self.channel_power_dbfs_trace,
            *self.residual_frequency_hz_trace,
        )
        if trace_values and not all(math.isfinite(float(value)) for value in trace_values):
            raise MonitoringError("invalid_observation_trace", "Kanal gözlem dizileri sonlu olmalıdır.")
