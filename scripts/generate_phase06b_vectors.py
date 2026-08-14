#!/usr/bin/env python3
"""Generate or byte-check deterministic PHASE-06B Hann vectors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.rtl.hann_vectors import build_vector_files


OUTPUT = ROOT / "datasets" / "fixtures" / "phase06b"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files, _ = build_vector_files()
    if args.write:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, payload in files.items():
            (OUTPUT / name).write_bytes(payload)
        print("PHASE-06B Hann vectors written")
        return 0
    mismatches = [
        name
        for name, payload in files.items()
        if not (OUTPUT / name).is_file() or (OUTPUT / name).read_bytes() != payload
    ]
    if mismatches:
        print("PHASE-06B vector mismatch: " + ", ".join(mismatches))
        return 1
    print("PHASE-06B Hann vectors: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
