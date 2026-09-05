import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-product-integration-v1.json"


def test_old_build_evidence_rejects_changed_product_sources() -> None:
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "scripts/verify_st06_product_integration.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode != 0
    assert "güncel kaynak ve çıktılarla eşleşmiyor" in completed.stdout


def test_st06_product_image_closes_build_but_not_physical_acceptance() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    assert evidence["build"]["package"]["tasks_failed"] == 0
    assert evidence["build"]["full_image"]["tasks_failed"] == 0
    assert evidence["hardware_input"]["slice_lut_utilization_percent"] < 50.0
    assert evidence["gates"]["current_routed_fpga_input"] is True
    assert evidence["gates"]["current_arm_sources_packaged"] is True
    assert evidence["gates"]["full_product_image_built"] is True
    assert evidence["gates"]["cold_boot_product_image_on_board"] is False
    assert evidence["gates"]["physical_product_service_lifecycle"] is False
    assert evidence["gates"]["controlled_blind_rf_accuracy"] is False
