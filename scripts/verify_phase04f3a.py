#!/usr/bin/env python3
"""Write or verify the PHASE-04-F3A read-only failure analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.operator_reference import canonical_json_bytes
from verification.phase04f3_analysis import build_analysis


SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f3" / "f3a-analysis.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build_analysis()
    payload = canonical_json_bytes(document)
    if args.write:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_bytes(payload)
    elif not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_bytes() != payload:
        print("PHASE-04-F3A analysis is missing or stale")
        return 1
    print(f"PHASE-04-F3A analysis: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
