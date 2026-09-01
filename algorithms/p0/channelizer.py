"""Stateful 8 MS/s to 2 MS/s channel selection for the P0 FPGA input."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time

import numpy as np
import numpy.typing as npt

from .transport import IQFrame


@dataclass(frozen=True)
class P0ChannelizerProfile:
    input_sample_rate_hz: int = 8_000_000
    output_sample_rate_hz: int = 2_000_000
    input_samples_per_frame: int = 16_384
    output_samples_per_frame: int = 4_096
    passband_edge_hz: int = 800_000
    stopband_edge_hz: int = 1_000_000
    filter_taps: int = 193
    kaiser_beta: float = 7.85726
    minimum_dc_safe_offset_hz: int = 1_250_000
    maximum_tuning_offset_hz: int = 2_750_000

    def __post_init__(self) -> None:
        if self.input_sample_rate_hz != 4 * self.output_sample_rate_hz:
            raise ValueError("P0 kanal seçici yalnız 4:1 örnek azaltma profilini kabul eder.")
        if self.input_samples_per_frame != 4 * self.output_samples_per_frame:
            raise ValueError("Giriş ve çıkış çerçeve boyları 4:1 oranıyla uyumlu değildir.")
        if self.filter_taps < 5 or (self.filter_taps - 1) % 4 != 0:
            raise ValueError("FIR tap sayısı 4:1 polyphase düzeni için 4k+1 olmalıdır.")
        nyquist = self.output_sample_rate_hz // 2
        if not 0 < self.passband_edge_hz < self.stopband_edge_hz <= nyquist:
            raise ValueError("Geçiş bandı 2 MS/s Nyquist sınırı içinde olmalıdır.")
        if not nyquist < self.minimum_dc_safe_offset_hz <= self.maximum_tuning_offset_hz:
            raise ValueError("DC-güvenli tuning ofseti çıkış Nyquist sınırının dışında olmalıdır.")

    @property
    def decimation_factor(self) -> int:
        return self.input_sample_rate_hz // self.output_sample_rate_hz

    @property
    def group_delay_input_samples(self) -> int:
        return (self.filter_taps - 1) // 2


@dataclass(frozen=True)
class ChannelizedFrame:
    frame: IQFrame
    saturated_components: int
    processing_seconds: float
    input_center_frequency_hz: int
    tuning_offset_hz: int
    filter_group_delay_input_samples: int


def _design_lowpass(profile: P0ChannelizerProfile) -> npt.NDArray[np.float64]:
    cutoff_hz = 0.5 * (profile.passband_edge_hz + profile.stopband_edge_hz)
    index = np.arange(profile.filter_taps, dtype=np.float64)
    index -= 0.5 * (profile.filter_taps - 1)
    normalized_cutoff = cutoff_hz / profile.input_sample_rate_hz
    taps = 2.0 * normalized_cutoff * np.sinc(2.0 * normalized_cutoff * index)
    taps *= np.kaiser(profile.filter_taps, profile.kaiser_beta)
    taps /= np.sum(taps)
    taps.setflags(write=False)
    return taps


class P0Channelizer:
    """Frequency-shift, anti-alias filter, decimate and quantize one FPGA frame.

    State is preserved across consecutive frames. A reset is required whenever
    the source stream or either center frequency changes.
    """

    backend_name = "numpy-reference"

    def __init__(self, profile: P0ChannelizerProfile | None = None) -> None:
        self.profile = profile or P0ChannelizerProfile()
        self._taps = _design_lowpass(self.profile)
        self._polyphase_taps = tuple(
            self._taps[phase :: self.profile.decimation_factor]
            for phase in range(self.profile.decimation_factor)
        )
        self._delay = np.zeros(self.profile.filter_taps - 1, dtype=np.complex128)
        self._nco_phase_radians = 0.0
        self._nco_vector: npt.NDArray[np.complex128] | None = None
        self._stream_binding: tuple[int, int] | None = None

    @property
    def taps(self) -> npt.NDArray[np.float64]:
        return self._taps

    def reset(self) -> None:
        self._delay.fill(0.0)
        self._nco_phase_radians = 0.0
        self._nco_vector = None
        self._stream_binding = None

    backend_name = "numpy-reference"

    def process_ci8(self, payload: bytes, **arguments) -> tuple[ChannelizedFrame, int]:
        """Reference CI8 adapter used when the native real-time core is unavailable."""
        expected_bytes = self.profile.input_samples_per_frame * 2
        if len(payload) != expected_bytes:
            raise ValueError("Kanal seçici tam 16.384 kompleks CI8 giriş örneği gerektirir.")
        raw = np.frombuffer(payload, dtype=np.int8)
        input_saturated = int(np.count_nonzero((raw == -128) | (raw == 127)))
        values = raw.astype(np.float64).reshape(-1, 2) / 128.0
        samples = values[:, 0] + 1j * values[:, 1]
        return self.process(samples, **arguments), input_saturated

    def process(
        self,
        samples: npt.ArrayLike,
        *,
        sequence_number: int,
        frame_id: int,
        input_sample_rate_hz: int,
        input_center_frequency_hz: int,
        output_center_frequency_hz: int,
        require_dc_safe_tuning: bool = True,
    ) -> ChannelizedFrame:
        started = time.perf_counter()
        profile = self.profile
        if input_sample_rate_hz != profile.input_sample_rate_hz:
            raise ValueError("Kanal seçici girişi kilitli 8 MS/s profiliyle eşleşmiyor.")
        values = np.asarray(samples, dtype=np.complex128)
        if values.ndim != 1 or values.size != profile.input_samples_per_frame:
            raise ValueError("Kanal seçici tam 16.384 kompleks giriş örneği gerektirir.")
        if not np.all(np.isfinite(values.real)) or not np.all(np.isfinite(values.imag)):
            raise ValueError("Kanal seçici girişi sonlu kompleks örneklerden oluşmalıdır.")
        if not 0 <= sequence_number <= 0xFFFFFFFF or not 0 <= frame_id <= 0xFFFFFFFF:
            raise ValueError("Çerçeve ve sıra kimliği uint32 sınırında olmalıdır.")
        if input_center_frequency_hz <= 0 or output_center_frequency_hz <= 0:
            raise ValueError("Giriş ve çıkış merkez frekansları pozitif olmalıdır.")

        offset_hz = output_center_frequency_hz - input_center_frequency_hz
        absolute_offset_hz = abs(offset_hz)
        if absolute_offset_hz > profile.maximum_tuning_offset_hz:
            raise ValueError("Seçilen kanal HackRF örnekleme bandının güvenli tuning zarfı dışındadır.")
        if require_dc_safe_tuning and absolute_offset_hz < profile.minimum_dc_safe_offset_hz:
            raise ValueError("Canlı HackRF yolu için merkez frekansı DC-güvenli ofsetle seçilmelidir.")

        binding = (input_center_frequency_hz, output_center_frequency_hz)
        if self._stream_binding is None:
            self._stream_binding = binding
            phase_step = -2.0 * math.pi * offset_hz / input_sample_rate_hz
            self._nco_vector = np.exp(
                1j * phase_step * np.arange(values.size, dtype=np.float64)
            )
        elif self._stream_binding != binding:
            raise ValueError("Akış merkez frekansı değişmeden önce kanal seçici sıfırlanmalıdır.")

        phase_step = -2.0 * math.pi * offset_hz / input_sample_rate_hz
        assert self._nco_vector is not None
        mixed = values * self._nco_vector * np.exp(1j * self._nco_phase_radians)
        self._nco_phase_radians = math.remainder(
            self._nco_phase_radians + phase_step * values.size,
            2.0 * math.pi,
        )

        extended = np.concatenate((self._delay, mixed))
        decimated = np.zeros(profile.output_samples_per_frame, dtype=np.complex128)
        for phase, phase_taps in enumerate(self._polyphase_taps):
            stream = extended[(profile.filter_taps - 1 - phase) % 4 :: 4]
            filtered_phase = np.convolve(stream, phase_taps, mode="full")
            first = (profile.filter_taps - 1 - phase) // 4
            decimated += filtered_phase[first : first + profile.output_samples_per_frame]
        self._delay[:] = extended[-self._delay.size :]
        if decimated.size != profile.output_samples_per_frame:
            raise RuntimeError("Kanal seçici beklenen FPGA çerçeve boyunu üretmedi.")

        scaled_real = np.rint(decimated.real * 128.0)
        scaled_imag = np.rint(decimated.imag * 128.0)
        saturated = int(
            np.count_nonzero((scaled_real < -128.0) | (scaled_real > 127.0))
            + np.count_nonzero((scaled_imag < -128.0) | (scaled_imag > 127.0))
        )
        interleaved = np.empty(profile.output_samples_per_frame * 2, dtype=np.int8)
        interleaved[0::2] = np.clip(scaled_real, -128.0, 127.0).astype(np.int8)
        interleaved[1::2] = np.clip(scaled_imag, -128.0, 127.0).astype(np.int8)
        frame = IQFrame(
            sequence_number=sequence_number,
            sample_rate_hz=profile.output_sample_rate_hz,
            center_frequency_hz=output_center_frequency_hz,
            payload=interleaved.tobytes(),
            frame_id=frame_id,
        )
        return ChannelizedFrame(
            frame=frame,
            saturated_components=saturated,
            processing_seconds=time.perf_counter() - started,
            input_center_frequency_hz=input_center_frequency_hz,
            tuning_offset_hz=offset_hz,
            filter_group_delay_input_samples=profile.group_delay_input_samples,
        )
