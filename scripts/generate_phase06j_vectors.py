#!/usr/bin/env python3
"""Generate deterministic PHASE-06J temporal-confirmation fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.ps.temporal_vectors import build_all_files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = ROOT / "datasets" / "fixtures" / "phase06j"
    files = build_all_files()
    if args.check:
        return 0 if all((output / name).is_file() and (output / name).read_bytes() == data for name, data in files.items()) else 1
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
