"""Bounded signal-domain features and classifier for PHASE-04-F2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .f1_domain import _band_limited, extract_domain_vector
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "domain-model-v3.json"
FEATURE_NAMES = (
    "envelope_cv",
    "off_fraction",
    "envelope_kurtosis",
    "phase_moment_2",
    "phase_moment_4",
    "phase_concentration_2",
    "phase_concentration_4",
    "phase_step_kurtosis",
    "large_phase_step_fraction",
    "phase_step_spectral_entropy",
    "envelope_spectral_entropy",
    "spectral_entropy",
    "spectral_flatness",
    "normalized_c20",
    "normalized_c40",
    "normalized_c42",
    "envelope_skewness",
    "phase_step_iqr",
)
FEATURE_SET_ID = "phase04f2-domain-features-v3.1"


@dataclass(frozen=True)
class DomainDecision:
    value: str
    state: str
    reason: str | None
    nearest_family: str | None
    distance: float | None
    margin: float | None


def extract_domain_vector_v3(samples: tuple[np.ndarray, ...], lower: int, upper: int) -> np.ndarray:
    """Extend the immutable F1 feature vector with normalized higher-order statistics."""
    base = extract_domain_vector(samples, lower, upper)
    rows: list[list[float]] = []
    for frame in samples:
        channel = _band_limited(frame, lower, upper)[64:-64]
        power = max(float(np.mean(np.abs(channel) ** 2)), np.finfo(float).tiny)
        moment20 = complex(np.mean(channel**2))
        moment40 = complex(np.mean(channel**4))
        moment42 = float(np.mean(np.abs(channel) ** 4))
        c20 = abs(moment20) / power
        c40 = abs(moment40 - 3.0 * moment20**2) / (power**2)
        c42 = abs(moment42 - abs(moment20) ** 2 - 2.0 * power**2) / (power**2)

        envelope = np.abs(channel)
        mean_envelope = float(np.mean(envelope))
        envelope_scale = max(float(np.std(envelope)), np.finfo(float).tiny)
        envelope_skewness = float(np.mean(((envelope - mean_envelope) / envelope_scale) ** 3))
        phase_step = np.angle(channel[1:] * np.conj(channel[:-1]))
        phase_step -= float(np.median(phase_step))
        phase_step_iqr = float(np.quantile(phase_step, 0.75) - np.quantile(phase_step, 0.25)) / math.pi
        rows.append([
            min(c20, 10.0),
            min(c40, 20.0),
            min(c42, 20.0),
            float(np.clip(envelope_skewness, -10.0, 10.0)),
            float(np.clip(phase_step_iqr, 0.0, 2.0)),
        ])
    return np.concatenate((base, np.mean(np.asarray(rows, dtype=np.float64), axis=0)))


def fit_domain_model(rows: Iterable[dict[str, Any]], *, covariance_mix: float = 0.35) -> dict[str, Any]:
    records = list(rows)
    matrix = np.stack([np.asarray(row["vector"], dtype=np.float64) for row in records])
    center = np.mean(matrix, axis=0)
    scale = np.maximum(np.std(matrix, axis=0), 1.0e-6)
    normalized = (matrix - center) / scale
    prototype_keys = sorted({(str(row["family_id"]), float(row["snr_db"])) for row in records})
    prototypes: list[dict[str, Any]] = []
    residuals: list[np.ndarray] = []
    clusters_per_condition = 6
    for family_id, snr_db in prototype_keys:
        mask = np.asarray([
            row["family_id"] == family_id
            and float(row["snr_db"]) == snr_db
            for row in records
        ])
        prototype_rows = normalized[mask]
        centroids = [np.mean(prototype_rows, axis=0)]
        while len(centroids) < clusters_per_condition:
            distance = np.min(np.stack([
                np.sum((prototype_rows - candidate) ** 2, axis=1)
                for candidate in centroids
            ]), axis=0)
            centroids.append(prototype_rows[int(np.argmax(distance))].copy())
        centroid_matrix = np.stack(centroids)
        for _ in range(50):
            distances = np.stack([
                np.sum((prototype_rows - candidate) ** 2, axis=1)
                for candidate in centroid_matrix
            ], axis=1)
            labels = np.argmin(distances, axis=1)
            updated = np.stack([
                np.mean(prototype_rows[labels == index], axis=0)
                if np.any(labels == index) else centroid_matrix[index]
                for index in range(clusters_per_condition)
            ])
            if np.allclose(updated, centroid_matrix, rtol=0.0, atol=1.0e-10):
                centroid_matrix = updated
                break
            centroid_matrix = updated
        domain = str(next(row["domain"] for row in records if row["family_id"] == family_id))
        for cluster_index, centroid in enumerate(centroid_matrix):
            prototypes.append({
                "family_id": family_id,
                "snr_db": snr_db,
                "cluster": cluster_index,
                "domain": domain,
                "centroid": centroid.tolist(),
            })
        residuals.extend(prototype_rows - centroid_matrix[labels])
    covariance = np.cov(np.stack(residuals), rowvar=False)
    regularized = covariance_mix * covariance + (1.0 - covariance_mix) * np.eye(covariance.shape[0])
    precision = np.linalg.inv(regularized)
    return {
        "feature_names": list(FEATURE_NAMES),
        "scaling": {"center": center.tolist(), "scale": scale.tolist()},
        "prototypes": prototypes,
        "neighbors_per_family": 1,
        "clusters_per_condition": clusters_per_condition,
        "shared_precision": precision.tolist(),
        "covariance_mix": covariance_mix,
    }


def rank_prototypes(vector: np.ndarray, model: dict[str, Any]) -> list[tuple[float, dict[str, Any]]]:
    center = np.asarray(model["scaling"]["center"], dtype=np.float64)
    scale = np.asarray(model["scaling"]["scale"], dtype=np.float64)
    normalized = (np.asarray(vector, dtype=np.float64) - center) / scale
    precision = np.asarray(model["shared_precision"], dtype=np.float64)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in model["prototypes"]:
        delta = normalized - np.asarray(item["centroid"], dtype=np.float64)
        distance = float(delta @ precision @ delta / delta.size)
        ranked.append((distance, item))
    return sorted(ranked, key=lambda value: value[0])


def prototype_scores(vector: np.ndarray, model: dict[str, Any]) -> tuple[float, float, dict[str, Any]]:
    ranked = rank_prototypes(vector, model)
    neighbors = int(model["neighbors_per_family"])
    families: list[tuple[float, dict[str, Any]]] = []
    for family_id in sorted({str(prototype["family_id"]) for _, prototype in ranked}):
        matches = [item for item in ranked if item[1]["family_id"] == family_id]
        count = min(neighbors, len(matches))
        score = float(np.mean([distance for distance, _ in matches[:count]]))
        families.append((score, matches[0][1]))
    families.sort(key=lambda item: item[0])
    nearest_distance, nearest = families[0]
    other_domain_distance = min(
        distance for distance, prototype in families
        if prototype["domain"] != nearest["domain"]
    )
    return nearest_distance, other_domain_distance - nearest_distance, nearest


def classify_domain_v3(
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
