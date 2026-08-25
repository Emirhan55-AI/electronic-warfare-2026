from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.lock_phase04f3_method import METHOD_LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F3MethodLockTests(unittest.TestCase):
    def test_method_lock_is_current_and_precedes_reveal(self) -> None:
        self.assertFalse((METHOD_LOCK_PATH.parent / "evaluation-seeds.json").exists())
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_lock())
        self.assertEqual("locked-before-seed-reveal", stored["status"])
        self.assertFalse(stored["seed_revealed"])

    def test_payload_and_contracts_are_bound(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        constants = stored["constants"]
        self.assertLessEqual(constants["combined_persistent_payload_bytes"], 65_536)
        self.assertEqual(18_880, constants["domain_model_numeric_bytes"])
        self.assertIn("development_results_sha256", stored["contracts"])
        self.assertIn("carrier_analysis_sha256", stored["contracts"])


if __name__ == "__main__":
    unittest.main()
