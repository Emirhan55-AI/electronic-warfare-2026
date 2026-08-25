from __future__ import annotations

import json
from pathlib import Path
import unittest

from algorithms.parameters.f5_estimator import F5ParameterEstimator
from verification.phase04f5_scoring import REQUIRED_DIAGNOSTICS


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "development-results-v6.json"


class Phase04F5DevelopmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    def test_all_locked_development_checks_passed(self) -> None:
        scoring = self.result["scoring"]
        groups = (
            scoring["base_scoring"]["checks"],
            scoring["f3_inherited_risk_checks"],
            scoring["f4_additional_risk_checks"],
            scoring["f5_additional_risk_checks"],
        )
        self.assertEqual("passed", self.result["status"])
        self.assertEqual((40, 14, 4, 7), tuple(len(group) for group in groups))
        self.assertTrue(all(item["status"] == "passed" for group in groups for item in group))

    def test_selected_calibration_matches_estimator(self) -> None:
        selected = self.result["selected_obw_calibration"]
        self.assertEqual(F5ParameterEstimator.OBW_TAIL_FRACTION_V6, selected["tail_fraction"])
        self.assertEqual(F5ParameterEstimator.OBW_EDGE_EXPANSION_BINS_V6, selected["edge_expansion_bins"])
        self.assertEqual(
            F5ParameterEstimator.OBW_TEMPORAL_RANGE_MAXIMUM_V6,
            selected["temporal_range_maximum_bins"],
        )

    def test_obw_risk_and_required_diagnostics_are_present(self) -> None:
        metrics = self.result["f5_additional_risk_metrics"]
        self.assertGreaterEqual(metrics["obw.family_min_valid_count_12_db"], 379)
        self.assertGreaterEqual(metrics["obw.seed_min_valid_count_12_db"], 47)
        self.assertLessEqual(metrics["obw.family_max_lower_edge_q95_bins_12_db"], 2.0)
        self.assertLessEqual(metrics["obw.family_max_upper_edge_q95_bins_12_db"], 2.0)
        diagnostics = self.result["diagnostics"]
        self.assertTrue(set(REQUIRED_DIAGNOSTICS).issubset(diagnostics))
        outcomes = diagnostics["obw.recovery_outcome_counts_12_db"]
        recovered = sum(row.get("recovered_parent_invalid", 0) for row in outcomes.values())
        self.assertGreater(recovered, 0)

    def test_negative_controls_remain_fail_closed(self) -> None:
        noise = {
            key: value for key, value in self.result["inherited_risk_metrics"].items()
            if key.startswith("noise.")
        }
        self.assertEqual(6, len(noise))
        self.assertTrue(all(value == 0 for value in noise.values()))


if __name__ == "__main__":
    unittest.main()
