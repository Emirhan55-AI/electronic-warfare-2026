import json
from pathlib import Path
import subprocess
import sys

from scripts.verify_st06_product_optimization import verify_historical_statistics


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-arm-algorithm-timing-v2.json"


def test_st06_arm_evidence_is_source_bound_and_scope_limited() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["schema"] == "phase08-st06-arm-algorithm-timing-v2"
    assert evidence["status"] == "passed"
    assert evidence["arm_algorithm_kernel_measured"] is True
    assert evidence["dma_transfer_included"] is False
    assert evidence["pl_full_power_image_loaded"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["st06_complete"] is False
    assert evidence["gates"]["decision_equivalence"] is True
    assert evidence["gates"]["isolated_arm_kernel_real_time"] is True
    assert evidence["gates"]["sustained_end_to_end_real_time"] is False
    assert evidence["optimized_measurement"]["run_count"] == 5
    assert (
        evidence["optimized_measurement"]["wide_signal"]
        ["minimum_frames_per_second"]
        >= evidence["deadline"]["required_frames_per_second"]
    )
    assert (
        evidence["optimized_measurement"]["wide_signal"]
        ["maximum_observed_latency_ms"]
        <= evidence["deadline"]["frame_interval_ms"]
    )


def test_st06_arm_evidence_historical_statistics_recompute_exactly() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    verify_historical_statistics("scripts.verify_st06_arm_benchmark", evidence)
