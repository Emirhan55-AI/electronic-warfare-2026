#!/usr/bin/env python3
"""Compare structural v6 OBW candidates on every open F5 signal family."""

from __future__ import annotations

import math
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
from algorithms.parameters.f5_estimator import _tail_corrected_obw
from algorithms.parameters.operator_reference import canonical_json_bytes, load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f5" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "obw-temporal-candidates-v6.json"
TAIL_FRACTION = 0.0075
EDGE_EXPANSIONS_BINS = (0.375,)
TEMPORAL_LIMITS = (5.0, 5.5, 6.0, 7.0)


def _q95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[max(0, int(math.ceil(0.95 * len(ordered))) - 1)])


def _wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    half = z * math.sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)) / denominator
    return center - half


def evaluate_candidates() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    catalog = load_parameter_catalog()
    common = development["common"]
    processor = SpectrumProcessor()
    estimator = F4ParameterEstimator()
    candidate_keys = tuple(
        (edge_expansion, temporal_limit)
        for edge_expansion in EDGE_EXPANSIONS_BINS
        for temporal_limit in TEMPORAL_LIMITS
    )
    accumulators: dict[str, dict[str, Any]] = {
        key: {
            str(family["id"]): {
                "valid": 0,
                "per_seed": [0] * len(common["development_seeds"]),
                "relative_errors": [],
                "lower_errors": [],
                "upper_errors": [],
                "temporal_ranges": [],
                "reasons": Counter(),
                "attempts": Counter(),
                "outcomes": Counter(),
                "invalid_trials": [],
            }
            for family in development["families"]
        }
        for key in candidate_keys
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
                parent = estimator.measure(intent, samples, spectra)
                for key in candidate_keys:
                    edge_expansion, temporal_limit = key
                    result = _tail_corrected_obw(
                        parent,
                        intent,
                        spectra,
                        tail_fraction=TAIL_FRACTION,
                        edge_expansion_bins=edge_expansion,
                        maximum_temporal_range_bins=temporal_limit,
                    )
                    bucket = accumulators[key][family_id]
                    attempted = result is not parent
                    bucket["attempts"]["attempted" if attempted else "not_attempted"] += 1
                    parent_valid = parent.occupied_bandwidth.state == "valid"
                    result_valid = result.occupied_bandwidth.state == "valid"
                    if parent_valid and result_valid:
                        bucket["outcomes"]["retained_valid"] += 1
                    elif parent_valid:
                        bucket["outcomes"]["invalidated_parent_valid"] += 1
                    elif result_valid:
                        bucket["outcomes"]["recovered_parent_invalid"] += 1
                    else:
                        bucket["outcomes"]["remained_invalid"] += 1
                    if result.quality.temporal_edge_range_bins is not None:
                        bucket["temporal_ranges"].append(float(result.quality.temporal_edge_range_bins))
                    if result.occupied_bandwidth.state != "valid":
                        bucket["reasons"][result.occupied_bandwidth.reason or "unspecified"] += 1
                        bucket["invalid_trials"].append({
                            "seed_index": seed_index,
                            "trial_index": trial,
                            "reason": result.occupied_bandwidth.reason or "unspecified",
                            "parent_state": parent.occupied_bandwidth.state,
                            "parent_reason": parent.occupied_bandwidth.reason,
                            "temporal_range_bins": result.quality.temporal_edge_range_bins,
                        })
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
    candidates: list[dict[str, Any]] = []
    for key, families in accumulators.items():
        family_rows = {
            family: {
                "valid_count": data["valid"],
                "seed_valid_counts": data["per_seed"],
                "wilson_lower_95": _wilson_lower(data["valid"], 384),
                "relative_q95": _q95(data["relative_errors"]),
                "lower_edge_q95_bins": _q95(data["lower_errors"]),
                "upper_edge_q95_bins": _q95(data["upper_errors"]),
                "temporal_range_q95_bins": _q95(data["temporal_ranges"]),
                "temporal_range_q99_bins": (
                    float(np.quantile(data["temporal_ranges"], 0.99, method="higher"))
                    if data["temporal_ranges"] else None
                ),
                "temporal_range_maximum_bins": (
                    max(data["temporal_ranges"]) if data["temporal_ranges"] else None
                ),
                "rejection_reason_counts": dict(sorted(data["reasons"].items())),
                "recovery_attempt_counts": dict(sorted(data["attempts"].items())),
                "recovery_outcome_counts": dict(sorted(data["outcomes"].items())),
                "invalid_trial_diagnostics": data["invalid_trials"],
            }
            for family, data in families.items()
        }
        metrics = {
            "obw.family_min_valid_count_12_db": min(item["valid_count"] for item in family_rows.values()),
            "obw.seed_min_valid_count_12_db": min(min(item["seed_valid_counts"]) for item in family_rows.values()),
            "obw.family_min_wilson_lower_95_12_db": min(item["wilson_lower_95"] for item in family_rows.values()),
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
            and metrics["obw.family_min_wilson_lower_95_12_db"] >= 0.96875
            and metrics["obw.family_max_relative_q95_12_db"] <= 0.2
            and metrics["obw.family_max_lower_edge_q95_bins_12_db"] <= 2.0
            and metrics["obw.family_max_upper_edge_q95_bins_12_db"] <= 2.0
            and metrics["obw.family_max_temporal_rejection_count_12_db"] <= 5
        )
        candidates.append({
            "tail_fraction": TAIL_FRACTION,
            "edge_expansion_bins": float(key[0]),
            "temporal_range_maximum_bins": float(key[1]),
            "status": "passed" if passed else "failed",
            "metrics": metrics,
            "families": family_rows,
        })
    selected = next((item for item in candidates if item["status"] == "passed"), None)
    selected_diagnostics = None if selected is None else {
        "obw.seed_counts_12_db": {
            family: row["seed_valid_counts"] for family, row in selected["families"].items()
        },
        "obw.rejection_reason_counts_12_db": {
            family: row["rejection_reason_counts"] for family, row in selected["families"].items()
        },
        "obw.temporal_range_quantiles_12_db": {
            family: {
                "q95_bins": row["temporal_range_q95_bins"],
                "q99_bins": row["temporal_range_q99_bins"],
                "maximum_bins": row["temporal_range_maximum_bins"],
            }
            for family, row in selected["families"].items()
        },
        "obw.recovery_attempt_counts_12_db": {
            family: row["recovery_attempt_counts"] for family, row in selected["families"].items()
        },
        "obw.recovery_outcome_counts_12_db": {
            family: row["recovery_outcome_counts"] for family, row in selected["families"].items()
        },
        "obw.invalid_trial_diagnostics_12_db": [
            {"family": family, **item}
            for family, row in selected["families"].items()
            for item in row["invalid_trial_diagnostics"]
        ],
    }
    return {
        "schema_version": 1,
        "artifact_id": "phase04f5-obw-temporal-candidates-v6",
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
        "selected": None if selected is None else {
            "tail_fraction": selected["tail_fraction"],
            "edge_expansion_bins": selected["edge_expansion_bins"],
            "temporal_range_maximum_bins": selected["temporal_range_maximum_bins"],
        },
        "selected_diagnostics": selected_diagnostics,
        "selection_policy": "Sabit yapısal OBW düzeltmesiyle kilitli yedi kapının tamamını geçen en sıkı temporal üst sınır seçilir.",
        "claim_boundary": "Yalnız açık F5 geliştirme seed'lerinde yapısal aday karşılaştırmasıdır; binding/OOS, FPGA veya ürün sonucu değildir.",
    }


def main() -> int:
    document = evaluate_candidates()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(canonical_json_bytes(document))
    print(f"PHASE-04-F5 structural OBW candidates: {document['status']}; selected={document['selected']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
