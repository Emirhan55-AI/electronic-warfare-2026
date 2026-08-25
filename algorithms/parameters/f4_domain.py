"""Family-conditioned signal-domain rejection for PHASE-04-F4."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .f2_domain import DomainDecision, prototype_scores
from .f3_domain import extract_domain_vector_v4, fit_domain_model_v4
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "datasets" / "fixtures" / "phase04f4" / "domain-model-v5.json"
FEATURE_SET_ID = "phase04f4-domain-features-v5.0"


def extract_domain_vector_v5(samples: tuple[np.ndarray, ...], lower: int, upper: int) -> np.ndarray:
    """Keep the bounded v4 feature vector; v5 changes only rejection calibration."""
    return extract_domain_vector_v4(samples, lower, upper)


def fit_domain_model_v5(rows: Iterable[dict[str, Any]], *, covariance_mix: float = 0.35) -> dict[str, Any]:
    """Fit the frozen prototype structure on the independent F4 development split."""
    return fit_domain_model_v4(rows, covariance_mix=covariance_mix)


def minimum_margin_for_family(model: dict[str, Any], family_id: str) -> float:
    thresholds = model["thresholds"]
    overrides = thresholds.get("minimum_cross_domain_margin_by_nearest_family", {})
    return float(overrides.get(family_id, thresholds["minimum_cross_domain_margin"]))


def classify_domain_v5(
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
    minimum_margin = minimum_margin_for_family(document, str(nearest["family_id"]))
    if (
        distance > float(thresholds["maximum_distance"])
        or margin < minimum_margin
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
