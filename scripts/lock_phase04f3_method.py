#!/usr/bin/env python3
"""Lock the PHASE-04-F3 v4 method and open-development evidence before reveal."""

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

from algorithms.parameters.f3_estimator import F3ParameterEstimator, PERSISTENT_PAYLOAD_BYTES
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.lock_phase04f3_protocol import INPUTS, PROTECTED_INPUTS


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
METHOD_LOCK_PATH = FIXTURES / "method-lock-v4.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
DOMAIN_MODEL_PATH = FIXTURES / "domain-model-v4.json"
EVIDENCE = ROOT / "results" / "evidence" / "phase04f3"
DEVELOPMENT_RESULT_PATH = EVIDENCE / "development-results-v4.json"
CARRIER_RESULT_PATH = EVIDENCE / "carrier-analysis-v4.json"
IMPLEMENTATION_PATHS = (
    "algorithms/parameters/f3_estimator.py",
    "algorithms/parameters/f3_domain.py",
    "algorithms/parameters/f3_development.py",
    "scripts/develop_phase04f3_carrier.py",
    "scripts/develop_phase04f3_domain.py",
    "scripts/verify_phase04f3_development.py",
    "scripts/lock_phase04f3_method.py",
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
    if any(sha256_file(ROOT / path) != protocol["inputs"][path] for path in INPUTS):
        raise RuntimeError("F3 protocol input changed after the pre-method lock")
    if any(
        sha256_file(ROOT / path) != protocol["protected_historical_inputs"][path]
        for path in PROTECTED_INPUTS
    ):
        raise RuntimeError("protected F1/F2 evidence changed during F3C")
    return protocol


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("F3 evaluation seeds were revealed before the v4 method lock")
    protocol = _verify_protocol_lock()
    development = _load(DEVELOPMENT_RESULT_PATH)
    carrier = _load(CARRIER_RESULT_PATH)
    model = _load(DOMAIN_MODEL_PATH)
    if development.get("status") != "passed" or development.get("role") != "development-only":
        raise RuntimeError("the complete F3 open-development gates have not passed")
    if carrier.get("status") != "passed" or carrier.get("role") != "development-only":
        raise RuntimeError("the F3 carrier analysis is incomplete")
    if model.get("status") != "development-only" or model.get("persistent_numeric_bytes", 65_537) > 65_536:
        raise RuntimeError("the v4 domain model is not bounded development evidence")
    selected = carrier["selected"]
    expected_carrier = {
        "minimum_prominence_db": F3ParameterEstimator.CARRIER_PROMINENCE_DB_MINIMUM_V4,
        "minimum_share": F3ParameterEstimator.CARRIER_SHARE_MINIMUM_V4,
        "minimum_frame_prominence_db": F3ParameterEstimator.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4,
        "artifact_spectral_entropy_minimum": F3ParameterEstimator.CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4,
        "artifact_envelope_skewness_maximum": F3ParameterEstimator.CARRIER_ARTIFACT_ENVELOPE_SKEWNESS_MAXIMUM_V4,
    }
    if any(not _isclose(float(selected[name]), float(value)) for name, value in expected_carrier.items()):
        raise RuntimeError("carrier analysis and estimator constants differ")
    if PERSISTENT_PAYLOAD_BYTES > 65_536:
        raise RuntimeError("combined v4 persistent payload exceeds the memory bound")
    manifest = implementation_manifest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f3-method-lock-v4",
        "status": "locked-before-seed-reveal",
        "methods": F3ParameterEstimator.METHOD_IDS,
        "constants": {
            "required_frames": 4,
            "frame_length": 4096,
            "maximum_persistent_payload_bytes": 65_536,
            "combined_persistent_payload_bytes": PERSISTENT_PAYLOAD_BYTES,
            "domain_model_numeric_bytes": model["persistent_numeric_bytes"],
            "corrected_detection_significance_minimum": F3ParameterEstimator.CORRECTED_DETECTION_SIGNIFICANCE_MINIMUM,
            "low_snr_abstention_db": F3ParameterEstimator.LOW_SNR_ABSTENTION_DB,
            "obw_temporal_range_maximum_bins": F3ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM,
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
            "implementation_manifest_sha256": manifest["sha256"],
        },
        "implementation": manifest,
        "seed_revealed": False,
        "claim_boundary": "Yöntem yalnız açık F3 geliştirme kanıtından sonra ve binding/OOS seed reveal öncesinde kilitlenmiştir; ürün veya PHASE-04 başarı kararı değildir.",
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "method_lock_sha256": identity}


def _isclose(left: float, right: float) -> bool:
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
            print("PHASE-04-F3 method lock already differs")
            return 1
        METHOD_LOCK_PATH.write_bytes(expected)
    elif not METHOD_LOCK_PATH.is_file() or METHOD_LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F3 method lock is missing or stale")
        return 1
    print("PHASE-04-F3 method lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
