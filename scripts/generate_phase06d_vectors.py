#!/usr/bin/env python3
"""Generate deterministic PHASE-06D input fixtures without invoking vendor tools."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.rtl.phase06d_vectors import build_vector_files


def main() -> int:
    destination = ROOT / "datasets" / "fixtures" / "phase06d"
    destination.mkdir(parents=True, exist_ok=True)
    files = build_vector_files()
    for name, payload in files.items():
        (destination / name).write_bytes(payload)
    print(f"PHASE-06D vectors generated: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
