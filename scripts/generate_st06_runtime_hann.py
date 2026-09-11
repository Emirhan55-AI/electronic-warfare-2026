#!/usr/bin/env python3
"""Generate or verify deterministic block-ROM images for runtime Hann lengths."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.rtl.runtime_hann import SUPPORTED_FFT_SIZES, quantized_coefficients


OUTPUT_DIR = ROOT / "datasets/fixtures/phase06b"


def payload(size: int) -> bytes:
    return "".join(f"{value:04x}\n" for value in quantized_coefficients(size)).encode("ascii")


def path_for(size: int) -> Path:
    return OUTPUT_DIR / f"hann-runtime-coefficients-{size}.mem"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for size in SUPPORTED_FFT_SIZES:
        path = path_for(size)
        expected = payload(size)
        if args.check:
            if not path.exists() or path.read_bytes() != expected:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    if mismatches:
        print("Hann ROM uyuşmazlığı: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print("Hann ROM doğrulandı: 4096, 8192, 16384")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
