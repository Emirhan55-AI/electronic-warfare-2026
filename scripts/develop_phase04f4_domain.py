#!/usr/bin/env python3
"""Fit and diagnose the F4 v5 domain model on the open development split."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f2_domain import prototype_scores
from algorithms.parameters.f4_domain import (
    DEFAULT_MODEL_PATH,
    FEATURE_SET_ID,
    extract_domain_vector_v5,
    fit_domain_model_v5,
)
from algorithms.parameters.operator_reference import load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor
from scripts.develop_phase04f2_domain import _span


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f4" / "development-catalog.json"
V4_MODEL_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "domain-model-v4.json"
CACHE_PATH = ROOT / "build" / "phase04f4" / "domain-rows-v5.npz"
DEVELOPMENT_LIMITS = {
    "family_min_correct_rate": 0.75,
    "family_max_wrong_rate": 0.04,
    "global_min_correct_rate": 0.85,
    "global_max_wrong_rate": 0.015,
    "ambiguous_min_rejection_rate": 0.95,
    "ook_seed_min_correct_count_6_db": 40,
    "ook_seed_max_wrong_count_6_db": 1,
    "ook_aggregate_max_wrong_count_6_db": 2,
    "nfm_seed_min_correct_count_6_db": 40,
    "nfm_seed_max_wrong_count_6_db": 1,
    "nfm_seed_max_abstained_count_6_db": 8,
    "nfm_aggregate_max_wrong_count_6_db": 2,
}


def build_rows() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    development = load_json(DEVELOPMENT_PATH)
    cache_key = hashlib.sha256(
        FEATURE_SET_ID.encode("utf-8")
        + DEVELOPMENT_PATH.read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f1_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f2_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f3_domain.py").read_bytes()
        + (ROOT / "algorithms" / "parameters" / "f4_domain.py").read_bytes()
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
                            str(family["scene_id"]), trial_index=trial, condition_index=condition_index,
                            frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=snr_db,
                            catalog=catalog, scene_seed_override=scene_seed,
                        )
                        for frame_index in frame_indices
                    )
                    lower, upper = _span(
                        tuple(frame.clean_samples for frame in frames), processor,
                        int(common["operator_span_truth_margin_bins_per_side"]),
                    )
                    rows.append({
                        "seed_index": seed_index,
                        "family_id": str(family["id"]),
                        "domain": str(family["domain"]),
                        "snr_db": snr_db,
                        "trial": trial,
                        "vector": extract_domain_vector_v5(
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
        model = fit_domain_model_v5(row for row in rows if row["seed_index"] != seed_index)
        for row in (item for item in rows if item["seed_index"] == seed_index):
            distance, margin, nearest = prototype_scores(row["vector"], model)
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


def _prediction(
    item: dict[str, Any], maximum_distance: float,
    minimum_margin: float, nfm_minimum_margin: float,
) -> str:
    required_margin = nfm_minimum_margin if item["nearest_family"] == "nfm" else minimum_margin
    definite = (
        item["distance"] <= maximum_distance
        and item["margin"] >= required_margin
        and item["nearest_domain"] != "Belirsiz"
    )
    return str(item["nearest_domain"]) if definite else "Belirsiz"


def _quantiles(values: list[float]) -> dict[str, float]:
    labels = ("q0", "q10", "q25", "q50", "q75", "q90", "q100")
    result = np.quantile(np.asarray(values, dtype=np.float64), (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0))
    return {label: float(value) for label, value in zip(labels, result, strict=True)}


def _rates(
    predictions: list[dict[str, Any]], maximum_distance: float,
    minimum_margin: float, nfm_minimum_margin: float,
) -> dict[str, Any]:
    evaluated = [
        {**item, "predicted": _prediction(item, maximum_distance, minimum_margin, nfm_minimum_margin)}
        for item in predictions
    ]
    nonambiguous = [item for item in evaluated if item["truth"] != "Belirsiz"]
    family_condition: dict[str, dict[str, float]] = {}
    for family in sorted({str(item["family_id"]) for item in nonambiguous}):
        for snr_db in (6.0, 12.0):
            group = [item for item in nonambiguous if item["family_id"] == family and item["snr_db"] == snr_db]
            family_condition[f"{family}:{snr_db}"] = {
                "correct_rate": sum(item["predicted"] == item["truth"] for item in group) / len(group),
                "wrong_rate": sum(item["predicted"] not in {item["truth"], "Belirsiz"} for item in group) / len(group),
            }
    global_rates: dict[str, dict[str, float]] = {}
    for snr_db in (6.0, 12.0):
        group = [item for item in nonambiguous if item["snr_db"] == snr_db]
        global_rates[str(snr_db)] = {
            "correct_rate": sum(item["predicted"] == item["truth"] for item in group) / len(group),
            "wrong_rate": sum(item["predicted"] not in {item["truth"], "Belirsiz"} for item in group) / len(group),
        }

    def seed_counts(family_id: str, expected: str) -> list[dict[str, int]]:
        counts: list[dict[str, int]] = []
        for seed_index in sorted({int(item["seed_index"]) for item in evaluated}):
            group = [
                item for item in evaluated
                if item["family_id"] == family_id and item["snr_db"] == 6.0
                and item["seed_index"] == seed_index
            ]
            counts.append({
                "seed_index": seed_index,
                "correct": sum(item["predicted"] == expected for item in group),
                "wrong": sum(item["predicted"] not in {expected, "Belirsiz"} for item in group),
                "abstained": sum(item["predicted"] == "Belirsiz" for item in group),
            })
        return counts

    nfm = [item for item in evaluated if item["family_id"] == "nfm" and item["snr_db"] == 6.0]
    rejection_reasons = {"distance_only": 0, "margin_only": 0, "both": 0, "nearest_uncertain": 0}
    for item in nfm:
        if item["predicted"] != "Belirsiz":
            continue
        distance_failed = item["distance"] > maximum_distance
        margin_threshold = nfm_minimum_margin if item["nearest_family"] == "nfm" else minimum_margin
        margin_failed = item["margin"] < margin_threshold
        if item["nearest_domain"] == "Belirsiz":
            rejection_reasons["nearest_uncertain"] += 1
        elif distance_failed and margin_failed:
            rejection_reasons["both"] += 1
        elif distance_failed:
            rejection_reasons["distance_only"] += 1
        else:
            rejection_reasons["margin_only"] += 1

    nfm_seed = seed_counts("nfm", "Analog")
    ook_seed = seed_counts("ook", "Sayısal")
    ambiguous = [item for item in evaluated if item["truth"] == "Belirsiz" and item["snr_db"] == 12.0]
    total_wrong = sum(item["predicted"] not in {item["truth"], "Belirsiz"} for item in nonambiguous)
    return {
        "family_condition": family_condition,
        "global": global_rates,
        "family_min_correct_rate": min(item["correct_rate"] for item in family_condition.values()),
        "family_max_wrong_rate": max(item["wrong_rate"] for item in family_condition.values()),
        "ambiguous_rejection_rate": sum(item["predicted"] == "Belirsiz" for item in ambiguous) / len(ambiguous),
        "total_wrong_count": total_wrong,
        "ook_6_db_seed_counts": ook_seed,
        "ook_6_db_seed_min_correct_count": min(item["correct"] for item in ook_seed),
        "ook_6_db_seed_max_wrong_count": max(item["wrong"] for item in ook_seed),
        "ook_6_db_aggregate_wrong_count": sum(item["wrong"] for item in ook_seed),
        "nfm_6_db_seed_counts": nfm_seed,
        "nfm_6_db_seed_min_correct_count": min(item["correct"] for item in nfm_seed),
        "nfm_6_db_seed_max_wrong_count": max(item["wrong"] for item in nfm_seed),
        "nfm_6_db_seed_max_abstained_count": max(item["abstained"] for item in nfm_seed),
        "nfm_6_db_aggregate_correct_count": sum(item["correct"] for item in nfm_seed),
        "nfm_6_db_aggregate_wrong_count": sum(item["wrong"] for item in nfm_seed),
        "nfm_6_db_rejection_reason_counts": rejection_reasons,
        "nfm_6_db_distance_quantiles": _quantiles([float(item["distance"]) for item in nfm]),
        "nfm_6_db_margin_quantiles": _quantiles([float(item["margin"]) for item in nfm]),
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
        and rates["nfm_6_db_seed_min_correct_count"] >= DEVELOPMENT_LIMITS["nfm_seed_min_correct_count_6_db"]
        and rates["nfm_6_db_seed_max_wrong_count"] <= DEVELOPMENT_LIMITS["nfm_seed_max_wrong_count_6_db"]
        and rates["nfm_6_db_seed_max_abstained_count"] <= DEVELOPMENT_LIMITS["nfm_seed_max_abstained_count_6_db"]
        and rates["nfm_6_db_aggregate_wrong_count"] <= DEVELOPMENT_LIMITS["nfm_aggregate_max_wrong_count_6_db"]
    )


def _choose_nfm_margin(predictions: list[dict[str, Any]]) -> tuple[float, float, float, dict[str, Any]]:
    inherited = load_json(V4_MODEL_PATH)["thresholds"]
    maximum_distance = float(inherited["maximum_distance"])
    minimum_margin = float(inherited["minimum_cross_domain_margin"])
    accepted: list[tuple[tuple[float, ...], float, dict[str, Any]]] = []
    for index in range(101):
        nfm_margin = minimum_margin * index / 100.0
        rates = _rates(predictions, maximum_distance, minimum_margin, nfm_margin)
        if _passes(rates):
            objective = (
                float(rates["total_wrong_count"]),
                -float(rates["nfm_6_db_seed_min_correct_count"]),
                -float(rates["nfm_6_db_aggregate_correct_count"]),
                -nfm_margin,
            )
            accepted.append((objective, nfm_margin, rates))
    if not accepted:
        raise RuntimeError("no family-conditioned margin satisfies the locked F4 development gates")
    _, nfm_margin, rates = min(accepted, key=lambda item: item[0])
    return maximum_distance, minimum_margin, nfm_margin, rates


def _v4_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    model = load_json(V4_MODEL_PATH)
    predictions: list[dict[str, Any]] = []
    for row in rows:
        distance, margin, nearest = prototype_scores(row["vector"], model)
        predictions.append({
            "seed_index": row["seed_index"], "family_id": row["family_id"],
            "truth": row["domain"], "snr_db": row["snr_db"],
            "nearest_domain": str(nearest["domain"]), "nearest_family": str(nearest["family_id"]),
            "distance": distance, "margin": margin,
        })
    thresholds = model["thresholds"]
    return _rates(
        predictions, float(thresholds["maximum_distance"]),
        float(thresholds["minimum_cross_domain_margin"]),
        float(thresholds["minimum_cross_domain_margin"]),
    )


def build_model() -> dict[str, Any]:
    development, rows = build_rows()
    predictions = _predictions(rows, len(development["common"]["development_seeds"]))
    maximum_distance, minimum_margin, nfm_margin, diagnostics = _choose_nfm_margin(predictions)
    fitted = fit_domain_model_v5(rows)
    baseline = _v4_baseline(rows)
    return {
        "schema_version": 1,
        "model_id": "phase04f4-domain-family-conditioned-rejection-v5",
        "status": "development-only",
        **fitted,
        "thresholds": {
            "minimum_snr_db": 3.0,
            "maximum_distance": maximum_distance,
            "minimum_cross_domain_margin": minimum_margin,
            "minimum_cross_domain_margin_by_nearest_family": {"nfm": nfm_margin},
        },
        "development_split": {
            "method": "leave-one-seed-out",
            "seed_count": len(development["common"]["development_seeds"]),
            "trials_per_seed_per_family": development["common"]["trials_per_seed_per_family"],
            "snr_db": [6.0, 12.0],
            "margin_candidate_grid_size": 101,
        },
        "v4_fixed_model_baseline": {
            "nfm_6_db_seed_counts": baseline["nfm_6_db_seed_counts"],
            "nfm_6_db_rejection_reason_counts": baseline["nfm_6_db_rejection_reason_counts"],
            "nfm_6_db_distance_quantiles": baseline["nfm_6_db_distance_quantiles"],
            "nfm_6_db_margin_quantiles": baseline["nfm_6_db_margin_quantiles"],
        },
        "cross_seed_diagnostics": diagnostics,
        "development_limits": DEVELOPMENT_LIMITS,
        "persistent_numeric_bytes": (
            len(fitted["scaling"]["center"])
            + len(fitted["scaling"]["scale"])
            + sum(len(item["centroid"]) for item in fitted["prototypes"])
            + sum(len(row) for row in fitted["shared_precision"])
            + 1
        ) * 8,
        "literature_basis": {
            "automatic_modulation_classification": {
                "title": "Survey of automatic modulation classification techniques: classical approaches and new trends",
                "doi": "10.1049/iet-com:20050176",
            },
            "reject_option": {
                "title": "On Reject and Refine Options in Multicategory Classification",
                "identifier": "arXiv:1701.02265",
            },
            "applied_boundary": "The existing bounded statistics and prototype distances are retained; only the nearest-NFM reject margin is selected by leave-one-seed-out risk and coverage gates.",
        },
        "claim_boundary": "Yalnız sekiz açık F4 geliştirme seed'inden türetilmiştir; önceki popülasyonlar, F4 binding/OOS, canlı RF veya genel modülasyon tanıma sonucu değildir.",
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
        print("PHASE-04-F4 domain model is missing or stale")
        return 1
    print("PHASE-04-F4 domain model: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
