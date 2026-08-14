#!/usr/bin/env python3
"""Generate or check the deterministic PHASE-04-D1 clean OBW99 reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.obw99_reference import build_clean_reference, canonical_json_bytes


OUTPUT = ROOT / "datasets" / "fixtures" / "phase04d1" / "clean-reference.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = canonical_json_bytes(build_clean_reference())
    if args.write:
        OUTPUT.write_bytes(payload)
        print(f"clean reference written: {OUTPUT.relative_to(ROOT).as_posix()}")
        return 0
    if not OUTPUT.is_file():
        print("clean reference is missing", file=sys.stderr)
        return 1
    if OUTPUT.read_bytes() != payload:
        print("clean reference differs from deterministic generation", file=sys.stderr)
        return 1
    print("clean reference check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
