"""ctypes binding for the bounded real-time P0 CI8 channelizer core."""

from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

from .channelizer import ChannelizedFrame, P0ChannelizerProfile, _design_lowpass
from .transport import IQFrame


def _library_candidates() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[2]
    configured = os.environ.get("P0_CHANNELIZER_NATIVE_LIBRARY")
    name = "p0_channelizer.dll" if sys.platform == "win32" else (
        "libp0_channelizer.dylib" if sys.platform == "darwin" else "libp0_channelizer.so"
    )
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend((
        root / "build" / "native" / "p0_channelizer" / "Release" / name,
        root / "build" / "native" / "p0_channelizer" / name,
        Path(__file__).with_name("native") / "bin" / name,
    ))
    return tuple(candidates)


def find_native_channelizer_library() -> Path | None:
    return next((path for path in _library_candidates() if path.is_file()), None)


def native_channelizer_cpu_supported() -> bool:
    """Confirm the instruction set required by the optimized native core."""
    try:
        features = np._core._multiarray_umath.__cpu_features__
    except (AttributeError, ImportError):
        return False
    return bool(features.get("AVX2") and features.get("FMA3"))


class NativeP0Channelizer:
    """Stateful native CI8 channelizer with the same frame contract as the NumPy model."""

    backend_name = "native-cpp"

    def __init__(self, profile: P0ChannelizerProfile | None = None, *, library_path: Path | None = None) -> None:
        self.profile = profile or P0ChannelizerProfile()
        if not native_channelizer_cpu_supported():
            raise RuntimeError("İşlemci P0 yerel kanal seçicinin AVX2/FMA3 gereksinimini karşılamıyor.")
        path = library_path or find_native_channelizer_library()
        if path is None:
            raise RuntimeError("P0 yerel kanal seçici kitaplığı bulunamadı.")
        self.library_path = path.resolve()
        self._library = ctypes.CDLL(str(self.library_path))
        self._configure_library()
        if self._library.p0_channelizer_abi_version() != 1:
            raise RuntimeError("P0 yerel kanal seçici ABI sürümü uyumsuz.")
        self._handle: int | None = None
        self._binding: tuple[int, int] | None = None
        self._taps = np.ascontiguousarray(_design_lowpass(self.profile), dtype=np.float64)
        self._input_buffer = (ctypes.c_int8 * (self.profile.input_samples_per_frame * 2))()
        self._output_buffer = (ctypes.c_int8 * (self.profile.output_samples_per_frame * 2))()
        self._input_saturated = ctypes.c_uint64()
        self._output_saturated = ctypes.c_uint64()

    def _configure_library(self) -> None:
        library = self._library
        library.p0_channelizer_abi_version.restype = ctypes.c_uint32
        library.p0_channelizer_create.argtypes = (
            ctypes.POINTER(ctypes.c_double), ctypes.c_size_t, ctypes.c_double,
        )
        library.p0_channelizer_create.restype = ctypes.c_void_p
        library.p0_channelizer_reset.argtypes = (ctypes.c_void_p,)
        library.p0_channelizer_destroy.argtypes = (ctypes.c_void_p,)
        library.p0_channelizer_process_ci8.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int8), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int8), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64),
        )
        library.p0_channelizer_process_ci8.restype = ctypes.c_int

    def reset(self) -> None:
        if self._handle is not None:
            self._library.p0_channelizer_destroy(self._handle)
            self._handle = None
        self._binding = None

    def close(self) -> None:
        self.reset()

    def _bind(self, input_center_frequency_hz: int, output_center_frequency_hz: int) -> None:
        binding = (input_center_frequency_hz, output_center_frequency_hz)
        if self._binding is not None and binding != self._binding:
            raise ValueError("Akış merkez frekansı değişmeden önce kanal seçici sıfırlanmalıdır.")
        if self._handle is not None:
            return
        offset_hz = output_center_frequency_hz - input_center_frequency_hz
        phase_step = -2.0 * math.pi * offset_hz / self.profile.input_sample_rate_hz
        handle = self._library.p0_channelizer_create(
            self._taps.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._taps.size,
            phase_step,
        )
        if not handle:
            raise RuntimeError("P0 yerel kanal seçici durumu oluşturulamadı.")
        self._handle = int(handle)
        self._binding = binding

    def process_ci8(
        self,
        payload: bytes,
        *,
        sequence_number: int,
        frame_id: int,
        input_sample_rate_hz: int,
        input_center_frequency_hz: int,
        output_center_frequency_hz: int,
        require_dc_safe_tuning: bool = True,
    ) -> tuple[ChannelizedFrame, int]:
        started = time.perf_counter()
        profile = self.profile
        if input_sample_rate_hz != profile.input_sample_rate_hz:
            raise ValueError("Kanal seçici girişi kilitli 8 MS/s profiliyle eşleşmiyor.")
        if len(payload) != profile.input_samples_per_frame * 2:
            raise ValueError("Kanal seçici tam 16.384 kompleks CI8 giriş örneği gerektirir.")
        if not 0 <= sequence_number <= 0xFFFFFFFF or not 0 <= frame_id <= 0xFFFFFFFF:
            raise ValueError("Çerçeve ve sıra kimliği uint32 sınırında olmalıdır.")
        if input_center_frequency_hz <= 0 or output_center_frequency_hz <= 0:
            raise ValueError("Giriş ve çıkış merkez frekansları pozitif olmalıdır.")
        offset_hz = output_center_frequency_hz - input_center_frequency_hz
        if abs(offset_hz) > profile.maximum_tuning_offset_hz:
            raise ValueError("Seçilen kanal HackRF örnekleme bandının güvenli tuning zarfı dışındadır.")
        if require_dc_safe_tuning and abs(offset_hz) < profile.minimum_dc_safe_offset_hz:
            raise ValueError("Canlı HackRF yolu için merkez frekansı DC-güvenli ofsetle seçilmelidir.")
        self._bind(input_center_frequency_hz, output_center_frequency_hz)
        ctypes.memmove(self._input_buffer, payload, len(payload))
        status = self._library.p0_channelizer_process_ci8(
            self._handle,
            self._input_buffer, len(payload),
            self._output_buffer, len(self._output_buffer),
            ctypes.byref(self._input_saturated), ctypes.byref(self._output_saturated),
        )
        if status != 0:
            raise RuntimeError(f"P0 yerel kanal seçici hatası ({status}).")
        frame = IQFrame(
            sequence_number=sequence_number,
            sample_rate_hz=profile.output_sample_rate_hz,
            center_frequency_hz=output_center_frequency_hz,
            payload=bytes(self._output_buffer),
            frame_id=frame_id,
        )
        return ChannelizedFrame(
            frame=frame,
            saturated_components=int(self._output_saturated.value),
            processing_seconds=time.perf_counter() - started,
            input_center_frequency_hz=input_center_frequency_hz,
            tuning_offset_hz=offset_hz,
            filter_group_delay_input_samples=profile.group_delay_input_samples,
            output_amplitude_scale=profile.output_amplitude_scale,
        ), int(self._input_saturated.value)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def create_realtime_channelizer():
    path = find_native_channelizer_library()
    if path is not None:
        return NativeP0Channelizer(library_path=path)
    from .channelizer import P0Channelizer
    return P0Channelizer()
