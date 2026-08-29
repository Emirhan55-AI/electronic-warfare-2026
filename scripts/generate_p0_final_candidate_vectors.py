#!/usr/bin/env python3
"""Generate or check complete P0 candidate-reducer RTL vectors."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.rtl.p0_final_candidate_vectors import build_vector_files


TARGET = ROOT / "datasets/fixtures/p0_final_candidate"


def check() -> bool:
    files = build_vector_files()
    return all(
        (TARGET / name).is_file() and (TARGET / name).read_bytes() == payload
        for name, payload in files.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.write:
        TARGET.mkdir(parents=True, exist_ok=True)
        for name, payload in build_vector_files().items():
            (TARGET / name).write_bytes(payload)
    passed = check()
    print(f"P0 final aday vektör doğrulaması: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
