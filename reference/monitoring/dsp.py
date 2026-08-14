"""Bounded, deterministic AM/NFM demodulation using NumPy only."""

from __future__ import annotations

import io
import math
import wave
from collections import deque
from pathlib import Path

import numpy as np
import numpy.typing as npt

from .models import AnalogMonitorConfig, AnalogMonitorResult, MonitoringError


AUDIO_SAMPLE_RATE_HZ = 48_000
MAX_IQ_FRAMES = 4
FRAME_LENGTH = 4096
MAX_AUDIO_SECONDS = 10
MAX_AUDIO_SAMPLES = AUDIO_SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS
CHANNEL_TAPS = 129
AUDIO_TAPS = 65


def _readonly(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64)
    result.setflags(write=False)
    return result


def _lowpass(cutoff_hz: float, sample_rate_hz: float, taps: int) -> npt.NDArray[np.float64]:
    if not 0.0 < cutoff_hz < sample_rate_hz / 2.0:
        raise MonitoringError("invalid_filter_cutoff", "Filtre kesim frekansı geçersizdir.")
    index = np.arange(taps, dtype=np.float64) - (taps - 1) / 2.0
    normalized = 2.0 * cutoff_hz / sample_rate_hz
    kernel = normalized * np.sinc(normalized * index) * np.hamming(taps)
    kernel /= np.sum(kernel)
    return kernel


def _resample_linear(values: npt.NDArray[np.float64], input_rate: float) -> npt.NDArray[np.float64]:
    duration = values.size / input_rate
    count = int(math.floor(duration * AUDIO_SAMPLE_RATE_HZ))
    if count < 128:
        raise MonitoringError("insufficient_iq", "Dört çerçeve yeterli ses örneği üretmedi.")
    source_time = np.arange(values.size, dtype=np.float64) / input_rate
    target_time = np.arange(count, dtype=np.float64) / AUDIO_SAMPLE_RATE_HZ
    return np.interp(target_time, source_time, values).astype(np.float64, copy=False)


def dominant_tone_hz(audio: npt.ArrayLike, sample_rate_hz: int = AUDIO_SAMPLE_RATE_HZ) -> float:
    values = np.asarray(audio, dtype=np.float64)
    if values.ndim != 1 or values.size < 128 or not np.all(np.isfinite(values)):
        raise MonitoringError("insufficient_audio", "Baskın ton için yeterli sonlu ses örneği yok.")
    nfft = 1 << max(12, int(math.ceil(math.log2(values.size))))
    window = np.hanning(values.size)
    spectrum = np.abs(np.fft.rfft((values - np.mean(values)) * window, n=nfft))
    spectrum[0] = 0.0
    return float(np.argmax(spectrum) * sample_rate_hz / nfft)


def aligned_correlation(reference: npt.ArrayLike, observed: npt.ArrayLike, max_lag: int = 512) -> float:
    left = np.asarray(reference, dtype=np.float64)
    right = np.asarray(observed, dtype=np.float64)
    if left.ndim != 1 or right.ndim != 1 or min(left.size, right.size) < 128:
        raise MonitoringError("insufficient_audio", "Korelasyon için yeterli ses örneği yok.")
    size = min(left.size, right.size)
    left = left[:size] - np.mean(left[:size])
    right = right[:size] - np.mean(right[:size])
    best = -1.0
    limit = min(max_lag, size // 3)
    for lag in range(-limit, limit + 1):
        if lag < 0:
            a, b = left[-lag:], right[: size + lag]
        elif lag > 0:
            a, b = left[: size - lag], right[lag:]
        else:
            a, b = left, right
        denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denominator > 0.0:
            best = max(best, abs(float(np.dot(a, b)) / denominator))
    return best


def pcm16_bytes(audio: npt.ArrayLike, volume: float = 1.0) -> tuple[bytes, int]:
    values = np.asarray(audio, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise MonitoringError("nonfinite_audio", "PCM girişi sonlu mono örneklerden oluşmalıdır.")
    if not math.isfinite(volume) or not 0.0 <= volume <= 1.0:
        raise MonitoringError("invalid_volume", "Ses seviyesi 0 ile 1 arasında olmalıdır.")
    peak = float(np.max(np.abs(values), initial=0.0))
    normalized = values if peak == 0.0 else values * (0.95 / peak)
    scaled = normalized * float(volume)
    clipping = int(np.count_nonzero(np.abs(scaled) > 1.0))
    clipped = np.clip(scaled, -1.0, 1.0)
    pcm = np.rint(clipped * 32767.0).astype("<i2")
    return pcm.tobytes(), clipping


def wav_bytes(pcm16: bytes, sample_rate_hz: int = AUDIO_SAMPLE_RATE_HZ) -> bytes:
    if len(pcm16) % 2:
        raise MonitoringError("invalid_pcm_length", "PCM16 verisi tek byte ile bitemez.")
    if len(pcm16) // 2 > MAX_AUDIO_SAMPLES:
        raise MonitoringError("audio_limit", "WAV süresi bounded sınırı aşıyor.")
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate_hz)
        stream.writeframes(pcm16)
    return output.getvalue()


def write_wav(path: Path, pcm16: bytes, sample_rate_hz: int = AUDIO_SAMPLE_RATE_HZ) -> None:
    Path(path).write_bytes(wav_bytes(pcm16, sample_rate_hz))


class AnalogMonitor:
    """Demodulate exactly one bounded group of consecutive I/Q frames."""

    def process(self, frames: tuple[npt.ArrayLike, ...], config: AnalogMonitorConfig, *, volume: float = 1.0) -> AnalogMonitorResult:
        if len(frames) != MAX_IQ_FRAMES:
            raise MonitoringError("insufficient_iq", "Dinleme için dört ardışık çerçeve gereklidir.")
        converted = tuple(np.asarray(frame, dtype=np.complex128) for frame in frames)
        if any(frame.ndim != 1 or frame.size != FRAME_LENGTH for frame in converted):
            raise MonitoringError("short_iq_frame", "Her I/Q çerçevesi tam 4096 karmaşık örnek içermelidir.")
        iq = np.concatenate(converted)
        if not np.all(np.isfinite(iq.real)) or not np.all(np.isfinite(iq.imag)):
            raise MonitoringError("nonfinite_iq", "I/Q örneklerinde NaN veya Inf bulundu.")

        sample_index = np.arange(iq.size, dtype=np.float64)
        oscillator = np.exp(-2j * np.pi * config.center_offset_hz * sample_index / config.sample_rate_hz)
        shifted = iq * oscillator
        cutoff = min(config.channel_bandwidth_hz * 0.45, config.sample_rate_hz * 0.45)
        channel_kernel = _lowpass(cutoff, config.sample_rate_hz, CHANNEL_TAPS)
        filtered = np.convolve(shifted, channel_kernel, mode="same")
        guard = (CHANNEL_TAPS - 1) // 2
        filtered = filtered[guard:-guard]
        if filtered.size < 256:
            raise MonitoringError("insufficient_iq", "Filtre geçici rejimi sonrasında yeterli I/Q kalmadı.")

        if config.mode == "am":
            baseband = np.abs(filtered)
        else:
            products = filtered[1:] * np.conj(filtered[:-1])
            baseband = np.angle(products) * config.sample_rate_hz / (2.0 * np.pi)
        baseband = np.asarray(baseband - np.mean(baseband), dtype=np.float64)
        audio = _resample_linear(baseband, config.sample_rate_hz)
        audio_cutoff = min(15_000.0, max(3_000.0, config.channel_bandwidth_hz * 0.42), 0.45 * AUDIO_SAMPLE_RATE_HZ)
        audio_kernel = _lowpass(audio_cutoff, AUDIO_SAMPLE_RATE_HZ, AUDIO_TAPS)
        audio = np.convolve(audio, audio_kernel, mode="same")
        audio_guard = (AUDIO_TAPS - 1) // 2
        audio = audio[audio_guard:-audio_guard]
        audio -= np.mean(audio)
        if audio.size < 128 or audio.size > MAX_AUDIO_SAMPLES or not np.all(np.isfinite(audio)):
            raise MonitoringError("insufficient_audio", "Bounded ve sonlu ses sonucu üretilemedi.")
        peak = float(np.max(np.abs(audio), initial=0.0))
        if peak <= np.finfo(np.float64).eps:
            raise MonitoringError("insufficient_audio", "Demodüle edilen ses enerjisi yetersizdir.")
        audio = audio / peak
        pcm, clipping = pcm16_bytes(audio, volume)
        readonly = _readonly(audio)
        return AnalogMonitorResult(
            mode=config.mode,
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            audio=readonly,
            pcm16=pcm,
            dominant_tone_hz=dominant_tone_hz(readonly),
            clipping_count=clipping,
            input_frame_count=len(frames),
            input_complex_samples=iq.size,
            transient_guard_input_samples=guard,
            quality_code="passed",
        )


class AudioRingBuffer:
    """Bounded PCM16 ring retaining at most ten seconds."""

    def __init__(self, maximum_samples: int = MAX_AUDIO_SAMPLES) -> None:
        if not 1 <= maximum_samples <= MAX_AUDIO_SAMPLES:
            raise MonitoringError("audio_limit", "Ses ring buffer sınırı geçersizdir.")
        self.maximum_samples = maximum_samples
        self._chunks: deque[bytes] = deque()
        self._sample_count = 0

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def clear(self) -> None:
        self._chunks.clear()
        self._sample_count = 0

    def append(self, pcm16: bytes) -> None:
        if len(pcm16) % 2:
            raise MonitoringError("invalid_pcm_length", "PCM16 verisi tek byte ile bitemez.")
        self._chunks.append(bytes(pcm16))
        self._sample_count += len(pcm16) // 2
        while self._sample_count > self.maximum_samples and self._chunks:
            removed = self._chunks.popleft()
            self._sample_count -= len(removed) // 2

    def payload(self) -> bytes:
        return b"".join(self._chunks)
