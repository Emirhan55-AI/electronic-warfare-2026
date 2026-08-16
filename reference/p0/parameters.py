"""Mandatory P0 parameter extraction sharing the OS-CFAR noise definition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .bandwidth import BandwidthEstimator
from .models import CandidateRegion, P0ParameterResult, Provenance


@dataclass(frozen=True)
class ParameterProfile:
    minimum_snr_db: float = 3.0
    analog_if_discontinuity_maximum: float = 0.22
    digital_if_discontinuity_minimum: float = 0.35
    digital_time_frequency_variation_minimum: float = 0.28
    noise_like_flatness_minimum: float = 0.50
    minimum_region_bins: int = 1


class ParameterExtractor:
    def __init__(self, profile: ParameterProfile | None = None) -> None:
        self.profile = profile or ParameterProfile()
        self.bandwidth_estimator = BandwidthEstimator()

    def extract(
        self,
        *,
        frame_id: int,
        iq: npt.ArrayLike,
        shifted_power: npt.ArrayLike,
        sample_rate_hz: float,
        center_frequency_hz: float,
        candidate: CandidateRegion,
        confirmed: bool,
        provenance: Provenance,
        backend: str,
        neighboring_candidates: tuple[CandidateRegion, ...] = (),
    ) -> P0ParameterResult:
        samples = np.asarray(iq, dtype=np.complex128)
        power = np.asarray(shifted_power, dtype=np.float64)
        if samples.ndim != 1 or power.ndim != 1 or samples.size != power.size:
            raise ValueError("iq and shifted_power must be equal one-dimensional frames")
        if samples.size < 64 or not np.all(np.isfinite(samples)):
            raise ValueError("iq frame is invalid")
        if not np.all(np.isfinite(power)) or np.any(power < 0):
            raise ValueError("shifted_power is invalid")
        if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be finite and positive")
        if not 0 <= candidate.start_bin <= candidate.peak_bin <= candidate.end_bin < power.size:
            raise ValueError("candidate bounds are invalid")

        start, end = candidate.start_bin, candidate.end_bin
        region_power = power[start : end + 1]
        frequencies = center_frequency_hz + np.fft.fftshift(np.fft.fftfreq(samples.size, d=1.0 / sample_rate_hz))
        region_frequencies = frequencies[start : end + 1]
        weight_sum = float(np.sum(region_power))
        if weight_sum <= 0:
            raise ValueError("candidate has no positive power")
        carrier = float(np.sum(region_frequencies * region_power) / weight_sum)
        bandwidth = self.bandwidth_estimator.estimate(
            shifted_power=power,
            sample_rate_hz=sample_rate_hz,
            center_frequency_hz=center_frequency_hz,
            candidate=candidate,
            neighboring_candidates=neighboring_candidates,
        )

        noise_total = candidate.noise_power_per_bin * candidate.bin_count
        signal_power_raw = max(weight_sum - noise_total, np.finfo(np.float64).tiny)
        snr_linear = signal_power_raw / max(noise_total, np.finfo(np.float64).tiny)
        window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(samples.size, dtype=np.float64) / samples.size)
        relative_linear = signal_power_raw / (samples.size * float(np.sum(window * window)))
        relative_dbfs = 10.0 * np.log10(relative_linear)
        snr_db = 10.0 * np.log10(snr_linear)

        features = self._features(samples, power, candidate)
        domain, reasons = self._classify(features, snr_db, candidate.bin_count)
        return P0ParameterResult(
            frame_id=frame_id,
            candidate=candidate,
            confirmed=confirmed,
            carrier_frequency_hz=carrier,
            lower_frequency_hz=bandwidth.lower_frequency_hz,
            upper_frequency_hz=bandwidth.upper_frequency_hz,
            bandwidth_hz=bandwidth.bandwidth_hz,
            bandwidth_method=bandwidth.method,
            threshold_bandwidth_hz=bandwidth.threshold_bandwidth_hz,
            occupied_bandwidth_hz=bandwidth.occupied_bandwidth_hz,
            coarse_candidate_lower_frequency_hz=bandwidth.coarse_lower_frequency_hz,
            coarse_candidate_upper_frequency_hz=bandwidth.coarse_upper_frequency_hz,
            coarse_candidate_bandwidth_hz=bandwidth.coarse_bandwidth_hz,
            relative_power_linear=relative_linear,
            relative_power_dbfs=float(relative_dbfs),
            snr_db=float(snr_db),
            signal_domain=domain,
            classification_reasons=reasons,
            spectral_flatness=features[0],
            envelope_variation=features[1],
            instantaneous_frequency_discontinuity=features[2],
            time_frequency_variation=features[3],
            calibration_state="KALİBRASYON BEKLİYOR",
            provenance=provenance,
            backend=backend,
        )

    @staticmethod
    def _features(
        samples: npt.NDArray[np.complex128],
        power: npt.NDArray[np.float64],
        candidate: CandidateRegion,
    ) -> tuple[float, float, float, float]:
        region = power[candidate.start_bin : candidate.end_bin + 1]
        eps = np.finfo(np.float64).tiny
        flatness = float(np.exp(np.mean(np.log(region + eps))) / max(np.mean(region), eps))

        mask = np.zeros(samples.size, dtype=np.complex128)
        shifted_fft = np.fft.fftshift(np.fft.fft(samples))
        mask[candidate.start_bin : candidate.end_bin + 1] = shifted_fft[candidate.start_bin : candidate.end_bin + 1]
        channel = np.fft.ifft(np.fft.ifftshift(mask))
        envelope = np.abs(channel)
        envelope_variation = float(np.std(envelope) / max(np.mean(envelope), eps))

        phase_steps = np.angle(channel[1:] * np.conj(channel[:-1]))
        if phase_steps.size > 1:
            discontinuity = float(np.median(np.abs(np.diff(np.unwrap(phase_steps)))) / np.pi)
        else:
            discontinuity = 0.0

        chunks = np.array_split(channel, 4)
        centroids: list[float] = []
        for chunk in chunks:
            chunk_power = np.abs(np.fft.fft(chunk)) ** 2
            indices = np.arange(chunk_power.size, dtype=np.float64)
            centroids.append(float(np.sum(indices * chunk_power) / max(np.sum(chunk_power), eps)))
        tf_variation = float(np.std(centroids) / max(len(chunks[0]), 1))
        return flatness, envelope_variation, discontinuity, tf_variation

    def _classify(self, features: tuple[float, float, float, float], snr_db: float, region_bins: int) -> tuple[str, tuple[str, ...]]:
        flatness, envelope_variation, discontinuity, tf_variation = features
        profile = self.profile
        if snr_db < profile.minimum_snr_db:
            return "Belirsiz", ("SNR kesin ayrım için yetersiz",)
        if flatness >= profile.noise_like_flatness_minimum and region_bins >= 8:
            return "Belirsiz", ("Spektrum gürültü benzeri düz",)
        if flatness >= 0.50 and envelope_variation >= 0.50:
            return "Sayısal", ("Düz spektrum ve kesikli zarf davranışı",)
        digital_score = int(discontinuity >= profile.digital_if_discontinuity_minimum)
        digital_score += int(tf_variation >= profile.digital_time_frequency_variation_minimum)
        digital_score += int(envelope_variation >= 1.0)
        if digital_score >= 2:
            return "Sayısal", ("Anlık frekans/zaman davranışında kesikli yapı",)
        if discontinuity <= profile.analog_if_discontinuity_maximum and envelope_variation < 1.0:
            return "Analog", ("Sürekli anlık frekans veya zarf davranışı",)
        return "Belirsiz", ("Açıklanabilir özellikler tutarlı çoğunluk üretmedi",)
