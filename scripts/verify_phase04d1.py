#!/usr/bin/env python3
"""Read-only verification of PHASE-04-D1F locks, evidence, and decisions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.obw99_evaluation import EVALUATION_LOCK_PATH, evidence_hash, verify_evaluation_lock
from reference.parameters.obw99_reference import load_json, sha256_file
from scripts.run_phase04d1_evaluation import FILES


def verify() -> list[str]:
    failures: list[str] = []
    try:
        lock = load_json(EVALUATION_LOCK_PATH)
        verify_evaluation_lock(lock)
    except (OSError, ValueError, KeyError) as exc:
        return [f"evaluation-lock:{type(exc).__name__}"]
    if not all(path.is_file() for path in FILES.values()):
        return ["evidence:missing"]
    documents = {key: load_json(path) for key, path in FILES.items()}
    lock_sha = sha256_file(EVALUATION_LOCK_PATH)
    method_identity = lock["method_lock_identity"]
    for key, document in documents.items():
        if document.get("evaluation_lock_sha256") != lock_sha:
            failures.append(f"{key}:evaluation-lock-sha")
        if document.get("method_lock_identity") != method_identity:
            failures.append(f"{key}:method-lock-identity")
        if document.get("comparison_id") != lock["comparison_id"]:
            failures.append(f"{key}:comparison-id")
    summary = documents["summary"]
    expected_hashes = {
        "binding_results_sha256": evidence_hash(documents["binding"]),
        "oos_results_sha256": evidence_hash(documents["oos"]),
        "comparison_sha256": evidence_hash(documents["comparison"]),
        "golden_sha256": evidence_hash(documents["golden"]),
    }
    if summary.get("failure_class") == "infrastructure_failed":
        return failures
    if summary.get("artifact_hashes") != expected_hashes:
        failures.append("summary:artifact-hashes")
    binding_status = documents["binding"].get("status")
    oos_status = documents["oos"].get("status")
    passed = binding_status == "passed" and oos_status == "passed"
    if documents["comparison"].get("capability_candidate") is not passed:
        failures.append("comparison:capability-decision")
    if summary.get("capability_candidate") is not passed:
        failures.append("summary:capability-decision")
    if any(document.get("universal_signal_support_claimed") is not False for document in (documents["comparison"], summary)):
        failures.append("claims:universal")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    failures = verify()
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("PHASE-04-D1F verification check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
