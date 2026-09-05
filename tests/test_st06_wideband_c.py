import ctypes
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

from algorithms.p0.st05_wideband import ST05WidebandDetector
from scripts.evaluate_st05_wideband import _frames
from scripts.verify_st06_wideband_c import (
    CONTRACT,
    CResult,
    ST05_EVIDENCE,
    _close_library,
    _compile,
    _configure,
    _run_sequence,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-wideband-c-equivalence-v3.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_st06_evidence_is_source_bound_and_keeps_hardware_acceptance_open() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["schema"] == "phase08-st06-wideband-c-equivalence-v3"
    assert evidence["status"] == "passed"
    assert evidence["st06_c_ps_reference_complete"] is True
    assert evidence["st06_complete"] is False
    assert evidence["arm_execution_performed"] is False
    assert evidence["rtl_implementation_present"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["transmit_enabled"] is False
    assert evidence["supersedes"] == "results/evidence/phase08/st06-wideband-c-equivalence-v2.json"
    for relative, expected in evidence["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_full_frozen_corpus_has_exact_decision_and_boundary_equivalence() -> None:
    evidence = _load(EVIDENCE)
    st05 = _load(ST05_EVIDENCE)

    assert evidence["corpus"]["sequences"] == len(st05["records"]) == 960
    assert evidence["corpus"]["frames"] == 7680
    assert evidence["corpus"]["input_hash_mismatches"] == 0
    assert evidence["equivalence"]["sequence_mismatches"] == 0
    assert evidence["equivalence"]["mismatch_details"] == []
    assert all(item["matched"] for item in evidence["records"])
    assert evidence["api_boundary_checks"]["status"] == "passed"


def test_compiled_c_matches_python_for_each_decision_family() -> None:
    contract = _load(CONTRACT)
    selected = {
        "noise-flat",
        "bounded-1024",
        "strong-weak-near",
        "close-merge",
        "edge-left",
        "full-window",
        "transient-two-of-eight",
        "persistent-six-of-eight",
    }
    detector = ST05WidebandDetector()
    with tempfile.TemporaryDirectory(prefix="test-st06-wideband-c-") as raw:
        library_path, _, _ = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = _configure(library)
        try:
            for scene_index, scene in enumerate(contract["scenes"]):
                if scene["id"] not in selected:
                    continue
                seed = int(contract["holdout_seed_base"]) + scene_index * 10_000
                frames = _frames(
                    scene,
                    seed=seed,
                    count=int(contract["frames_per_sequence"]),
                )
                _, mismatches, _, _ = _run_sequence(function, detector, frames)
                assert mismatches == []
        finally:
            del function
            _close_library(library)


def test_c_api_rejects_an_oversized_temporal_buffer() -> None:
    frames = np.ones((65, 4096), dtype=np.float64)
    result = CResult()
    with tempfile.TemporaryDirectory(prefix="test-st06-wideband-c-limit-") as raw:
        library_path, _, _ = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = _configure(library)
        try:
            status = function(
                frames.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                frames.shape[0],
                frames.shape[1],
                ctypes.byref(result),
            )
            assert status == -1
        finally:
            del function
            _close_library(library)
