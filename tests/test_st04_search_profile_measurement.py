"""Tests for the receive-only ST-04 search-profile baseline."""

from __future__ import annotations

from argparse import Namespace
import hashlib
import json
from pathlib import Path

from scripts.measure_st04_search_profiles import (
    build_report,
    estimate_profiles,
    parse_sweep_csv,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st04-search-profile-baseline-v1.json"
RAW = ROOT / "results/evidence/phase08/st04-search-profile-baseline-v1.csv"


def test_sweep_parser_accepts_out_of_order_contiguous_rows(tmp_path: Path) -> None:
    capture = tmp_path / "sweep.csv"
    capture.write_text(
        "2026-09-04, 12:00:00.100000, 25000000, 30000000, 1000000.00, 20, -70, -71, -72, -73, -74\n"
        "2026-09-04, 12:00:00.000000, 20000000, 25000000, 1000000.00, 20, -60, -61, -62, -63, -64\n",
        encoding="utf-8",
    )
    summary = parse_sweep_csv(capture, expected_lower_hz=20_000_000, expected_upper_hz=30_000_000)
    assert summary.rows == 2
    assert summary.power_bins == 10
    assert summary.covered_hz == 10_000_000
    assert summary.gap_count == 0


def test_profile_estimates_preserve_detector_ownership_and_exclusions() -> None:
    estimates = estimate_profiles(20_000_000, 6_000_000_000)
    detailed = estimates["detailed_2msps_fpga_survey"]
    coarse = estimates["bounded_8msps_coarse_plan"]
    assert detailed["decision_owner"] == "FPGA_PL_and_ARM_PS"
    assert detailed["window_count"] == 9967
    assert detailed["raw_sample_seconds_full_range"] > 2600.0
    assert coarse["decision_owner"] == "host_candidate_only"
    assert coarse["window_count"] == 2392
    assert coarse["raw_sample_seconds_full_range"] < 15.0


def test_report_never_claims_rf_or_phase_acceptance(tmp_path: Path) -> None:
    capture = tmp_path / "sweep.csv"
    capture.write_text(
        "2026-09-04, 12:00:00.000000, 20000000, 25000000, 1000000.00, 20, -60, -61, -62, -63, -64\n",
        encoding="utf-8",
    )
    args = Namespace(
        lower_hz=20_000_000,
        upper_hz=25_000_000,
        serial="0123456789abcdef0123456789abcdef",
        bin_width_hz=1_000_000,
        lna_gain_db=16,
        vga_gain_db=16,
    )
    report = build_report(args, capture, 0.5)
    assert report["transmit_enabled"] is False
    assert report["st04_complete"] is False
    assert report["phase08_complete"] is False
    assert report["physical_host_sweep"]["gap_count"] == 0


def test_physical_baseline_is_source_bound_and_contiguous() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-st04-search-profile-baseline-v1"
    assert report["status"] == "baseline_measured"
    assert report["transmit_enabled"] is False
    assert report["st04_complete"] is False
    assert report["phase08_complete"] is False
    assert report["requested_range_hz"] == [20_000_000, 6_000_000_000]
    sweep = report["physical_host_sweep"]
    assert sweep["gap_count"] == 0
    assert sweep["covered_lower_hz"] <= 20_000_000
    assert sweep["covered_upper_hz"] >= 6_000_000_000
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == sweep["csv_sha256"]
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
