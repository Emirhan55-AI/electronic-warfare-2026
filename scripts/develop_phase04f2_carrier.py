#!/usr/bin/env python3
"""Analyze conservative v3 carrier thresholds on the open F2 catalog."""

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
from algorithms.parameters.f1_estimator import F1ParameterEstimator
from algorithms.parameters.f2_estimator import carrier_evidence
from algorithms.parameters.operator_reference import load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f2" / "carrier-threshold-analysis-v3.json"


def build_analysis() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    common = development["common"]
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F1ParameterEstimator()
    rows: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(common["development_seeds"]):
        for family_index, family in enumerate(development["families"]):
            frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
            for trial in range(int(common["trials_per_seed_per_family"])):
                frames = tuple(
                    generate_parameter_scene(
                        str(family["scene_id"]), trial_index=trial, condition_index=3,
                        frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=12.0,
                        catalog=catalog, scene_seed_override=int(seed) + family_index * 10_000,
                    )
                    for frame_index in frame_indices
                )
                spectra = tuple(
                    processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
                    for frame in frames
                )
                clean_spectra = tuple(
                    processor.process(frame.clean_samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
                    for frame in frames
                )
                truth = _truth(clean_spectra, int(common["operator_span_truth_margin_bins_per_side"]))
                span = tuple(int(value) for value in truth["span"])
                result = estimator.measure(_intent(span, family_index + 1, trial), tuple(frame.samples for frame in frames), spectra)
                evidence = None
                if result.emission_center_frequency.state == "valid":
                    evidence = carrier_evidence(_intent(span, family_index + 1, trial), spectra, float(result.emission_center_frequency.value))
                rows.append({
                    "seed_index": seed_index,
                    "family_id": str(family["id"]),
                    "applicable": bool(family["carrier_line_applicable"]),
                    "prominence_db": evidence[0] if evidence is not None else -math.inf,
                    "share": evidence[1] if evidence is not None else -math.inf,
                    "minimum_frame_prominence_db": evidence[2] if evidence is not None else -math.inf,
                })
    candidates: list[tuple[float, float, float, float, float, int]] = []
    applicable_families = sorted({row["family_id"] for row in rows if row["applicable"]})
    nonapplicable_count = sum(not row["applicable"] for row in rows)
    prominence_values = np.asarray([row["prominence_db"] for row in rows])
    share_values = np.asarray([row["share"] for row in rows])
    frame_prominence_values = np.asarray([row["minimum_frame_prominence_db"] for row in rows])
    applicable_mask = np.asarray([row["applicable"] for row in rows], dtype=bool)
    family_masks = {
        family_id: np.asarray([row["family_id"] == family_id for row in rows], dtype=bool)
        for family_id in applicable_families
    }
    for prominence in np.arange(5.0, 12.01, 0.25):
        for share in np.arange(0.21, 0.401, 0.005):
            for frame_prominence in np.arange(0.0, 8.01, 0.25):
                selected = (
                    (prominence_values >= prominence)
                    & (share_values >= share)
                    & (frame_prominence_values >= frame_prominence)
                )
                false_count = int(np.sum(selected & ~applicable_mask))
                family_rates = [
                    float(np.sum(selected & family_masks[family_id]) / np.sum(family_masks[family_id]))
                    for family_id in applicable_families
                ]
                global_rate = float(np.sum(selected & applicable_mask) / np.sum(applicable_mask))
                if false_count <= 2 and min(family_rates) >= 0.88 and global_rate >= 0.92:
                    candidates.append((min(family_rates), global_rate, prominence, share, frame_prominence, false_count))
    if not candidates:
        raise RuntimeError("no carrier threshold pair meets the open-catalog development constraints")
    family_rate, global_rate, prominence, share, frame_prominence, false_count = max(
        candidates,
        key=lambda item: (item[0], item[1], -item[5], -item[2], -item[3], -item[4]),
    )
    return {
        "schema_version": 1,
        "artifact_id": "phase04f2-carrier-threshold-analysis-v3",
        "role": "development-only",
        "selected": {
            "minimum_prominence_db": prominence,
            "minimum_share": share,
            "minimum_frame_prominence_db": frame_prominence,
            "family_min_valid_rate": family_rate,
            "global_valid_rate": global_rate,
            "false_valid_count": false_count,
            "false_valid_rate": false_count / nonapplicable_count,
        },
        "constraints": {
            "family_min_valid_rate": 0.88,
            "global_valid_rate": 0.92,
            "false_valid_count_maximum": 2,
        },
        "population": {"trials": len(rows), "nonapplicable_trials": nonapplicable_count},
        "claim_boundary": "Yalnız açık F2 geliştirme kataloğunun 12 dB koşuludur; binding veya OOS sonucu değildir.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build_analysis()
    payload = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if args.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(payload)
    elif not RESULT_PATH.is_file() or RESULT_PATH.read_bytes() != payload:
        print("PHASE-04-F2 carrier analysis is missing or stale")
        return 1
    print(json.dumps(document["selected"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
