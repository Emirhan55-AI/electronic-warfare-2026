#!/usr/bin/env python3
"""Lock PHASE-04-F1 methods and implementation digests before seed reveal."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_estimator import F1ParameterEstimator
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
METHOD_LOCK_PATH = FIXTURES / "method-lock.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
DEVELOPMENT_RESULT_PATH = ROOT / "results" / "evidence" / "phase04f1" / "development-results.json"
IMPLEMENTATION_PATHS = (
    "algorithms/parameters/f1_estimator.py",
    "algorithms/parameters/f1_domain.py",
    "algorithms/parameters/f1_development.py",
    "scripts/develop_phase04f1_domain.py",
    "scripts/verify_phase04f1_development.py",
    "scripts/lock_phase04f1_method.py",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def implementation_manifest() -> dict[str, Any]:
    sources = [{"path": path, "sha256": sha256_file(ROOT / path)} for path in IMPLEMENTATION_PATHS]
    digest = hashlib.sha256(canonical_json_bytes({"schema_version": 1, "sources": sources})).hexdigest()
    return {"schema_version": 1, "sources": sources, "sha256": digest}


def _domain_model_numeric_bytes(model: dict[str, Any]) -> int:
    scalar_count = len(model["scaling"]["center"]) + len(model["scaling"]["scale"])
    scalar_count += len(model["domain_linear"]["weights"]) + 1
    for prototype in model["prototypes"]:
        scalar_count += len(prototype["centroid"]) + 1
        scalar_count += sum(len(row) for row in prototype["precision"])
    return scalar_count * 8


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("evaluation seeds were revealed before the F1 method lock")
    development = _load(DEVELOPMENT_RESULT_PATH)
    model = _load(FIXTURES / "domain-model.json")
    if development.get("status") != "passed" or development.get("role") != "development-only":
        raise RuntimeError("development-only field gates have not passed")
    if model.get("status") != "development-only":
        raise RuntimeError("domain model is not a development-only artifact")
    model_numeric_bytes = _domain_model_numeric_bytes(model)
    persistent_payload_bytes = 34_084 + model_numeric_bytes
    if persistent_payload_bytes > 65_536:
        raise RuntimeError("F1 persistent payload exceeds the locked memory bound")
    manifest = implementation_manifest()
    estimator = F1ParameterEstimator
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f1-method-lock-v1",
        "status": "locked-before-seed-reveal",
        "methods": estimator.METHOD_IDS,
        "constants": {
            "required_frames": 4,
            "frame_length": 4096,
            "maximum_persistent_payload_bytes": 65536,
            "estimator_persistent_payload_bytes": 34084,
            "domain_model_numeric_bytes": model_numeric_bytes,
            "combined_persistent_payload_bytes": persistent_payload_bytes,
            "detection_significance_minimum": estimator.DETECTION_SIGNIFICANCE_MINIMUM,
            "center_uncertainty_bins_maximum": estimator.CENTER_UNCERTAINTY_BINS_MAXIMUM,
            "center_shrink_sigma": estimator.CENTER_SHRINK_SIGMA,
            "broad_span_minimum_bins": estimator.BROAD_SPAN_MINIMUM_BINS,
            "obw_shrink_sigma": estimator.OBW_SHRINK_SIGMA,
            "carrier_prominence_db_minimum": estimator.CARRIER_PROMINENCE_DB_MINIMUM,
            "carrier_share_minimum": estimator.CARRIER_SHARE_MINIMUM,
            "snr_linear_calibration": {"slope": 0.8, "intercept_db": 1.6},
            "reference_cells_per_side": 32,
            "reference_guard_bins": 4,
            "reference_difference_db_maximum": 3.0,
        },
        "contracts": {
            "protocol_lock_sha256": sha256_file(FIXTURES / "protocol-lock.json"),
            "acceptance_gates_sha256": sha256_file(FIXTURES / "acceptance-gates.json"),
            "development_scenes_sha256": sha256_file(FIXTURES / "development-scenes.json"),
            "evaluation_commitments_sha256": sha256_file(FIXTURES / "evaluation-commitments.json"),
            "domain_model_sha256": sha256_file(FIXTURES / "domain-model.json"),
            "development_results_sha256": sha256_file(DEVELOPMENT_RESULT_PATH),
            "implementation_manifest_sha256": manifest["sha256"],
        },
        "implementation": manifest,
        "seed_revealed": False,
        "claim_boundary": "Yöntem ve uygulama geliştirme sonucundan sonra, binding/OOS seed reveal öncesinde kilitlenmiştir; ürün veya PHASE-04 başarı kararı değildir.",
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "method_lock_sha256": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = canonical_json_bytes(build_lock())
    if args.write:
        if METHOD_LOCK_PATH.exists() and METHOD_LOCK_PATH.read_bytes() != expected:
            print("PHASE-04-F1 method lock already exists with different content")
            return 1
        METHOD_LOCK_PATH.write_bytes(expected)
    elif not METHOD_LOCK_PATH.is_file() or METHOD_LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F1 method lock is missing or stale")
        return 1
    print("PHASE-04-F1 method lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
