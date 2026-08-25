#!/usr/bin/env python3
"""Verify the unchanged v4 carrier decision on the open F4 catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import develop_phase04f3_carrier as inherited
from algorithms.parameters.f4_estimator import F4ParameterEstimator


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f4" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f4" / "carrier-analysis-v5.json"


def build_analysis() -> dict[str, Any]:
    original_path = inherited.DEVELOPMENT_PATH
    original_estimator = inherited.F3ParameterEstimator
    inherited.DEVELOPMENT_PATH = DEVELOPMENT_PATH
    inherited.F3ParameterEstimator = F4ParameterEstimator
    try:
        document = inherited.build_analysis()
    finally:
        inherited.DEVELOPMENT_PATH = original_path
        inherited.F3ParameterEstimator = original_estimator
    return {
        **document,
        "artifact_id": "phase04f4-carrier-analysis-v5",
        "inherited_carrier_method": "frequency.carrier-temporal-artifact-rejection-v4",
        "selection_boundary": "Only the frame-support and artifact-entropy margins differ from v4; all locked F4 carrier risk gates remain unchanged.",
        "claim_boundary": "Yalnız sekiz açık F4 geliştirme seed'inin 12 dB koşuludur; F4 binding/OOS veya ürün sonucu değildir.",
    }


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build_analysis()
    payload = _canonical(document)
    if args.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(payload)
    elif not RESULT_PATH.is_file() or RESULT_PATH.read_bytes() != payload:
        print("PHASE-04-F4 carrier analysis is missing or stale")
        return 1
    print(f"PHASE-04-F4 carrier analysis: {document['status']}")
    return 0 if document["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
