"""Frame-local, explainable Analog/Sayısal ayrımı for PHASE-04-E1."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DomainFeatures:
    envelope_cv: float
    off_fraction: float
    two_level_score: float
    constant_modulus_cv: float
    phase_jump_rate: float
    mode_separation: float
    valley_ratio: float


def _frame_local_channel(samples: np.ndarray, lower: int, upper: int) -> np.ndarray:
    """Band-limit one frame without claiming continuity across frame boundaries."""
    n = samples.size
    shifted = np.fft.fftshift(np.fft.fft(np.asarray(samples, dtype=np.complex128)))
    mask = np.zeros(n, dtype=np.float64)
    mask[lower : upper + 1] = 1.0
    width = upper - lower + 1
    transition = min(4, max(1, width // 4))
    taper = np.sin(np.linspace(0.0, np.pi / 2.0, transition + 1, dtype=np.float64))[1:] ** 2
    mask[lower : lower + transition] *= taper
    mask[upper - transition + 1 : upper + 1] *= taper[::-1]
    filtered = np.fft.ifft(np.fft.ifftshift(shifted * mask))
    center = 0.5 * (lower + upper) - n / 2.0
    index = np.arange(n, dtype=np.float64)
    return np.asarray(filtered * np.exp(-1j * 2.0 * np.pi * center * index / n), dtype=np.complex128)


def extract_domain_features(samples: np.ndarray, lower: int, upper: int) -> DomainFeatures:
    channel = _frame_local_channel(samples, lower, upper)
    valid = channel[64:-64]
    envelope = np.abs(valid)
    mean_envelope = max(float(np.mean(envelope)), np.finfo(np.float64).tiny)
    normalized = envelope / mean_envelope
    envelope_cv = float(np.std(envelope) / mean_envelope)
    off_fraction = float(np.mean(normalized <= 0.25))
    histogram, edges = np.histogram(normalized, bins=24, range=(0.0, 2.5))
    peaks = np.argsort(histogram)[-2:]
    peaks.sort()
    if peaks[1] - peaks[0] >= 3:
        valley = int(np.min(histogram[peaks[0] + 1 : peaks[1]]))
        two_level = 1.0 - valley / max(int(min(histogram[peaks[0]], histogram[peaks[1]])), 1)
    else:
        two_level = 0.0
    constant_modulus = envelope_cv
    phase_step = np.angle(valid[1:] * np.conj(valid[:-1]))
    centered_step = phase_step - float(np.median(phase_step))
    phase_jump_rate = float(np.mean(np.abs(centered_step) >= np.pi / 3.0))
    instantaneous = centered_step / (2.0 * np.pi)
    hist, _ = np.histogram(instantaneous, bins=31)
    strongest = np.argsort(hist)[-2:]
    strongest.sort()
    if strongest[1] - strongest[0] >= 3:
        separation = float(strongest[1] - strongest[0])
        valley_ratio = float(np.min(hist[strongest[0] + 1 : strongest[1]]) / max(min(hist[strongest]), 1))
    else:
        separation = 0.0
        valley_ratio = 1.0
    return DomainFeatures(
        envelope_cv=envelope_cv,
        off_fraction=off_fraction,
        two_level_score=float(two_level),
        constant_modulus_cv=constant_modulus,
        phase_jump_rate=phase_jump_rate,
        mode_separation=separation,
        valley_ratio=valley_ratio,
    )


def classify_domain(features: tuple[DomainFeatures, ...], *, snr_db: float) -> tuple[str, float, tuple[str, ...]]:
    if len(features) < 4 or not math.isfinite(snr_db) or snr_db < 6.0:
        return "Belirsiz", 0.0, ("quality_below_domain_threshold",)
    mean = lambda name: float(np.mean([getattr(item, name) for item in features]))
    off = mean("off_fraction")
    two = mean("two_level_score")
    modulus = mean("constant_modulus_cv")
    jump = mean("phase_jump_rate")
    separation = mean("mode_separation")
    valley = mean("valley_ratio")
    envelope = mean("envelope_cv")
    digital = 0
    analog = 0
    reasons: list[str] = []
    if off >= 0.20 or two >= 0.75:
        digital += 2
        reasons.append("ook_evidence")
    if separation >= 4.0 and valley <= 0.50:
        digital += 2
        reasons.append("fsk_evidence")
    if modulus <= 0.20 and 0.005 <= jump <= 0.25:
        digital += 2
        reasons.append("psk_evidence")
    if jump < 0.005 and (0.05 <= envelope <= 0.55 or modulus <= 0.20):
        analog += 2
        reasons.append("analog_evidence")
    margin = abs(digital - analog)
    confidence = margin / max(digital + analog, 1)
    if margin < 2 or confidence < 0.33 or (digital and analog):
        return "Belirsiz", confidence, tuple(reasons or ["conflicting_or_weak_evidence"])
    return ("Sayısal" if digital > analog else "Analog"), confidence, tuple(reasons)
