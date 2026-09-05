"""Preserve the native channelizer measurement with its original sources."""

from __future__ import annotations

import hashlib

from algorithms.p0 import find_native_channelizer_library
from scripts.verify_phase08_native_channelizer import SOURCES
from scripts.verify_phase08_evidence_recovery import verify_native_history


def test_native_channelizer_evidence_preserves_historical_measurement() -> None:
    report = verify_native_history()
    assert report["schema"] == "phase08-native-channelizer-evidence-v3"
    assert report["status"] == "passed"
    assert all(report["checks"].values())
    assert len(report["comparison"]) == 5
    assert all(item["frames"] == 16 and item["maximum_lsb_error"] == 0
               for item in report["comparison"])
    assert report["latency_ms"]["samples"] == 2_000
    assert report["latency_ms"]["p95"] < report["input_period_ms"] == 2.048
    assert set(report["source_sha256"]) == set(SOURCES)
    library = find_native_channelizer_library()
    assert library is not None
    assert hashlib.sha256(library.read_bytes()).hexdigest() == report["library"]["sha256"]
