#!/usr/bin/env python3
"""Check PHASE-04-R2 calibration and emit a path-free diagnostic document."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.r2 import (  # noqa: E402
    build_method_lock,
    canonical_json_bytes,
    hann_covariance_calibration,
    hann_end_to_end_calibration,
    morphology_calibration,
)


LOCK = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"
R1_COMPARISON = ROOT / "results" / "evidence" / "phase04" / "parameter-comparison.json"


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    covariance = hann_covariance_calibration(full=True)
    end_to_end = hann_end_to_end_calibration()
    morphology = morphology_calibration()
    expected_lock = build_method_lock(covariance, end_to_end, morphology)
    r1 = json.loads(R1_COMPARISON.read_text(encoding="utf-8"))
    records = [
        item
        for item in r1["noise_bandwidth_pairs"]
        if item["analysis_window_method"] == "analysis.clustered-regions-v1"
        and item["noise_method"] == "noise.trimmed-mean-20"
        and item["bandwidth_method"] == "band.multi-component-excess-99-v1"
    ]
    if len(records) != 1:
        raise ValueError("R1 best tuple cannot be identified uniquely")
    best = records[0]
    diagnostic = {
        "schema_version": 1,
        "phase": "PHASE-04-R2",
        "status": "passed",
        "source_r1_comparison_sha256": hashlib.sha256(R1_COMPARISON.read_bytes()).hexdigest(),
        "source_tuple": {
            "analysis_window": best["analysis_window_method"],
            "noise": best["noise_method"],
            "bandwidth": best["bandwidth_method"],
        },
        "r1_binding_metrics": {
            "valid_rate": best["valid_rate"],
            "q95_relative_bandwidth_error": best["q95_relative_bandwidth_error"],
            "q95_lower_edge_normalized": best["q95_lower_edge_normalized_to_scene_limit"],
            "q95_upper_edge_normalized": best["q95_upper_edge_normalized_to_scene_limit"],
            "region_success_rate": best["region_success_rate"],
        },
        "family_snr_diagnostics": best["family_snr_diagnostics"],
        "noise_calibration": covariance,
        "noise_end_to_end_validation": end_to_end,
        "morphology_calibration": morphology,
        "ground_truth_used_by_runtime": False,
        "diagnostic_oracle_used_by_selector": False,
    }
    return diagnostic, expected_lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.check and args.output is None:
        parser.error("one of --check or --output is required")
    diagnostic, expected_lock = build()
    actual_lock = json.loads(LOCK.read_text(encoding="utf-8"))
    passed = actual_lock == expected_lock and diagnostic["status"] == "passed"
    if args.output is not None:
        target = args.output.resolve()
        if target == ROOT or ROOT in target.parents:
            parser.error("diagnostic output must remain outside the repository")
        _atomic(target, canonical_json_bytes(diagnostic))
    print(f"PHASE-04-R2 calibration: {'passed' if passed else 'failed'}")
    print(f"Method-lock SHA-256: {hashlib.sha256(LOCK.read_bytes()).hexdigest()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
