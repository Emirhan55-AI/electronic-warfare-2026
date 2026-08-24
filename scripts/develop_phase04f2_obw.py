#!/usr/bin/env python3
"""Compare immutable F1 OBW output with the bounded F2 temporal recovery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_development import _intent, _q95, _truth
from algorithms.parameters.f1_estimator import F1ParameterEstimator
from algorithms.parameters.f2_estimator import F2ParameterEstimator, _recover_obw
from algorithms.parameters.operator_reference import load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f2" / "obw-ablation-v3.json"


def _record() -> dict[str, Any]:
    return {"trials": 0, "valid": 0, "lower_errors": [], "upper_errors": [], "relative_errors": [], "temporal": []}


def _add(record: dict[str, Any], result: Any, truth: dict[str, Any], center_hz: float, spacing_hz: float) -> None:
    record["trials"] += 1
    if result.occupied_bandwidth.state != "valid":
        return
    lower = (float(result.lower_band_edge.value) - center_hz) / spacing_hz + 2048.0
    upper = (float(result.upper_band_edge.value) - center_hz) / spacing_hz + 2048.0
    record["valid"] += 1
    record["lower_errors"].append(abs(lower - float(truth["lower_bin"])))
    record["upper_errors"].append(abs(upper - float(truth["upper_bin"])))
    record["relative_errors"].append(abs((upper - lower) - float(truth["width_bins"])) / float(truth["width_bins"]))
    if result.quality.temporal_edge_range_bins is not None:
        record["temporal"].append(result.quality.temporal_edge_range_bins)


def _summary(record: dict[str, Any]) -> dict[str, float | int | None]:
    return {
        "trial_count": record["trials"],
        "valid_count": record["valid"],
        "valid_rate": record["valid"] / record["trials"],
        "relative_q95": _q95(record["relative_errors"]),
        "lower_edge_q95_bins": _q95(record["lower_errors"]),
        "upper_edge_q95_bins": _q95(record["upper_errors"]),
        "temporal_q95_bins": _q95(record["temporal"]),
    }


def build_analysis() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    common = development["common"]
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F1ParameterEstimator()
    methods = {"f1": _record(), "f2": _record()}
    families = {
        str(family["id"]): {"f1": _record(), "f2": _record()}
        for family in development["families"]
    }
    for seed_index, seed in enumerate(common["development_seeds"]):
        for family_index, family in enumerate(development["families"]):
            family_id = str(family["id"])
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
                intent = _intent(span, seed_index * 100 + family_index + 1, trial)
                f1 = estimator.measure(intent, tuple(frame.samples for frame in frames), spectra)
                f2 = _recover_obw(f1, intent, spectra, F2ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM)
                for name, result in (("f1", f1), ("f2", f2)):
                    _add(methods[name], result, truth, 100_000_000.0, 8_000_000.0 / 4096.0)
                    _add(families[family_id][name], result, truth, 100_000_000.0, 8_000_000.0 / 4096.0)
    summaries = {name: _summary(record) for name, record in methods.items()}
    family_summaries = {
        family_id: {name: _summary(record) for name, record in records.items()}
        for family_id, records in families.items()
    }
    return {
        "schema_version": 1,
        "artifact_id": "phase04f2-obw-ablation-v3",
        "role": "development-only",
        "status": "passed" if (
            min(item["f2"]["valid_rate"] for item in family_summaries.values()) >= 0.90
            and summaries["f2"]["valid_rate"] >= 0.95
            and summaries["f2"]["relative_q95"] <= 0.20
            and summaries["f2"]["lower_edge_q95_bins"] <= 2.0
            and summaries["f2"]["upper_edge_q95_bins"] <= 2.0
            and summaries["f2"]["temporal_q95_bins"] <= 2.0
        ) else "failed",
        "maximum_recoverable_temporal_range_bins": F2ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM,
        "aggregate": summaries,
        "families": family_summaries,
        "claim_boundary": "Yalnız açık F2 geliştirme kataloğunun 12 dB koşuludur; binding veya OOS sonucu değildir.",
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
        print("PHASE-04-F2 OBW ablation is missing or stale")
        return 1
    print(f"PHASE-04-F2 OBW ablation: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
