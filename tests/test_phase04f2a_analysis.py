from __future__ import annotations

import json
from pathlib import Path
import unittest

from verification.phase04f2_analysis import build_analysis


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "evidence" / "phase04f2" / "f2a-analysis.json"


class Phase04F2AFailureAnalysisTests(unittest.TestCase):
    def test_stored_analysis_is_current_and_reproduces_f1_decisions(self) -> None:
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_analysis())
        self.assertEqual("passed", stored["status"])
        self.assertEqual("failed", stored["f1_evaluation_status"])
        self.assertTrue(stored["checks"]["recorded_field_decisions_reproduced"])
        self.assertTrue(stored["checks"]["stored_comparison_reproduced"])

    def test_protocol_coverage_gaps_and_failure_classes_are_explicit(self) -> None:
        analysis = build_analysis()
        missing = {item["gate"] for item in analysis["protocol_scorer_coverage"] if item["status"] == "not_evaluated"}
        self.assertEqual(
            {
                "binding.carrier_line_frequency.abstention_rate_minimum",
                "binding.noise_frames_per_sequence",
                "oos.noise_frames_per_sequence",
            },
            missing,
        )
        self.assertEqual(
            {"F2A-01", "F2A-02", "F2A-03", "F2A-04", "F2A-05"},
            {item["id"] for item in analysis["findings"]},
        )

    def test_revealed_f1_population_is_not_declared_as_f2_training_data(self) -> None:
        analysis = build_analysis()
        self.assertFalse(analysis["checks"]["f1_reveal_used_for_method_tuning"])
        self.assertFalse(analysis["checks"]["f1_locked_sources_modified"])


if __name__ == "__main__":
    unittest.main()
