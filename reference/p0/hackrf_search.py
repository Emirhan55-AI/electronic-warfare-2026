"""Receive-only HackRF tuning plans and hardware-ready P0 search backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import numpy.typing as npt

from host.acquisition import HackRFBackend, HackRFHostRxSource, RXConfig

from .search import (
    MAX_RECEIVER_FREQUENCY_HZ,
    MIN_RECEIVER_FREQUENCY_HZ,
    SearchMode,
    SearchRequest,
    TuningWindow,
)


@dataclass(frozen=True)
class HackRFTuningProfile:
    sample_rate_hz: int = 8_000_000
    edge_guard_hz: int = 1_000_000
    overlap_hz: int = 500_000
    sample_count: int = 16_384

    def __post_init__(self) -> None:
        if self.sample_rate_hz not in {8_000_000, 10_000_000, 20_000_000}:
            raise ValueError("HackRF örnekleme hızı desteklenen hazırlık zarfında değildir.")
        if not 0 <= self.edge_guard_hz < self.sample_rate_hz // 2:
            raise ValueError("HackRF kenar guard değeri geçersizdir.")
        if not 0 <= self.overlap_hz < self.analysis_bandwidth_hz:
            raise ValueError("HackRF pencere overlap değeri geçersizdir.")
        if not 4_096 <= self.sample_count <= 65_536 or self.sample_count % 4_096:
            raise ValueError("HackRF bounded capture örnek sayısı geçersizdir.")

    @property
    def analysis_bandwidth_hz(self) -> int:
        return self.sample_rate_hz - 2 * self.edge_guard_hz

    @property
    def tuning_step_hz(self) -> int:
        return self.analysis_bandwidth_hz - self.overlap_hz


@dataclass(frozen=True)
class HackRFTuningWindowPlan:
    index: int
    center_frequency_hz: int
    covered_lower_frequency_hz: int
    covered_upper_frequency_hz: int
    requested_lower_frequency_hz: int
    requested_upper_frequency_hz: int


@dataclass(frozen=True)
class HackRFTuningPlan:
    mode: SearchMode
    windows: tuple[HackRFTuningWindowPlan, ...]
    requested_ranges_hz: tuple[tuple[int, int], ...]


class HackRFSearchPlanner:
    """Translate Block A requests into deterministic, gap-free RX windows."""

    def __init__(
        self,
        *,
        profile: HackRFTuningProfile | None = None,
        unknown_ranges_hz: tuple[tuple[int, int], ...] = (),
    ) -> None:
        self.profile = profile or HackRFTuningProfile()
        self.unknown_ranges_hz = tuple(unknown_ranges_hz)
        for lower, upper in self.unknown_ranges_hz:
            self._validate_interval(lower, upper)

    @staticmethod
    def _validate_interval(lower: float, upper: float) -> None:
        if not np.isfinite(lower) or not np.isfinite(upper):
            raise ValueError("HackRF arama sınırları sonlu olmalıdır.")
        if not MIN_RECEIVER_FREQUENCY_HZ <= lower < upper <= MAX_RECEIVER_FREQUENCY_HZ:
            raise ValueError("HackRF arama aralığı alıcı sınırlarının dışındadır.")

    def plan(self, request: SearchRequest) -> HackRFTuningPlan:
        if request.mode is SearchMode.UNKNOWN:
            if not self.unknown_ranges_hz:
                raise ValueError("Bilinmeyen frekans arama profili henüz atanmadı.")
            ranges = self.unknown_ranges_hz
        elif request.mode is SearchMode.JUDGE_BAND:
            bounds = request.analysis_bounds_hz()
            assert bounds is not None
            ranges = ((round(bounds[0]), round(bounds[1])),)
        else:
            assert request.center_frequency_hz is not None
            center = round(request.center_frequency_hz)
            half = round(request.frequency_window_hz / 2.0)
            self._validate_interval(center - half, center + half)
            width = self.profile.analysis_bandwidth_hz
            covered_lower = max(round(MIN_RECEIVER_FREQUENCY_HZ), center - width // 2)
            covered_upper = min(round(MAX_RECEIVER_FREQUENCY_HZ), center + width // 2)
            window = HackRFTuningWindowPlan(0, center, covered_lower, covered_upper, center - half, center + half)
            return HackRFTuningPlan(request.mode, (window,), ((center - half, center + half),))

        windows: list[HackRFTuningWindowPlan] = []
        for lower, upper in ranges:
            self._validate_interval(lower, upper)
            windows.extend(self._plan_interval(round(lower), round(upper), start_index=len(windows)))
        return HackRFTuningPlan(request.mode, tuple(windows), tuple((round(a), round(b)) for a, b in ranges))

    def _plan_interval(self, lower: int, upper: int, *, start_index: int) -> list[HackRFTuningWindowPlan]:
        width = self.profile.analysis_bandwidth_hz
        step = self.profile.tuning_step_hz
        span = upper - lower
        if span <= width:
            centers = [round((lower + upper) / 2.0)]
        else:
            first = lower + width // 2
            last = upper - width // 2
            centers = [first]
            while centers[-1] + step < last:
                centers.append(centers[-1] + step)
            if centers[-1] != last:
                centers.append(last)
        result: list[HackRFTuningWindowPlan] = []
        for offset, center in enumerate(centers):
            covered_lower = max(round(MIN_RECEIVER_FREQUENCY_HZ), center - width // 2)
            covered_upper = min(round(MAX_RECEIVER_FREQUENCY_HZ), center + width // 2)
            result.append(
                HackRFTuningWindowPlan(
                    start_index + offset,
                    center,
                    covered_lower,
                    covered_upper,
                    max(lower, covered_lower),
                    min(upper, covered_upper),
                )
            )
        return result


def shifted_absolute_frequency_axis(
    center_frequency_hz: float,
    sample_rate_hz: float,
    fft_length: int,
) -> npt.NDArray[np.float64]:
    if not np.isfinite(center_frequency_hz) or not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("Frekans ekseni girdileri geçersizdir.")
    if isinstance(fft_length, bool) or not isinstance(fft_length, int) or fft_length < 2:
        raise ValueError("FFT uzunluğu geçersizdir.")
    return np.asarray(
        center_frequency_hz + np.fft.fftshift(np.fft.fftfreq(fft_length, d=1.0 / sample_rate_hz)),
        dtype=np.float64,
    )


class HackRFSearchBackend:
    """Blocking RX backend intended for an existing non-UI worker boundary."""

    backend_name = "HACKRF/HOST"

    def __init__(
        self,
        backend: HackRFBackend,
        *,
        device_serial: str,
        planner: HackRFSearchPlanner,
        progress_callback: Callable[[int, int, HackRFTuningWindowPlan], None] | None = None,
    ) -> None:
        if backend.backend_kind != "real":
            raise ValueError("HackRF arama backend'i yalnız gerçek RX backend sözleşmesini kabul eder.")
        self.backend = backend
        self.device_serial = device_serial
        self.planner = planner
        self.progress_callback = progress_callback
        self.last_progress = (0, 0)

    def acquire(self, request: SearchRequest) -> tuple[TuningWindow, ...]:
        plan = self.planner.plan(request)
        windows: list[TuningWindow] = []
        self.last_progress = (0, len(plan.windows))
        for item in plan.windows:
            config = RXConfig(
                center_frequency_hz=item.center_frequency_hz,
                sample_rate_hz=self.planner.profile.sample_rate_hz,
                sample_count=self.planner.profile.sample_count,
                device_serial=self.device_serial,
            )
            source = HackRFHostRxSource(self.backend, config, queue_capacity=4)
            try:
                frames = tuple(source.read() for _ in range(config.sample_count // 4096))
            finally:
                source.stop()
            if any(frame is None for frame in frames):
                raise RuntimeError("HackRF bounded RX beklenen frame sayısını üretmedi.")
            windows.append(
                TuningWindow(
                    f"hackrf-window-{item.index:04d}",
                    item.center_frequency_hz,
                    self.planner.profile.sample_rate_hz,
                    tuple(frame.samples for frame in frames if frame is not None),
                    provenance="LIVE_HACKRF",
                )
            )
            self.last_progress = (len(windows), len(plan.windows))
            if self.progress_callback is not None:
                self.progress_callback(len(windows), len(plan.windows), item)
        return tuple(windows)
