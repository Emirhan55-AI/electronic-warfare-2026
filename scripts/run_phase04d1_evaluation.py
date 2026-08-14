#!/usr/bin/env python3
"""Run the only PHASE-04-D1F binding and locked OOS evaluation."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.obw99_evaluation import (
    CLEAN_REFERENCE_PATH,
    COMPARISON_ID,
    EVALUATION_LOCK_PATH,
    METHOD_LOCK_PATH,
    evaluate_population,
    evidence_hash,
    verify_evaluation_lock,
)
from reference.parameters.obw99_reference import canonical_json_bytes, load_json, sha256_file


EVIDENCE = ROOT / "results" / "evidence" / "phase04d1"
FILES = {
    "comparison": EVIDENCE / "obw99-comparison.json",
    "binding": EVIDENCE / "obw99-binding-results.json",
    "oos": EVIDENCE / "obw99-oos-results.json",
    "golden": EVIDENCE / "golden-obw99.json",
    "summary": EVIDENCE / "verification-summary.json",
}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(payload))
    os.replace(temporary, path)


def _base(role: str, lock_sha: str, method_identity: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "PHASE-04-D1F",
        "role": role,
        "comparison_id": COMPARISON_ID,
        "evaluation_lock_sha256": lock_sha,
        "method_lock_identity": method_identity,
    }


def _failure_list(binding: dict[str, Any], oos: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": role, **gate}
        for role, result in (("binding", binding), ("oos", oos))
        for gate in result["gate_results"]
        if gate["status"] == "failed"
    ]


def _write_results(binding: dict[str, Any], oos: dict[str, Any], lock_sha: str, method_identity: str) -> bool:
    binding_doc = {**_base("binding", lock_sha, method_identity), **binding}
    oos_doc = {**_base("oos", lock_sha, method_identity), **oos}
    failures = _failure_list(binding, oos)
    passed = binding["status"] == "passed" and oos["status"] == "passed" and not failures
    comparison = {
        **_base("comparison", lock_sha, method_identity),
        "status": "passed" if passed else "failed",
        "binding_status": binding["status"],
        "oos_status": oos["status"],
        "capability_candidate": passed,
        "failed_gates": failures,
        "universal_signal_support_claimed": False,
        "live_hackrf_performance_claimed": False,
        "full_source_hashed": False,
    }
    clean = load_json(CLEAN_REFERENCE_PATH)
    golden = {
        **_base("golden", lock_sha, method_identity),
        "status": clean["status"],
        "clean_reference_sha256": sha256_file(CLEAN_REFERENCE_PATH),
        "measurement": clean["measurement"],
        "sample_rate_hz": clean["sample_rate_hz"],
        "fft_length": clean["fft_length"],
        "occupied_power_fraction": clean["occupied_power_fraction"],
        "families": clean["families"],
    }
    hashes = {
        "binding_results_sha256": evidence_hash(binding_doc),
        "oos_results_sha256": evidence_hash(oos_doc),
        "comparison_sha256": evidence_hash(comparison),
        "golden_sha256": evidence_hash(golden),
    }
    summary = {
        **_base("verification-summary", lock_sha, method_identity),
        "status": "passed" if passed else "failed",
        "failure_class": None if passed else "algorithmic_failed",
        "binding_status": binding["status"],
        "oos_status": oos["status"],
        "capability_candidate": passed,
        "failed_gate_count": len(failures),
        "artifact_hashes": hashes,
        "protected_evidence_modified": False,
        "phase04_profile_created": False,
        "universal_signal_support_claimed": False,
        "live_hackrf_performance_claimed": False,
        "full_source_hashed": False,
    }
    for key, document in (("binding", binding_doc), ("oos", oos_doc), ("comparison", comparison), ("golden", golden), ("summary", summary)):
        _atomic_write(FILES[key], document)
    return passed


def _write_infrastructure_failure(code: str, lock_sha: str, method_identity: str) -> None:
    common = {
        "status": "failed",
        "failure_class": "infrastructure_failed",
        "error_code": code,
        "capability_candidate": False,
        "universal_signal_support_claimed": False,
        "live_hackrf_performance_claimed": False,
        "full_source_hashed": False,
    }
    for key in ("binding", "oos", "comparison", "golden"):
        _atomic_write(FILES[key], {**_base(key, lock_sha, method_identity), **common})
    _atomic_write(FILES["summary"], {**_base("verification-summary", lock_sha, method_identity), **common})


def main() -> int:
    if any(path.exists() for path in FILES.values()):
        print("D1F evidence already exists; rerun is forbidden", file=sys.stderr)
        return 3
    evaluation_lock = load_json(EVALUATION_LOCK_PATH)
    method_lock = load_json(METHOD_LOCK_PATH)
    lock_sha = sha256_file(EVALUATION_LOCK_PATH)
    method_identity = str(method_lock["identity_sha256"])
    try:
        verify_evaluation_lock(evaluation_lock)
        binding = evaluate_population("binding")
        oos = evaluate_population("oos")
        passed = _write_results(binding, oos, lock_sha, method_identity)
        print("D1F evaluation completed: " + ("passed" if passed else "algorithmic_failed"))
        return 0 if passed else 1
    except Exception as exc:
        _write_infrastructure_failure(type(exc).__name__, lock_sha, method_identity)
        print("D1F infrastructure failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
