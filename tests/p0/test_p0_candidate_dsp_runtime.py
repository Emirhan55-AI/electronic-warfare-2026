from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_p0_candidate_dsp_runtime import EVIDENCE_PATH, evaluate


ROOT = Path(__file__).resolve().parents[2]


def test_complete_candidate_runtime_compile_boundary_is_current() -> None:
    observed = evaluate()
    recorded = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert observed == recorded
    assert observed["status"] == "passed"
    assert observed["top"] == "p0_candidate_dsp_runtime_top"
    assert observed["functional_simulation"] == "not_run_in_compile_gate"
    assert "live HackRF processing" in observed["claim_boundary"]


def test_hann_coefficients_use_vivado_ooc_basename() -> None:
    runtime = (
        ROOT / "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_top.sv"
    ).read_text(encoding="utf-8")

    assert '.COEFFICIENT_FILE("hann-coefficients.mem")' in runtime
    assert '.COEFFICIENT_FILE("datasets/fixtures/phase06b/hann-coefficients.mem")' not in runtime
