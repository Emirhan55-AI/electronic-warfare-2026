#!/usr/bin/env python3
"""Fit the F3 v4 domain model with seed-wise leave-one-seed-out gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f3_domain import (
    DEFAULT_MODEL_PATH,
    FEATURE_NAMES,
    FEATURE_SET_ID,
    extract_domain_vector_v4,
    fit_domain_model_v4,
)
from algorithms.parameters.f2_domain import prototype_scores
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor
from scripts.develop_phase04f2_domain import _span


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "development-catalog.json"
CACHE_PATH = ROOT / "build" / "phase04f3" / "domain-rows-v4.npz"
DEVELOPMENT_LIMITS = {
    "family_min_correct_rate": 0.75,
    "family_max_wrong_rate": 0.04,
    "global_min_correct_rate": 0.85,
    "global_max_wrong_rate": 0.015,
    "ambiguous_min_rejection_rate": 0.95,
    "ook_seed_min_correct_count_6_db": 40,
    "ook_seed_max_wrong_count_6_db": 1,
    "ook_aggregate_max_wrong_count_6_db": 2,
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def build_rows() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    development = _load(DEVELOPMENT_PATH)
    cache_key = hashlib.sha256(
        FEATURE_SET_ID.encode("utf-8")
        + DEVELOPMENT_PATH.read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f1_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f2_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f3_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "scenes.py").read_bytes()
    ).hexdigest()
    if CACHE_PATH.is_file():
        cached = np.load(CACHE_PATH, allow_pickle=False)
        if str(cached["cache_key"].item()) == cache_key:
            metadata = json.loads(str(cached["metadata"].item()))
            vectors = np.asarray(cached["vectors"], dtype=np.float64)
            return development, [
                {**item, "vector": vector}
                for item, vector in zip(metadata, vectors, strict=True)
            ]
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    common = development["common"]
    rows: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(common["development_seeds"]):
        for family_index, family in enumerate(development["families"]):
            frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
            scene_seed = int(seed) + family_index * 10_000
            for condition_index, snr_db in ((2, 6.0), (3, 12.0)):
                for trial in range(int(common["trials_per_seed_per_family"])):
                    frames = tuple(
                        generate_parameter_scene(
                            str(family["scene_id"]),
                            trial_index=trial,
                            condition_index=condition_index,
                            frame_index=frame_index,
                            clean_power_dbfs=-18.0,
                            snr_db=snr_db,
                            catalog=catalog,
                            scene_seed_override=scene_seed,
                        )
                        for frame_index in frame_indices
                    )
                    lower, upper = _span(
                        tuple(frame.clean_samples for frame in frames),
                        processor,
                        int(common["operator_span_truth_margin_bins_per_side"]),
                    )
                    rows.append({
                        "seed_index": seed_index,
                        "family_id": str(family["id"]),
                        "domain": str(family["domain"]),
                        "snr_db": snr_db,
                        "trial": trial,
                        "vector": extract_domain_vector_v4(
                            tuple(frame.samples for frame in frames), lower, upper,
                        ),
                    })
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata = [{key: value for key, value in row.items() if key != "vector"} for row in rows]
    np.savez_compressed(
        CACHE_PATH,
        cache_key=np.asarray(cache_key),
        metadata=np.asarray(json.dumps(metadata, ensure_ascii=False)),
        vectors=np.stack([row["vector"] for row in rows]),
    )
    return development, rows


def _predictions(rows: list[dict[str, Any]], seed_count: int) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    for seed_index in range(seed_count):
        training = [row for row in rows if row["seed_index"] != seed_index]
        validation = [row for row in rows if row["seed_index"] == seed_index]
        fold_model = fit_domain_model_v4(training)
        for row in validation:
            distance, margin, nearest = prototype_scores(row["vector"], fold_model)
            predictions.append({
                "seed_index": seed_index,
                "family_id": row["family_id"],
                "truth": row["domain"],
                "snr_db": row["snr_db"],
                "nearest_domain": str(nearest["domain"]),
                "nearest_family": str(nearest["family_id"]),
                "distance": distance,
                "margin": margin,
            })
    return predictions


def _rates(
    predictions: list[dict[str, Any]],
    maximum_distance: float,
    minimum_cross_domain_margin: float,
) -> dict[str, Any]:
    evaluated: list[dict[str, Any]] = []
    for item in predictions:
        definite = (
            item["distance"] <= maximum_distance
            and item["margin"] >= minimum_cross_domain_margin
            and item["nearest_domain"] != "Belirsiz"
        )
        predicted = item["nearest_domain"] if definite else "Belirsiz"
        evaluated.append({**item, "predicted": predicted})
    nonambiguous = [item for item in evaluated if item["truth"] != "Belirsiz"]
    family_condition: dict[str, dict[str, float]] = {}
    for family in sorted({item["family_id"] for item in nonambiguous}):
        for snr_db in (6.0, 12.0):
            group = [item for item in nonambiguous if item["family_id"] == family and item["snr_db"] == snr_db]
            family_condition[f"{family}:{snr_db}"] = {
                "correct_rate": sum(item["predicted"] == item["truth"] for item in group) / len(group),
                "wrong_rate": sum(item["predicted"] not in {item["truth"], "Belirsiz"} for item in group) / len(group),
            }
    global_rates = {}
    for snr_db in (6.0, 12.0):
        group = [item for item in nonambiguous if item["snr_db"] == snr_db]
        global_rates[str(snr_db)] = {
            "correct_rate": sum(item["predicted"] == item["truth"] for item in group) / len(group),
            "wrong_rate": sum(item["predicted"] not in {item["truth"], "Belirsiz"} for item in group) / len(group),
        }
    ambiguous = [item for item in evaluated if item["truth"] == "Belirsiz" and item["snr_db"] == 12.0]
    ook_seed_counts = []
    for seed_index in sorted({int(item["seed_index"]) for item in evaluated}):
        group = [
            item for item in evaluated
            if item["family_id"] == "ook" and item["snr_db"] == 6.0 and item["seed_index"] == seed_index
        ]
        ook_seed_counts.append({
            "seed_index": seed_index,
            "correct": sum(item["predicted"] == "Sayısal" for item in group),
            "wrong": sum(item["predicted"] == "Analog" for item in group),
            "abstained": sum(item["predicted"] == "Belirsiz" for item in group),
        })
    return {
        "family_condition": family_condition,
        "global": global_rates,
        "family_min_correct_rate": min(item["correct_rate"] for item in family_condition.values()),
        "family_max_wrong_rate": max(item["wrong_rate"] for item in family_condition.values()),
        "ambiguous_rejection_rate": sum(item["predicted"] == "Belirsiz" for item in ambiguous) / len(ambiguous),
        "ook_6_db_seed_counts": ook_seed_counts,
        "ook_6_db_seed_min_correct_count": min(item["correct"] for item in ook_seed_counts),
        "ook_6_db_seed_max_wrong_count": max(item["wrong"] for item in ook_seed_counts),
        "ook_6_db_aggregate_wrong_count": sum(item["wrong"] for item in ook_seed_counts),
    }


def _passes(rates: dict[str, Any]) -> bool:
    return (
        rates["family_min_correct_rate"] >= DEVELOPMENT_LIMITS["family_min_correct_rate"]
        and rates["family_max_wrong_rate"] <= DEVELOPMENT_LIMITS["family_max_wrong_rate"]
        and all(
            item["correct_rate"] >= DEVELOPMENT_LIMITS["global_min_correct_rate"]
            and item["wrong_rate"] <= DEVELOPMENT_LIMITS["global_max_wrong_rate"]
            for item in rates["global"].values()
        )
        and rates["ambiguous_rejection_rate"] >= DEVELOPMENT_LIMITS["ambiguous_min_rejection_rate"]
        and rates["ook_6_db_seed_min_correct_count"] >= DEVELOPMENT_LIMITS["ook_seed_min_correct_count_6_db"]
        and rates["ook_6_db_seed_max_wrong_count"] <= DEVELOPMENT_LIMITS["ook_seed_max_wrong_count_6_db"]
        and rates["ook_6_db_aggregate_wrong_count"] <= DEVELOPMENT_LIMITS["ook_aggregate_max_wrong_count_6_db"]
    )


def _choose_thresholds(predictions: list[dict[str, Any]]) -> tuple[float, float, dict[str, Any]]:
    distances = np.asarray([item["distance"] for item in predictions], dtype=np.float64)
    margins = np.asarray([item["margin"] for item in predictions], dtype=np.float64)
    distance_candidates = sorted({float("inf"), *[float(np.quantile(distances, q)) for q in np.linspace(0.55, 1.0, 46)]})
    margin_candidates = sorted({float("-inf"), *[float(np.quantile(margins, q)) for q in np.linspace(0.0, 0.45, 46)]})
    accepted: list[tuple[int, int, float, float, dict[str, Any]]] = []
    best_near_miss: tuple[float, float, float, dict[str, Any]] | None = None
    for maximum_distance in distance_candidates:
        for minimum_cross_domain_margin in margin_candidates:
            rates = _rates(predictions, maximum_distance, minimum_cross_domain_margin)
            if _passes(rates):
                correct_score = round(sum(item["correct_rate"] * 10_000 for item in rates["family_condition"].values()))
                wrong_score = round(sum(item["wrong_rate"] * 10_000 for item in rates["family_condition"].values()))
                accepted.append((correct_score, wrong_score, maximum_distance, minimum_cross_domain_margin, rates))
            violation = (
                max(0.0, DEVELOPMENT_LIMITS["family_min_correct_rate"] - rates["family_min_correct_rate"])
                + max(0.0, rates["family_max_wrong_rate"] - DEVELOPMENT_LIMITS["family_max_wrong_rate"])
                + max(0.0, DEVELOPMENT_LIMITS["ook_seed_min_correct_count_6_db"] - rates["ook_6_db_seed_min_correct_count"]) / 48.0
                + max(0.0, rates["ook_6_db_seed_max_wrong_count"] - DEVELOPMENT_LIMITS["ook_seed_max_wrong_count_6_db"]) / 48.0
                + max(0.0, rates["ook_6_db_aggregate_wrong_count"] - DEVELOPMENT_LIMITS["ook_aggregate_max_wrong_count_6_db"]) / 384.0
            )
            candidate = (violation, maximum_distance, minimum_cross_domain_margin, rates)
            if best_near_miss is None or candidate[0] < best_near_miss[0]:
                best_near_miss = candidate
    if not accepted:
        assert best_near_miss is not None
        raise RuntimeError(
            "no leave-one-seed-out threshold pair satisfies the F3 development constraints; "
            + json.dumps({
                "violation": best_near_miss[0],
                "maximum_distance": best_near_miss[1],
                "minimum_cross_domain_margin": best_near_miss[2],
                "rates": best_near_miss[3],
            }, ensure_ascii=False)
        )
    _, _, maximum_distance, minimum_cross_domain_margin, rates = max(
        accepted,
        key=lambda item: (-item[1], item[0], -item[2], item[3]),
    )
    return maximum_distance, minimum_cross_domain_margin, rates


def build_model() -> dict[str, Any]:
    development, rows = build_rows()
    seed_count = len(development["common"]["development_seeds"])
    predictions = _predictions(rows, seed_count)
    maximum_distance, minimum_cross_domain_margin, diagnostics = _choose_thresholds(predictions)
    fitted = fit_domain_model_v4(rows)
    return {
        "schema_version": 1,
        "model_id": "phase04f3-domain-envelope-spectrum-v4",
        "status": "development-only",
        **fitted,
        "thresholds": {
            "minimum_snr_db": 3.0,
            "maximum_distance": maximum_distance,
            "minimum_cross_domain_margin": minimum_cross_domain_margin,
        },
        "development_split": {
            "method": "leave-one-seed-out",
            "seed_count": seed_count,
            "trials_per_seed_per_family": development["common"]["trials_per_seed_per_family"],
            "snr_db": [6.0, 12.0],
        },
        "cross_seed_diagnostics": diagnostics,
        "development_limits": DEVELOPMENT_LIMITS,
        "persistent_numeric_bytes": (
            len(fitted["scaling"]["center"])
            + len(fitted["scaling"]["scale"])
            + sum(len(item["centroid"]) for item in fitted["prototypes"])
            + sum(len(row) for row in fitted["shared_precision"])
        ) * 8,
        "literature_basis": {
            "feature_family": "complex-envelope statistics, higher-order cumulants and transformed-envelope spectrum",
            "selection_boundary": "project-specific leave-one-seed-out thresholds; not a universal modulation classifier",
        },
        "claim_boundary": "Yalnız sekiz açık F3 geliştirme seed'inden türetilmiştir; F1/F2 popülasyonları, F3 binding/OOS veya genel modülasyon tanıma değildir.",
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
        DEFAULT_MODEL_PATH.write_bytes(payload)
    elif not DEFAULT_MODEL_PATH.is_file() or DEFAULT_MODEL_PATH.read_bytes() != payload:
        print("PHASE-04-F3 domain model is missing or stale")
        return 1
    print("PHASE-04-F3 domain model: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
