"""Run the single frozen binding and locked OOS evaluation for PHASE-04-E1."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.operator_evaluation import compare, complete_existing_v2_result, evaluate
from reference.parameters.operator_reference import (
    ACCEPTANCE_PATH,
    METHOD_LOCK_PATH,
    PHASE03_PROFILE_PATH,
    canonical_json_bytes,
    implementation_manifest,
    load_json,
    sha256_file,
)


OUT = ROOT / "results" / "evidence" / "phase04e1"


def _attach_lock(payload: dict[str, object]) -> dict[str, object]:
    lock = load_json(METHOD_LOCK_PATH)
    if lock.get("status") != "locked-pre-binding":
        raise RuntimeError("PHASE-04-E1 method lock is not established")
    return {**payload, "method_lock_sha256": sha256_file(METHOD_LOCK_PATH)}


def _write_outputs(binding: dict[str, object], oos: dict[str, object]) -> None:
    comparison = _attach_lock(compare(binding, oos))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "binding-results.json").write_bytes(canonical_json_bytes(binding))
    (OUT / "oos-results.json").write_bytes(canonical_json_bytes(oos))
    (OUT / "parameter-comparison.json").write_bytes(canonical_json_bytes(comparison))
    profile_path = ROOT / "profiles" / "phase04e1" / "operation-default.json"
    validated = tuple(comparison["validated_fields"])
    if validated:
        lock = load_json(METHOD_LOCK_PATH)
        methods = dict(lock["methods"])
        if not comparison["automatic_span_validated"]:
            methods.pop("automatic_span", None)
        profile = {
            "schema_version": 1,
            "profile_id": "phase04e1-operator-assisted-parameters",
            "lifecycle": "validated",
            "base_profile_id": "phase03-operation-default",
            "validated_fields": list(validated),
            "automatic_span_validated": bool(comparison["automatic_span_validated"]),
            "protocol_revision": "independent-fields-v2",
            "methods": methods,
            "method_lock_sha256": sha256_file(METHOD_LOCK_PATH),
            "comparison_sha256": sha256_file(OUT / "parameter-comparison.json"),
            "implementation_manifest_sha256": implementation_manifest()["sha256"],
            "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
            "acceptance_contract_sha256": sha256_file(ACCEPTANCE_PATH),
            "claim_boundary": "Kayıtlı/sentetik I/Q ve operatörce onaylanan span; PHASE-04 tamamlanmış değildir."
        }
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_bytes(canonical_json_bytes(profile))
    elif profile_path.exists():
        profile_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--complete-v2-protocol", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        binding = _attach_lock(evaluate("binding"))
        oos = _attach_lock(evaluate("oos"))
    else:
        binding = _attach_lock(complete_existing_v2_result(load_json(OUT / "binding-results.json")))
        oos = _attach_lock(complete_existing_v2_result(load_json(OUT / "oos-results.json")))
    _write_outputs(binding, oos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
