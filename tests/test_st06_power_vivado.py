import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-power-vivado-v1.json"


def test_st06_power_vivado_evidence_is_source_bound() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_st06_power_vivado.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_st06_power_option_meets_route_and_resource_gates() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    assert evidence["product_algorithm_changed"] is False
    assert evidence["st06_complete"] is False
    assert evidence["route"]["routing_errors"] == 0
    assert evidence["timing"]["setup_failing_endpoints"] == 0
    assert evidence["timing"]["hold_failing_endpoints"] == 0
    assert evidence["dma"]["output_fits_length_field"] is True
    assert evidence["post_route_resources"]["slice_luts"]["utilization_percent"] < 50.0
    assert evidence["p03_comparison"]["resource_delta"]["slice_luts"]["absolute"] < 0.0
