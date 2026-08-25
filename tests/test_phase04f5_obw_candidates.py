from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "obw-candidate-analysis-v6.json"


class Phase04F5ObwCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    def test_no_simple_temporal_limit_candidate_is_selected(self) -> None:
        self.assertEqual("no-candidate-passed", self.result["status"])
        self.assertIsNone(self.result["selected_temporal_recovery_limit_bins"])
        self.assertEqual([3.0, 3.25, 3.5, 4.0, 5.0], [item["temporal_recovery_limit_bins"] for item in self.result["candidates"]])
        self.assertTrue(all(item["status"] == "failed" for item in self.result["candidates"]))

    def test_widest_candidate_retains_locked_failure_evidence(self) -> None:
        widest = self.result["candidates"][-1]
        metrics = widest["metrics"]
        self.assertEqual(377, metrics["obw.family_min_valid_count_12_db"])
        self.assertEqual(46, metrics["obw.seed_min_valid_count_12_db"])
        self.assertGreater(metrics["obw.family_max_upper_edge_q95_bins_12_db"], 2.0)
        self.assertEqual(380, widest["families"]["nfm"]["valid_count"])


if __name__ == "__main__":
    unittest.main()
