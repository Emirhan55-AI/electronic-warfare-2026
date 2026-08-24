from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from algorithms.parameters.f1_evaluation import _oos_adapter_gates, compare_results
from scripts.reveal_phase04f1_seeds import verify_reveal
from scripts.lock_phase04f1_evaluation_runner import LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1EvaluationRunnerTests(unittest.TestCase):
    def test_runner_lock_matches_sources_before_reveal(self) -> None:
        stored = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual("locked-before-seed-reveal", stored["status"])
        reveal_path = ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-seeds.json"
        if reveal_path.exists():
            for source in stored["source_manifest"]["sources"]:
                digest = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
                self.assertEqual(source["sha256"], digest)
            self.assertTrue(verify_reveal(json.loads(reveal_path.read_text(encoding="utf-8"))))
        else:
            self.assertEqual(stored, build_lock())

    def test_oos_count_gates_are_adapted_without_relaxing_locked_counts(self) -> None:
        acceptance = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase04f1" / "acceptance-gates.json").read_text(encoding="utf-8")
        )
        adapted = _oos_adapter_gates(acceptance["oos"], acceptance["binding"])
        self.assertEqual(32, adapted["trials_per_family"])
        self.assertEqual(28 / 32, adapted["emission_center_frequency"]["family_valid_minimum"])
        self.assertEqual(31 / 32, adapted["occupied_bandwidth"]["family_valid_minimum"])
        self.assertEqual(24 / 32, adapted["signal_domain"]["family_correct_definite_minimum"])
        self.assertEqual(1 / 32, adapted["signal_domain"]["family_wrong_definite_maximum"])

    def test_stored_comparison_matches_the_one_shot_population_results(self) -> None:
        evidence = ROOT / "results" / "evidence" / "phase04f1"
        comparison_path = evidence / "parameter-comparison.json"
        if not comparison_path.is_file():
            self.skipTest("one-shot evaluation has not run")
        binding = json.loads((evidence / "binding-results.json").read_text(encoding="utf-8"))
        oos = json.loads((evidence / "oos-results.json").read_text(encoding="utf-8"))
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        self.assertEqual(comparison, compare_results(binding, oos))


if __name__ == "__main__":
    unittest.main()
