#!/usr/bin/env python3
"""Generate or check deterministic PHASE-06H candidate-grouping vectors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.rtl.candidate_vectors import build_vector_files


TARGET = ROOT / "datasets" / "fixtures" / "phase06h"


def check() -> bool:
    files = build_vector_files()
    return all((TARGET / name).is_file() and (TARGET / name).read_bytes() == payload for name, payload in files.items())


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        TARGET.mkdir(parents=True, exist_ok=True)
        files = build_vector_files()
        for name, payload in files.items():
            (TARGET / name).write_bytes(payload)
        print(f"PHASE-06H vectors written: {len(files)} files")
    passed = check()
    print(f"PHASE-06H vector verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
