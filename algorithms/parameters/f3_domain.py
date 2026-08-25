"""Seed-robust signal-domain features and classifier for PHASE-04-F3."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .f1_domain import _band_limited
from .f2_domain import (
    FEATURE_NAMES as F2_FEATURE_NAMES,
    DomainDecision,
    extract_domain_vector_v3,
    fit_domain_model,
    prototype_scores,
)
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "domain-model-v4.json"
FEATURE_NAMES = F2_FEATURE_NAMES + (
    "envelope_modulation_high_band_fraction",
    "envelope_modulation_centroid_bins",
)
FEATURE_SET_ID = "phase04f3-domain-features-v4.0"
ENVELOPE_HIGH_BAND_START_BIN = 8


def extract_domain_vector_v4(samples: tuple[np.ndarray, ...], lower: int, upper: int) -> np.ndarray:
    """Add bounded envelope-spectrum descriptors to the frozen v3 feature vector."""
    base = extract_domain_vector_v3(samples, lower, upper)
    rows: list[list[float]] = []
    for frame in samples:
        channel = _band_limited(frame, lower, upper)[64:-64]
        envelope = np.abs(channel)
        envelope /= max(float(np.mean(envelope)), np.finfo(float).tiny)
        centered = envelope - float(np.mean(envelope))
        power = np.abs(np.fft.rfft(centered)) ** 2
        power[0] = 0.0
        total = max(float(np.sum(power)), np.finfo(float).tiny)
        bins = np.arange(power.size, dtype=np.float64)
        high_band_fraction = float(np.sum(power[ENVELOPE_HIGH_BAND_START_BIN:]) / total)
        centroid_bins = float(np.sum(bins * power) / total)
        rows.append([
            float(np.clip(high_band_fraction, 0.0, 1.0)),
            float(np.clip(centroid_bins, 0.0, 64.0)),
        ])
    return np.concatenate((base, np.mean(np.asarray(rows, dtype=np.float64), axis=0)))


def fit_domain_model_v4(rows: Iterable[dict[str, Any]], *, covariance_mix: float = 0.35) -> dict[str, Any]:
    model = fit_domain_model(rows, covariance_mix=covariance_mix)
    model["feature_names"] = list(FEATURE_NAMES)
    return model


def classify_domain_v4(
    vector: np.ndarray,
    *,
    snr_db: float,
    model: dict[str, Any] | None = None,
) -> DomainDecision:
    document = model or load_json(DEFAULT_MODEL_PATH)
    if not math.isfinite(snr_db) or snr_db < float(document["thresholds"]["minimum_snr_db"]):
        return DomainDecision("Belirsiz", "uncertain", "quality_below_domain_threshold", None, None, None)
    distance, margin, nearest = prototype_scores(vector, document)
    thresholds = document["thresholds"]
    if (
        distance > float(thresholds["maximum_distance"])
        or margin < float(thresholds["minimum_cross_domain_margin"])
        or nearest["domain"] == "Belirsiz"
    ):
        return DomainDecision(
            "Belirsiz", "uncertain", "classification_ambiguous",
            str(nearest["family_id"]), distance, margin,
        )
    return DomainDecision(
        str(nearest["domain"]), "valid", None,
        str(nearest["family_id"]), distance, margin,
    )
