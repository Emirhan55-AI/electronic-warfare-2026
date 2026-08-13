#!/usr/bin/env python3
"""Evaluate or safely establish the PHASE-04-R1 comparison/profile pair."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters import evaluate_parameter_methods  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes  # noqa: E402
from reference.pipeline import VerifiedProfileBinding, build_phase04_profile, canonical_profile_bytes  # noqa: E402


COMPARISON_PATH = ROOT / "results" / "evidence" / "phase04" / "parameter-comparison.json"
PROFILE_PATH = ROOT / "profiles" / "phase04" / "operation-default.json"


def _atomic_write(path: Path, data: bytes) -> None:
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


def _binding(comparison: dict[str, object], selected: dict[str, str], comparison_bytes: bytes) -> VerifiedProfileBinding:
    return VerifiedProfileBinding(
        comparison_id=str(comparison["comparison_id"]),
        comparison_sha256=hashlib.sha256(comparison_bytes).hexdigest(),
        implementation_manifest_sha256=str(comparison["implementation_manifest_sha256"]),
        catalog_sha256=str(comparison["catalog_sha256"]),
        phase03_profile_sha256=str(comparison["phase03_profile_sha256"]),
        selected_methods=tuple(selected.items()),
    )


def establish(
    *, full: bool = True, reestablish: bool = False, check: bool = False, evaluate: bool = False,
) -> tuple[int, dict[str, object]]:
    comparison, selected = evaluate_parameter_methods(full=full)
    comparison_bytes = canonical_json_bytes(comparison)
    if evaluate:
        return (0 if selected is not None else 1), comparison

    profile_bytes: bytes | None = None
    if selected is not None:
        binding = _binding(comparison, selected, comparison_bytes)
        profile_bytes = canonical_profile_bytes(
            build_phase04_profile(selected, binding=binding, lifecycle="validated")
        )

    comparison_same = COMPARISON_PATH.is_file() and COMPARISON_PATH.read_bytes() == comparison_bytes
    profile_same = profile_bytes is not None and PROFILE_PATH.is_file() and PROFILE_PATH.read_bytes() == profile_bytes
    if check:
        if selected is None:
            return (1 if comparison_same else 2), comparison
        return (0 if comparison_same and profile_same else 2), comparison

    if reestablish:
        _atomic_write(COMPARISON_PATH, comparison_bytes)
        if profile_bytes is not None:
            _atomic_write(PROFILE_PATH, profile_bytes)
            return 0, comparison
        return 1, comparison

    if selected is None:
        if comparison_same:
            return 1, comparison
        return 2, comparison
    if comparison_same and profile_same:
        return 0, comparison
    if not COMPARISON_PATH.exists() and not PROFILE_PATH.exists():
        _atomic_write(COMPARISON_PATH, comparison_bytes)
        assert profile_bytes is not None
        _atomic_write(PROFILE_PATH, profile_bytes)
        return 0, comparison
    return 2, comparison


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--evaluate", action="store_true", help="evaluate in memory without reading success state or writing files")
    action.add_argument("--write", action="store_true", help="establish only an exact or explicitly re-established pair")
    action.add_argument("--check", action="store_true", help="read-only byte comparison with the established pair")
    parser.add_argument("--reestablish", action="store_true")
    parser.add_argument("--quick", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reestablish and not args.write:
        parser.error("--reestablish requires --write")
    code, payload = establish(
        full=not args.quick, reestablish=args.reestablish, check=args.check, evaluate=args.evaluate,
    )
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    print(f"PHASE-04 comparison SHA-256: {digest}")
    if code == 0:
        print(f"PHASE-04 method selection passed: {payload.get('selected_methods')}")
    elif code == 2:
        print("PHASE-04 result differs from established state; no file was changed.")
    else:
        print("PHASE-04 selection failed; no validated profile was established.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
