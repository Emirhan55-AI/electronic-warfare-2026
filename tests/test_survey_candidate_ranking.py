from app.operator_console.survey_controller import _rank_observation_rows


def test_repeatable_high_contrast_candidates_rank_above_recent_weak_rows():
    rows = [
        {"eventId": "weak-new", "frequencyHz": 900e6, "evidenceKey": "dual_tune",
         "qualityScore": 82.0, "latestWindow": True},
        {"eventId": "strong-old", "frequencyHz": 433e6, "evidenceKey": "dual_tune",
         "qualityScore": 113.0, "latestWindow": False},
    ]

    ranked = _rank_observation_rows(rows)

    assert [row["eventId"] for row in ranked] == ["strong-old", "weak-new"]


def test_controlled_comparison_evidence_outranks_unattributed_energy():
    rows = [
        {"eventId": "energy", "frequencyHz": 1.2e9, "evidenceKey": "energy_candidate",
         "qualityScore": 200.0},
        {"eventId": "changed", "frequencyHz": 1.8e9, "evidenceKey": "ab_candidate",
         "qualityScore": 80.0},
    ]

    ranked = _rank_observation_rows(rows)

    assert [row["eventId"] for row in ranked] == ["changed", "energy"]
