"""Receive-only HackRF tuning plans and hardware-ready P0 search backend."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import numpy.typing as npt

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
    dc_exclusion_hz: int = 100_000
    offset_tuning_hz: int = 500_000

    def __post_init__(self) -> None:
        if self.sample_rate_hz not in {8_000_000, 10_000_000, 20_000_000}:
            raise ValueError("HackRF örnekleme hızı desteklenen hazırlık zarfında değildir.")
        if not 0 <= self.edge_guard_hz < self.sample_rate_hz // 2:
            raise ValueError("HackRF kenar guard değeri geçersizdir.")
        if not 0 <= self.overlap_hz < self.analysis_bandwidth_hz:
            raise ValueError("HackRF pencere overlap değeri geçersizdir.")
        if not 4_096 <= self.sample_count <= 65_536 or self.sample_count % 4_096:
            raise ValueError("HackRF bounded capture örnek sayısı geçersizdir.")
        if not 0 < self.dc_exclusion_hz < self.offset_tuning_hz:
            raise ValueError("HackRF DC dışlama ve offset tuning değerleri geçersizdir.")
        if self.offset_tuning_hz >= self.analysis_bandwidth_hz // 2:
            raise ValueError("HackRF offset tuning değeri kullanılabilir yarı banttan küçük olmalıdır.")

    @property
    def analysis_bandwidth_hz(self) -> int:
        return self.sample_rate_hz - 2 * self.edge_guard_hz

    @property
    def tuning_step_hz(self) -> int:
        return self.analysis_bandwidth_hz - self.overlap_hz

    @property
    def maximum_dc_safe_interval_hz(self) -> int:
        return self.analysis_bandwidth_hz // 2 - self.offset_tuning_hz


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
            window = self._offset_window(center - half, center + half, index=0)
            return HackRFTuningPlan(request.mode, (window,), ((center - half, center + half),))

        windows: list[HackRFTuningWindowPlan] = []
        for lower, upper in ranges:
            self._validate_interval(lower, upper)
            windows.extend(self._plan_interval(round(lower), round(upper), start_index=len(windows)))
        return HackRFTuningPlan(request.mode, tuple(windows), tuple((round(a), round(b)) for a, b in ranges))

    def _plan_interval(self, lower: int, upper: int, *, start_index: int) -> list[HackRFTuningWindowPlan]:
        result: list[HackRFTuningWindowPlan] = []
        cursor = lower
        while cursor < upper:
            segment_upper = min(cursor + self.profile.maximum_dc_safe_interval_hz, upper)
            result.append(self._offset_window(cursor, segment_upper, index=start_index + len(result)))
            cursor = segment_upper
        return result

    def _offset_window(self, lower: int, upper: int, *, index: int) -> HackRFTuningWindowPlan:
        span = upper - lower
        if span > self.profile.maximum_dc_safe_interval_hz:
            raise ValueError("HackRF DC-güvenli tuning aralığı tek pencere sınırını aşıyor.")
        offset = self.profile.offset_tuning_hz
        minimum = round(MIN_RECEIVER_FREQUENCY_HZ)
        maximum = round(MAX_RECEIVER_FREQUENCY_HZ)
        if lower - offset >= minimum:
            center = lower - offset
        elif upper + offset <= maximum:
            center = upper + offset
        else:
            raise ValueError("HackRF DC-güvenli offset tuning alıcı sınırında kurulamıyor.")
        half_width = self.profile.analysis_bandwidth_hz // 2
        covered_lower = max(minimum, center - half_width)
        covered_upper = min(maximum, center + half_width)
        if covered_lower > lower or covered_upper < upper:
            raise AssertionError("HackRF DC-güvenli tuning penceresi istenen aralığı kapsamıyor.")
        return HackRFTuningWindowPlan(index, center, covered_lower, covered_upper, lower, upper)


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
