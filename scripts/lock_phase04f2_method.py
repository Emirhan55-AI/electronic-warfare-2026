#!/usr/bin/env python3
"""Lock the PHASE-04-F2 v3 method and open-development evidence before reveal."""

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

from algorithms.parameters.f2_estimator import F2ParameterEstimator, PERSISTENT_PAYLOAD_BYTES
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.lock_phase04f2_protocol import F1_PROTECTED, INPUTS


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f2"
METHOD_LOCK_PATH = FIXTURES / "method-lock-v3.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
DOMAIN_MODEL_PATH = FIXTURES / "domain-model-v3.json"
EVIDENCE = ROOT / "results" / "evidence" / "phase04f2"
DEVELOPMENT_RESULT_PATH = EVIDENCE / "development-results-v3.json"
CARRIER_RESULT_PATH = EVIDENCE / "carrier-threshold-analysis-v3.json"
OBW_RESULT_PATH = EVIDENCE / "obw-ablation-v3.json"
IMPLEMENTATION_PATHS = (
    "algorithms/parameters/f2_estimator.py",
    "algorithms/parameters/f2_domain.py",
    "algorithms/parameters/f2_development.py",
    "scripts/develop_phase04f2_carrier.py",
    "scripts/develop_phase04f2_domain.py",
    "scripts/develop_phase04f2_obw.py",
    "scripts/verify_phase04f2_development.py",
    "scripts/lock_phase04f2_method.py",
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


def _verify_pre_method_lock() -> dict[str, Any]:
    protocol = _load(FIXTURES / "protocol-lock.json")
    if any(sha256_file(ROOT / path) != protocol["inputs"][path] for path in INPUTS):
        raise RuntimeError("F2 protocol input changed after the pre-method lock")
    if any(sha256_file(ROOT / path) != protocol["f1_protected_inputs"][path] for path in F1_PROTECTED):
        raise RuntimeError("protected F1 evidence changed during F2C")
    return protocol


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("F2 evaluation seeds were revealed before the v3 method lock")
    protocol = _verify_pre_method_lock()
    development = _load(DEVELOPMENT_RESULT_PATH)
    carrier = _load(CARRIER_RESULT_PATH)
    obw = _load(OBW_RESULT_PATH)
    model = _load(DOMAIN_MODEL_PATH)
    if development.get("status") != "passed" or development.get("role") != "development-only":
        raise RuntimeError("the complete open-development gates have not passed")
    if obw.get("status") != "passed" or obw.get("role") != "development-only":
        raise RuntimeError("the open-development OBW ablation has not passed")
    if carrier.get("role") != "development-only" or carrier.get("selected", {}).get("false_valid_count", 3) > 2:
        raise RuntimeError("the open-development carrier analysis is incomplete")
    if model.get("status") != "development-only" or model.get("persistent_numeric_bytes", 65_537) > 65_536:
        raise RuntimeError("the v3 domain model is not bounded development evidence")
    selected = carrier["selected"]
    expected_carrier = {
        "minimum_prominence_db": F2ParameterEstimator.CARRIER_PROMINENCE_DB_MINIMUM_V3,
        "minimum_share": F2ParameterEstimator.CARRIER_SHARE_MINIMUM_V3,
        "minimum_frame_prominence_db": F2ParameterEstimator.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V3,
    }
    if any(not math_isclose(float(selected[name]), float(value)) for name, value in expected_carrier.items()):
        raise RuntimeError("carrier analysis and estimator constants differ")
    if PERSISTENT_PAYLOAD_BYTES > 65_536:
        raise RuntimeError("combined v3 persistent payload exceeds the memory bound")
    manifest = implementation_manifest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f2-method-lock-v3",
        "status": "locked-before-seed-reveal",
        "methods": F2ParameterEstimator.METHOD_IDS,
        "constants": {
            "required_frames": 4,
            "frame_length": 4096,
            "maximum_persistent_payload_bytes": 65_536,
            "combined_persistent_payload_bytes": PERSISTENT_PAYLOAD_BYTES,
            "domain_model_numeric_bytes": model["persistent_numeric_bytes"],
            "corrected_detection_significance_minimum": F2ParameterEstimator.CORRECTED_DETECTION_SIGNIFICANCE_MINIMUM,
            "low_snr_abstention_db": F2ParameterEstimator.LOW_SNR_ABSTENTION_DB,
            "obw_temporal_range_maximum_bins": F2ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM,
            "carrier": expected_carrier,
            "reference_cells_per_side": 32,
            "reference_guard_bins": 4,
        },
        "contracts": {
            "protocol_lock_sha256": sha256_file(FIXTURES / "protocol-lock.json"),
            "protocol_lock_identity": protocol["protocol_lock_sha256"],
            "acceptance_gates_sha256": sha256_file(FIXTURES / "acceptance-gates.json"),
            "development_catalog_sha256": sha256_file(FIXTURES / "development-catalog.json"),
            "evaluation_commitments_sha256": sha256_file(FIXTURES / "evaluation-commitments.json"),
            "domain_model_sha256": sha256_file(DOMAIN_MODEL_PATH),
            "development_results_sha256": sha256_file(DEVELOPMENT_RESULT_PATH),
            "carrier_analysis_sha256": sha256_file(CARRIER_RESULT_PATH),
            "obw_ablation_sha256": sha256_file(OBW_RESULT_PATH),
            "implementation_manifest_sha256": manifest["sha256"],
        },
        "implementation": manifest,
        "seed_revealed": False,
        "claim_boundary": "Yöntem yalnız açık F2 geliştirme kanıtından sonra ve binding/OOS seed reveal öncesinde kilitlenmiştir; ürün veya PHASE-04 başarı kararı değildir.",
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "method_lock_sha256": identity}


def math_isclose(left: float, right: float) -> bool:
    return abs(left - right) <= max(1.0e-12, abs(right) * 1.0e-12)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = canonical_json_bytes(build_lock())
    if args.write:
        if METHOD_LOCK_PATH.exists() and METHOD_LOCK_PATH.read_bytes() != expected:
            print("PHASE-04-F2 method lock already differs")
            return 1
        METHOD_LOCK_PATH.write_bytes(expected)
    elif not METHOD_LOCK_PATH.is_file() or METHOD_LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F2 method lock is missing or stale")
        return 1
    print("PHASE-04-F2 method lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
