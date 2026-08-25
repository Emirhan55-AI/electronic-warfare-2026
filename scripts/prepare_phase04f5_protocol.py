#!/usr/bin/env python3
"""Create independent F5 development seeds and sealed evaluation commitments once."""

from __future__ import annotations

import hashlib
import json
import secrets
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
COMMITMENTS_PATH = FIXTURES / "evaluation-commitments.json"
SEALED_PATH = ROOT / "build" / "phase04f5" / "sealed-seeds.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def seed_commitment(role: str, salt: str, seed: str) -> str:
    payload = json.dumps({"role": role, "salt": salt, "seed": seed}, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_preimages(sealed: dict[str, Any], commitments: dict[str, Any]) -> bool:
    expected = {item["role"]: item["seed_commitment_sha256"] for item in commitments["populations"]}
    seeds = sealed.get("seeds", ())
    return [item.get("role") for item in seeds] == ["binding", "oos"] and all(
        seed_commitment(str(item["role"]), str(item["salt"]), str(item["seed"])) == expected[item["role"]]
        for item in seeds
    )


def historical_seeds() -> set[int]:
    values = {20261010}
    for phase in ("phase04f1", "phase04f2", "phase04f3", "phase04f4"):
        reveal = ROOT / "datasets" / "fixtures" / phase / "evaluation-seeds.json"
        values.update(int(item["seed"]) for item in _load(reveal)["seeds"])
    for phase in ("phase04f2", "phase04f3", "phase04f4"):
        catalog = _load(ROOT / "datasets" / "fixtures" / phase / "development-catalog.json")
        values.update(int(seed) for seed in catalog["common"]["development_seeds"])
    return values


def _unique_seed(excluded: set[int]) -> int:
    while True:
        value = secrets.randbits(63)
        if value not in excluded:
            excluded.add(value)
            return value


def main() -> int:
    owned = (DEVELOPMENT_PATH, COMMITMENTS_PATH, SEALED_PATH, REVEAL_PATH)
    if any(path.exists() for path in owned):
        print("PHASE-04-F5 protocol data or preimages already exist")
        return 1
    acceptance = _load(ACCEPTANCE_PATH)
    base = _load(ROOT / acceptance["base_acceptance"]["path"])
    excluded = historical_seeds()
    public_seeds = [_unique_seed(excluded) for _ in range(8)]
    evaluation_seeds = [
        {"role": role, "seed": str(_unique_seed(excluded)), "salt": secrets.token_hex(16)}
        for role in ("binding", "oos")
    ]
    development = deepcopy(_load(ROOT / "datasets" / "fixtures" / "phase04f4" / "development-catalog.json"))
    development.update({
        "catalog_id": "phase04f5-open-development-v1",
        "role": "development-only",
        "claim_boundary": "Yalnız F5C yöntem geliştirme ve OBW tanı kataloğudur; önceki veya F5 değerlendirme sonucu değildir.",
    })
    development["common"]["development_seeds"] = public_seeds
    development["data_separation"] = {
        "f1_f2_f3_f4_open_or_revealed_populations_allowed_for_tuning": False,
        "f5_binding_oos_preimages_available_to_method": False,
    }
    sealed = {
        "schema_version": 1,
        "status": "sealed-local-preimage",
        "seeds": evaluation_seeds,
        "repository_owned": False,
    }
    populations = []
    for item in evaluation_seeds:
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
        "commitment_id": "phase04f5-sealed-evaluation-seeds-v1",
        "status": "committed-before-v6-method-development",
        "canonical_preimage": "UTF-8 JSON, sorted keys, compact separators, one trailing LF; seed encoded as decimal string",
        "populations": populations,
        "reveal_policy": "Seed ve salt değerleri yalnız yöntem ve çalıştırıcı kilitleri commit/push sonrasında açılır.",
        "claim_boundary": "Commitment değerlendirme sonucunu veya algoritma başarısını içermez.",
    }
    if not verify_preimages(sealed, commitments):
        print("generated preimages do not match commitments")
        return 1
    FIXTURES.mkdir(parents=True, exist_ok=True)
    SEALED_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEVELOPMENT_PATH.write_bytes(_canonical(development))
    COMMITMENTS_PATH.write_bytes(_canonical(commitments))
    SEALED_PATH.write_bytes(_canonical(sealed))
    print("PHASE-04-F5 data partition created; evaluation preimages remain local and sealed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
