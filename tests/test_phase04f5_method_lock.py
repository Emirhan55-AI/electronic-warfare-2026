from __future__ import annotations

import json
import unittest

from scripts.lock_phase04f5_method import METHOD_LOCK_PATH, build_lock


class Phase04F5MethodLockTests(unittest.TestCase):
    def test_method_lock_is_current_and_precedes_reveal(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertFalse((METHOD_LOCK_PATH.parent / "evaluation-seeds.json").exists())
        self.assertEqual(stored, build_lock())
        self.assertEqual("locked-before-seed-reveal", stored["status"])
        self.assertFalse(stored["seed_revealed"])

    def test_method_payload_and_obw_constants_are_bounded(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        constants = stored["constants"]
        self.assertLessEqual(constants["combined_persistent_payload_bytes"], 65_536)
        self.assertEqual(0.0075, constants["obw"]["tail_fraction"])
        self.assertEqual(0.375, constants["obw"]["edge_expansion_bins"])
        self.assertEqual(7.0, constants["obw"]["temporal_range_maximum_bins"])
        self.assertIn("development_results_sha256", stored["contracts"])
        self.assertIn("obw_analysis_sha256", stored["contracts"])


if __name__ == "__main__":
    unittest.main()
