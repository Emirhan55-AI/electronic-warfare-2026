import json
from pathlib import Path
import subprocess
import sys

from scripts.verify_st06_product_optimization import verify_historical_statistics


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-pipelined-dma-profile-v1.json"


def test_st06_pipelined_dma_profile_retains_historical_source_binding() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    verify_historical_statistics("scripts.verify_st06_pipelined_dma_profile", evidence)


def test_st06_pipelined_dma_profile_meets_only_the_physical_capacity_gate() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gates = evidence["gates"]

    assert evidence["schema"] == "phase08-st06-pipelined-dma-profile-v1"
    assert evidence["status"] == "passed"
    assert evidence["transmit_enabled"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["st06_complete"] is False
    assert gates["measurement_integrity"] is True
    assert gates["full_power_pl_loaded"] is True
    assert gates["bounded_dual_core_pipeline_exercised"] is True
    assert gates["sustained_end_to_end_real_time"] is True
    assert gates["product_lifecycle_integration"] is False
    assert gates["controlled_rf_accuracy"] is False
    assert evidence["board"]["producer_affinity"] == "CPU0"
    assert evidence["board"]["consumer_affinity"] == "CPU1"
    assert evidence["board"]["queue_depth"] == 4
    assert (
        evidence["measurement"]["minimum_frames_per_second"]
        >= evidence["deadline"]["required_frames_per_second"]
    )
    assert 1.0 < evidence["measurement"]["maximum_cpu_core_equivalents"] < 2.0
    assert evidence["measurement"]["maximum_dual_core_cpu_percent"] < 100.0
