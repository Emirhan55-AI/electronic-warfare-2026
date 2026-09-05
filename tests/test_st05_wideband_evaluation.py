import hashlib
import json
from pathlib import Path

from scripts.evaluate_st05_wideband import evaluate


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/st05_wideband_evaluation.json"
EVIDENCE = ROOT / "results/evidence/phase08/st05-wideband-holdout-v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_was_frozen_before_the_holdout_and_covers_required_families() -> None:
    contract = _load(CONTRACT)

    assert contract["status"] == "frozen_before_holdout"
    assert contract["frames_per_sequence"] == 8
    assert contract["trials_per_scene"] == 64
    assert {scene["family"] for scene in contract["scenes"]} == {
        "negative",
        "positive",
        "separation",
        "merge",
        "edge",
        "identifiability",
        "temporal_negative",
        "temporal_positive",
    }


def test_evidence_is_source_bound_and_keeps_product_acceptance_open() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["schema"] == "phase08-st05-wideband-holdout-v2"
    assert evidence["status"] == "python_reference_selected"
    assert evidence["st05_complete"] is True
    assert evidence["st06_complete"] is False
    assert evidence["product_algorithm_changed"] is False
    assert evidence["transmit_enabled"] is False
    assert evidence["supersedes"] == "results/evidence/phase08/st05-wideband-holdout-v1.json"
    assert evidence["contract_sha256"] == hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    for relative, expected in evidence["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_holdout_is_complete_unique_and_all_predeclared_gates_pass() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    expected_records = len(contract["scenes"]) * contract["trials_per_scene"]

    assert len(evidence["records"]) == expected_records == 960
    assert len({(item["scene"], item["trial"]) for item in evidence["records"]}) == expected_records
    assert len({item["seed"] for item in evidence["records"]}) == expected_records
    assert all(evidence["gate_results"].values())
    proposed = evidence["summaries"]["proposed"]["families"]
    assert proposed["negative"]["bounded_candidate_events"] == 0
    assert proposed["edge"]["pass_rate"] == 1.0
    assert proposed["separation"]["pass_rate"] == 1.0
    assert proposed["temporal_negative"]["pass_rate"] == 1.0
    assert sum(item["absolute_absence_claims"] for item in proposed.values()) == 0


def test_current_reference_counterexamples_are_preserved_in_the_comparison() -> None:
    current = _load(EVIDENCE)["summaries"]["current"]["families"]

    assert current["edge"]["pass_rate"] == 0.0
    assert current["identifiability"]["pass_rate"] == 0.0
    assert current["separation"]["pass_rate"] == 0.0
    assert current["temporal_negative"]["pass_rate"] == 0.0


def test_frozen_holdout_recomputes_to_the_recorded_summary() -> None:
    contract = _load(CONTRACT)
    recorded = _load(EVIDENCE)
    recomputed = evaluate(contract)

    assert recomputed["gate_results"] == recorded["gate_results"]
    assert recomputed["summaries"] == recorded["summaries"]
    assert [item["frame_power_sha256"] for item in recomputed["records"]] == [
        item["frame_power_sha256"] for item in recorded["records"]
    ]
