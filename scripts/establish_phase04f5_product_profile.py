#!/usr/bin/env python3
"""Establish or verify the digest-bound PHASE-04-F5 host product profile."""

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

from algorithms.parameters.f5_estimator import F5ParameterEstimator
from algorithms.parameters.f5_evaluation import compare_results
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.verify_phase04f5_evaluation import build_summary


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
EVIDENCE = ROOT / "results" / "evidence" / "phase04f5"
PROFILE_PATH = ROOT / "profiles" / "phase04f5" / "operation-default.json"
METHOD_LOCK_PATH = FIXTURES / "method-lock-v6.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
BINDING_PATH = EVIDENCE / "binding-results-v6.json"
OOS_PATH = EVIDENCE / "oos-results-v6.json"
COMPARISON_PATH = EVIDENCE / "parameter-comparison-v6.json"
F5D_VERIFICATION_PATH = EVIDENCE / "f5d-verification.json"
DOMAIN_MODEL_PATHS = (
    "datasets/fixtures/phase04f1/domain-model.json",
    "datasets/fixtures/phase04f2/domain-model-v3.json",
    "datasets/fixtures/phase04f4/domain-model-v5.json",
)

VALIDATED_FIELDS = (
    "emission_center_frequency",
    "carrier_line_frequency",
    "occupied_bandwidth",
    "uncalibrated_channel_power_dbfs",
    "snr_estimate_db",
    "signal_domain",
)
RUNTIME_SOURCES = (
    "algorithms/parameters/models.py",
    "algorithms/parameters/operator_assisted.py",
    "algorithms/parameters/operator_classification.py",
    "algorithms/parameters/operator_reference.py",
    "algorithms/parameters/f1_domain.py",
    "algorithms/parameters/f1_estimator.py",
    "algorithms/parameters/f2_domain.py",
    "algorithms/parameters/f2_estimator.py",
    "algorithms/parameters/f3_domain.py",
    "algorithms/parameters/f3_estimator.py",
    "algorithms/parameters/f4_domain.py",
    "algorithms/parameters/f4_estimator.py",
    "algorithms/parameters/f5_estimator.py",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _runtime_manifest() -> dict[str, Any]:
    sources = [{"path": path, "sha256": sha256_file(ROOT / path)} for path in RUNTIME_SOURCES]
    models = [
        {"source_path": path, "package_path": path, "sha256": sha256_file(ROOT / path)}
        for path in DOMAIN_MODEL_PATHS
    ]
    identity = {"schema_version": 1, "sources": sources, "runtime_models": models}
    return {**identity, "sha256": hashlib.sha256(canonical_json_bytes(identity)).hexdigest()}


def _verify_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    method_lock = _load(METHOD_LOCK_PATH)
    binding = _load(BINDING_PATH)
    oos = _load(OOS_PATH)
    comparison = _load(COMPARISON_PATH)
    stored_summary = _load(F5D_VERIFICATION_PATH)

    if stored_summary != build_summary() or stored_summary.get("status") != "passed":
        raise RuntimeError("F5D evidence integrity is not passed")
    if stored_summary.get("evaluation_status") != "passed":
        raise RuntimeError("F5D evaluation did not pass")
    if binding.get("status") != "passed" or oos.get("status") != "passed":
        raise RuntimeError("binding and OOS must both pass")
    if len(binding.get("scoring", {}).get("checks", ())) != 40:
        raise RuntimeError("binding check coverage is incomplete")
    if len(oos.get("scoring", {}).get("checks", ())) != 24:
        raise RuntimeError("OOS check coverage is incomplete")
    if comparison != compare_results(binding, oos) or comparison.get("status") != "passed":
        raise RuntimeError("stored F5 comparison is not reproducible")

    decisions = comparison.get("field_decisions", ())
    decision_fields = tuple(item.get("field") for item in decisions if item.get("status") == "passed")
    if decision_fields != (*VALIDATED_FIELDS, "span_robustness"):
        raise RuntimeError("all required F5 fields and span robustness must pass")
    if method_lock.get("status") != "locked-before-seed-reveal":
        raise RuntimeError("F5 method lock is not valid")
    if method_lock.get("methods") != F5ParameterEstimator.METHOD_IDS:
        raise RuntimeError("runtime F5 methods differ from the locked methods")
    for item in method_lock.get("implementation", {}).get("sources", ()):
        if sha256_file(ROOT / str(item["path"])) != item.get("sha256"):
            raise RuntimeError(f"locked implementation changed: {item['path']}")
    identity = {key: value for key, value in method_lock.items() if key != "method_lock_sha256"}
    if hashlib.sha256(canonical_json_bytes(identity)).hexdigest() != method_lock.get("method_lock_sha256"):
        raise RuntimeError("F5 method lock identity is invalid")
    return method_lock, binding, oos, comparison


def build_profile() -> dict[str, Any]:
    method_lock, _, _, comparison = _verify_inputs()
    evidence = {
        "method_lock_sha256": sha256_file(METHOD_LOCK_PATH),
        "acceptance_contract_sha256": sha256_file(ACCEPTANCE_PATH),
        "base_acceptance_contract_sha256": sha256_file(BASE_ACCEPTANCE_PATH),
        "binding_results_sha256": sha256_file(BINDING_PATH),
        "oos_results_sha256": sha256_file(OOS_PATH),
        "comparison_sha256": sha256_file(COMPARISON_PATH),
        "f5d_verification_sha256": sha256_file(F5D_VERIFICATION_PATH),
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "profile_id": "phase04f5-operator-assisted-parameters-v6",
        "status": "validated",
        "validated_fields": list(VALIDATED_FIELDS),
        "span_robustness_validated": True,
        "operator_confirmed_span_required": True,
        "automatic_span_validated": False,
        "methods": method_lock["methods"],
        "runtime_constraints": {
            "frames_per_measurement": 4,
            "frame_length": 4096,
            "worker_count": 1,
            "maximum_pending_intent_count": 1,
            "maximum_persistent_payload_bytes": 65_536,
        },
        "evidence": evidence,
        "runtime_implementation": _runtime_manifest(),
        "claim_boundary": (
            "Bu profil yalnız operatörce onaylanan izole analiz aralığında, dört ardışık kare üzerinde "
            "çalışan host F5 kestirimcisini etkinleştirir. FPGA, canlı RF doğruluğu, dBm kalibrasyonu veya "
            "saha başarı iddiası değildir."
        ),
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "profile_identity_sha256": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = canonical_json_bytes(build_profile())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PHASE-04-F5E profile input rejected: {exc}")
        return 1
    if args.write:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_bytes(expected)
    elif not PROFILE_PATH.is_file() or PROFILE_PATH.read_bytes() != expected:
        print("PHASE-04-F5E product profile is missing or stale")
        return 1
    print("PHASE-04-F5E product profile: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
