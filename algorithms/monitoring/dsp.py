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
MAX_AUDIO_SECONDS = 20
MAX_AUDIO_SAMPLES = AUDIO_SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS
CHANNEL_TAPS = 129
AUDIO_TAPS = 65
AUDIO_RESAMPLE_TAPS = 257
OBSERVATION_INTERVAL_SECONDS = 0.250


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


def _resample_voice(
    values: npt.NDArray[np.float64], input_rate: float, cutoff_hz: float
) -> npt.NDArray[np.float64]:
    """Band-limit demodulated voice before conversion to the 48 kHz output rate."""
    if input_rate <= AUDIO_SAMPLE_RATE_HZ:
        return _resample_linear(values, input_rate)
    cutoff = min(float(cutoff_hz), 0.45 * AUDIO_SAMPLE_RATE_HZ, 0.45 * input_rate)
    kernel = _lowpass(cutoff, input_rate, AUDIO_RESAMPLE_TAPS)
    guard = (AUDIO_RESAMPLE_TAPS - 1) // 2
    padded = np.pad(values, (guard, guard), mode="edge")
    filtered = np.convolve(padded, kernel, mode="valid")
    return _resample_linear(filtered, input_rate)


def _voice_cutoff_hz(config: AnalogMonitorConfig) -> float:
    if config.mode == "nfm" and config.channel_bandwidth_hz <= 12_500.0:
        return 2_550.0
    return 3_000.0


def _remove_voice_rumble(values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Optional 200 Hz high-pass; symmetric FIR preserves speech-band phase.

    Apply once to the assembled audio, before normalization. This removes low
    frequency rumble, not in-band noise, and does not estimate speech content.
    """
    kernel = -_lowpass(200.0, AUDIO_SAMPLE_RATE_HZ, 1025)
    kernel[512] += 1.0
    return np.convolve(np.pad(values, (512, 512), mode="edge"), kernel, mode="valid")


def nfm_deemphasis(values: npt.ArrayLike, time_constant_us: float) -> npt.NDArray[np.float64]:
    """Apply the standard first-order 6 dB/octave NFM receive de-emphasis."""
    source = np.asarray(values, dtype=np.float64)
    if source.ndim != 1 or not np.all(np.isfinite(source)):
        raise MonitoringError("nonfinite_audio", "NFM de-emphasis girişi sonlu mono olmalıdır.")
    if not math.isfinite(time_constant_us) or not 0.0 <= time_constant_us <= 2_000.0:
        raise MonitoringError("invalid_deemphasis", "NFM de-emphasis zaman sabiti geçersizdir.")
    if time_constant_us == 0.0 or source.size == 0:
        return source.copy()
    alpha = math.exp(-1.0 / (AUDIO_SAMPLE_RATE_HZ * time_constant_us * 1e-6))
    output = np.empty_like(source)
    state = float(source[0])
    output[0] = state
    for index in range(1, source.size):
        state = alpha * state + (1.0 - alpha) * float(source[index])
        output[index] = state
    return output


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
        audio_cutoff = _voice_cutoff_hz(config)
        audio = _resample_voice(baseband, config.sample_rate_hz, audio_cutoff)
        if config.mode == "nfm":
            audio = nfm_deemphasis(audio, config.nfm_deemphasis_us)
        audio_kernel = _lowpass(audio_cutoff, AUDIO_SAMPLE_RATE_HZ, AUDIO_TAPS)
        audio = np.convolve(audio, audio_kernel, mode="same")
        audio_guard = (AUDIO_TAPS - 1) // 2
        audio = audio[audio_guard:-audio_guard]
        if config.voice_filter:
            audio = _remove_voice_rumble(audio)
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
            voice_filter=config.voice_filter,
            nfm_deemphasis_us=config.nfm_deemphasis_us,
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

    def process_continuous(
        self,
        blocks: npt.ArrayLike | tuple[npt.ArrayLike, ...] | list[npt.ArrayLike],
        config: AnalogMonitorConfig,
        *,
        volume: float = 1.0,
    ) -> AnalogMonitorResult:
        """Demodulate one 5–10 s contiguous recording while retaining stream state.

        The NCO, both FIR delay lines, decimator phase and discriminator's previous
        complex sample remain continuous across every supplied block.
        """
        if isinstance(blocks, np.ndarray) and blocks.ndim == 1:
            input_blocks = (np.asarray(blocks, dtype=np.complex128),)
        else:
            input_blocks = tuple(np.asarray(block, dtype=np.complex128) for block in blocks)  # type: ignore[arg-type]
        if not input_blocks or any(block.ndim != 1 or block.size == 0 for block in input_blocks):
            raise MonitoringError("insufficient_iq", "Kesintisiz dinleme için I/Q örnekleri gerekli.")
        total = sum(block.size for block in input_blocks)
        if total < int(math.ceil(5.0 * config.sample_rate_hz)):
            raise MonitoringError("insufficient_iq", "Dinleme için en az beş saniyelik kesintisiz I/Q gerekli.")
        if total > int(math.floor(MAX_AUDIO_SECONDS * config.sample_rate_hz)):
            raise MonitoringError("audio_limit", "Kesintisiz dinleme süresi yirmi saniyeyi aşamaz.")
        if any(not np.all(np.isfinite(block.real)) or not np.all(np.isfinite(block.imag)) for block in input_blocks):
            raise MonitoringError("nonfinite_iq", "I/Q örneklerinde NaN veya Inf bulundu.")

        # First decimate from the capture rate with a stateful anti-alias FIR.
        decimation = max(1, int(config.sample_rate_hz // 200_000.0))
        intermediate_rate = config.sample_rate_hz / decimation
        anti_alias = _lowpass(min(80_000.0, intermediate_rate * 0.42), config.sample_rate_hz, CHANNEL_TAPS)
        channel = _lowpass(min(config.channel_bandwidth_hz * 0.45, intermediate_rate * 0.45), intermediate_rate, CHANNEL_TAPS)
        anti_state = np.zeros(CHANNEL_TAPS - 1, dtype=np.complex128)
        channel_state = np.zeros(CHANNEL_TAPS - 1, dtype=np.complex128)
        phase = 0
        decimator_index = 0
        previous: complex | None = None
        baseband_parts: list[npt.NDArray[np.float64]] = []
        channel_power_sum = 0.0
        channel_power_count = 0
        observation_size = max(256, int(round(intermediate_rate * OBSERVATION_INTERVAL_SECONDS)))
        observation_pending = np.empty(0, dtype=np.complex128)
        observation_times: list[float] = []
        observation_power: list[float] = []
        observation_frequency: list[float] = []
        observed_channel_samples = 0

        def observe(segment: npt.NDArray[np.complex128]) -> None:
            nonlocal observed_channel_samples
            power = float(np.mean(np.abs(segment) ** 2))
            products = segment[1:] * np.conj(segment[:-1])
            phasor = complex(np.sum(products))
            residual_hz = (
                math.atan2(phasor.imag, phasor.real) * intermediate_rate / (2.0 * math.pi)
                if abs(phasor) > np.finfo(np.float64).tiny
                else 0.0
            )
            observation_times.append((observed_channel_samples + segment.size / 2.0) / intermediate_rate)
            observation_power.append(10.0 * math.log10(max(power, np.finfo(np.float64).tiny)))
            observation_frequency.append(residual_hz)
            observed_channel_samples += segment.size

        for block in input_blocks:
            indices = phase + np.arange(block.size, dtype=np.float64)
            mixed = block * np.exp(-2j * np.pi * config.center_offset_hz * indices / config.sample_rate_hz)
            phase += block.size
            anti_filtered = np.convolve(np.concatenate((anti_state, mixed)), anti_alias, mode="valid")
            anti_state = np.asarray(mixed[-(CHANNEL_TAPS - 1):], dtype=np.complex128)
            positions = np.arange(decimator_index, decimator_index + anti_filtered.size)
            decimated = anti_filtered[positions % decimation == 0]
            decimator_index += anti_filtered.size
            if not decimated.size:
                continue
            filtered = np.convolve(np.concatenate((channel_state, decimated)), channel, mode="valid")
            channel_state = np.asarray(decimated[-(CHANNEL_TAPS - 1):], dtype=np.complex128)
            channel_power_sum += float(np.vdot(filtered, filtered).real)
            channel_power_count += filtered.size
            observation_pending = np.concatenate((observation_pending, filtered))
            while observation_pending.size >= observation_size:
                observe(observation_pending[:observation_size])
                observation_pending = observation_pending[observation_size:]
            if config.mode == "am":
                baseband_parts.append(np.abs(filtered))
            else:
                extended = filtered if previous is None else np.concatenate((np.asarray([previous]), filtered))
                baseband_parts.append(np.angle(extended[1:] * np.conj(extended[:-1])) * intermediate_rate / (2.0 * np.pi))
                previous = complex(filtered[-1])

        if not baseband_parts:
            raise MonitoringError("insufficient_iq", "Kesintisiz kanaldan ses örneği üretilemedi.")
        if observation_pending.size >= observation_size // 2:
            observe(observation_pending)
        baseband = np.concatenate(baseband_parts)
        baseband -= float(np.mean(baseband))  # DC/audio offset removal, before resampling.
        audio_cutoff = _voice_cutoff_hz(config)
        audio = _resample_voice(baseband, intermediate_rate, audio_cutoff)
        if config.mode == "nfm":
            audio = nfm_deemphasis(audio, config.nfm_deemphasis_us)
        audio = np.convolve(audio, _lowpass(audio_cutoff, AUDIO_SAMPLE_RATE_HZ, AUDIO_TAPS), mode="same")
        # Discard the causal filter warm-up once, never at each capture block.
        audio = audio[AUDIO_TAPS - 1 :]
        if config.voice_filter:
            audio = _remove_voice_rumble(audio)
        audio -= float(np.mean(audio))
        if audio.size < 128 or audio.size > MAX_AUDIO_SAMPLES or not np.all(np.isfinite(audio)):
            raise MonitoringError("insufficient_audio", "Bounded ve sonlu ses sonucu üretilemedi.")
        peak = float(np.max(np.abs(audio), initial=0.0))
        if peak <= np.finfo(np.float64).eps:
            raise MonitoringError("insufficient_audio", "Demodüle edilen ses enerjisi yetersizdir.")
        # One global normalization is applied only after the full contiguous buffer.
        audio = audio / peak
        pcm, clipping = pcm16_bytes(audio, volume)
        readonly = _readonly(audio)
        power = channel_power_sum / max(channel_power_count, 1)
        return AnalogMonitorResult(
            mode=config.mode,
            voice_filter=config.voice_filter,
            nfm_deemphasis_us=config.nfm_deemphasis_us,
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            audio=readonly,
            pcm16=pcm,
            dominant_tone_hz=dominant_tone_hz(readonly),
            clipping_count=clipping,
            input_frame_count=0,
            input_complex_samples=total,
            transient_guard_input_samples=CHANNEL_TAPS - 1,
            quality_code="passed",
            rf_power_dbfs=10.0 * math.log10(max(power, np.finfo(np.float64).tiny)),
            observation_interval_s=OBSERVATION_INTERVAL_SECONDS,
            observation_times_s=tuple(observation_times),
            channel_power_dbfs_trace=tuple(observation_power),
            residual_frequency_hz_trace=tuple(observation_frequency),
        )


class StreamingAnalogMonitor:
    """Stateful AM/NFM demodulator for consecutive live I/Q chunks.

    NCO phase, RF/audio FIR histories, decimator phase, FM discriminator,
    resampler phase, DC blocker and gain all survive chunk boundaries.  The
    class owns no device or unbounded queue; callers remain responsible for
    proving that every supplied chunk is consecutive.
    """

    def __init__(self, config: AnalogMonitorConfig) -> None:
        self.config = config
        self.decimation = max(1, int(config.sample_rate_hz // 200_000.0))
        self.intermediate_rate = config.sample_rate_hz / self.decimation
        self.anti_alias = _lowpass(
            min(80_000.0, self.intermediate_rate * 0.42),
            config.sample_rate_hz,
            CHANNEL_TAPS,
        )
        self.channel = _lowpass(
            min(config.channel_bandwidth_hz * 0.45, self.intermediate_rate * 0.45),
            self.intermediate_rate,
            CHANNEL_TAPS,
        )
        self.voice_cutoff = _voice_cutoff_hz(config)
        self.voice = _lowpass(
            min(self.voice_cutoff, self.intermediate_rate * 0.45),
            self.intermediate_rate,
            AUDIO_RESAMPLE_TAPS,
        )
        self.output = _lowpass(self.voice_cutoff, AUDIO_SAMPLE_RATE_HZ, AUDIO_TAPS)
        self.rumble = None
        if config.voice_filter:
            self.rumble = -_lowpass(200.0, AUDIO_SAMPLE_RATE_HZ, 1025)
            self.rumble[512] += 1.0
        self._anti_state = np.zeros(CHANNEL_TAPS - 1, dtype=np.complex128)
        self._channel_state = np.zeros(CHANNEL_TAPS - 1, dtype=np.complex128)
        self._voice_state = np.zeros(AUDIO_RESAMPLE_TAPS - 1, dtype=np.float64)
        self._output_state = np.zeros(AUDIO_TAPS - 1, dtype=np.float64)
        self._rumble_state = np.zeros(1024, dtype=np.float64)
        self._input_index = 0
        self._decimator_index = 0
        self._previous_iq: complex | None = None
        self._resample_tail: float | None = None
        self._resample_input_count = 0
        self._next_output_position = 0.0
        self._dc_input = 0.0
        self._dc_output = 0.0
        self._deemphasis_state: float | None = None
        self._gain = 1.0
        self._agc_envelope = 0.0
        self._elapsed_intermediate_samples = 0
        self._observation_pending = np.empty(0, dtype=np.complex128)

    @staticmethod
    def _fir(values, kernel, state):
        joined = np.concatenate((state, values))
        output = np.convolve(joined, kernel, mode="valid")
        return output, np.asarray(joined[-(kernel.size - 1):], dtype=values.dtype)

    def _resample(self, values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        if not values.size:
            return np.empty(0, dtype=np.float64)
        start = self._resample_input_count
        if self._resample_tail is None:
            source = values
            source_start = start
        else:
            source = np.concatenate((np.asarray([self._resample_tail]), values))
            source_start = start - 1
        source_end = start + values.size - 1
        step = self.intermediate_rate / AUDIO_SAMPLE_RATE_HZ
        first = max(self._next_output_position, float(source_start))
        if first > source_end:
            output = np.empty(0, dtype=np.float64)
        else:
            count = int(math.floor((source_end - first) / step)) + 1
            positions = first + step * np.arange(count, dtype=np.float64)
            output = np.interp(
                positions,
                source_start + np.arange(source.size, dtype=np.float64),
                source,
            )
            self._next_output_position = float(positions[-1] + step)
        self._resample_tail = float(values[-1])
        self._resample_input_count += values.size
        return np.asarray(output, dtype=np.float64)

    def _remove_dc(self, values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        # Stateful first-order 30 Hz high-pass avoids per-chunk mean steps.
        pole = math.exp(-2.0 * math.pi * 30.0 / AUDIO_SAMPLE_RATE_HZ)
        output = np.empty_like(values)
        previous_input, previous_output = self._dc_input, self._dc_output
        for index, value in enumerate(values):
            current = float(value) - previous_input + pole * previous_output
            output[index] = current
            previous_input, previous_output = float(value), current
        self._dc_input, self._dc_output = previous_input, previous_output
        return output

    def _deemphasize(self, values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        tau = self.config.nfm_deemphasis_us
        if self.config.mode != "nfm" or tau == 0.0 or not values.size:
            return values
        alpha = math.exp(-1.0 / (AUDIO_SAMPLE_RATE_HZ * tau * 1e-6))
        output = np.empty_like(values)
        state = float(values[0]) if self._deemphasis_state is None else self._deemphasis_state
        for index, value in enumerate(values):
            state = alpha * state + (1.0 - alpha) * float(value)
            output[index] = state
        self._deemphasis_state = state
        return output

    def process(self, blocks: npt.ArrayLike | tuple[npt.ArrayLike, ...], *, volume: float = 1.0) -> AnalogMonitorResult:
        if isinstance(blocks, np.ndarray) and blocks.ndim == 1:
            input_blocks = (np.asarray(blocks, dtype=np.complex128),)
        else:
            input_blocks = tuple(np.asarray(block, dtype=np.complex128) for block in blocks)  # type: ignore[arg-type]
        if not input_blocks or any(block.ndim != 1 or block.size == 0 for block in input_blocks):
            raise MonitoringError("insufficient_iq", "Canlı dinleme için ardışık I/Q blokları gereklidir.")
        if not math.isfinite(volume) or not 0.0 <= volume <= 1.0:
            raise MonitoringError("invalid_volume", "Ses seviyesi 0 ile 1 arasında olmalıdır.")

        audio_parts: list[npt.NDArray[np.float64]] = []
        observation_times: list[float] = []
        observation_power: list[float] = []
        observation_frequency: list[float] = []
        total_input = 0
        power_sum = 0.0
        power_count = 0
        observation_size = max(256, int(round(self.intermediate_rate * OBSERVATION_INTERVAL_SECONDS)))

        for block in input_blocks:
            if not np.all(np.isfinite(block.real)) or not np.all(np.isfinite(block.imag)):
                raise MonitoringError("nonfinite_iq", "I/Q örneklerinde NaN veya Inf bulundu.")
            total_input += block.size
            indices = self._input_index + np.arange(block.size, dtype=np.float64)
            mixed = block * np.exp(
                -2j * np.pi * self.config.center_offset_hz * indices / self.config.sample_rate_hz
            )
            self._input_index += block.size
            anti, self._anti_state = self._fir(mixed, self.anti_alias, self._anti_state)
            positions = np.arange(self._decimator_index, self._decimator_index + anti.size)
            decimated = anti[positions % self.decimation == 0]
            self._decimator_index += anti.size
            if not decimated.size:
                continue
            filtered, self._channel_state = self._fir(decimated, self.channel, self._channel_state)
            power_sum += float(np.vdot(filtered, filtered).real)
            power_count += filtered.size
            self._observation_pending = np.concatenate((self._observation_pending, filtered))
            while self._observation_pending.size >= observation_size:
                segment = self._observation_pending[:observation_size]
                self._observation_pending = self._observation_pending[observation_size:]
                power = float(np.mean(np.abs(segment) ** 2))
                products = segment[1:] * np.conj(segment[:-1])
                phasor = complex(np.sum(products))
                residual = (
                    math.atan2(phasor.imag, phasor.real) * self.intermediate_rate / (2.0 * math.pi)
                    if abs(phasor) > np.finfo(np.float64).tiny else 0.0
                )
                self._elapsed_intermediate_samples += segment.size
                observation_times.append(self._elapsed_intermediate_samples / self.intermediate_rate)
                observation_power.append(10.0 * math.log10(max(power, np.finfo(np.float64).tiny)))
                observation_frequency.append(residual)
            if self.config.mode == "am":
                baseband = np.abs(filtered)
            else:
                extended = filtered if self._previous_iq is None else np.concatenate((np.asarray([self._previous_iq]), filtered))
                baseband = np.angle(extended[1:] * np.conj(extended[:-1])) * self.intermediate_rate / (2.0 * np.pi)
                self._previous_iq = complex(filtered[-1])
            voice, self._voice_state = self._fir(np.asarray(baseband, dtype=np.float64), self.voice, self._voice_state)
            resampled = self._resample(voice)
            if resampled.size:
                audio_parts.append(resampled)

        if not audio_parts:
            raise MonitoringError("insufficient_audio", "Canlı dinleme parçasından ses üretilemedi.")
        audio = np.concatenate(audio_parts)
        audio = self._deemphasize(self._remove_dc(audio))
        audio, self._output_state = self._fir(audio, self.output, self._output_state)
        if self.rumble is not None:
            audio, self._rumble_state = self._fir(audio, self.rumble, self._rumble_state)
        rms = float(np.sqrt(np.mean(audio * audio)))
        if not math.isfinite(rms) or rms <= np.finfo(np.float64).eps:
            raise MonitoringError("insufficient_audio", "Canlı demodüle ses enerjisi yetersizdir.")
        # Stateful slow AGC is sample-invariant: changing worker chunk sizes must
        # not create volume steps or different PCM at a chunk boundary.
        scaled = np.empty_like(audio)
        envelope, gain = self._agc_envelope, self._gain
        for index, value in enumerate(audio):
            envelope = max(abs(float(value)), envelope * 0.9998)
            target_gain = min(20.0, max(0.1, 0.18 / max(envelope, 1e-3)))
            gain += 0.002 * (target_gain - gain)
            scaled[index] = min(0.95, max(-0.95, float(value) * gain * volume))
        self._agc_envelope, self._gain = envelope, gain
        pcm = np.rint(scaled * 32767.0).astype("<i2").tobytes()
        readonly = _readonly(scaled)
        power = power_sum / max(power_count, 1)
        return AnalogMonitorResult(
            mode=self.config.mode,
            voice_filter=self.config.voice_filter,
            nfm_deemphasis_us=self.config.nfm_deemphasis_us,
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            audio=readonly,
            pcm16=pcm,
            dominant_tone_hz=dominant_tone_hz(readonly),
            clipping_count=0,
            input_frame_count=0,
            input_complex_samples=total_input,
            transient_guard_input_samples=0,
            quality_code="streaming",
            rf_power_dbfs=10.0 * math.log10(max(power, np.finfo(np.float64).tiny)),
            observation_interval_s=OBSERVATION_INTERVAL_SECONDS,
            observation_times_s=tuple(observation_times),
            channel_power_dbfs_trace=tuple(observation_power),
            residual_frequency_hz_trace=tuple(observation_frequency),
        )


class AudioRingBuffer:
    """Bounded PCM16 ring retaining at most twenty seconds."""

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
