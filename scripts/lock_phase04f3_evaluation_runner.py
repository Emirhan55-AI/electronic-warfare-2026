#!/usr/bin/env python3
"""Lock the PHASE-04-F3D evaluator and one-shot orchestration before reveal."""

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

from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
LOCK_PATH = FIXTURES / "evaluation-runner-lock-v4.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
SOURCES = (
    "algorithms/parameters/f3_evaluation.py",
    "scripts/reveal_phase04f3_seeds.py",
    "scripts/run_phase04f3_evaluation.py",
    "scripts/verify_phase04f3_evaluation.py",
    "scripts/lock_phase04f3_evaluation_runner.py",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def verify_runner_lock(document: dict[str, Any] | None = None) -> bool:
    lock = document or _load(LOCK_PATH)
    return (
        lock.get("status") == "locked-before-seed-reveal"
        and all(sha256_file(ROOT / item["path"]) == item["sha256"] for item in lock["source_manifest"]["sources"])
        and lock.get("method_lock_sha256") == sha256_file(FIXTURES / "method-lock-v4.json")
        and lock.get("protocol_lock_sha256") == sha256_file(FIXTURES / "protocol-lock.json")
        and lock.get("acceptance_gates_sha256") == sha256_file(FIXTURES / "acceptance-gates.json")
        and lock.get("base_acceptance_gates_sha256")
        == sha256_file(ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json")
        and lock.get("evaluation_commitments_sha256") == sha256_file(FIXTURES / "evaluation-commitments.json")
    )


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("F3 evaluation seeds were revealed before runner lock")
    method_lock = _load(FIXTURES / "method-lock-v4.json")
    if method_lock.get("status") != "locked-before-seed-reveal":
        raise RuntimeError("F3C method lock is missing")
    sources = [{"path": path, "sha256": sha256_file(ROOT / path)} for path in SOURCES]
    source_manifest = {"schema_version": 1, "sources": sources}
    source_manifest_sha256 = hashlib.sha256(canonical_json_bytes(source_manifest)).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f3-evaluation-runner-lock-v4",
        "status": "locked-before-seed-reveal",
        "method_lock_sha256": sha256_file(FIXTURES / "method-lock-v4.json"),
        "protocol_lock_sha256": sha256_file(FIXTURES / "protocol-lock.json"),
        "acceptance_gates_sha256": sha256_file(FIXTURES / "acceptance-gates.json"),
        "base_acceptance_gates_sha256": sha256_file(
            ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
        ),
        "evaluation_commitments_sha256": sha256_file(FIXTURES / "evaluation-commitments.json"),
        "source_manifest": source_manifest,
        "source_manifest_sha256": source_manifest_sha256,
        "execution_order": ["runner-lock", "commit-and-push", "seed-reveal", "binding", "oos", "verification"],
        "clean_synced_head_required_for_reveal": True,
        "rerun_after_started_allowed": False,
        "threshold_changes_after_reveal_allowed": False,
        "claim_boundary": "Çalıştırıcı ve skor dönüşümü seed reveal öncesinde kilitlenmiştir; değerlendirme sonucu değildir.",
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "evaluation_runner_lock_sha256": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = canonical_json_bytes(build_lock())
    if args.write:
        if LOCK_PATH.exists() and LOCK_PATH.read_bytes() != expected:
            print("PHASE-04-F3 evaluation runner lock already differs")
            return 1
        LOCK_PATH.write_bytes(expected)
    elif not LOCK_PATH.is_file() or LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F3 evaluation runner lock is missing or stale")
        return 1
    print("PHASE-04-F3 evaluation runner lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
