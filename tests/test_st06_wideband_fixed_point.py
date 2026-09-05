import hashlib
import json
from pathlib import Path

from scripts.verify_st06_wideband_fixed_point import (
    MAXIMUM_REACHABLE_POWER,
    SCALE,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-wideband-uq28-30-v4.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_uq28_30_evidence_is_complete_and_source_bound() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["schema"] == "phase08-st06-wideband-uq28-30-v4"
    assert evidence["status"] == "passed"
    assert evidence["st06_fixed_point_boundary_complete"] is True
    assert evidence["st06_complete"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["transmit_enabled"] is False
    assert evidence["supersedes"] == "results/evidence/phase08/st06-wideband-uq28-30-v3.json"
    for relative, expected in evidence["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_quantization_preserves_every_frozen_decision_and_boundary() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["corpus"]["sequences"] == 960
    assert evidence["corpus"]["frames"] == 7680
    assert evidence["corpus"]["source_hash_mismatches"] == 0
    assert evidence["corpus"]["maximum_encoded_power_observed"] <= MAXIMUM_REACHABLE_POWER
    assert evidence["corpus"]["maximum_input_quantization_error"] <= 0.5 / SCALE
    assert evidence["equivalence"][
        "floating_to_uq28_30_decision_or_shape_mismatches"
    ] == 0
    assert evidence["equivalence"]["uq28_30_python_to_c_mismatches"] == 0
    assert evidence["equivalence"]["mismatch_details"] == []
    assert evidence["stress"]["status"] == "passed"
