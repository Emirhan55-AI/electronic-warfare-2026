import json
from pathlib import Path
import subprocess
import sys

from scripts.verify_st06_product_optimization import verify_historical_statistics


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-power-arm-timing-v1.json"


def test_st06_power_arm_timing_keeps_end_to_end_gate_open() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    assert evidence["input"]["run_count"] == 5
    assert evidence["gates"]["measurement_integrity"] is True
    assert evidence["gates"]["isolated_mean_capacity"] is True
    assert evidence["gates"]["isolated_p99_deadline"] is True
    assert evidence["gates"]["every_observed_frame_deadline"] is False
    assert evidence["gates"]["full_power_dma_integration"] is False
    assert evidence["gates"]["pipelined_end_to_end_capacity"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["st06_complete"] is False


def test_st06_power_arm_timing_historical_statistics_recompute_exactly() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    verify_historical_statistics("scripts.verify_st06_power_arm_benchmark", evidence)
