#!/usr/bin/env python3
"""Lock the F2 protocol, scorer and commitments before v3 development."""

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

from verification.phase04f2_scoring import validate_acceptance


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f2"
LOCK_PATH = FIXTURES / "protocol-lock.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
INPUTS = (
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f2/development-catalog.json",
    "datasets/fixtures/phase04f2/evaluation-commitments.json",
    "docs/interfaces/PHASE04_F2_PARAMETER_CONTRACT.md",
    "docs/plans/PHASE04_F2_RECOVERY_PLAN.md",
    "results/evidence/phase04f2/f2a-analysis.json",
    "verification/phase04f2_scoring.py",
    "scripts/prepare_phase04f2_protocol.py",
    "scripts/lock_phase04f2_protocol.py",
    "scripts/verify_phase04f2_protocol.py",
    "algorithms/parameters/scenes.py",
    "algorithms/spectrum/dsp.py",
    "profiles/phase03/operation-default.json",
)
F1_PROTECTED = (
    "datasets/fixtures/phase04f1/method-lock.json",
    "datasets/fixtures/phase04f1/evaluation-runner-lock.json",
    "results/evidence/phase04f1/binding-results.json",
    "results/evidence/phase04f1/oos-results.json",
    "results/evidence/phase04f1/parameter-comparison.json",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def build_lock() -> dict[str, Any]:
    if REVEAL_PATH.exists():
        raise RuntimeError("F2 evaluation seeds were revealed before protocol lock")
    if any((ROOT / "algorithms" / "parameters").glob("f2_*.py")):
        raise RuntimeError("F2 method source exists before protocol lock")
    acceptance = _load(FIXTURES / "acceptance-gates.json")
    coverage = validate_acceptance(acceptance)
    if coverage["status"] != "passed":
        raise RuntimeError("F2 acceptance coverage is incomplete")
    inputs = {path: _sha256(ROOT / path) for path in INPUTS}
    protected = {path: _sha256(ROOT / path) for path in F1_PROTECTED}
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f2-evaluation-protocol-lock-v1",
        "status": "locked-before-v3-method-development",
        "inputs": inputs,
        "f1_protected_inputs": protected,
        "required_parameter_fields": acceptance["required_parameter_fields"],
        "required_support_gates": acceptance["required_support_gates"],
        "scoring_coverage": coverage,
        "evaluation_order": [
            "protocol-lock",
            "v3-development",
            "method-lock",
            "runner-lock",
            "commit-and-push",
            "seed-reveal",
            "binding",
            "oos",
            "profile-binding",
        ],
        "runtime_ground_truth_allowed": False,
        "f1_revealed_populations_allowed_for_tuning": False,
        "threshold_changes_after_method_development_allowed": False,
        "claim_boundary": "F2 protokol, scorer ve commitment kilididir; yöntem, değerlendirme veya ürün başarısı değildir.",
    }
    identity = hashlib.sha256(_canonical(payload)).hexdigest()
    return {**payload, "protocol_lock_sha256": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = _canonical(build_lock())
    if args.write:
        if LOCK_PATH.exists() and LOCK_PATH.read_bytes() != expected:
            print("PHASE-04-F2 protocol lock already differs")
            return 1
        LOCK_PATH.write_bytes(expected)
    elif not LOCK_PATH.is_file() or LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F2 protocol lock is missing or stale")
        return 1
    print("PHASE-04-F2 protocol lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
