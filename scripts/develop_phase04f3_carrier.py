#!/usr/bin/env python3
"""Verify the v4 carrier decision on the open F3 catalog."""

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

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f2_estimator import F2ParameterEstimator
from algorithms.parameters.f3_domain import extract_domain_vector_v4
from algorithms.parameters.f3_estimator import F3ParameterEstimator, carrier_evidence_v4
from algorithms.parameters.operator_reference import load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f3" / "carrier-analysis-v4.json"


def _q95(values: list[float]) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), 0.95, method="inverted_cdf"))


def build_analysis() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    common = development["common"]
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    v3 = F2ParameterEstimator()
    v4 = F3ParameterEstimator()
    per_seed = [
        {
            "seed_index": seed_index,
            "ook_valid_count": 0,
            "ook_qualifying_frame_count": 0,
            "ook_all_frames_qualified_count": 0,
            "nonapplicable_false_valid_count": 0,
        }
        for seed_index in range(len(common["development_seeds"]))
    ]
    family = {
        str(item["id"]): {"applicable": bool(item["carrier_line_applicable"]), "v3_valid": 0, "v4_valid": 0, "errors": []}
        for item in development["families"]
    }
    for seed_index, seed in enumerate(common["development_seeds"]):
        for family_index, item in enumerate(development["families"]):
            frame_indices = tuple(int(value) for value in item.get("active_frames", [0, 1, 2, 3]))[:4]
            for trial in range(int(common["trials_per_seed_per_family"])):
                frames = tuple(
                    generate_parameter_scene(
                        str(item["scene_id"]), trial_index=trial, condition_index=3,
                        frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=12.0,
                        catalog=catalog, scene_seed_override=int(seed) + family_index * 10_000,
                    )
                    for frame_index in frame_indices
                )
                spectra = tuple(
                    processor.process(
                        frame.samples,
                        sample_rate_hz=float(common["sample_rate_hz"]),
                        center_frequency_hz=float(common["center_frequency_hz"]),
                    )
                    for frame in frames
                )
                clean = tuple(
                    processor.process(
                        frame.clean_samples,
                        sample_rate_hz=float(common["sample_rate_hz"]),
                        center_frequency_hz=float(common["center_frequency_hz"]),
                    )
                    for frame in frames
                )
                truth = _truth(clean, int(common["operator_span_truth_margin_bins_per_side"]))
                intent = _intent(tuple(int(value) for value in truth["span"]), family_index + 1, trial)
                samples = tuple(frame.samples for frame in frames)
                old = v3.measure(intent, samples, spectra)
                result = v4.measure(intent, samples, spectra)
                record = family[str(item["id"])]
                record["v3_valid"] += int(old.carrier_line_frequency.state == "valid")
                record["v4_valid"] += int(result.carrier_line_frequency.state == "valid")
                vector = extract_domain_vector_v4(samples, intent.span.lower_shifted_bin, intent.span.upper_shifted_bin)
                evidence = carrier_evidence_v4(
                    intent, spectra, float(result.emission_center_frequency.value), vector,
                )
                if str(item["id"]) == "ook" and evidence is not None:
                    qualifies = sum(
                        value >= v4.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4
                        for value in evidence.frame_prominences_db
                    )
                    per_seed[seed_index]["ook_qualifying_frame_count"] += qualifies
                    per_seed[seed_index]["ook_all_frames_qualified_count"] += int(qualifies == 4)
                    per_seed[seed_index]["ook_valid_count"] += int(result.carrier_line_frequency.state == "valid")
                elif not item["carrier_line_applicable"]:
                    per_seed[seed_index]["nonapplicable_false_valid_count"] += int(
                        result.carrier_line_frequency.state == "valid"
                    )
                if item["carrier_line_applicable"] and result.carrier_line_frequency.state == "valid":
                    truth_hz = float(frames[0].ground_truth["nominal_center_frequency_hz"])
                    record["errors"].append(
                        abs(float(result.carrier_line_frequency.value) - truth_hz) / spectra[0].bin_spacing_hz
                    )
    trials = int(common["total_trials_per_family"])
    applicable = [item for item in family.values() if item["applicable"]]
    false_counts = [item["nonapplicable_false_valid_count"] for item in per_seed]
    status = "passed" if (
        min(item["v4_valid"] / trials for item in applicable) >= 0.85
        and sum(item["v4_valid"] for item in applicable) / (len(applicable) * trials) >= 0.90
        and max(_q95(item["errors"]) for item in applicable) <= 1.0
        and min(item["ook_valid_count"] for item in per_seed) >= 45
        and min(item["ook_qualifying_frame_count"] for item in per_seed) >= 180
        and min(item["ook_all_frames_qualified_count"] for item in per_seed) >= 42
        and max(false_counts) <= 1
        and sum(false_counts) <= 2
    ) else "failed"
    family_summary = {
        name: {
            "applicable": item["applicable"],
            "trial_count": trials,
            "v3_valid_count": item["v3_valid"],
            "v4_valid_count": item["v4_valid"],
            "v4_q95_error_bins": _q95(item["errors"]) if item["errors"] else None,
        }
        for name, item in family.items()
    }
    return {
        "schema_version": 1,
        "artifact_id": "phase04f3-carrier-analysis-v4",
        "role": "development-only",
        "status": status,
        "selected": {
            "minimum_prominence_db": v4.CARRIER_PROMINENCE_DB_MINIMUM_V4,
            "minimum_share": v4.CARRIER_SHARE_MINIMUM_V4,
            "minimum_frame_prominence_db": v4.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4,
            "artifact_spectral_entropy_minimum": v4.CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4,
            "artifact_envelope_skewness_maximum": v4.CARRIER_ARTIFACT_ENVELOPE_SKEWNESS_MAXIMUM_V4,
        },
        "per_seed": per_seed,
        "families": family_summary,
        "aggregate": {
            "v3_ook_valid_count": family_summary["ook"]["v3_valid_count"],
            "v4_ook_valid_count": family_summary["ook"]["v4_valid_count"],
            "v4_false_valid_count": sum(false_counts),
        },
        "literature_basis": "Temporal spectral-line evidence with complex-envelope statistics and conservative artifact rejection.",
        "claim_boundary": "Yalnız sekiz açık F3 geliştirme seed'inin 12 dB koşuludur; F3 binding/OOS veya ürün sonucu değildir.",
    }


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build_analysis()
    payload = _canonical(document)
    if args.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(payload)
    elif not RESULT_PATH.is_file() or RESULT_PATH.read_bytes() != payload:
        print("PHASE-04-F3 carrier analysis is missing or stale")
        return 1
    print(f"PHASE-04-F3 carrier analysis: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
