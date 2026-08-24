from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.develop_phase04f1_domain import build_model


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1DevelopmentTests(unittest.TestCase):
    def test_fixed_domain_model_is_reproducible(self) -> None:
        stored = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase04f1" / "domain-model.json").read_text(encoding="utf-8")
        )
        self.assertEqual(stored, build_model())
        self.assertEqual("development-only", stored["status"])

    def test_historical_development_evidence_remains_unchanged_after_reveal(self) -> None:
        evidence = json.loads(
            (ROOT / "results" / "evidence" / "phase04f1" / "development-results.json").read_text(encoding="utf-8")
        )
        self.assertEqual("passed", evidence["status"])
        self.assertTrue(all(value == "passed" for value in evidence["field_decisions"].values()))
        reveal_path = ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-seeds.json"
        if reveal_path.exists():
            self.assertTrue(
                (ROOT / "results" / "evidence" / "phase04f1" / "f1d-run-started.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()
