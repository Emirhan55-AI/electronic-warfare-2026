#!/usr/bin/env python3
"""Compare bounded OBW temporal-recovery candidates on the open F5 catalog."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f4_estimator import F4ParameterEstimator
from algorithms.parameters.operator_reference import canonical_json_bytes, load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f5" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "obw-candidate-analysis-v6.json"
CANDIDATES = (3.0, 3.25, 3.5, 4.0, 5.0)


def _q95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[max(0, int(np.ceil(0.95 * len(ordered))) - 1)])


def _estimator(limit: float) -> F4ParameterEstimator:
    estimator_type = type(
        f"F5ObwCandidate{str(limit).replace('.', '_')}",
        (F4ParameterEstimator,),
        {"OBW_TEMPORAL_RANGE_MAXIMUM": limit},
    )
    return estimator_type()


def evaluate_candidates() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    catalog = load_parameter_catalog()
    common = development["common"]
    processor = SpectrumProcessor()
    estimators = {str(limit): _estimator(limit) for limit in CANDIDATES}
    accumulators: dict[str, dict[str, Any]] = {
        key: {
            family["id"]: {
                "valid": 0,
                "per_seed": [0] * len(common["development_seeds"]),
                "relative_errors": [],
                "lower_errors": [],
                "upper_errors": [],
                "reasons": Counter(),
                "recovered_temporal_ranges": [],
            }
            for family in development["families"]
        }
        for key in estimators
    }
    for family_index, family in enumerate(development["families"]):
        family_id = str(family["id"])
        frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
        for seed_index, seed in enumerate(common["development_seeds"]):
            scene_seed = int(seed) + family_index * 10_000
            for trial in range(int(common["trials_per_seed_per_family"])):
                frames = tuple(
                    generate_parameter_scene(
                        str(family["scene_id"]), trial_index=trial, condition_index=3,
                        frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=12.0,
                        catalog=catalog, scene_seed_override=scene_seed,
                    )
                    for frame_index in frame_indices
                )
                spectra = tuple(
                    processor.process(
                        frame.samples, sample_rate_hz=float(common["sample_rate_hz"]),
                        center_frequency_hz=float(common["center_frequency_hz"]),
                    )
                    for frame in frames
                )
                clean = tuple(
                    processor.process(
                        frame.clean_samples, sample_rate_hz=float(common["sample_rate_hz"]),
                        center_frequency_hz=float(common["center_frequency_hz"]),
                    )
                    for frame in frames
                )
                truth = _truth(clean, int(common["operator_span_truth_margin_bins_per_side"]))
                span = tuple(int(value) for value in truth["span"])
                intent = _intent(span, seed_index * 100 + family_index + 1, trial)
                samples = tuple(frame.samples for frame in frames)
                baseline = None
                for key, estimator in estimators.items():
                    result = estimator.measure(intent, samples, spectra)
                    if key == "3.0":
                        baseline = result
                    bucket = accumulators[key][family_id]
                    if result.occupied_bandwidth.state != "valid":
                        bucket["reasons"][result.occupied_bandwidth.reason or "unspecified"] += 1
                        continue
                    bucket["valid"] += 1
                    bucket["per_seed"][seed_index] += 1
                    spacing = spectra[0].bin_spacing_hz
                    center = float(common["center_frequency_hz"])
                    lower_bin = (float(result.lower_band_edge.value) - center) / spacing + 2048.0
                    upper_bin = (float(result.upper_band_edge.value) - center) / spacing + 2048.0
                    bucket["relative_errors"].append(
                        abs((upper_bin - lower_bin) - float(truth["width_bins"])) / float(truth["width_bins"])
                    )
                    bucket["lower_errors"].append(abs(lower_bin - float(truth["lower_bin"])))
                    bucket["upper_errors"].append(abs(upper_bin - float(truth["upper_bin"])))
                    if (
                        baseline is not None
                        and baseline.occupied_bandwidth.state != "valid"
                        and result.quality.temporal_edge_range_bins is not None
                    ):
                        bucket["recovered_temporal_ranges"].append(float(result.quality.temporal_edge_range_bins))
    candidates: list[dict[str, Any]] = []
    for key, families in accumulators.items():
        family_rows = {
            family: {
                "valid_count": data["valid"],
                "seed_valid_counts": data["per_seed"],
                "relative_q95": _q95(data["relative_errors"]),
                "lower_edge_q95_bins": _q95(data["lower_errors"]),
                "upper_edge_q95_bins": _q95(data["upper_errors"]),
                "rejection_reason_counts": dict(sorted(data["reasons"].items())),
                "recovered_temporal_range_q95_bins": _q95(data["recovered_temporal_ranges"]),
            }
            for family, data in families.items()
        }
        metrics = {
            "obw.family_min_valid_count_12_db": min(item["valid_count"] for item in family_rows.values()),
            "obw.seed_min_valid_count_12_db": min(min(item["seed_valid_counts"]) for item in family_rows.values()),
            "obw.family_max_relative_q95_12_db": max(float(item["relative_q95"]) for item in family_rows.values()),
            "obw.family_max_lower_edge_q95_bins_12_db": max(float(item["lower_edge_q95_bins"]) for item in family_rows.values()),
            "obw.family_max_upper_edge_q95_bins_12_db": max(float(item["upper_edge_q95_bins"]) for item in family_rows.values()),
            "obw.family_max_temporal_rejection_count_12_db": max(
                int(item["rejection_reason_counts"].get("obw_temporal_instability", 0))
                for item in family_rows.values()
            ),
        }
        passed = (
            metrics["obw.family_min_valid_count_12_db"] >= 379
            and metrics["obw.seed_min_valid_count_12_db"] >= 47
            and metrics["obw.family_max_relative_q95_12_db"] <= 0.2
            and metrics["obw.family_max_lower_edge_q95_bins_12_db"] <= 2.0
            and metrics["obw.family_max_upper_edge_q95_bins_12_db"] <= 2.0
            and metrics["obw.family_max_temporal_rejection_count_12_db"] <= 5
        )
        candidates.append({
            "temporal_recovery_limit_bins": float(key),
            "status": "passed" if passed else "failed",
            "metrics": metrics,
            "families": family_rows,
        })
    selected = next((item for item in candidates if item["status"] == "passed"), None)
    return {
        "schema_version": 1,
        "artifact_id": "phase04f5-obw-candidate-analysis-v6",
        "role": "development-only",
        "status": "passed" if selected is not None else "no-candidate-passed",
        "population": {
            "seed_count": len(common["development_seeds"]),
            "trials_per_seed_per_family": common["trials_per_seed_per_family"],
            "total_trials_per_family": common["total_trials_per_family"],
            "snr_db": 12.0,
            "frames_per_measurement": common["frames_per_measurement"],
        },
        "candidates": candidates,
        "selected_temporal_recovery_limit_bins": None if selected is None else selected["temporal_recovery_limit_bins"],
        "selection_policy": "Kilitli kapıların tamamını geçen en küçük temporal recovery üst sınırı seçilir.",
        "claim_boundary": "Yalnız açık F5 geliştirme seed'lerinde aday karşılaştırmasıdır; binding/OOS, FPGA veya ürün sonucu değildir.",
    }


def main() -> int:
    document = evaluate_candidates()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(canonical_json_bytes(document))
    print(f"PHASE-04-F5 OBW candidates: {document['status']}; selected={document['selected_temporal_recovery_limit_bins']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
