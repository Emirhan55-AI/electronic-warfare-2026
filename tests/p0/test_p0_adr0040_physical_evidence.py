import json
from pathlib import Path

from scripts.verify_p0_adr0040_physical import EXPECTED_FUNCTIONAL, check


ROOT = Path(__file__).resolve().parents[2]


def test_adr0040_physical_evidence_is_current_and_keeps_rf_claim_open() -> None:
    assert check()
    evidence = json.loads(
        (ROOT / "results/evidence/p0/adr0040-physical-acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    throughput = evidence["throughput_acceptance"]
    assert throughput["completed_measured_frames"] == 20_480
    assert throughput["minimum_frames_per_second"] >= 488.28125
    assert throughput["client_sequence_errors"] == 0
    assert evidence["profile"]["maximum_tracked_weak_nominations_per_frame"] == 8

    functional = tuple(
        (
            item["raw_candidate_count"],
            item["active_count"],
            item["ended_count"],
            item["dropped_candidates"],
            item["reset_applied"],
        )
        for item in evidence["functional_acceptance"]
    )
    assert functional == EXPECTED_FUNCTIONAL
    assert "kör RF" in evidence["claim_boundary"]
    assert "ayrıca saha kabulü gerektirir" in evidence["claim_boundary"]
