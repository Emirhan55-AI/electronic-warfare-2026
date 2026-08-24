from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.lock_phase04f1_method import METHOD_LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1MethodLockTests(unittest.TestCase):
    def test_method_lock_matches_implementation_and_precedes_reveal(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored, build_lock())
        self.assertEqual("locked-before-seed-reveal", stored["status"])
        self.assertFalse(stored["seed_revealed"])
        self.assertFalse((ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-seeds.json").exists())


if __name__ == "__main__":
    unittest.main()
