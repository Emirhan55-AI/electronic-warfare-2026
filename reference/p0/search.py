"""Hardware-independent competition search requests and replay execution backend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np
import numpy.typing as npt

from .detection import OSCFARDetector
from .models import P0ParameterResult
from .parameters import ParameterExtractor
from .temporal import TemporalConfirmation


MIN_RECEIVER_FREQUENCY_HZ = 1_000_000.0
MAX_RECEIVER_FREQUENCY_HZ = 6_000_000_000.0
MAX_JUDGE_BAND_SPAN_HZ = 20_000_000.0
DEFAULT_FREQUENCY_WINDOW_HZ = 50_000.0


class SearchMode(str, Enum):
    UNKNOWN = "UNKNOWN"
    JUDGE_BAND = "JUDGE_BAND"
    JUDGE_FREQUENCY = "JUDGE_FREQUENCY"


@dataclass(frozen=True)
class SearchRequest:
    mode: SearchMode
    lower_frequency_hz: float | None = None
    upper_frequency_hz: float | None = None
    center_frequency_hz: float | None = None
    frequency_window_hz: float = DEFAULT_FREQUENCY_WINDOW_HZ

    def __post_init__(self) -> None:
        supplied = tuple(
            value for value in (self.lower_frequency_hz, self.upper_frequency_hz, self.center_frequency_hz) if value is not None
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) for value in supplied):
            raise ValueError("Frekans değerleri sonlu sayılar olmalıdır.")
        if not np.isfinite(self.frequency_window_hz) or not 1_000.0 <= self.frequency_window_hz <= MAX_JUDGE_BAND_SPAN_HZ:
            raise ValueError("Merkez frekans analiz penceresi desteklenen sınırın dışındadır.")
        if self.mode is SearchMode.UNKNOWN:
            if supplied:
                raise ValueError("Bilinmeyen frekans modu hakem frekans girdisi kabul etmez.")
            return
        if self.mode is SearchMode.JUDGE_BAND:
            if self.lower_frequency_hz is None or self.upper_frequency_hz is None or self.center_frequency_hz is not None:
                raise ValueError("Hakem bant modu alt ve üst frekans gerektirir.")
            lower, upper = float(self.lower_frequency_hz), float(self.upper_frequency_hz)
            if not MIN_RECEIVER_FREQUENCY_HZ <= lower < upper <= MAX_RECEIVER_FREQUENCY_HZ:
                raise ValueError("Alt frekans üst frekanstan küçük ve alıcı sınırları içinde olmalıdır.")
            if upper - lower > MAX_JUDGE_BAND_SPAN_HZ:
                raise ValueError("Hakem bant aralığı desteklenen azami spanı aşıyor.")
            return
        if self.mode is SearchMode.JUDGE_FREQUENCY:
            if self.center_frequency_hz is None or self.lower_frequency_hz is not None or self.upper_frequency_hz is not None:
                raise ValueError("Hakem frekans modu yalnız merkez frekans gerektirir.")
            if not MIN_RECEIVER_FREQUENCY_HZ <= float(self.center_frequency_hz) <= MAX_RECEIVER_FREQUENCY_HZ:
                raise ValueError("Merkez frekans alıcı sınırlarının dışındadır.")
            return
        raise ValueError("Desteklenmeyen arama modu.")

    @classmethod
    def unknown(cls) -> "SearchRequest":
        return cls(SearchMode.UNKNOWN)

    @classmethod
    def judge_band_mhz(cls, lower_mhz: float, upper_mhz: float) -> "SearchRequest":
        return cls(SearchMode.JUDGE_BAND, float(lower_mhz) * 1_000_000.0, float(upper_mhz) * 1_000_000.0)

    @classmethod
    def judge_frequency_mhz(cls, center_mhz: float, *, window_khz: float = 50.0) -> "SearchRequest":
        return cls(
            SearchMode.JUDGE_FREQUENCY,
            center_frequency_hz=float(center_mhz) * 1_000_000.0,
            frequency_window_hz=float(window_khz) * 1_000.0,
        )

    def analysis_bounds_hz(self) -> tuple[float, float] | None:
        if self.mode is SearchMode.UNKNOWN:
            return None
        if self.mode is SearchMode.JUDGE_BAND:
            assert self.lower_frequency_hz is not None and self.upper_frequency_hz is not None
            return float(self.lower_frequency_hz), float(self.upper_frequency_hz)
        assert self.center_frequency_hz is not None
        half = self.frequency_window_hz / 2.0
        return float(self.center_frequency_hz - half), float(self.center_frequency_hz + half)


@dataclass(frozen=True)
class TuningWindow:
    window_id: str
    center_frequency_hz: float
    sample_rate_hz: float
    frames: tuple[npt.NDArray[np.complex128], ...]
    provenance: str = "REPLAY"

    def __post_init__(self) -> None:
        if not np.isfinite(self.center_frequency_hz) or not MIN_RECEIVER_FREQUENCY_HZ <= self.center_frequency_hz <= MAX_RECEIVER_FREQUENCY_HZ:
            raise ValueError("Tuning-window merkez frekansı geçersiz.")
        if not np.isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 0 or len(self.frames) < 2:
            raise ValueError("Tuning-window örnekleme hızı veya frame adedi geçersiz.")
        sizes = {np.asarray(frame).size for frame in self.frames}
        if len(sizes) != 1 or next(iter(sizes)) < 64:
            raise ValueError("Tuning-window frame boyları eşit ve bounded olmalıdır.")

    @property
    def lower_frequency_hz(self) -> float:
        return self.center_frequency_hz - self.sample_rate_hz / 2.0

    @property
    def upper_frequency_hz(self) -> float:
        return self.center_frequency_hz + self.sample_rate_hz / 2.0


class SearchAcquisitionBackend(Protocol):
    backend_name: str

    def acquire(self, request: SearchRequest) -> tuple[TuningWindow, ...]: ...


class ReplaySearchBackend:
    """Deterministic tuning-window emulator; it never reports live RF."""

    backend_name = "REPLAY/HOST"

    def __init__(self, windows: tuple[TuningWindow, ...]) -> None:
        if not windows:
            raise ValueError("Replay search backend requires at least one tuning window")
        self.windows = windows

    def acquire(self, request: SearchRequest) -> tuple[TuningWindow, ...]:
        bounds = request.analysis_bounds_hz()
        if request.mode is SearchMode.UNKNOWN:
            return self.windows
        assert bounds is not None
        lower, upper = bounds
        return tuple(window for window in self.windows if window.lower_frequency_hz <= upper and window.upper_frequency_hz >= lower)


@dataclass(frozen=True)
class SearchExecutionResult:
    request: SearchRequest
    backend_name: str
    examined_window_ids: tuple[str, ...]
    parameters: tuple[P0ParameterResult, ...]
    status: str


class P0SearchEngine:
    """Run all competition modes through one acquisition request abstraction."""

    def __init__(self, backend: SearchAcquisitionBackend) -> None:
        self.backend = backend

    def execute(self, request: SearchRequest) -> SearchExecutionResult:
        windows = self.backend.acquire(request)
        results: list[P0ParameterResult] = []
        for window in windows:
            tracker = TemporalConfirmation()
            final_iq: npt.NDArray[np.complex128] | None = None
            final_power: npt.NDArray[np.float64] | None = None
            final_detection = None
            final_tracks = ()
            for frame_id, raw_frame in enumerate(window.frames):
                iq = np.asarray(raw_frame, dtype=np.complex128)
                periodic_hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(iq.size, dtype=np.float64) / iq.size)
                power = np.abs(np.fft.fftshift(np.fft.fft(iq * periodic_hann))) ** 2
                detection = OSCFARDetector().process(power, frame_id=frame_id)
                candidates = self._filter_candidates(request, window, detection.candidates, iq.size)
                tracks = tracker.update(candidates, frame_id=frame_id)
                final_iq, final_power, final_detection, final_tracks = iq, power, detection, tracks
            assert final_iq is not None and final_power is not None and final_detection is not None
            confirmed = [track for track in final_tracks if track.state == "confirmed" and track.observed_this_frame]
            for track in confirmed:
                results.append(
                    ParameterExtractor().extract(
                        frame_id=len(window.frames) - 1,
                        iq=final_iq,
                        shifted_power=final_power,
                        sample_rate_hz=window.sample_rate_hz,
                        center_frequency_hz=window.center_frequency_hz,
                        candidate=track.candidate,
                        confirmed=True,
                        provenance=window.provenance,
                        backend=f"{self.backend.backend_name} -> {request.mode.value} -> P0 OS-CFAR",
                        neighboring_candidates=final_detection.candidates,
                    )
                )
        results.sort(key=lambda item: (-item.candidate.peak_power, item.carrier_frequency_hz))
        return SearchExecutionResult(
            request,
            self.backend.backend_name,
            tuple(window.window_id for window in windows),
            tuple(results),
            "COMPLETED_SIGNAL_FOUND" if results else "COMPLETED_NO_SIGNAL",
        )

    @staticmethod
    def _filter_candidates(request: SearchRequest, window: TuningWindow, candidates: tuple, frame_length: int) -> tuple:
        bounds = request.analysis_bounds_hz()
        if bounds is None:
            return candidates
        lower, upper = bounds
        bin_width = window.sample_rate_hz / frame_length
        frequencies = window.center_frequency_hz + np.fft.fftshift(np.fft.fftfreq(frame_length, d=1.0 / window.sample_rate_hz))
        return tuple(
            candidate
            for candidate in candidates
            if float(frequencies[candidate.end_bin] + bin_width / 2.0) >= lower
            and float(frequencies[candidate.start_bin] - bin_width / 2.0) <= upper
        )
