#!/usr/bin/env python3
"""Run once or establish the locked PHASE-04-R2 comparison without reevaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters import evaluate_phase04_r2  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes, phase04_implementation_manifest  # noqa: E402
from reference.parameters.r2 import R2_COMPARISON_ID  # noqa: E402
from reference.pipeline import VerifiedProfileBinding, build_phase04_profile, canonical_profile_bytes  # noqa: E402


LOCK = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"
COMPARISON = ROOT / "results" / "evidence" / "phase04" / "r2-parameter-comparison.json"
PROFILE = ROOT / "profiles" / "phase04" / "operation-default.json"


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _profile_bytes(payload: dict[str, Any]) -> bytes | None:
    selected = payload.get("selected_methods")
    if not isinstance(selected, dict):
        return None
    comparison_bytes = canonical_json_bytes(payload)
    binding = VerifiedProfileBinding(
        comparison_id=R2_COMPARISON_ID,
        comparison_sha256=hashlib.sha256(comparison_bytes).hexdigest(),
        implementation_manifest_sha256=str(payload["implementation_manifest_sha256"]),
        catalog_sha256=str(payload["catalog_sha256"]),
        phase03_profile_sha256=str(payload["phase03_profile_sha256"]),
        selected_methods=tuple((str(key), str(value)) for key, value in selected.items()),
        method_lock_sha256=str(payload["method_lock_sha256"]),
    )
    return canonical_profile_bytes(build_phase04_profile(selected, binding=binding, lifecycle="validated"))


def _validate_payload(payload: dict[str, Any]) -> bytes:
    if payload.get("schema_version") != 3 or payload.get("comparison_id") != R2_COMPARISON_ID:
        raise ValueError("temporary R2 comparison identity is invalid")
    lock_digest = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    manifest = phase04_implementation_manifest()
    if payload.get("method_lock_sha256") != lock_digest:
        raise ValueError("temporary R2 comparison method-lock digest is stale")
    for field in ("catalog_sha256", "implementation_manifest_sha256", "phase03_profile_sha256"):
        if payload.get(field) != manifest[field]:
            raise ValueError(f"temporary R2 comparison {field} is stale")
    return canonical_json_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--evaluate", action="store_true")
    actions.add_argument("--establish-from", type=Path)
    actions.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quick", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    lock_digest = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    if args.evaluate:
        if args.output is None:
            parser.error("--evaluate requires --output")
        target = args.output.resolve()
        if target == ROOT or ROOT in target.parents:
            parser.error("binding output must remain outside the repository")
        payload, selected = evaluate_phase04_r2(full=not args.quick, method_lock_sha256=lock_digest)
        data = _validate_payload(payload)
        _atomic(target, data)
        print(f"PHASE-04-R2 comparison SHA-256: {hashlib.sha256(data).hexdigest()}")
        print(f"PHASE-04-R2 band status: {payload['noise_bandwidth_decision']['status']}")
        return 0 if selected is not None else 1
    if args.establish_from is not None:
        payload = json.loads(args.establish_from.read_text(encoding="utf-8"))
        data = _validate_payload(payload)
        profile = _profile_bytes(payload)
        _atomic(COMPARISON, data)
        if profile is not None:
            _atomic(PROFILE, profile)
        elif PROFILE.exists():
            existing = json.loads(PROFILE.read_text(encoding="utf-8"))
            block = next((item for item in existing.get("blocks", []) if item.get("id") == "parameters"), None)
            if block is not None and block.get("parameters", {}).get("comparison_id") == R2_COMPARISON_ID:
                PROFILE.unlink()
        print(f"PHASE-04-R2 established comparison SHA-256: {hashlib.sha256(data).hexdigest()}")
        return 0
    if not COMPARISON.is_file():
        print("PHASE-04-R2 comparison is missing")
        return 2
    payload = json.loads(COMPARISON.read_text(encoding="utf-8"))
    data = _validate_payload(payload)
    if COMPARISON.read_bytes() != data:
        print("PHASE-04-R2 comparison is not canonical")
        return 2
    expected_profile = _profile_bytes(payload)
    profile_ok = (
        not PROFILE.exists() if expected_profile is None else PROFILE.is_file() and PROFILE.read_bytes() == expected_profile
    )
    print(f"PHASE-04-R2 check: {'passed' if profile_ok else 'failed'}")
    print(f"PHASE-04-R2 algorithm status: {payload.get('overall')}")
    return 0 if profile_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
