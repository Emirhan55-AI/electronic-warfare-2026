"""Binding-free preflight tests for PHASE-04-D1F evaluation mathematics."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from reference.parameters.obw99_evaluation import (
    _binding_decision,
    _oos_decision,
    summarize_expected_trials,
    verify_evaluation_lock,
)
from reference.parameters.obw99_reference import load_json


ROOT = Path(__file__).resolve().parents[1]


def _family(identifier: str, trials: int) -> dict:
    records = [
        {
            "state": "valid",
            "relative_error": 0.1,
            "lower_error_bins": 0.5,
            "upper_error_bins": 0.5,
            "analysis_clipped": False,
            "quality_reasons": [],
        }
        for _ in range(trials)
    ]
    summary = summarize_expected_trials(records)
    summary["family_id"] = identifier
    summary["_relative_obw_error_values"] = [0.1] * trials
    summary["_lower_edge_error_bins_values"] = [0.5] * trials
    summary["_upper_edge_error_bins_values"] = [0.5] * trials
    return summary


class Phase04D1EvaluationTests(unittest.TestCase):
    def test_nearest_rank_summary_and_invalid_denominator(self) -> None:
        records = [
            {"state": "valid", "relative_error": value, "lower_error_bins": value, "upper_error_bins": value, "analysis_clipped": False, "quality_reasons": []}
            for value in range(1, 20)
        ]
        records.append({"state": "insufficient_quality", "analysis_clipped": False, "quality_reasons": ["temporal_warmup"]})
        summary = summarize_expected_trials(records)
        self.assertEqual(summary["valid_count"], 19)
        self.assertEqual(summary["invalid_or_abstention_count"], 1)
        self.assertEqual(summary["valid_rate"], 0.95)
        self.assertEqual(summary["relative_obw_error"]["rank"], 19)
        self.assertEqual(summary["relative_obw_error"]["q95"], 19.0)

    def test_binding_decision_enforces_each_family_valid_rate(self) -> None:
        gates = load_json(ROOT / "datasets/fixtures/phase04d1/acceptance-gates.json")
        families = [_family(f"family-{index}", 128) for index in range(8)]
        close = {"separation_rate": 1.0, "cross_match_rate": 0.0, "cross_match_count": 0}
        noise = {"false_valid_rate": 0.0}
        decisions, passed = _binding_decision(copy.deepcopy(families), close, noise, gates)
        self.assertTrue(passed)
        broken = copy.deepcopy(families)
        broken[3]["valid_count"] = 120
        broken[3]["invalid_or_abstention_count"] = 8
        broken[3]["valid_rate"] = 0.9375
        decisions, passed = _binding_decision(broken, close, noise, gates)
        self.assertFalse(passed)
        self.assertTrue(any(item["scope"] == "family-3" and item["status"] == "failed" for item in decisions))

    def test_oos_decision_cannot_hide_one_failed_family(self) -> None:
        gates = load_json(ROOT / "datasets/fixtures/phase04d1/acceptance-gates.json")
        families = [_family(f"family-{index}", 32) for index in range(8)]
        families[2]["valid_count"] = 30
        families[2]["invalid_or_abstention_count"] = 2
        families[2]["valid_rate"] = 0.9375
        close = {"separation_rate": 1.0, "cross_match_count": 0}
        noise = {"false_valid_frames": 0}
        decisions, passed = _oos_decision(families, close, noise, gates)
        self.assertFalse(passed)
        self.assertTrue(any(item["scope"] == "family-2" and item["status"] == "failed" for item in decisions))

    def test_evaluation_lock_matches_every_current_input_and_source(self) -> None:
        lock = load_json(ROOT / "datasets/fixtures/phase04d1/evaluation-lock.json")
        verify_evaluation_lock(lock)

    def test_evaluator_does_not_pass_labels_to_runtime_estimator(self) -> None:
        source = (ROOT / "reference/parameters/obw99_evaluation.py").read_text(encoding="utf-8")
        start = source.index("estimator.process(")
        end = source.index("\n        )", start) + len("\n        )")
        call = source[start:end]
        for forbidden in ("truth", "family", "scene", "snr", "modulation"):
            self.assertNotIn(forbidden, call.lower())


if __name__ == "__main__":
    unittest.main()
