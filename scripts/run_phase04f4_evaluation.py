#!/usr/bin/env python3
"""Run the one-shot PHASE-04-F4 binding and OOS populations."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f4_evaluation import compare_results, evaluate_population
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from scripts.lock_phase04f4_evaluation_runner import verify_runner_lock
from scripts.reveal_phase04f4_seeds import REVEAL_PATH, RUNNER_LOCK_PATH, verify_reveal


EVIDENCE = ROOT / "results" / "evidence" / "phase04f4"
STARTED_PATH = EVIDENCE / "f4d-run-started.json"
BINDING_PATH = EVIDENCE / "binding-results-v5.json"
OOS_PATH = EVIDENCE / "oos-results-v5.json"
COMPARISON_PATH = EVIDENCE / "parameter-comparison-v5.json"
FAILURE_PATH = EVIDENCE / "f4d-run-failure.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _write(path: Path, document: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(document))


def main() -> int:
    owned = (STARTED_PATH, BINDING_PATH, OOS_PATH, COMPARISON_PATH, FAILURE_PATH)
    if any(path.exists() for path in owned):
        print("PHASE-04-F4D one-shot evaluation was already started")
        return 1
    if not REVEAL_PATH.is_file() or not RUNNER_LOCK_PATH.is_file():
        print("revealed seeds or runner lock is missing")
        return 1
    reveal = _load(REVEAL_PATH)
    if not verify_reveal(reveal) or not verify_runner_lock():
        print("revealed seeds or runner sources do not match their locks")
        return 1
    seeds = {item["role"]: int(item["seed"]) for item in reveal["seeds"]}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    started = {
        "schema_version": 1,
        "run_id": "phase04f4-one-shot-binding-oos-v1",
        "status": "started",
        "head_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout.strip(),
        "runner_lock_sha256": sha256_file(RUNNER_LOCK_PATH),
        "method_lock_sha256": sha256_file(ROOT / "datasets" / "fixtures" / "phase04f4" / "method-lock-v5.json"),
        "evaluation_seeds_sha256": sha256_file(REVEAL_PATH),
        "threshold_changes_allowed": False,
        "rerun_allowed": False,
    }
    _write(STARTED_PATH, started)
    try:
        binding = evaluate_population("binding", seeds["binding"])
        _write(BINDING_PATH, binding)
        oos = evaluate_population("oos", seeds["oos"])
        _write(OOS_PATH, oos)
        comparison = compare_results(binding, oos)
        _write(COMPARISON_PATH, comparison)
    except Exception as exc:
        _write(FAILURE_PATH, {
            "schema_version": 1,
            "status": "infrastructure_failure",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "rerun_allowed": False,
        })
        raise
    print(f"PHASE-04-F4D evaluation completed: {comparison['status']}")
    return 0 if comparison["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
