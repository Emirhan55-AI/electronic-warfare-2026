import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-power-runtime-v3.json"


def test_st06_power_runtime_contract_and_lifecycle() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["schema"] == "phase08-st06-power-runtime-v3"
    assert evidence["status"] == "passed"
    assert evidence["st06_power_runtime_complete"] is True
    assert evidence["st06_complete"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["input_contract"] == {
        "bins": 4096,
        "bytes": 32768,
        "natural_order": True,
        "output_marker_required_on_every_word": True,
        "fft_shift_applied_on_arm": True,
    }
    assert evidence["evaluated_sliding_windows"] == 540
    assert evidence["decision_or_shape_mismatches"] == 0
    assert evidence["warmup_or_context_errors"] == 0
    assert evidence["lifecycle"]["passed_checks"] == evidence["lifecycle"][
        "expected_checks"
    ]
