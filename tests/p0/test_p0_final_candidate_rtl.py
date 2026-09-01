from __future__ import annotations

import json
from pathlib import Path

from algorithms.rtl.p0_final_candidate_vectors import build_vector_files as build_final_files
from algorithms.rtl.p0_sparse_os_candidate_vectors import build_vector_files as build_sparse_files
from scripts.verify_p0_final_candidate_rtl import EVIDENCE_PATH, evaluate


ROOT = Path(__file__).resolve().parents[2]
SPARSE_FIXTURE = ROOT / "datasets/fixtures/p0_sparse_os_candidate"
FINAL_FIXTURE = ROOT / "datasets/fixtures/p0_final_candidate"


def test_sparse_and_final_vector_files_are_deterministic_and_current() -> None:
    for fixture, generated in (
        (SPARSE_FIXTURE, build_sparse_files()),
        (FINAL_FIXTURE, build_final_files()),
    ):
        for name, payload in generated.items():
            assert (fixture / name).read_bytes() == payload
    sparse = json.loads(build_sparse_files()["golden-vectors.json"])
    final = json.loads(build_final_files()["golden-vectors.json"])
    assert sparse["semantic_candidates"] == 151
    assert sparse["output_records"] == 157
    assert final["semantic_candidates"] == 63
    assert final["output_records"] == 65


def test_final_candidate_reducer_is_bit_true_and_within_functional_budget() -> None:
    observed = evaluate()
    recorded = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert observed == recorded
    assert observed["status"] == "passed"
    assert observed["sparse_os_candidates"]["candidate_metadata_mismatches"] == 0
    assert observed["final_candidates"]["candidate_metadata_mismatches"] == 0
    assert observed["final_candidates"]["wideband_overlap_suppression_checked"] is True
    assert observed["guards"]["maximum_os_candidate_records"] == 1352
    assert observed["guards"]["fusion_overflow_failed_closed"] is True
    assert observed["capacity"]["maximum_sequential_functional_cycles"] < 102400
    assert "physical real-time acceptance remain open" in observed["claim_boundary"]
