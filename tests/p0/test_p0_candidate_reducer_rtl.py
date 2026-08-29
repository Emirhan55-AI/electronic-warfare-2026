from __future__ import annotations

import json
from pathlib import Path

from algorithms.rtl.p0_candidate_reducer_vectors import build_vector_files
from scripts.verify_p0_candidate_reducer_rtl import EVIDENCE_PATH, evaluate


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "datasets/fixtures/p0_candidate_reducer"


def test_candidate_reducer_vector_files_are_deterministic_and_current() -> None:
    generated = build_vector_files()

    assert generated == build_vector_files()
    for name, payload in generated.items():
        assert (FIXTURE / name).read_bytes() == payload
    golden = json.loads(generated["golden-vectors.json"])
    assert golden["status"] == "passed"
    assert golden["frame_count"] == 5


def test_parallel_region_median_rtl_is_bit_true_and_within_substage_budget() -> None:
    observed = evaluate()
    recorded = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert observed == recorded
    assert observed["status"] == "passed"
    assert observed["vectors"]["median_mismatches"] == 0
    assert observed["latency"]["maximum_processing_cycles"] <= 30000
    assert "substage only" in observed["claim_boundary"]
