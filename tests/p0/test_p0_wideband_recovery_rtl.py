from __future__ import annotations

import json
from pathlib import Path

from algorithms.rtl.p0_wideband_recovery_vectors import build_vector_files
from scripts.verify_p0_wideband_recovery_rtl import EVIDENCE_PATH, evaluate


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "datasets/fixtures/p0_wideband_recovery"


def test_wideband_recovery_vector_files_are_deterministic_and_current() -> None:
    generated = build_vector_files()

    assert generated == build_vector_files()
    for name, payload in generated.items():
        assert (FIXTURE / name).read_bytes() == payload
    golden = json.loads(generated["golden-vectors.json"])
    assert golden["status"] == "passed"
    assert golden["frame_count"] == 8
    assert golden["semantic_candidates"] == 24
    assert golden["output_records"] == 27


def test_wideband_recovery_rtl_is_bit_true_and_within_substage_budget() -> None:
    observed = evaluate()
    recorded = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert observed == recorded
    assert observed["status"] == "passed"
    assert observed["vectors"]["candidate_metadata_mismatches"] == 0
    assert observed["vectors"]["out_of_range_frame_failed_closed"] is True
    assert observed["latency"]["maximum_last_input_to_last_output_cycles"] <= 50000
    assert "fusion" in observed["claim_boundary"]
