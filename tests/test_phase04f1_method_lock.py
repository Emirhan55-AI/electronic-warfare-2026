from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from scripts.lock_phase04f1_method import METHOD_LOCK_PATH, build_lock


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1MethodLockTests(unittest.TestCase):
    def test_method_lock_matches_implementation_and_precedes_reveal(self) -> None:
        stored = json.loads(METHOD_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual("locked-before-seed-reveal", stored["status"])
        self.assertFalse(stored["seed_revealed"])
        reveal_path = ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-seeds.json"
        if reveal_path.exists():
            for source in stored["implementation"]["sources"]:
                digest = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
                self.assertEqual(source["sha256"], digest)
            runner_lock = json.loads(
                (ROOT / "datasets" / "fixtures" / "phase04f1" / "evaluation-runner-lock.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                runner_lock["method_lock_sha256"],
                hashlib.sha256(METHOD_LOCK_PATH.read_bytes()).hexdigest(),
            )
        else:
            self.assertEqual(stored, build_lock())


if __name__ == "__main__":
    unittest.main()
