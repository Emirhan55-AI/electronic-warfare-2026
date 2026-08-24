#!/usr/bin/env python3
"""Verify the stored PHASE-04-F1D one-shot evidence without rerunning it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.reveal_phase04f1_seeds import REVEAL_PATH, RUNNER_LOCK_PATH, verify_reveal
from scripts.run_phase04f1_evaluation import BINDING_PATH, COMPARISON_PATH, OOS_PATH, STARTED_PATH


SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f1" / "f1d-verification.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def build_summary() -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    reveal = _load(REVEAL_PATH)
    checks.append({"id": "seed-commitments", "status": "passed" if verify_reveal(reveal) else "failed"})
    started = _load(STARTED_PATH)
    ordering_ok = (
        started.get("status") == "started"
        and started.get("runner_lock_sha256") == sha256_file(RUNNER_LOCK_PATH)
        and started.get("evaluation_seeds_sha256") == sha256_file(REVEAL_PATH)
        and started.get("threshold_changes_allowed") is False
    )
    checks.append({"id": "one-shot-ordering", "status": "passed" if ordering_ok else "failed"})
    binding = _load(BINDING_PATH)
    oos = _load(OOS_PATH)
    comparison = _load(COMPARISON_PATH)
    population_ok = (
        binding.get("role") == "binding"
        and binding.get("population_trial_count") == 128
        and oos.get("role") == "oos"
        and oos.get("population_trial_count") == 32
    )
    checks.append({"id": "population-counts", "status": "passed" if population_ok else "failed"})
    required = {
        "emission_center_frequency",
        "carrier_line_frequency",
        "occupied_bandwidth",
        "span_robustness",
        "uncalibrated_channel_power_dbfs",
        "snr_estimate_db",
        "signal_domain",
    }
    fields_ok = set(binding.get("field_decisions", {})) == required and set(oos.get("field_decisions", {})) == required
    checks.append({"id": "field-coverage", "status": "passed" if fields_ok else "failed"})
    comparison_ok = comparison.get("status") in {"passed", "failed"} and len(comparison.get("field_decisions", ())) == 7
    checks.append({"id": "comparison-complete", "status": "passed" if comparison_ok else "failed"})
    evidence_hashes = {
        "run_started_sha256": sha256_file(STARTED_PATH),
        "binding_results_sha256": sha256_file(BINDING_PATH),
        "oos_results_sha256": sha256_file(OOS_PATH),
        "comparison_sha256": sha256_file(COMPARISON_PATH),
    }
    integrity_ok = all(len(value) == 64 for value in evidence_hashes.values())
    checks.append({"id": "evidence-digests", "status": "passed" if integrity_ok else "failed"})
    passed = all(item["status"] == "passed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-04-F1D",
        "status": "passed" if passed else "failed",
        "evaluation_status": comparison.get("status"),
        "checks": checks,
        "evidence": evidence_hashes,
        "claim_boundary": "Kanıt bütünlüğü sonucu değerlendirme alanlarının geçtiği anlamına gelmez; evaluation_status ayrı karardır.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = build_summary()
    payload = canonical_json_bytes(summary)
    if args.write:
        SUMMARY_PATH.write_bytes(payload)
    elif not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_bytes() != payload:
        print("PHASE-04-F1D verification evidence is missing or stale")
        return 1
    print(f"PHASE-04-F1D evidence: {summary['status']}; evaluation: {summary['evaluation_status']}")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
