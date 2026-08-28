#!/usr/bin/env python3
"""Generate or check deterministic P0 PL OS-CFAR vectors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.rtl.p0_os_cfar_vectors import build_vector_files


TARGET = ROOT / "datasets" / "fixtures" / "p0_os_cfar"


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
    args = parser.parse_args()
    if args.write:
        TARGET.mkdir(parents=True, exist_ok=True)
        for name, payload in build_vector_files().items():
            (TARGET / name).write_bytes(payload)
        print("P0 PL OS-CFAR vektörleri yazıldı.")
    passed = check()
    print(f"P0 PL OS-CFAR vektör doğrulaması: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
