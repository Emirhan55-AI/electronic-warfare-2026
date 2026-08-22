"""Real two-point HackRF amplitude comparison for the operator console."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np

from reference.spectrum import SigMFFrameSource, SpectrumProcessor


REAL_TWO_POINT_SOURCE = "HACKRF KAYDI / GERÇEK AÇI–GÜÇ ÖLÇÜMÜ"


@dataclass(frozen=True)
class TwoPointPower:
    angle_deg: int
    metadata_path: Path
    measured_power_dbfs: float
    analyzed_frame_count: int
    discarded_frame_count: int
    robust_spread_db: float


@dataclass(frozen=True)
class TwoPointDFResult:
    frequency_hz: float
    channel_bandwidth_hz: float
    zero: TwoPointPower
    ninety: TwoPointPower

    @property
    def power_difference_db(self) -> float:
        return self.zero.measured_power_dbfs - self.ninety.measured_power_dbfs

    @property
    def comparison_uncertainty_db(self) -> float:
        return math.hypot(self.zero.robust_spread_db, self.ninety.robust_spread_db)

    @property
    def stronger(self) -> TwoPointPower | None:
        """Return a direction only when the recorded difference exceeds spread."""
        if abs(self.power_difference_db) <= self.comparison_uncertainty_db:
            return None
        return self.zero if self.power_difference_db > 0.0 else self.ninety


def _measure(path: Path, angle_deg: int, *, channel_bandwidth_hz: float, maximum_frames: int) -> tuple[TwoPointPower, float]:
    source = SigMFFrameSource(path)
    if source.source_description != "HackRF recorded IQ replay":
        raise ValueError(f"{path.name}: gerçek HackRF kayıt tanımı doğrulanamadı")
    discard = int(math.ceil(0.5 * source.sample_rate_hz / source.frame_length))
    if source.frame_count - discard < 8:
        raise ValueError(f"{path.name}: 0,5 saniye sonrasında yeterli tam frame yok")
    target_frequency = source.center_frequency_hz
    axis = np.fft.fftshift(np.fft.fftfreq(source.frame_length, d=1.0 / source.sample_rate_hz)) + target_frequency
    mask = np.abs(axis - target_frequency) <= channel_bandwidth_hz / 2.0
    indexes = np.linspace(discard, source.frame_count - 1, min(maximum_frames, source.frame_count - discard), dtype=np.int64)
    processor = SpectrumProcessor()
    powers: list[float] = []
    for index in indexes:
        result = processor.process(
            source.read_frame(int(index)), sample_rate_hz=source.sample_rate_hz, center_frequency_hz=target_frequency
        )
        powers.append(10.0 * math.log10(max(float(np.sum(result.display.bin_power_fs2[mask])), 1e-300)))
    values = np.asarray(powers)
    median = float(np.median(values))
    robust_spread = float(1.4826 * np.median(np.abs(values - median)))
    return TwoPointPower(angle_deg, path, median, len(indexes), discard, robust_spread), target_frequency


def analyze_two_point_hackrf_df(
    zero_metadata_path: Path,
    ninety_metadata_path: Path,
    *,
    channel_bandwidth_hz: float = 12_500.0,
    maximum_frames: int = 256,
) -> TwoPointDFResult:
    """Measure 0° and 90° directly from their SigMF I/Q recordings.

    The selected channel is centred at each recording's declared centre
    frequency; no synthetic samples, power values, or bearing are introduced.
    """
    if not 2_000.0 <= channel_bandwidth_hz <= 200_000.0 or maximum_frames < 8:
        raise ValueError("iki noktalı DF analiz ayarı geçersiz")
    zero, zero_frequency = _measure(Path(zero_metadata_path), 0, channel_bandwidth_hz=channel_bandwidth_hz, maximum_frames=maximum_frames)
    ninety, ninety_frequency = _measure(Path(ninety_metadata_path), 90, channel_bandwidth_hz=channel_bandwidth_hz, maximum_frames=maximum_frames)
    if zero_frequency != ninety_frequency:
        raise ValueError("iki gerçek kayıt aynı merkez frekansına sahip değil")
    return TwoPointDFResult(zero_frequency, channel_bandwidth_hz, zero, ninety)
