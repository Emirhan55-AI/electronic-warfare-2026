"""Tests for repeated receive-only ST-04 sweep characterization."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.measure_st04_sweep_resolution import (
    parse_hackrf_timing,
    parse_shortfalls,
    split_and_summarize_sweeps,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st04-sweep-resolution-v1.json"
ARCHIVE = ROOT / "results/evidence/phase08/st04-sweep-resolution-v1.zip"


def _write_sweep_rows(path: Path) -> None:
    rows: list[list[object]] = []
    for timestamp, base in (("12:00:00.000000", -60), ("12:00:01.000000", -70)):
        rows.extend(
            [
                ["2026-09-04", timestamp, 25_000_000, 30_000_000, 1_000_000, 20,
                 base, base - 1, base - 2, base - 3, base - 4],
                ["2026-09-04", timestamp, 20_000_000, 25_000_000, 1_000_000, 20,
                 base - 5, base - 6, base - 7, base - 8, base - 9],
            ]
        )
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(rows)


def test_timing_and_shortfall_parsers_are_fail_closed() -> None:
    output = "Total sweeps: 3 in 2.23078 seconds (0.95 sweeps/second)"
    assert parse_hackrf_timing(output) == (3, 2.23078, 0.95)
    assert parse_shortfalls("Number of shortfalls: 0") == 0
    with pytest.raises(ValueError):
        parse_hackrf_timing("2 total sweeps completed")
    with pytest.raises(ValueError):
        parse_shortfalls("M0 state unavailable")


def test_each_constant_timestamp_sweep_requires_full_coverage(tmp_path: Path) -> None:
    capture = tmp_path / "multi.csv"
    groups = tmp_path / "groups"
    groups.mkdir()
    _write_sweep_rows(capture)
    summaries = split_and_summarize_sweeps(
        capture,
        expected_lower_hz=20_000_000,
        expected_upper_hz=30_000_000,
        expected_sweeps=2,
        workspace=groups,
    )
    assert len(summaries) == 2
    assert all(summary.covered_hz == 10_000_000 for summary in summaries)
    assert all(summary.gap_count == 0 for summary in summaries)


def test_physical_resolution_evidence_is_source_and_raw_bound() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-st04-sweep-resolution-v1"
    assert report["status"] == "timing_characterized"
    assert report["transmit_enabled"] is False
    assert report["st04_complete"] is False
    assert report["phase08_complete"] is False
    assert report["requested_range_hz"] == [20_000_000, 6_000_000_000]
    assert report["timing_only_result"]["selected_for_rf_detection"] is False
    assert report["usb_shortfall_counter"]["after_is_zero"] is True
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == report["raw_archive"]["sha256"]
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert sorted(archive.namelist()) == report["raw_archive"]["entries"]
        for profile in report["profiles"]:
            assert profile["trial_count"] >= 2
            assert profile["sweeps_per_trial"] >= 2
            assert profile["all_sweeps_gap_free"] is True
            assert profile["validated_sweep_count"] == (
                profile["trial_count"] * profile["sweeps_per_trial"]
            )
            for trial in profile["trials"]:
                payload = archive.read(trial["csv_entry"])
                assert hashlib.sha256(payload).hexdigest() == trial["csv_sha256"]
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
