"""Host-only coarse detection on the wide HackRF preview spectrum.

This stage proposes receive candidates.  It does not replace the 2 MHz FPGA
detector or turn an unverified host proposal into a confirmed event.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import numpy.typing as npt

from .detection import MultiscaleDetector
from .models import CandidateRegion
from .temporal import TemporalConfirmation


@dataclass(frozen=True)
class CoarseDetectionConfig:
    input_bins: int = 16_384
    detector_bins: int = 4_096
    usable_half_band_hz: float = 3_000_000.0
    dc_guard_hz: float = 100_000.0

    def __post_init__(self) -> None:
        if self.input_bins <= 0 or self.detector_bins <= 0:
            raise ValueError("Kaba tespit hücre sayıları pozitif olmalıdır.")
        if self.input_bins % self.detector_bins:
            raise ValueError("Geniş spektrum hücreleri detector hücrelerine tam bölünmelidir.")
        if not math.isfinite(self.usable_half_band_hz) or self.usable_half_band_hz <= 0.0:
            raise ValueError("Kaba tespit kullanılabilir bandı geçersizdir.")
        if not math.isfinite(self.dc_guard_hz) or not 0.0 <= self.dc_guard_hz < self.usable_half_band_hz:
            raise ValueError("Kaba tespit DC koruması geçersizdir.")


@dataclass(frozen=True)
class CoarseDetection:
    track_id: int
    state: str
    observed_this_frame: bool
    lower_frequency_hz: float
    upper_frequency_hz: float
    peak_frequency_hz: float
    peak_to_noise_db: float


@dataclass(frozen=True)
class CoarseDetectionFrame:
    sequence_number: int
    center_frequency_hz: float
    sample_rate_hz: float
    candidates: tuple[CoarseDetection, ...]
    limitation: str = "Tüm 8 MHz gözlemi dolduran yayın için bağımsız gürültü referansı yoktur."


class CoarseSpectrumDetector:
    """Rebin a 16k wide spectrum and reuse the bounded 4096-cell detector."""

    def __init__(self, config: CoarseDetectionConfig | None = None) -> None:
        self.config = config or CoarseDetectionConfig()
        self._detector = MultiscaleDetector()
        self._tracker = TemporalConfirmation(association_tolerance_bins=8)
        self._observation_index = 0
        self._binding: tuple[float, float] | None = None

    def reset(self) -> None:
        self._tracker.reset()
        self._observation_index = 0
        self._binding = None

    def process(
        self,
        shifted_bin_power: npt.ArrayLike,
        *,
        center_frequency_hz: float,
        sample_rate_hz: float,
        sequence_number: int,
    ) -> CoarseDetectionFrame:
        power = np.asarray(shifted_bin_power, dtype=np.float64)
        if power.ndim != 1 or power.size != self.config.input_bins:
            raise ValueError(f"Kaba tespit tam {self.config.input_bins} güç hücresi ister.")
        if not np.all(np.isfinite(power)) or np.any(power < 0.0):
            raise ValueError("Kaba tespit gücü sonlu ve negatif olmayan değerler içermelidir.")
        center = float(center_frequency_hz)
        sample_rate = float(sample_rate_hz)
        if not math.isfinite(center) or not math.isfinite(sample_rate) or sample_rate <= 0.0:
            raise ValueError("Kaba tespit frekans bağı geçersizdir.")
        if self.config.usable_half_band_hz >= sample_rate / 2.0:
            raise ValueError("Kaba tespit kullanılabilir bandı Nyquist sınırının içinde olmalıdır.")

        binding = (center, sample_rate)
        if self._binding is not None and binding != self._binding:
            self._tracker.reset()
            self._observation_index = 0
        self._binding = binding

        group = self.config.input_bins // self.config.detector_bins
        detector_power = np.sum(power.reshape(self.config.detector_bins, group), axis=1)
        detected = self._vectorized_candidates(detector_power)
        bin_width = sample_rate / self.config.detector_bins
        usable_lower = center - self.config.usable_half_band_hz
        usable_upper = center + self.config.usable_half_band_hz
        retained: list[CandidateRegion] = []
        for candidate in detected:
            lower = center + (candidate.start_bin - self.config.detector_bins / 2.0) * bin_width
            upper = center + (candidate.end_bin + 1 - self.config.detector_bins / 2.0) * bin_width
            if lower < usable_lower or upper > usable_upper:
                continue
            broad = candidate.end_bin - candidate.start_bin + 1 >= self._detector.recovery_config.broad_minimum_span_bins
            if not broad and lower <= center + self.config.dc_guard_hz and upper >= center - self.config.dc_guard_hz:
                continue
            retained.append(candidate)

        tracks = self._tracker.update(tuple(retained), frame_id=self._observation_index)
        self._observation_index += 1
        rows = []
        for track in tracks:
            candidate = track.candidate
            lower = center + (candidate.start_bin - self.config.detector_bins / 2.0) * bin_width
            upper = center + (candidate.end_bin + 1 - self.config.detector_bins / 2.0) * bin_width
            peak = center + (candidate.peak_bin - self.config.detector_bins / 2.0) * bin_width
            ratio_db = (
                10.0 * math.log10(candidate.peak_power / candidate.noise_power_per_bin)
                if candidate.peak_power > 0.0 and candidate.noise_power_per_bin > 0.0
                else float("nan")
            )
            rows.append(CoarseDetection(
                track.track_id,
                track.state,
                track.observed_this_frame,
                lower,
                upper,
                peak,
                ratio_db,
            ))
        return CoarseDetectionFrame(
            int(sequence_number),
            center,
            sample_rate,
            tuple(rows),
        )

    def _vectorized_candidates(
        self,
        power: npt.NDArray[np.float64],
    ) -> tuple[CandidateRegion, ...]:
        """Return the canonical result with a vectorized host OS-CFAR stage."""
        os_detector = self._detector.os_detector
        cfg = os_detector.config
        radius = cfg.reference_cells_per_side + cfg.guard_cells_per_side
        windows = np.lib.stride_tricks.sliding_window_view(power, 2 * radius + 1)
        references = np.concatenate((
            windows[:, :cfg.reference_cells_per_side],
            windows[:, radius + cfg.guard_cells_per_side + 1:],
        ), axis=1)
        local_noise = np.partition(
            references,
            cfg.order_statistic_rank - 1,
            axis=1,
        )[:, cfg.order_statistic_rank - 1]
        local_threshold = local_noise * cfg.threshold_coefficient
        detections = np.zeros(power.size, dtype=np.bool_)
        noise = np.full(power.size, np.nan, dtype=np.float64)
        threshold = np.full(power.size, np.nan, dtype=np.float64)
        evaluated = slice(radius, power.size - radius)
        noise[evaluated] = local_noise
        threshold[evaluated] = local_threshold
        detections[evaluated] = power[evaluated] > local_threshold
        os_candidates = os_detector._group(power, detections, noise, threshold)
        recoveries = self._detector.recovery_candidates(power)
        retained = tuple(
            candidate for candidate in os_candidates
            if not any(
                candidate.start_bin <= recovery.end_bin
                and recovery.start_bin <= candidate.end_bin
                for recovery in recoveries
            )
        )
        return tuple(sorted(
            (*retained, *recoveries),
            key=lambda candidate: (candidate.start_bin, candidate.end_bin, candidate.peak_bin),
        ))
