#!/usr/bin/env python3
"""Reveal the committed PHASE-04-F1 evaluation seeds after runner lock."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file


FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
SEALED_PATH = ROOT / "build" / "phase04f1" / "sealed-seeds.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"
RUNNER_LOCK_PATH = FIXTURES / "evaluation-runner-lock.json"
RUN_STARTED_PATH = ROOT / "results" / "evidence" / "phase04f1" / "f1d-run-started.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _commitment(role: str, salt: str, seed: str) -> str:
    payload = json.dumps(
        {"role": role, "salt": salt, "seed": seed},
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_reveal(document: dict[str, Any]) -> bool:
    commitments = _load(FIXTURES / "evaluation-commitments.json")
    expected = {item["role"]: item["seed_commitment_sha256"] for item in commitments["populations"]}
    seeds = document.get("seeds", ())
    return (
        document.get("status") == "revealed-after-runner-lock"
        and document.get("runner_lock_sha256") == sha256_file(RUNNER_LOCK_PATH)
        and [item.get("role") for item in seeds] == ["binding", "oos"]
        and all(
            _commitment(str(item["role"]), str(item["salt"]), str(item["seed"])) == expected[item["role"]]
            for item in seeds
        )
    )


def main() -> int:
    if REVEAL_PATH.exists() or RUN_STARTED_PATH.exists():
        print("PHASE-04-F1 seeds were already revealed or evaluation already started")
        return 1
    if not RUNNER_LOCK_PATH.is_file() or not SEALED_PATH.is_file():
        print("runner lock or local sealed seed preimage is missing")
        return 1
    lock = _load(RUNNER_LOCK_PATH)
    if lock.get("status") != "locked-before-seed-reveal":
        print("evaluation runner is not locked")
        return 1
    sealed = _load(SEALED_PATH)
    document = {
        "schema_version": 1,
        "reveal_id": "phase04f1-evaluation-seeds-v1",
        "status": "revealed-after-runner-lock",
        "runner_lock_sha256": sha256_file(RUNNER_LOCK_PATH),
        "seeds": sealed["seeds"],
        "claim_boundary": "Seed ve salt değerleri yöntem ile değerlendirme çalıştırıcısı kilitlendikten sonra açılmıştır.",
    }
    if not verify_reveal(document):
        print("sealed seed preimages do not match public commitments")
        return 1
    REVEAL_PATH.write_bytes(canonical_json_bytes(document))
    print("PHASE-04-F1 seed reveal: commitments verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
