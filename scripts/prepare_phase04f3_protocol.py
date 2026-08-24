#!/usr/bin/env python3
"""Create sealed F3 evaluation preimages and public commitments once."""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
COMMITMENTS_PATH = FIXTURES / "evaluation-commitments.json"
SEALED_PATH = ROOT / "build" / "phase04f3" / "sealed-seeds.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def seed_commitment(role: str, salt: str, seed: str) -> str:
    payload = json.dumps(
        {"role": role, "salt": salt, "seed": seed},
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_preimages(sealed: dict[str, Any], commitments: dict[str, Any]) -> bool:
    expected = {item["role"]: item["seed_commitment_sha256"] for item in commitments["populations"]}
    seeds = sealed.get("seeds", ())
    return [item.get("role") for item in seeds] == ["binding", "oos"] and all(
        seed_commitment(str(item["role"]), str(item["salt"]), str(item["seed"])) == expected[item["role"]]
        for item in seeds
    )


def main() -> int:
    if COMMITMENTS_PATH.exists() or SEALED_PATH.exists() or REVEAL_PATH.exists():
        print("PHASE-04-F3 protocol preimages or commitments already exist")
        return 1
    acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    base = json.loads((ROOT / acceptance["base_acceptance"]["path"]).read_text(encoding="utf-8"))
    seeds = [
        {"role": role, "seed": str(secrets.randbits(63)), "salt": secrets.token_hex(16)}
        for role in ("binding", "oos")
    ]
    sealed = {
        "schema_version": 1,
        "status": "sealed-local-preimage",
        "seeds": seeds,
        "repository_owned": False,
    }
    populations = []
    for item in seeds:
        population = base["population_contract"][item["role"]]
        populations.append({
            "role": item["role"],
            "seed_commitment_sha256": seed_commitment(item["role"], item["salt"], item["seed"]),
            "trials_per_family": population["trials_per_family"],
            "noise_measurements": population["noise_measurements"],
            "frames_per_measurement": population["frames_per_measurement"],
        })
    commitments = {
        "schema_version": 1,
        "commitment_id": "phase04f3-sealed-evaluation-seeds-v1",
        "status": "committed-before-v4-method-development",
        "canonical_preimage": "UTF-8 JSON, sorted keys, compact separators, one trailing LF; seed encoded as decimal string",
        "populations": populations,
        "reveal_policy": "Seed ve salt değerleri yalnız yöntem ve çalıştırıcı kilitleri commit/push sonrasında açılır.",
        "claim_boundary": "Commitment değerlendirme sonucunu veya algoritma başarısını içermez.",
    }
    if not verify_preimages(sealed, commitments):
        print("generated preimages do not match commitments")
        return 1
    SEALED_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMMITMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEALED_PATH.write_bytes(_canonical(sealed))
    COMMITMENTS_PATH.write_bytes(_canonical(commitments))
    print("PHASE-04-F3 commitments created; preimages remain local and sealed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
