from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Phase04F3DevelopmentTests(unittest.TestCase):
    def test_open_development_passed_all_locked_checks(self) -> None:
        result = json.loads(
            (ROOT / "results" / "evidence" / "phase04f3" / "development-results-v4.json").read_text(encoding="utf-8")
        )
        self.assertEqual("development-only", result["role"])
        self.assertEqual("passed", result["status"])
        base_checks = result["scoring"]["base_scoring"]["checks"]
        risk_checks = result["scoring"]["risk_checks"]
        self.assertEqual(40, len(base_checks))
        self.assertEqual(14, len(risk_checks))
        self.assertTrue(all(item["status"] == "passed" for item in base_checks + risk_checks))

    def test_seed_robustness_has_no_ook_wrong_decision_or_false_carrier(self) -> None:
        result = json.loads(
            (ROOT / "results" / "evidence" / "phase04f3" / "development-results-v4.json").read_text(encoding="utf-8")
        )
        risk = result["risk_metrics"]
        self.assertEqual(0, risk["carrier.nonapplicable.aggregate_false_valid_count_12_db"])
        self.assertEqual(0, risk["domain.ook.aggregate_wrong_count_6_db"])
        self.assertGreaterEqual(risk["carrier.ook.seed_min_valid_count_12_db"], 45)
        self.assertGreaterEqual(risk["domain.ook.seed_min_correct_count_6_db"], 40)


if __name__ == "__main__":
    unittest.main()
