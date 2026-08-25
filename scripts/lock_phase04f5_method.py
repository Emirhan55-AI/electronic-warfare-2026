#!/usr/bin/env python3
"""Lock the PHASE-04-F5 v6 method and development evidence before seed reveal."""

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

from algorithms.parameters.f4_estimator import PERSISTENT_PAYLOAD_BYTES
from algorithms.parameters.f5_estimator import F5ParameterEstimator
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.lock_phase04f5_protocol import INPUTS, PROTECTED_INPUTS, build_lock as build_protocol_lock
from verification.phase04f5_scoring import REQUIRED_DIAGNOSTICS


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
METHOD_LOCK_PATH = FIXTURES / "method-lock-v6.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
EVIDENCE = ROOT / "results" / "evidence" / "phase04f5"
DEVELOPMENT_RESULT_PATH = EVIDENCE / "development-results-v6.json"
CARRIER_RESULT_PATH = EVIDENCE / "carrier-analysis-v6.json"
OBW_RESULT_PATH = EVIDENCE / "obw-temporal-candidates-v6.json"
IMPLEMENTATION_PATHS = (
    "algorithms/parameters/f5_estimator.py",
    "algorithms/parameters/f5_development.py",
    "scripts/analyze_phase04f5_obw_structure.py",
    "scripts/develop_phase04f5_structural_obw.py",
    "scripts/develop_phase04f5_carrier.py",
    "scripts/verify_phase04f5_development.py",
    "scripts/lock_phase04f5_method.py",
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


def _verify_protocol_lock() -> dict[str, Any]:
    protocol = _load(FIXTURES / "protocol-lock.json")
    if protocol != build_protocol_lock():
        raise RuntimeError("F5 protocol lock differs from its pre-method inputs")
    if any(sha256_file(ROOT / path) != protocol["inputs"][path] for path in INPUTS):
        raise RuntimeError("F5 protocol input changed after the pre-method lock")
    if any(
        sha256_file(ROOT / path) != protocol["protected_historical_inputs"][path]
        for path in PROTECTED_INPUTS
    ):
        raise RuntimeError("protected F4 evidence changed during F5C")
    return protocol


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("F5 evaluation seeds were revealed before the v6 method lock")
    protocol = _verify_protocol_lock()
    development = _load(DEVELOPMENT_RESULT_PATH)
    carrier = _load(CARRIER_RESULT_PATH)
    obw = _load(OBW_RESULT_PATH)
    if development.get("status") != "passed" or development.get("role") != "development-only":
        raise RuntimeError("the complete F5 open-development gates have not passed")
    scoring = development.get("scoring", {})
    if (
        len(scoring.get("base_scoring", {}).get("checks", ())) != 40
        or len(scoring.get("f3_inherited_risk_checks", ())) != 14
        or len(scoring.get("f4_additional_risk_checks", ())) != 4
        or len(scoring.get("f5_additional_risk_checks", ())) != 7
    ):
        raise RuntimeError("the F5 development gate coverage is incomplete")
    if carrier.get("status") != "passed" or carrier.get("role") != "development-only":
        raise RuntimeError("the F5 carrier analysis is incomplete")
    if obw.get("status") != "passed" or obw.get("role") != "development-only":
        raise RuntimeError("the F5 OBW analysis is incomplete")
    diagnostics = development.get("diagnostics", {})
    if not set(REQUIRED_DIAGNOSTICS).issubset(diagnostics):
        raise RuntimeError("required F5 OBW diagnostics are incomplete")

    selected = development.get("selected_obw_calibration", {})
    expected_obw = {
        "tail_fraction": F5ParameterEstimator.OBW_TAIL_FRACTION_V6,
        "edge_expansion_bins": F5ParameterEstimator.OBW_EDGE_EXPANSION_BINS_V6,
        "temporal_range_maximum_bins": F5ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM_V6,
    }
    if any(abs(float(selected.get(name, -1.0)) - float(value)) > 1.0e-12 for name, value in expected_obw.items()):
        raise RuntimeError("OBW analysis and v6 estimator constants differ")
    if PERSISTENT_PAYLOAD_BYTES > 65_536:
        raise RuntimeError("combined v6 persistent payload exceeds the memory bound")

    manifest = implementation_manifest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f5-method-lock-v6",
        "status": "locked-before-seed-reveal",
        "methods": F5ParameterEstimator.METHOD_IDS,
        "constants": {
            "required_frames": 4,
            "frame_length": 4096,
            "maximum_persistent_payload_bytes": 65_536,
            "combined_persistent_payload_bytes": PERSISTENT_PAYLOAD_BYTES,
            "obw": expected_obw,
            "obw_smoothing_kernel": [0.25, 0.5, 0.25],
            "reference_cells_per_side": 32,
            "reference_guard_bins": 4,
        },
        "contracts": {
            "protocol_lock_sha256": sha256_file(FIXTURES / "protocol-lock.json"),
            "protocol_lock_identity": protocol["protocol_lock_sha256"],
            "acceptance_gates_sha256": sha256_file(FIXTURES / "acceptance-gates.json"),
            "development_catalog_sha256": sha256_file(FIXTURES / "development-catalog.json"),
            "evaluation_commitments_sha256": sha256_file(FIXTURES / "evaluation-commitments.json"),
            "development_results_sha256": sha256_file(DEVELOPMENT_RESULT_PATH),
            "carrier_analysis_sha256": sha256_file(CARRIER_RESULT_PATH),
            "obw_analysis_sha256": sha256_file(OBW_RESULT_PATH),
            "implementation_manifest_sha256": manifest["sha256"],
        },
        "implementation": manifest,
        "seed_revealed": False,
        "claim_boundary": "Yöntem yalnız açık F5 geliştirme kanıtından sonra ve binding/OOS seed reveal öncesinde kilitlenmiştir; FPGA veya ürün başarı kararı değildir.",
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
            print("PHASE-04-F5 method lock already differs")
            return 1
        METHOD_LOCK_PATH.write_bytes(expected)
    elif not METHOD_LOCK_PATH.is_file() or METHOD_LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F5 method lock is missing or stale")
        return 1
    print("PHASE-04-F5 method lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
