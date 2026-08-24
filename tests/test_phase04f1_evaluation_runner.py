from __future__ import annotations

import json
from pathlib import Path
import unittest

from algorithms.parameters.f1_evaluation import _oos_adapter_gates
from scripts.lock_phase04f1_evaluation_runner import LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1EvaluationRunnerTests(unittest.TestCase):
    def test_runner_lock_matches_sources_before_reveal(self) -> None:
        stored = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_lock())
        self.assertEqual("locked-before-seed-reveal", stored["status"])

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


if __name__ == "__main__":
    unittest.main()
