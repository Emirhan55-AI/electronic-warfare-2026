#!/usr/bin/env python3
"""Fit the fixed PHASE-04-F1 domain prototypes from the public development set."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_domain import DEFAULT_MODEL_PATH, extract_domain_vector
from algorithms.parameters.f1_estimator import _fractional_edge
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f1" / "development-scenes.json"
FEATURE_NAMES = [
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
]


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _span(clean_samples: tuple[np.ndarray, ...], processor: SpectrumProcessor, margin: int) -> tuple[int, int]:
    spectra = tuple(
        processor.process(frame, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
        for frame in clean_samples
    )
    mean_psd = np.mean(np.stack([item.display.psd_fs2_per_hz for item in spectra]), axis=0)
    lower = _fractional_edge(mean_psd, 0, 0.005)
    upper = _fractional_edge(mean_psd, 0, 0.995)
    return max(56, int(math.floor(lower)) - margin), min(4039, int(math.ceil(upper)) + margin)


def _vectors() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    development = _load(DEVELOPMENT_PATH)
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    rows: list[dict[str, Any]] = []
    base_seed = int(development["common"]["base_seed"])
    margin = int(development["common"]["operator_span_truth_margin_bins_per_side"])
    for family_index, family in enumerate(development["families"]):
        frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
        for condition_index, snr_db in ((2, 6.0), (3, 12.0)):
            for trial in range(int(development["common"]["trials_per_family"])):
                frames = tuple(
                    generate_parameter_scene(
                        str(family["scene_id"]),
                        trial_index=trial,
                        condition_index=condition_index,
                        frame_index=frame_index,
                        clean_power_dbfs=-18.0,
                        snr_db=snr_db,
                        catalog=catalog,
                        scene_seed_override=base_seed + family_index * 10_000,
                    )
                    for frame_index in frame_indices
                )
                lower, upper = _span(tuple(frame.clean_samples for frame in frames), processor, margin)
                rows.append({
                    "family_id": str(family["id"]),
                    "domain": str(family["domain"]),
                    "snr_db": snr_db,
                    "trial": trial,
                    "vector": extract_domain_vector(tuple(frame.samples for frame in frames), lower, upper),
                })
    return development, rows


def build_model() -> dict[str, Any]:
    development, rows = _vectors()
    training = [row for row in rows if int(row["trial"]) < 48]
    validation = [row for row in rows if int(row["trial"]) >= 48]
    matrix = np.stack([row["vector"] for row in training])
    center = np.mean(matrix, axis=0)
    scale = np.maximum(np.std(matrix, axis=0), 1e-6)
    prototypes: list[dict[str, Any]] = []
    for family in development["families"]:
        family_rows = [row for row in training if row["family_id"] == family["id"]]
        normalized = np.stack([(row["vector"] - center) / scale for row in family_rows])
        covariance = np.cov(normalized, rowvar=False)
        regularized = 0.75 * covariance + 0.25 * np.eye(covariance.shape[0])
        sign, log_determinant = np.linalg.slogdet(regularized)
        if sign <= 0.0:
            raise ValueError("domain prototype covariance is not positive definite")
        prototypes.append({
            "family_id": str(family["id"]),
            "domain": str(family["domain"]),
            "centroid": np.mean(normalized, axis=0).tolist(),
            "precision": np.linalg.inv(regularized).tolist(),
            "log_determinant": float(log_determinant),
        })

    distances: list[float] = []
    margins: list[float] = []
    correct_margins: list[float] = []
    wrong_margins: list[float] = []
    wrong_predictions: list[dict[str, Any]] = []
    correct = 0
    wrong = 0
    ambiguous_rejected = 0
    for row in validation:
        normalized = (row["vector"] - center) / scale
        ranked = sorted(
            (
                float(
                    (normalized - np.asarray(item["centroid"]))
                    @ np.asarray(item["precision"])
                    @ (normalized - np.asarray(item["centroid"]))
                    / normalized.size
                    + float(item["log_determinant"]) / normalized.size
                ),
                item,
            )
            for item in prototypes
        )
        distance, nearest = ranked[0]
        margin = ranked[1][0] - distance
        distances.append(distance)
        margins.append(margin)
        if nearest["domain"] == row["domain"] and row["domain"] != "Belirsiz":
            correct += 1
            correct_margins.append(margin)
        elif nearest["domain"] != row["domain"] and nearest["domain"] != "Belirsiz":
            wrong += 1
            wrong_margins.append(margin)
            wrong_predictions.append({
                "family_id": row["family_id"],
                "snr_db": row["snr_db"],
                "trial": row["trial"],
                "predicted_family": nearest["family_id"],
                "distance": distance,
                "margin": margin,
            })
        elif row["domain"] == "Belirsiz" and nearest["domain"] == "Belirsiz":
            ambiguous_rejected += 1
    maximum_distance = float(np.quantile(distances, 0.99))
    minimum_margin = max(0.0, float(np.quantile(margins, 0.01)))
    binary_training = [row for row in training if row["domain"] != "Belirsiz"]
    binary_matrix = np.stack([(row["vector"] - center) / scale for row in binary_training])
    design = np.column_stack((binary_matrix, np.ones(binary_matrix.shape[0])))
    target = np.asarray([1.0 if row["domain"] == "Sayısal" else -1.0 for row in binary_training])
    ridge = np.eye(design.shape[1], dtype=np.float64)
    ridge[-1, -1] = 0.0
    coefficients = np.linalg.solve(design.T @ design + ridge, design.T @ target)
    linear_correct = 0
    linear_wrong = 0
    linear_scores: list[dict[str, Any]] = []
    linear_correct_absolute_scores: list[float] = []
    for row in validation:
        if row["domain"] == "Belirsiz":
            continue
        normalized = (row["vector"] - center) / scale
        score = float(normalized @ coefficients[:-1] + coefficients[-1])
        predicted = "Sayısal" if score >= 0.0 else "Analog"
        linear_correct += int(predicted == row["domain"])
        linear_wrong += int(predicted != row["domain"])
        if predicted == row["domain"]:
            linear_correct_absolute_scores.append(abs(score))
        if predicted != row["domain"]:
            linear_scores.append({"family_id": row["family_id"], "snr_db": row["snr_db"], "trial": row["trial"], "score": score})
    return {
        "schema_version": 1,
        "model_id": "phase04f1-fixed-domain-prototypes-v1",
        "status": "development-only",
        "feature_names": FEATURE_NAMES,
        "scaling": {"center": center.tolist(), "scale": scale.tolist()},
        "prototypes": prototypes,
        "domain_linear": {
            "weights": coefficients[:-1].tolist(),
            "bias": float(coefficients[-1]),
            "minimum_absolute_score": 0.14,
            "ridge": 1.0,
        },
        "thresholds": {
            "minimum_snr_db": 3.0,
            "maximum_distance": maximum_distance,
            "minimum_margin": minimum_margin,
        },
        "development_split": {"training_trials": [0, 47], "validation_trials": [48, 63], "snr_db": [6.0, 12.0]},
        "validation_diagnostics": {
            "sample_count": len(validation),
            "nearest_domain_correct_count": correct,
            "nearest_domain_wrong_count": wrong,
            "ambiguous_rejected_count": ambiguous_rejected,
            "correct_margin_quantiles": {
                "q05": float(np.quantile(correct_margins, 0.05)),
                "q10": float(np.quantile(correct_margins, 0.10)),
                "q25": float(np.quantile(correct_margins, 0.25)),
            },
            "wrong_margin_quantiles": {
                "q50": float(np.quantile(wrong_margins, 0.50)),
                "q75": float(np.quantile(wrong_margins, 0.75)),
                "maximum": max(wrong_margins),
            },
            "wrong_predictions": wrong_predictions,
            "linear_correct_count": linear_correct,
            "linear_wrong_count": linear_wrong,
            "linear_wrong_predictions": linear_scores,
            "linear_correct_absolute_score_q05": float(np.quantile(linear_correct_absolute_scores, 0.05)),
            "linear_correct_absolute_score_q10": float(np.quantile(linear_correct_absolute_scores, 0.10)),
        },
        "claim_boundary": "Sabit istatistiksel prototipler yalnız açık sentetik geliştirme kataloğundan türetilmiştir; genel modülasyon tanıma veya canlı RF doğrulaması değildir.",
    }


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = _canonical(build_model())
    if args.write:
        DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_MODEL_PATH.write_bytes(payload)
    elif not DEFAULT_MODEL_PATH.is_file() or DEFAULT_MODEL_PATH.read_bytes() != payload:
        print("PHASE-04-F1 domain model is missing or stale")
        return 1
    print("PHASE-04-F1 domain model: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
