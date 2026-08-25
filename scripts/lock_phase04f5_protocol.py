#!/usr/bin/env python3
"""Lock the F5 protocol, scorer and commitments before v6 development."""

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

from verification.phase04f5_scoring import validate_acceptance


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
LOCK_PATH = FIXTURES / "protocol-lock.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
INPUTS = (
    "datasets/fixtures/phase04f5/acceptance-gates.json",
    "datasets/fixtures/phase04f5/development-catalog.json",
    "datasets/fixtures/phase04f5/evaluation-commitments.json",
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f3/acceptance-gates.json",
    "datasets/fixtures/phase04f4/acceptance-gates.json",
    "results/evidence/phase04f5/f5a-analysis.json",
    "verification/phase04f5_analysis.py",
    "verification/phase04f5_scoring.py",
    "scripts/verify_phase04f5a.py",
    "scripts/prepare_phase04f5_protocol.py",
    "scripts/lock_phase04f5_protocol.py",
    "scripts/verify_phase04f5_protocol.py",
    "algorithms/parameters/scenes.py",
    "algorithms/spectrum/dsp.py",
    "profiles/phase03/operation-default.json",
)
PROTECTED_INPUTS = (
    "datasets/fixtures/phase04f4/protocol-lock.json",
    "datasets/fixtures/phase04f4/method-lock-v5.json",
    "datasets/fixtures/phase04f4/evaluation-runner-lock-v5.json",
    "datasets/fixtures/phase04f4/evaluation-seeds.json",
    "datasets/fixtures/phase04f4/domain-model-v5.json",
    "results/evidence/phase04f4/development-results-v5.json",
    "results/evidence/phase04f4/binding-results-v5.json",
    "results/evidence/phase04f4/oos-results-v5.json",
    "results/evidence/phase04f4/parameter-comparison-v5.json",
    "results/evidence/phase04f4/f4d-verification.json",
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


def _method_sources_exist() -> bool:
    return any((ROOT / "algorithms" / "parameters").glob("f5_*.py"))


def build_lock() -> dict[str, Any]:
    acceptance = _load(FIXTURES / "acceptance-gates.json")
    base = _load(ROOT / acceptance["base_acceptance"]["path"])
    f3 = _load(ROOT / acceptance["f3_development_acceptance"]["path"])
    f4 = _load(ROOT / acceptance["f4_development_acceptance"]["path"])
    coverage = validate_acceptance(acceptance, f4, f3, base)
    if coverage["status"] != "passed":
        raise RuntimeError(f"F5 acceptance coverage is incomplete: {coverage['problems']}")
    for key in ("base_acceptance", "f3_development_acceptance", "f4_development_acceptance", "f5a_analysis"):
        item = acceptance[key]
        if _sha256(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"{key} digest differs")
    inputs = {path: _sha256(ROOT / path) for path in INPUTS}
    protected = {path: _sha256(ROOT / path) for path in PROTECTED_INPUTS}
    payload: dict[str, Any] = {
        "schema_version": 1,
        "lock_id": "phase04f5-evaluation-protocol-lock-v1",
        "status": "locked-before-v6-method-development",
        "inputs": inputs,
        "protected_historical_inputs": protected,
        "scoring_coverage": coverage,
        "evaluation_order": [
            "protocol-lock", "v6-development", "method-lock", "runner-lock", "commit-and-push",
            "seed-reveal", "binding", "oos", "profile-binding",
        ],
        "runtime_ground_truth_allowed": False,
        "f1_f2_f3_f4_populations_allowed_for_tuning": False,
        "threshold_changes_after_method_development_allowed": False,
        "claim_boundary": "F5 protokol, scorer ve commitment kilididir; yöntem, değerlendirme, FPGA entegrasyonu veya ürün başarısı değildir.",
    }
    identity = hashlib.sha256(_canonical(payload)).hexdigest()
    return {**payload, "protocol_lock_sha256": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write and (REVEAL_PATH.exists() or _method_sources_exist()):
        print("PHASE-04-F5 protocol must be locked before seed reveal and v6 sources")
        return 1
    expected = _canonical(build_lock())
    if args.write:
        if LOCK_PATH.exists() and LOCK_PATH.read_bytes() != expected:
            print("PHASE-04-F5 protocol lock already differs")
            return 1
        LOCK_PATH.write_bytes(expected)
    elif not LOCK_PATH.is_file() or LOCK_PATH.read_bytes() != expected:
        print("PHASE-04-F5 protocol lock is missing or stale")
        return 1
    print("PHASE-04-F5 protocol lock: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
