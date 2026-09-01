"""Source-bound checks for the optimized 8-to-2 MS/s channelizer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from algorithms.p0 import find_native_channelizer_library
from scripts.verify_phase08_native_channelizer import SOURCES


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/evidence/phase08/native-channelizer-v3.json"


def test_native_channelizer_evidence_is_exact_fast_and_current() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-native-channelizer-evidence-v3"
    assert report["status"] == "passed"
    assert all(report["checks"].values())
    assert len(report["comparison"]) == 5
    assert all(item["frames"] == 16 and item["maximum_lsb_error"] == 0
               for item in report["comparison"])
    assert report["latency_ms"]["samples"] == 2_000
    assert report["latency_ms"]["p95"] < report["input_period_ms"] == 2.048
    for name in SOURCES:
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == report["source_sha256"][name]
    library = find_native_channelizer_library()
    assert library is not None
    assert hashlib.sha256(library.read_bytes()).hexdigest() == report["library"]["sha256"]
