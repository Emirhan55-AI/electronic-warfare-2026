from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PATH = ROOT / "results" / "evidence" / "phase04f3" / "f3a-analysis.json"


class Phase04F3AAnalysisTests(unittest.TestCase):
    def test_stored_analysis_reproduces_decisions_and_open_counts(self) -> None:
        analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
        self.assertEqual("passed", analysis["status"])
        self.assertEqual("failed", analysis["f2d_evaluation_status"])
        self.assertTrue(analysis["recorded_decisions_reproduced"])
        self.assertTrue(analysis["open_seed_diagnostics"]["stored_development_counts_reproduced"])
        self.assertEqual(3, len(analysis["root_causes"]))

    def test_protected_f2_inputs_match_analysis_digests(self) -> None:
        analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
        for relative, digest in analysis["protected_inputs"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
