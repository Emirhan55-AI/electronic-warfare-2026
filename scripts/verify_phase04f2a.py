#!/usr/bin/env python3
"""Write or verify the deterministic PHASE-04-F2A failure analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification.phase04f2_analysis import build_analysis


OUTPUT = ROOT / "results" / "evidence" / "phase04f2" / "f2a-analysis.json"


def _payload() -> bytes:
    return (json.dumps(build_analysis(), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = _payload()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(payload)
    elif not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
        print("PHASE-04-F2A analysis evidence is missing or stale")
        return 1
    analysis = build_analysis()
    print(f"PHASE-04-F2A analysis: {analysis['status']}; F1 evaluation: {analysis['f1_evaluation_status']}")
    return 0 if analysis["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
