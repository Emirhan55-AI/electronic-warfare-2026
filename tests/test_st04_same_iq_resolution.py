"""Tests for ST-04 resolution comparison on identical physical CI8 data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.evaluate_st04_same_iq_resolution import associate_candidates


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st04-same-iq-resolution-v1.json"


def test_two_lo_association_uses_absolute_rf_and_is_one_to_one() -> None:
    first = [
        {"peak_frequency_hz": 100_000_000.0, "peak_to_noise_db": 9.0, "occupancy": 0.9},
        {"peak_frequency_hz": 101_000_000.0, "peak_to_noise_db": 8.0, "occupancy": 0.8},
    ]
    second = [
        {"peak_frequency_hz": 100_000_500.0, "peak_to_noise_db": 7.0, "occupancy": 0.7},
    ]
    matches = associate_candidates(first, second, tolerance_hz=1_000.0)
    assert len(matches) == 1
    assert matches[0]["frequency_hz"] == 100_000_250.0
    assert matches[0]["minimum_peak_to_noise_db"] == 7.0
    assert matches[0]["minimum_occupancy"] == 0.7


def test_physical_same_iq_evidence_preserves_claim_boundary() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-st04-same-iq-resolution-v1"
    assert report["status"] == "recorded_resolution_characterized"
    assert report["transmit_enabled"] is False
    assert report["blind_acceptance"] is False
    assert report["candidate_generation_uses_target_truth"] is False
    assert report["st04_complete"] is False
    assert report["phase08_complete"] is False
    assert report["same_recording_result"]["selected_for_product"] is False
    profiles = {item["fft_size"]: item for item in report["profiles"]}
    assert profiles[4_096]["evaluation_truth"]["target_recovered_in_two_lo_on"] is False
    assert profiles[8_192]["evaluation_truth"]["target_recovered_in_two_lo_on"] is False
    assert profiles[16_384]["evaluation_truth"]["target_recovered_in_two_lo_on"] is True
    assert profiles[16_384]["two_lo_off_matches"] == []
    assert profiles[16_384]["recording_pair_clean"] is True
    assert profiles[32_768]["evaluation_truth"]["target_recovered_in_two_lo_on"] is True
    assert len(profiles[32_768]["two_lo_off_matches"]) >= 1
    assert profiles[65_536]["evaluation_truth"]["target_recovered_in_two_lo_on"] is True
    assert len(profiles[65_536]["two_lo_off_matches"]) >= 1
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_local_raw_inputs_match_evidence_when_available() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for item in report["inputs"].values():
        path = ROOT / item["path"]
        if not path.is_file():
            continue
        assert path.stat().st_size == item["full_file_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["full_file_sha256"]
