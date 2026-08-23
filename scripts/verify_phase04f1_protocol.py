#!/usr/bin/env python3
"""Write or check the pre-method PHASE-04-F1 evaluation protocol evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
LOCK_PATH = FIXTURES / "protocol-lock.json"
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f1" / "f1b-verification.json"
REVEAL_PATH = FIXTURES / "evaluation-seeds.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def build_summary() -> dict[str, Any]:
    lock = _load(LOCK_PATH)
    acceptance = _load(FIXTURES / "acceptance-gates.json")
    development = _load(FIXTURES / "development-scenes.json")
    commitments = _load(FIXTURES / "evaluation-commitments.json")
    checks: list[dict[str, Any]] = []

    identity_ok = (
        lock.get("schema_version") == 1
        and lock.get("lock_id") == "phase04f1-evaluation-protocol-lock-v1"
        and lock.get("status") == "locked-before-method-development"
    )
    checks.append({"id": "protocol-lock-identity", "status": "passed" if identity_ok else "failed"})

    inputs = lock.get("inputs", {})
    input_ok = isinstance(inputs, dict) and all(
        (ROOT / path).is_file() and _sha256(ROOT / path) == digest
        for path, digest in inputs.items()
    )
    checks.append({"id": "input-digests", "status": "passed" if input_ok else "failed"})

    required_fields = {
        "emission_center_frequency",
        "carrier_line_frequency",
        "occupied_bandwidth",
        "uncalibrated_channel_power_dbfs",
        "snr_estimate_db",
        "signal_domain",
    }
    gate_ok = (
        acceptance.get("status") == "locked-before-method-development"
        and set(lock.get("required_fields", ())) == required_fields
        and required_fields <= set(acceptance.get("binding", {}))
        and required_fields <= set(acceptance.get("oos", {}))
        and acceptance.get("authority", {}).get("results_must_not_change_thresholds") is True
    )
    checks.append({"id": "acceptance-gates", "status": "passed" if gate_ok else "failed"})

    development_ok = (
        development.get("role") == "development-only"
        and development.get("common", {}).get("trials_per_family") == 64
        and len(development.get("families", ())) == 8
        and development.get("common", {}).get("snr_db") == [-6.0, 0.0, 6.0, 12.0]
    )
    checks.append({"id": "development-population", "status": "passed" if development_ok else "failed"})

    populations = commitments.get("populations", ())
    commitments_ok = (
        commitments.get("status") == "committed-before-method-development"
        and [item.get("role") for item in populations] == ["binding", "oos"]
        and all(
            isinstance(item.get("seed_commitment_sha256"), str)
            and len(item["seed_commitment_sha256"]) == 64
            and all(character in "0123456789abcdef" for character in item["seed_commitment_sha256"])
            for item in populations
        )
        and populations[0].get("seed_commitment_sha256") != populations[1].get("seed_commitment_sha256")
        and not REVEAL_PATH.exists()
    )
    checks.append({"id": "sealed-evaluation-populations", "status": "passed" if commitments_ok else "failed"})

    ordering_ok = lock.get("evaluation_order") == [
        "development", "method-lock", "seed-reveal", "binding", "oos", "profile-binding"
    ]
    checks.append({"id": "evaluation-order", "status": "passed" if ordering_ok else "failed"})

    passed = all(item["status"] == "passed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-04-F1B",
        "status": "passed" if passed else "failed",
        "checks": checks,
        "protocol_lock_sha256": _sha256(LOCK_PATH),
        "binding_seed_revealed": False,
        "oos_seed_revealed": False,
        "method_implementation_locked": False,
        "claim_boundary": "Değerlendirme protokolü kilididir; algoritma veya PHASE-04 başarı sonucu değildir.",
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
        print("PHASE-04-F1B evidence is missing or stale")
        return 1
    print(f"PHASE-04-F1B protocol: {summary['status']}")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

