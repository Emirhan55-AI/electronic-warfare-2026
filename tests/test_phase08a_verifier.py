from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase08a.py"
SPEC = importlib.util.spec_from_file_location("verify_phase08a", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-08A verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase08AVerifierTests(unittest.TestCase):
    def test_summary_has_honest_hardware_boundary(self) -> None:
        summary = VERIFY.build_summary()
        self.assertEqual("passed", summary["status"])
        self.assertEqual("not_exercised", summary["hardware_status"])
        self.assertEqual("not_exercised", summary["live_rx_status"])
        self.assertEqual("phase03-operation-default", summary["runtime_profile"])
        self.assertEqual("detector.regional", summary["detector"])
        self.assertNotIn("timestamp", json.dumps(summary).casefold())

    def test_verifier_check_is_read_only(self) -> None:
        before = subprocess.run(["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, check=True).stdout
        completed = subprocess.run([sys.executable, "-B", str(VERIFY_PATH), "--check"], cwd=ROOT, check=False)
        after = subprocess.run(["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, check=True).stdout
        self.assertEqual(0, completed.returncode)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
