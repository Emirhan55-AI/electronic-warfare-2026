"""Yerel, yayın bağlantısı bulunmayan C++ ET sinyal üreteci bağı."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np
import numpy.typing as npt


class NativeWaveform(IntEnum):
    TONE = 0
    FSK = 1
    SWEEP = 2
    PRBS = 3
    SINE = 4
    SQUARE = 5
    SAWTOOTH = 6
    TRIANGLE = 7
    CHIRP = 8
    AWGN = 9
    DC_OFFSET = 10


@dataclass(frozen=True)
class NativeSignalConfig:
    waveform: NativeWaveform = NativeWaveform.TONE
    sample_rate_hz: int = 48_000
    duration_seconds: float = 1.0
    frequency_hz: float = 1_000.0
    sweep_start_hz: float = -5_000.0
    sweep_stop_hz: float = 5_000.0
    amplitude: float = 0.7
    seed: int = 2026
    symbol_rate_hz: int = 1_000


@dataclass(frozen=True)
class NativeSignalResult:
    samples: npt.NDArray[np.complex128]
    raw_iq: npt.NDArray[np.int8]
    sample_rate_hz: int
    waveform: NativeWaveform
    provenance: str = "YEREL C++ OFFLINE TABAN BANT"
    tx_state: str = "KİLİTLİ"


class _NativeConfigV1(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("waveform", ctypes.c_uint32),
        ("sample_rate_hz", ctypes.c_uint32),
        ("symbol_rate_hz", ctypes.c_uint32),
        ("frequency_hz", ctypes.c_double),
        ("sweep_start_hz", ctypes.c_double),
        ("sweep_stop_hz", ctypes.c_double),
        ("amplitude", ctypes.c_double),
        ("seed", ctypes.c_uint32),
    ]


class NativeSignalGenerator:
    """C++ motorundan sınırlı yerel I/Q üretir; aygıt veya TX API'si sunmaz."""

    MAXIMUM_SAMPLES = 5_000_000

    def __init__(self, library_path: str | Path | None = None) -> None:
        path = Path(library_path) if library_path is not None else self.default_library_path()
        if path is None or not path.is_file():
            raise RuntimeError("ET yerel sinyal üreteci kitaplığı derlenmemiş")
        self._library = ctypes.CDLL(str(path))
        self._generate = self._library.et_signal_generate_v1
        self._generate.argtypes = [
            ctypes.POINTER(_NativeConfigV1),
            ctypes.POINTER(ctypes.c_int8),
            ctypes.c_size_t,
        ]
        self._generate.restype = ctypes.c_int32

    @staticmethod
    def default_library_path() -> Path | None:
        module_directory = Path(__file__).resolve().parent
        repository_root = module_directory.parents[1]
        names = (
            "et_signal_generator.dll",
            "libet_signal_generator.dll",
            "libet_signal_generator.so",
            "libet_signal_generator.dylib",
        )
        directories = (
            module_directory / "native" / "bin",
            repository_root / "build" / "et-signal-generator",
            repository_root / "build" / "et-signal-generator" / "Release",
        )
        for directory in directories:
            for name in names:
                candidate = directory / name
                if candidate.is_file():
                    return candidate
        return None

    def generate(self, config: NativeSignalConfig) -> NativeSignalResult:
        count = int(round(config.sample_rate_hz * config.duration_seconds))
        if count < 1 or count > self.MAXIMUM_SAMPLES:
            raise ValueError("örnek sayısı offline sınırının dışında")

        native = _NativeConfigV1(
            1,
            int(config.waveform),
            config.sample_rate_hz,
            config.symbol_rate_hz,
            config.frequency_hz,
            config.sweep_start_hz,
            config.sweep_stop_hz,
            config.amplitude,
            config.seed,
        )
        raw = np.empty((count, 2), dtype=np.int8)
        status = self._generate(
            ctypes.byref(native),
            raw.ctypes.data_as(ctypes.POINTER(ctypes.c_int8)),
            count,
        )
        if status != 0:
            raise ValueError(f"yerel sinyal üreteci yapılandırmayı reddetti: {status}")

        raw.setflags(write=False)
        samples = raw[:, 0].astype(np.float64) / 127.0 + 1j * raw[:, 1].astype(np.float64) / 127.0
        samples = np.asarray(samples, dtype=np.complex128)
        samples.setflags(write=False)
        return NativeSignalResult(samples, raw, config.sample_rate_hz, config.waveform)
