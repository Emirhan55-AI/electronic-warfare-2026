"""Qt-independent floating-point reference spectrum processing."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]


class SpectrumError(ValueError):
    """Raised when the spectrum contract is violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SpectrumConfig:
    """Immutable configuration for one spectrum frame."""

    frame_length: int = 4096
    remove_dc: bool = False
    log_floor_db: float = -200.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.frame_length, int)
            or isinstance(self.frame_length, bool)
            or self.frame_length < 2
        ):
            raise SpectrumError("invalid_frame_length", "frame_length must be an integer of at least two")
        if not isinstance(self.remove_dc, bool):
            raise SpectrumError("invalid_dc_setting", "remove_dc must be boolean")
        if not math.isfinite(self.log_floor_db) or self.log_floor_db >= 0:
            raise SpectrumError("invalid_log_floor", "log_floor_db must be finite and negative")


@dataclass(frozen=True)
class SpectrumDisplay:
    """Shifted, normalized spectrum values used by the operator display."""

    frequency_offset_hz: FloatArray
    frequency_absolute_hz: FloatArray
    amplitude_fs: FloatArray
    bin_power_fs2: FloatArray
    bin_power_dbfs: FloatArray
    psd_fs2_per_hz: FloatArray
    psd_dbfs_per_hz: FloatArray


@dataclass(frozen=True)
class SpectrumResult:
    """Canonical instantaneous FFT plus its display-domain values."""

    frame_length: int
    sample_rate_hz: float
    center_frequency_hz: float
    bin_spacing_hz: float
    dc_removed: bool
    window_coherent_gain: float
    window_power_sum: float
    fft_unshifted: ComplexArray
    fft_power_unshifted: FloatArray
    display: SpectrumDisplay


def _readonly(array: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
    array.setflags(write=False)
    return array


def periodic_hann(frame_length: int) -> FloatArray:
    """Return the periodic Hann window used by the PHASE-02 contract."""
    if not isinstance(frame_length, int) or isinstance(frame_length, bool) or frame_length < 2:
        raise SpectrumError("invalid_frame_length", "frame_length must be an integer of at least two")
    index = np.arange(frame_length, dtype=np.float64)
    window = 0.5 - 0.5 * np.cos((2.0 * np.pi * index) / frame_length)
    return _readonly(window)


class SpectrumProcessor:
    """Stateless reference FFT processor with explicit normalization."""

    def __init__(self, config: SpectrumConfig | None = None) -> None:
        self.config = config or SpectrumConfig()
        self.window = periodic_hann(self.config.frame_length)
        self.window_coherent_gain = float(np.sum(self.window) / self.config.frame_length)
        self.window_power_sum = float(np.sum(np.square(self.window)))
        self._linear_power_floor = 10.0 ** (self.config.log_floor_db / 10.0)

    def process(
        self,
        samples: npt.ArrayLike,
        *,
        sample_rate_hz: float,
        center_frequency_hz: float,
    ) -> SpectrumResult:
        sample_rate = self._positive_finite(sample_rate_hz, "sample_rate_hz")
        center_frequency = self._finite(center_frequency_hz, "center_frequency_hz")
        frame = np.asarray(samples, dtype=np.complex128)
        if frame.ndim != 1 or frame.size != self.config.frame_length:
            raise SpectrumError(
                "frame_size_mismatch",
                f"frame must contain exactly {self.config.frame_length} complex samples",
            )
        if not np.all(np.isfinite(frame.real)) or not np.all(np.isfinite(frame.imag)):
            raise SpectrumError("nonfinite_input", "frame contains a non-finite sample")

        working = frame - np.mean(frame) if self.config.remove_dc else frame
        fft_unshifted = np.asarray(np.fft.fft(working * self.window), dtype=np.complex128)
        fft_power = np.asarray(np.square(fft_unshifted.real) + np.square(fft_unshifted.imag), dtype=np.float64)
        display = self._make_display(
            frame_length=self.config.frame_length,
            sample_rate_hz=sample_rate,
            center_frequency_hz=center_frequency,
            window_coherent_gain=self.window_coherent_gain,
            window_power_sum=self.window_power_sum,
            fft_power_unshifted=fft_power,
        )
        return SpectrumResult(
            frame_length=self.config.frame_length,
            sample_rate_hz=sample_rate,
            center_frequency_hz=center_frequency,
            bin_spacing_hz=sample_rate / self.config.frame_length,
            dc_removed=self.config.remove_dc,
            window_coherent_gain=self.window_coherent_gain,
            window_power_sum=self.window_power_sum,
            fft_unshifted=_readonly(fft_unshifted),
            fft_power_unshifted=_readonly(fft_power),
            display=display,
        )

    def display_from_power(
        self,
        result: SpectrumResult,
        fft_power_unshifted: npt.ArrayLike,
    ) -> SpectrumDisplay:
        """Normalize and shift an instantaneous or averaged FFT-power vector."""
        return self._make_display(
            frame_length=result.frame_length,
            sample_rate_hz=result.sample_rate_hz,
            center_frequency_hz=result.center_frequency_hz,
            window_coherent_gain=result.window_coherent_gain,
            window_power_sum=result.window_power_sum,
            fft_power_unshifted=fft_power_unshifted,
        )

    def _make_display(
        self,
        *,
        frame_length: int,
        sample_rate_hz: float,
        center_frequency_hz: float,
        window_coherent_gain: float,
        window_power_sum: float,
        fft_power_unshifted: npt.ArrayLike,
    ) -> SpectrumDisplay:
        power = np.asarray(fft_power_unshifted, dtype=np.float64)
        if power.ndim != 1 or power.size != frame_length:
            raise SpectrumError("power_size_mismatch", "FFT power vector length does not match the frame")
        if not np.all(np.isfinite(power)) or np.any(power < 0.0):
            raise SpectrumError("invalid_fft_power", "FFT power vector must be finite and non-negative")

        amplitude = np.sqrt(power) / (frame_length * window_coherent_gain)
        bin_power = np.square(amplitude)
        psd = power / (sample_rate_hz * window_power_sum)
        bin_power_db = 10.0 * np.log10(np.maximum(bin_power, self._linear_power_floor))
        psd_db = 10.0 * np.log10(np.maximum(psd, self._linear_power_floor))
        offset = np.fft.fftshift(
            np.fft.fftfreq(frame_length, d=1.0 / sample_rate_hz)
        ).astype(np.float64, copy=False)

        return SpectrumDisplay(
            frequency_offset_hz=_readonly(offset),
            frequency_absolute_hz=_readonly(offset.copy() + center_frequency_hz),
            amplitude_fs=_readonly(np.fft.fftshift(amplitude).astype(np.float64, copy=False)),
            bin_power_fs2=_readonly(np.fft.fftshift(bin_power).astype(np.float64, copy=False)),
            bin_power_dbfs=_readonly(np.fft.fftshift(bin_power_db).astype(np.float64, copy=False)),
            psd_fs2_per_hz=_readonly(np.fft.fftshift(psd).astype(np.float64, copy=False)),
            psd_dbfs_per_hz=_readonly(np.fft.fftshift(psd_db).astype(np.float64, copy=False)),
        )

    @staticmethod
    def _finite(value: float, field: str) -> float:
        try:
            converted = float(value)
        except (TypeError, ValueError) as exc:
            raise SpectrumError("invalid_numeric_value", f"{field} must be numeric") from exc
        if not math.isfinite(converted):
            raise SpectrumError("invalid_numeric_value", f"{field} must be finite")
        return converted

    @classmethod
    def _positive_finite(cls, value: float, field: str) -> float:
        converted = cls._finite(value, field)
        if converted <= 0.0:
            raise SpectrumError("invalid_numeric_value", f"{field} must be positive")
        return converted


class ExponentialPowerAverager:
    """Bounded single-vector exponential average in linear FFT-power space."""

    def __init__(self, alpha: float = 0.2) -> None:
        if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
            raise SpectrumError("invalid_average_alpha", "alpha must be in the interval (0, 1]")
        self.alpha = float(alpha)
        self._state: FloatArray | None = None

    @property
    def initialized(self) -> bool:
        return self._state is not None

    def reset(self) -> None:
        self._state = None

    def update(self, fft_power_unshifted: npt.ArrayLike) -> FloatArray:
        current = np.asarray(fft_power_unshifted, dtype=np.float64)
        if current.ndim != 1 or not np.all(np.isfinite(current)) or np.any(current < 0.0):
            raise SpectrumError("invalid_fft_power", "FFT power vector must be one-dimensional and finite")
        if self._state is None:
            self._state = current.copy()
        else:
            if self._state.shape != current.shape:
                raise SpectrumError("power_size_mismatch", "average vector length changed without reset")
            self._state *= 1.0 - self.alpha
            self._state += self.alpha * current
        result = self._state.copy()
        return _readonly(result)
