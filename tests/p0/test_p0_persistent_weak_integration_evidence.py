import json
from pathlib import Path

from scripts.verify_p0_persistent_weak_integration import check


ROOT = Path(__file__).resolve().parents[2]


def test_current_persistent_weak_source_gate_records_digital_physical_acceptance() -> None:
    assert check()
    evidence = json.loads(
        (ROOT / "results/evidence/phase08/persistent-weak-integration-v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["status"] == "digital_physical_passed_live_rf_open"
    assert evidence["profile"]["maximum_weak_nominations_per_frame"] == 1352
    assert evidence["profile"]["maximum_tracked_weak_nominations_per_frame"] == 8
    assert evidence["model"]["false_confirmed_windows"] == 0
    assert evidence["model"]["confirmed_frequency_positions"] == 5
    assert evidence["pytest"]["status"] == "passed"
    assert evidence["deployment_gates"]["vivado_synthesis_and_route_passed"] is True
    assert evidence["deployment_gates"]["current_bitstream_generated"] is True
    assert evidence["deployment_gates"]["current_petalinux_image_built"] is True
    assert evidence["deployment_gates"]["current_sources_run_on_arm_board"] is True
    assert evidence["deployment_gates"]["current_sources_live_rf_acceptance"] is False
