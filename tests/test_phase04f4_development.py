from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f4" / "development-results-v5.json"


class Phase04F4DevelopmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    def test_all_locked_development_checks_passed(self) -> None:
        scoring = self.result["scoring"]
        base = scoring["base_scoring"]["checks"]
        inherited = scoring["inherited_risk_checks"]
        additional = scoring["additional_risk_checks"]
        self.assertEqual("passed", self.result["status"])
        self.assertEqual((40, 14, 4), (len(base), len(inherited), len(additional)))
        self.assertTrue(all(item["status"] == "passed" for item in base + inherited + additional))

    def test_nfm_seed_risk_and_required_diagnostics_are_present(self) -> None:
        metrics = self.result["additional_risk_metrics"]
        self.assertGreaterEqual(metrics["domain.nfm.seed_min_correct_count_6_db"], 40)
        self.assertLessEqual(metrics["domain.nfm.seed_max_wrong_count_6_db"], 1)
        self.assertLessEqual(metrics["domain.nfm.seed_max_abstained_count_6_db"], 8)
        self.assertLessEqual(metrics["domain.nfm.aggregate_wrong_count_6_db"], 2)
        diagnostics = self.result["diagnostics"]
        for name in (
            "domain.nfm.seed_counts_6_db",
            "domain.nfm.rejection_reason_counts_6_db",
            "domain.nfm.distance_margin_quantiles_6_db",
        ):
            self.assertIn(name, diagnostics)

    def test_negative_controls_remain_fail_closed(self) -> None:
        noise = {
            key: value for key, value in self.result["inherited_risk_metrics"].items()
            if key.startswith("noise.")
        }
        self.assertTrue(noise)
        self.assertTrue(all(value == 0 for value in noise.values()))


if __name__ == "__main__":
    unittest.main()
