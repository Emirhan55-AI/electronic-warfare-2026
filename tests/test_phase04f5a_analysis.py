from __future__ import annotations

import json
from pathlib import Path
import unittest

from verification.phase04f5_analysis import build_analysis


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f5" / "f5a-analysis.json"


class Phase04F5AAnalysisTests(unittest.TestCase):
    def test_stored_analysis_is_current_and_reproduces_f4d(self) -> None:
        stored = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_analysis())
        self.assertEqual("passed", stored["status"])
        self.assertTrue(stored["recorded_decisions_reproduced"])
        self.assertEqual("failed", stored["f4d_evaluation_status"])

    def test_obw_failure_is_temporal_and_lacks_development_margin(self) -> None:
        analysis = build_analysis()
        self.assertEqual("obw_temporal_instability", analysis["failure_isolation"]["remaining_failure_class"])
        self.assertEqual(0, analysis["failure_isolation"]["oos_clipping_count"])
        self.assertEqual(0.90, analysis["acceptance_gap"]["development_family_minimum_rate"])
        self.assertEqual(0.96875, analysis["acceptance_gap"]["oos_family_minimum_rate"])
        self.assertFalse(analysis["acceptance_gap"]["additional_seed_level_obw_validity_gate_present"])
        self.assertEqual(["am", "bpsk"], sorted(analysis["populations"]["development_below_oos_rate_equivalent"]))

    def test_oos_family_counts_and_protected_hashes_are_exact(self) -> None:
        analysis = build_analysis()
        counts = analysis["populations"]["oos"]
        self.assertEqual(61, counts["am"]["valid"])
        self.assertEqual(61, counts["ook"]["valid"])
        self.assertEqual(61, counts["bpsk"]["valid"])
        self.assertGreaterEqual(len(analysis["protected_inputs"]), 16)
        self.assertTrue(all(len(value) == 64 for value in analysis["protected_inputs"].values()))


if __name__ == "__main__":
    unittest.main()
