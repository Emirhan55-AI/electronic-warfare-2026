from __future__ import annotations

import json
from pathlib import Path
import unittest

from verification.phase04f4_analysis import build_analysis


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f4" / "f4a-analysis.json"


class Phase04F4AAnalysisTests(unittest.TestCase):
    def test_stored_analysis_is_current_and_reproduces_f3d(self) -> None:
        stored = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_analysis())
        self.assertEqual("passed", stored["status"])
        self.assertTrue(stored["recorded_decisions_reproduced"])
        self.assertEqual("failed", stored["f3d_evaluation_status"])

    def test_nfm_failure_is_abstention_and_not_wrong_decision(self) -> None:
        analysis = build_analysis()
        oos = analysis["nfm_6_db"]["oos"]
        self.assertEqual(44, oos["correct"])
        self.assertEqual(0, oos["wrong"])
        self.assertEqual(20, oos["abstained"])
        self.assertEqual(4, oos["correct_deficit"])
        causes = {item["id"]: item["status"] for item in analysis["root_causes"]}
        self.assertEqual("confirmed", causes["F4A-01"])
        self.assertEqual("not-identifiable-from-stored-evidence", causes["F4A-04"])

    def test_protected_f3_inputs_have_sha256_bindings(self) -> None:
        analysis = build_analysis()
        self.assertGreaterEqual(len(analysis["protected_inputs"]), 11)
        self.assertTrue(all(len(value) == 64 for value in analysis["protected_inputs"].values()))


if __name__ == "__main__":
    unittest.main()
