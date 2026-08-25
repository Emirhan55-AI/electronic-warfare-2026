#!/usr/bin/env python3
"""Generate or verify the PHASE-04-F5 open development result."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f5_development import evaluate_development
from algorithms.parameters.operator_reference import canonical_json_bytes


RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "development-results-v6.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = evaluate_development()
    payload = canonical_json_bytes(document)
    if args.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(payload)
    elif not RESULT_PATH.is_file() or RESULT_PATH.read_bytes() != payload:
        print("PHASE-04-F5 development result is missing or stale")
        return 1
    print(f"PHASE-04-F5 development: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
