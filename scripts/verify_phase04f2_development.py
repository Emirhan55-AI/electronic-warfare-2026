#!/usr/bin/env python3
"""Write or verify the reproducible PHASE-04-F2 open-development result."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f2_development import evaluate_development


RESULT_PATH = ROOT / "results" / "evidence" / "phase04f2" / "development-results-v3.json"


def _payload() -> bytes:
    return (json.dumps(evaluate_development(), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = _payload()
    if args.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(payload)
    elif not RESULT_PATH.is_file() or RESULT_PATH.read_bytes() != payload:
        print("PHASE-04-F2 development result is missing or stale")
        return 1
    document = json.loads(payload)
    print(f"PHASE-04-F2 development: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
