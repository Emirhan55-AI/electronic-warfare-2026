"""Deterministic signal-domain features for the PHASE-04-F1 estimator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "datasets" / "fixtures" / "phase04f1" / "domain-model.json"


@dataclass(frozen=True)
class DomainDecision:
    value: str
    state: str
    reason: str | None
    nearest_family: str | None
    distance: float | None
    margin: float | None


def _band_limited(samples: np.ndarray, lower: int, upper: int) -> np.ndarray:
    frame = np.asarray(samples, dtype=np.complex128)
    shifted = np.fft.fftshift(np.fft.fft(frame))
    mask = np.zeros(frame.size, dtype=np.float64)
    mask[lower : upper + 1] = 1.0
    transition = min(4, max(1, (upper - lower + 1) // 4))
    taper = np.sin(np.linspace(0.0, np.pi / 2.0, transition + 1))[1:] ** 2
    mask[lower : lower + transition] *= taper
    mask[upper - transition + 1 : upper + 1] *= taper[::-1]
    filtered = np.fft.ifft(np.fft.ifftshift(shifted * mask))
    center = 0.5 * (lower + upper) - frame.size / 2.0
    index = np.arange(frame.size, dtype=np.float64)
    return np.asarray(filtered * np.exp(-1j * 2.0 * np.pi * center * index / frame.size))


def extract_domain_vector(samples: tuple[np.ndarray, ...], lower: int, upper: int) -> np.ndarray:
    """Return bounded, scale-independent statistics averaged over four frames."""
    rows: list[list[float]] = []
    for frame in samples:
        channel = _band_limited(frame, lower, upper)[64:-64]
        envelope = np.abs(channel)
        mean_envelope = max(float(np.mean(envelope)), np.finfo(float).tiny)
        normalized = envelope / mean_envelope
        envelope_cv = float(np.std(normalized))
        off_fraction = float(np.mean(normalized <= 0.25))
        envelope_kurtosis = float(np.mean(((normalized - 1.0) / max(envelope_cv, 1e-9)) ** 4))

        phase_step = np.angle(channel[1:] * np.conj(channel[:-1]))
        residual_frequency = float(np.median(phase_step))
        unit = channel / np.maximum(envelope, np.finfo(float).tiny)
        phase_moment_2 = float(abs(np.mean(unit**2)))
        phase_moment_4 = float(abs(np.mean(unit**4)))
        phase_power_2 = np.abs(np.fft.fft(unit**2)) ** 2
        phase_power_4 = np.abs(np.fft.fft(unit**4)) ** 2
        phase_concentration_2 = float(np.max(phase_power_2) / max(float(np.sum(phase_power_2)), np.finfo(float).tiny))
        phase_concentration_4 = float(np.max(phase_power_4) / max(float(np.sum(phase_power_4)), np.finfo(float).tiny))
        phase_step -= residual_frequency
        step_scale = max(float(np.std(phase_step)), 1e-9)
        step_kurtosis = float(np.mean((phase_step / step_scale) ** 4))
        large_step_fraction = float(np.mean(np.abs(phase_step) >= np.pi / 3.0))
        step_spectrum = np.abs(np.fft.fft(phase_step - np.mean(phase_step))) ** 2
        step_spectrum /= max(float(np.sum(step_spectrum)), np.finfo(float).tiny)
        step_spectral_entropy = float(
            -np.sum(step_spectrum * np.log(np.maximum(step_spectrum, 1e-15))) / math.log(step_spectrum.size)
        )

        envelope_spectrum = np.abs(np.fft.fft(normalized - np.mean(normalized))) ** 2
        envelope_spectrum /= max(float(np.sum(envelope_spectrum)), np.finfo(float).tiny)
        envelope_spectral_entropy = float(
            -np.sum(envelope_spectrum * np.log(np.maximum(envelope_spectrum, 1e-15)))
            / math.log(envelope_spectrum.size)
        )

        spectrum = np.abs(np.fft.fft(channel)) ** 2
        spectrum /= max(float(np.sum(spectrum)), np.finfo(float).tiny)
        spectral_entropy = float(-np.sum(spectrum * np.log(np.maximum(spectrum, 1e-15))) / math.log(spectrum.size))
        spectral_flatness = float(
            np.exp(np.mean(np.log(np.maximum(spectrum, 1e-15))))
            / max(float(np.mean(spectrum)), np.finfo(float).tiny)
        )
        rows.append([
            envelope_cv,
            off_fraction,
            min(envelope_kurtosis, 20.0),
            phase_moment_2,
            phase_moment_4,
            phase_concentration_2,
            phase_concentration_4,
            min(step_kurtosis, 20.0),
            large_step_fraction,
            step_spectral_entropy,
            envelope_spectral_entropy,
            spectral_entropy,
            spectral_flatness,
        ])
    return np.mean(np.asarray(rows, dtype=np.float64), axis=0)


def classify_domain(
    vector: np.ndarray,
    *,
    snr_db: float,
    model: dict[str, Any] | None = None,
) -> DomainDecision:
    """Classify with fixed development centroids and conservative rejection."""
    document = model or load_json(DEFAULT_MODEL_PATH)
    minimum_snr_db = float(document["thresholds"]["minimum_snr_db"])
    if not math.isfinite(snr_db) or snr_db < minimum_snr_db:
        return DomainDecision("Belirsiz", "uncertain", "quality_below_domain_threshold", None, None, None)
    center = np.asarray(document["scaling"]["center"], dtype=np.float64)
    scale = np.asarray(document["scaling"]["scale"], dtype=np.float64)
    normalized = (np.asarray(vector, dtype=np.float64) - center) / scale
    distances: list[tuple[float, dict[str, Any]]] = []
    for prototype in document["prototypes"]:
        target = np.asarray(prototype["centroid"], dtype=np.float64)
        delta = normalized - target
        if "precision" in prototype:
            precision = np.asarray(prototype["precision"], dtype=np.float64)
            score = float(delta @ precision @ delta / delta.size + float(prototype["log_determinant"]) / delta.size)
        else:
            score = float(np.sqrt(np.mean(delta**2)))
        distances.append((score, prototype))
    distances.sort(key=lambda item: item[0])
    nearest_distance, nearest = distances[0]
    next_distance = distances[1][0]
    margin = next_distance - nearest_distance
    thresholds = document["thresholds"]
    if nearest_distance > float(thresholds["maximum_distance"]) or margin < float(thresholds["minimum_margin"]):
        return DomainDecision("Belirsiz", "uncertain", "classification_ambiguous", str(nearest["family_id"]), nearest_distance, margin)
    if str(nearest["domain"]) == "Belirsiz":
        return DomainDecision("Belirsiz", "uncertain", "classification_ambiguous", str(nearest["family_id"]), nearest_distance, margin)
    linear = document.get("domain_linear")
    if linear is None:
        value = str(nearest["domain"])
    else:
        score = float(normalized @ np.asarray(linear["weights"], dtype=np.float64) + float(linear["bias"]))
        if abs(score) < float(linear["minimum_absolute_score"]):
            return DomainDecision("Belirsiz", "uncertain", "classification_ambiguous", str(nearest["family_id"]), nearest_distance, abs(score))
        value = "Sayısal" if score >= 0.0 else "Analog"
    return DomainDecision(value, "valid", None, str(nearest["family_id"]), nearest_distance, margin)
