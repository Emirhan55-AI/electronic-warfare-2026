from __future__ import annotations

import json
import hashlib
from pathlib import Path
import unittest

from scripts.lock_phase04f2_method import METHOD_LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F2MethodLockTests(unittest.TestCase):
    def test_method_lock_is_current_and_precedes_reveal(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        reveal_path = METHOD_LOCK_PATH.parent / "evaluation-seeds.json"
        if reveal_path.exists():
            for source in stored["implementation"]["sources"]:
                self.assertEqual(source["sha256"], hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest())
            self.assertEqual("locked-before-seed-reveal", stored["status"])
            self.assertFalse(stored["seed_revealed"])
        else:
            self.assertEqual(stored, build_lock())

    def test_open_development_evidence_passed_all_locked_checks(self) -> None:
        result = json.loads(
            (ROOT / "results" / "evidence" / "phase04f2" / "development-results-v3.json").read_text(encoding="utf-8")
        )
        acceptance = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json").read_text(encoding="utf-8")
        )
        self.assertEqual("passed", result["status"])
        self.assertEqual(40, len(result["scoring"]["checks"]))
        self.assertEqual(
            {item["metric"] for item in acceptance["checks"]["binding"]},
            set(result["metrics"]),
        )


if __name__ == "__main__":
    unittest.main()
