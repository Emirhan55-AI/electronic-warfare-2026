import hashlib
import json

from scripts.verify_st06_product_optimization import verify_historical_sources
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-wideband-stream-v4.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stream_evidence_has_bounded_state_and_exact_sliding_results() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["schema"] == "phase08-st06-wideband-stream-v4"
    assert evidence["status"] == "passed"
    assert evidence["st06_stream_lifecycle_complete"] is True
    assert evidence["st06_complete"] is False
    assert evidence["state_bytes"] == 328840
    assert evidence["streams"] == 120
    assert evidence["evaluated_sliding_windows"] == 1080
    assert evidence["warmup_validity_errors"] == 0
    assert evidence["stream_mismatches"] == 0
    assert evidence["mismatch_details"] == []
    assert evidence["reset_checks"] == 120
    assert evidence["invalid_update_transaction_checks"] == 1
    assert evidence["supersedes"] == "results/evidence/phase08/st06-wideband-stream-v3.json"


def test_stream_evidence_retains_historical_sources_and_keeps_product_open() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["product_algorithm_changed"] is False
    assert evidence["transmit_enabled"] is False
    verify_historical_sources(evidence)
