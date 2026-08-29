"""Contract tests for the final reducer to PHASE-06I packetizer boundary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_packetizer_evidence_is_passed_and_bounded() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/candidate-reducer-packetizer.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["status"] == "passed"
    assert evidence["metrics"] == {
        "frames": 5,
        "candidates": 61,
        "beats": 345,
        "stalls": 30,
        "stability": 30,
    }
    assert evidence["architecture"]["candidate_loss"] == 0
    assert evidence["architecture"]["duplicate_records"] == 0


def test_packetizer_fixture_manifest_points_to_shared_power_input() -> None:
    manifest = json.loads(
        (ROOT / "datasets/fixtures/p0_candidate_reducer_packetizer/fixture-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    shared = manifest["shared_axis_power_input"]
    assert shared["path"] == "datasets/fixtures/p0_wideband_recovery/axis-power-input.mem"
    assert (ROOT / shared["path"]).is_file()
