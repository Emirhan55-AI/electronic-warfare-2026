from __future__ import annotations

import json
from pathlib import Path
import unittest

from algorithms.parameters.f5_evaluation import _oos_metrics, compare_results
from scripts.lock_phase04f5_evaluation_runner import LOCK_PATH, build_lock
from verification.phase04f2_scoring import score_population


ROOT = Path(__file__).resolve().parents[1]


class Phase04F5EvaluationRunnerTests(unittest.TestCase):
    def test_runner_lock_matches_sources_before_reveal(self) -> None:
        stored = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        reveal_path = ROOT / "datasets" / "fixtures" / "phase04f5" / "evaluation-seeds.json"
        self.assertFalse(reveal_path.exists())
        self.assertEqual(stored, build_lock())

    def test_oos_metrics_have_exact_locked_coverage(self) -> None:
        result = json.loads(
            (ROOT / "results" / "evidence" / "phase04f5" / "development-results-v6.json").read_text(encoding="utf-8")
        )
        acceptance = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json").read_text(encoding="utf-8")
        )
        adapted = _oos_metrics(result, acceptance)
        expected = {item["metric"] for item in acceptance["checks"]["oos"]}
        self.assertEqual(expected, set(adapted))
        self.assertIn(score_population(adapted, acceptance, "oos")["status"], {"passed", "failed"})

    def test_stored_comparison_matches_one_shot_results_when_present(self) -> None:
        evidence = ROOT / "results" / "evidence" / "phase04f5"
        comparison_path = evidence / "parameter-comparison-v6.json"
        if not comparison_path.is_file():
            self.skipTest("one-shot F5D evaluation has not run")
        binding = json.loads((evidence / "binding-results-v6.json").read_text(encoding="utf-8"))
        oos = json.loads((evidence / "oos-results-v6.json").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(comparison_path.read_text(encoding="utf-8")), compare_results(binding, oos))


if __name__ == "__main__":
    unittest.main()
