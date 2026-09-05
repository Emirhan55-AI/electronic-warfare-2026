"""Tests for the source-bound ST-04 hierarchical architecture decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st04-hierarchical-detection-architecture-v1.json"


def test_architecture_preserves_detection_authority_and_open_gates() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-st04-hierarchical-detection-architecture-v1"
    assert report["status"] == "architecture_selected"
    assert report["transmit_enabled"] is False
    assert report["st04_complete"] is True
    assert report["phase08_complete"] is False
    assert report["profile_decision"]["selected_for_controlled_blind_test"] is True
    assert report["profile_decision"]["selected_for_product"] is False
    stages = report["architecture"]
    assert stages["stage_0_full_band_discovery"]["authority"] == "candidate_only"
    assert stages["stage_1_candidate_refinement"]["authority"] == "rx_evidence_only"
    assert stages["stage_2_detailed_confirmation"]["owner"] == "fpga_pl_and_arm_ps"
    assert report["open_acceptance_gates"]


def test_existing_fpga_pipeline_is_not_claimed_as_8msps_capable() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    boundary = report["fpga_scaling_boundary"]
    assert boundary["direct_8msps_capacity_ratio"] < 1.0
    assert boundary["direct_8msps_existing_pipeline_meets_capacity"] is False
    assert boundary["post_route_slice_lut_utilization_percent"] == 90.3
    assert boundary["post_route_slice_luts_free"] == 5_160
    assert boundary["setup_wns_ns"] > 0.0
    assert boundary["hold_whs_ns"] > 0.0


def test_architecture_evidence_is_bound_to_inputs_and_sources() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for item in report["input_evidence_sha256"].values():
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
