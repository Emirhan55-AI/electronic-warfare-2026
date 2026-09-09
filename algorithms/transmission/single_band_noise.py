"""Bounded, deterministic complex noise for one selected RF test band.

This module only creates CI8 baseband data. It does not open an SDR or start an
RF transmission. The absolute RF band is carried in the plan so the hardware
boundary can independently validate it against an approved lab profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np
import numpy.typing as npt


HACKRF_MIN_FREQUENCY_HZ = 1_000_000
HACKRF_MAX_FREQUENCY_HZ = 6_000_000_000
MAX_DURATION_SECONDS = 30.0
MAX_NOISE_BANDWIDTH_HZ = 4_000_000
DEFAULT_SAMPLE_RATE_HZ = 8_000_000
DEFAULT_TILE_SAMPLE_COUNT = 262_144


@dataclass(frozen=True)
class SingleBandNoisePlan:
    lower_frequency_hz: int
    upper_frequency_hz: int
    duration_seconds: float
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ
    seed: int = 2026
    output_peak: float = 0.65
    tile_sample_count: int = DEFAULT_TILE_SAMPLE_COUNT

    def __post_init__(self) -> None:
        values = (self.lower_frequency_hz, self.upper_frequency_hz, self.duration_seconds, self.output_peak)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Tekli görev değerleri sonlu olmalıdır.")
        if not HACKRF_MIN_FREQUENCY_HZ <= self.lower_frequency_hz < self.upper_frequency_hz <= HACKRF_MAX_FREQUENCY_HZ:
            raise ValueError("Tekli görev frekans aralığı HackRF destek sınırları dışındadır.")
        if not 0.1 <= self.duration_seconds <= MAX_DURATION_SECONDS:
            raise ValueError("Tekli görev süresi 0,1–30 saniye arasında olmalıdır.")
        if self.sample_rate_hz != DEFAULT_SAMPLE_RATE_HZ:
            raise ValueError("PHASE-10 profili yalnız 8 MS/s örneklemeye izin verir.")
        if not 0 < self.output_peak <= 0.7:
            raise ValueError("Sayısal tepe seviyesi (0, 0,7] aralığında olmalıdır.")
        if self.bandwidth_hz > MAX_NOISE_BANDWIDTH_HZ:
            raise ValueError("Tekli görev bant genişliği 4 MHz sınırını aşamaz.")
        if self.tile_sample_count < 16_384 or self.tile_sample_count > 1_048_576:
            raise ValueError("Gürültü döşemesi örnek sayısı güvenli sınırın dışındadır.")
        if self.tile_sample_count & (self.tile_sample_count - 1):
            raise ValueError("Gürültü döşemesi örnek sayısı ikinin kuvveti olmalıdır.")
        if self.sample_count < 1:
            raise ValueError("Tekli görev en az bir örnek üretmelidir.")

    @property
    def center_frequency_hz(self) -> int:
        return int(round((self.lower_frequency_hz + self.upper_frequency_hz) / 2.0))

    @property
    def bandwidth_hz(self) -> int:
        return self.upper_frequency_hz - self.lower_frequency_hz

    @property
    def sample_count(self) -> int:
        return int(round(self.sample_rate_hz * self.duration_seconds))


@dataclass(frozen=True)
class SingleBandNoiseSummary:
    center_frequency_hz: int
    requested_bandwidth_hz: int
    measured_obw99_hz: float
    sample_rate_hz: int
    tile_sample_count: int
    mission_sample_count: int
    peak_magnitude: float
    rms_magnitude: float
    deterministic_seed: int
    provenance: str = "PHASE-10 İLETİMSİZ TABAN BANT"


class SingleBandNoiseEngine:
    """Generate a periodic CI8 noise tile and an exact-duration mission file."""

    def generate_tile(self, plan: SingleBandNoisePlan) -> npt.NDArray[np.complex128]:
        frequencies = np.fft.fftfreq(plan.tile_sample_count, d=1.0 / plan.sample_rate_hz)
        mask = np.abs(frequencies) <= plan.bandwidth_hz / 2.0
        if int(np.count_nonzero(mask)) < 16:
            raise ValueError("Seçilen bant gürültü doğrulaması için çok dardır.")
        rng = np.random.default_rng(plan.seed)
        spectrum = np.zeros(plan.tile_sample_count, dtype=np.complex128)
        count = int(np.count_nonzero(mask))
        spectrum[mask] = rng.normal(size=count) + 1j * rng.normal(size=count)
        tile = np.fft.ifft(spectrum)
        peak = float(np.max(np.abs(tile)))
        if not math.isfinite(peak) or peak <= 0:
            raise ValueError("Gürültü döşemesi geçerli enerji üretmedi.")
        tile = np.asarray(tile * (plan.output_peak / peak), dtype=np.complex128)
        tile.setflags(write=False)
        return tile

    def summarize(self, plan: SingleBandNoisePlan, tile: npt.ArrayLike | None = None) -> SingleBandNoiseSummary:
        values = self.generate_tile(plan) if tile is None else np.asarray(tile, dtype=np.complex128)
        frequencies = np.fft.fftshift(np.fft.fftfreq(values.size, d=1.0 / plan.sample_rate_hz))
        power = np.abs(np.fft.fftshift(np.fft.fft(values))) ** 2
        total = float(np.sum(power))
        if not math.isfinite(total) or total <= 0:
            raise ValueError("Gürültü spektrumu geçerli enerji üretmedi.")
        tail = total * 0.005
        lower_index = min(int(np.searchsorted(np.cumsum(power), tail, side="right")), power.size - 1)
        upper_from_end = int(np.searchsorted(np.cumsum(power[::-1]), tail, side="right"))
        upper_index = max(0, power.size - 1 - upper_from_end)
        return SingleBandNoiseSummary(
            center_frequency_hz=plan.center_frequency_hz,
            requested_bandwidth_hz=plan.bandwidth_hz,
            measured_obw99_hz=max(0.0, float(frequencies[upper_index] - frequencies[lower_index])),
            sample_rate_hz=plan.sample_rate_hz,
            tile_sample_count=plan.tile_sample_count,
            mission_sample_count=plan.sample_count,
            peak_magnitude=float(np.max(np.abs(values))),
            rms_magnitude=float(np.sqrt(np.mean(np.abs(values) ** 2))),
            deterministic_seed=plan.seed,
        )

    @staticmethod
    def encode_ci8(tile: npt.ArrayLike) -> bytes:
        values = np.asarray(tile, dtype=np.complex128)
        if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
            raise ValueError("CI8 dönüşümü için sonlu, tek boyutlu I/Q gerekir.")
        interleaved = np.empty(values.size * 2, dtype=np.int8)
        interleaved[0::2] = np.rint(np.clip(values.real, -1.0, 1.0) * 127.0).astype(np.int8)
        interleaved[1::2] = np.rint(np.clip(values.imag, -1.0, 1.0) * 127.0).astype(np.int8)
        return interleaved.tobytes()

    def write_mission_ci8(self, path: Path, plan: SingleBandNoisePlan) -> SingleBandNoiseSummary:
        tile = self.generate_tile(plan)
        payload = self.encode_ci8(tile)
        full_tiles, remaining = divmod(plan.sample_count, plan.tile_sample_count)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            for _ in range(full_tiles):
                stream.write(payload)
            if remaining:
                stream.write(payload[: remaining * 2])
        expected_bytes = plan.sample_count * 2
        if path.stat().st_size != expected_bytes:
            raise OSError("Görev I/Q dosyası beklenen uzunlukta yazılamadı.")
        return self.summarize(plan, tile)
