#!/usr/bin/env python3
"""Write or verify the pre-method PHASE-04-F3B protocol evidence."""

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

from scripts.lock_phase04f3_protocol import (
    INPUTS,
    LOCK_PATH,
    PROTECTED_INPUTS,
    REVEAL_PATH,
    _method_sources_exist,
    build_lock,
)
from scripts.prepare_phase04f3_protocol import COMMITMENTS_PATH, SEALED_PATH, verify_preimages
from verification.phase04f3_scoring import validate_acceptance


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f3" / "f3b-verification.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _historical_seeds() -> set[int]:
    seeds = {20261010}
    for path in (
        ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-seeds.json",
        ROOT / "datasets" / "fixtures" / "phase04f2" / "evaluation-seeds.json",
    ):
        seeds.update(int(item["seed"]) for item in _load(path)["seeds"])
    f2_development = _load(ROOT / "datasets" / "fixtures" / "phase04f2" / "development-catalog.json")
    seeds.update(int(value) for value in f2_development["common"]["development_seeds"])
    return seeds


def build_summary() -> dict[str, Any]:
    acceptance = _load(FIXTURES / "acceptance-gates.json")
    base_acceptance = _load(ROOT / acceptance["base_acceptance"]["path"])
    development = _load(FIXTURES / "development-catalog.json")
    commitments = _load(COMMITMENTS_PATH)
    stored_lock = _load(LOCK_PATH)
    checks: list[dict[str, str]] = []

    lock_ok = stored_lock == build_lock()
    checks.append({"id": "protocol-lock", "status": "passed" if lock_ok else "failed"})
    input_ok = all(_sha256(ROOT / path) == stored_lock["inputs"][path] for path in INPUTS)
    checks.append({"id": "input-digests", "status": "passed" if input_ok else "failed"})
    protected_ok = all(
        _sha256(ROOT / path) == stored_lock["protected_historical_inputs"][path]
        for path in PROTECTED_INPUTS
    )
    checks.append({"id": "historical-evidence-immutability", "status": "passed" if protected_ok else "failed"})

    coverage = validate_acceptance(acceptance, base_acceptance)
    coverage_ok = (
        coverage["status"] == "passed"
        and coverage["base_check_counts"] == {"binding": 40, "oos": 24}
        and coverage["development_check_count"] == 14
        and _sha256(ROOT / acceptance["base_acceptance"]["path"]) == acceptance["base_acceptance"]["sha256"]
    )
    checks.append({"id": "executable-gate-coverage", "status": "passed" if coverage_ok else "failed"})

    common = development.get("common", {})
    public_seeds = [int(value) for value in common.get("development_seeds", ())]
    development_ok = (
        development.get("role") == "development-only"
        and len(public_seeds) == 8
        and len(set(public_seeds)) == 8
        and common.get("trials_per_seed_per_family") == 48
        and common.get("total_trials_per_family") == 384
        and common.get("frames_per_measurement") == 4
        and common.get("total_negative_control_measurements") == 512
        and development.get("data_separation", {}).get("f1_open_or_revealed_populations_allowed_for_tuning") is False
        and development.get("data_separation", {}).get("f2_open_or_revealed_populations_allowed_for_tuning") is False
    )
    checks.append({"id": "open-development-partition", "status": "passed" if development_ok else "failed"})
    separation_ok = not _historical_seeds().intersection(public_seeds)
    checks.append({"id": "f1-f2-populations-excluded", "status": "passed" if separation_ok else "failed"})

    population_by_role = {item["role"]: item for item in commitments.get("populations", ())}
    commitment_ok = (
        commitments.get("status") == "committed-before-v4-method-development"
        and set(population_by_role) == {"binding", "oos"}
        and all(
            len(item.get("seed_commitment_sha256", "")) == 64
            and item["trials_per_family"] == base_acceptance["population_contract"][role]["trials_per_family"]
            and item["noise_measurements"] == base_acceptance["population_contract"][role]["noise_measurements"]
            and item["frames_per_measurement"] == 4
            for role, item in population_by_role.items()
        )
        and not REVEAL_PATH.exists()
    )
    checks.append({"id": "sealed-evaluation-populations", "status": "passed" if commitment_ok else "failed"})
    local_ok = True
    if SEALED_PATH.is_file():
        local_ok = verify_preimages(_load(SEALED_PATH), commitments)
    checks.append({"id": "local-preimages", "status": "passed" if local_ok else "failed"})

    method_absent = not _method_sources_exist()
    checks.append({"id": "v4-method-not-started", "status": "passed" if method_absent else "failed"})
    ordering_ok = stored_lock.get("evaluation_order") == [
        "protocol-lock", "v4-development", "method-lock", "runner-lock", "commit-and-push",
        "seed-reveal", "binding", "oos", "profile-binding",
    ]
    checks.append({"id": "evaluation-order", "status": "passed" if ordering_ok else "failed"})
    passed = all(item["status"] == "passed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-04-F3B",
        "status": "passed" if passed else "failed",
        "checks": checks,
        "protocol_lock_sha256": _sha256(LOCK_PATH),
        "protocol_lock_identity": stored_lock.get("protocol_lock_sha256"),
        "base_acceptance_sha256": acceptance["base_acceptance"]["sha256"],
        "public_development_seed_count": len(public_seeds),
        "binding_seed_revealed": False,
        "oos_seed_revealed": False,
        "v4_method_started": False,
        "claim_boundary": "F3 protokol ve veri ayrımı kanıtıdır; algoritma, binding/OOS veya ürün başarısı değildir.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = build_summary()
    payload = _canonical(summary)
    if args.write:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_bytes(payload)
    elif not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_bytes() != payload:
        print("PHASE-04-F3B verification evidence is missing or stale")
        return 1
    print(f"PHASE-04-F3B protocol: {summary['status']}")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
