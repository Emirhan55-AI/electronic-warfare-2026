from __future__ import annotations

import json
import hashlib
from pathlib import Path
import unittest

from scripts.lock_phase04f2_protocol import LOCK_PATH, build_lock
from scripts.prepare_phase04f2_protocol import COMMITMENTS_PATH, SEALED_PATH, verify_preimages
from scripts.verify_phase04f2_protocol import SUMMARY_PATH, build_summary
from verification.phase04f2_scoring import score_population, validate_acceptance


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"


class Phase04F2ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))

    def test_historical_protocol_lock_remains_current_after_v3(self) -> None:
        stored = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        method_lock = ACCEPTANCE_PATH.parent / "method-lock-v3.json"
        if not method_lock.exists():
            self.assertEqual(stored, build_lock())
            self.assertEqual(json.loads(SUMMARY_PATH.read_text(encoding="utf-8")), build_summary())
        else:
            for path, digest in stored["inputs"].items():
                self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
            for path, digest in stored["f1_protected_inputs"].items():
                self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertEqual("passed", json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))["status"])

    def test_all_gates_have_executable_boundary_coverage(self) -> None:
        coverage = validate_acceptance(self.acceptance)
        self.assertEqual("passed", coverage["status"], coverage["problems"])
        self.assertEqual({"binding": 40, "oos": 24}, coverage["check_counts"])

    def test_field_local_noise_failure_does_not_change_other_field_decisions(self) -> None:
        checks = self.acceptance["checks"]["binding"]
        metrics = {check["metric"]: check["threshold"] for check in checks}
        baseline = score_population(metrics, self.acceptance, "binding")
        self.assertEqual("passed", baseline["status"])
        metrics["noise.power_false_valid_count"] = 1
        failed = score_population(metrics, self.acceptance, "binding")
        self.assertEqual("failed", failed["status"])
        self.assertEqual("failed", failed["field_decisions"]["uncalibrated_channel_power_dbfs"])
        self.assertEqual("passed", failed["field_decisions"]["emission_center_frequency"])
        self.assertEqual("passed", failed["field_decisions"]["snr_estimate_db"])

    def test_scorer_rejects_missing_or_extra_metrics(self) -> None:
        checks = self.acceptance["checks"]["oos"]
        metrics = {check["metric"]: check["threshold"] for check in checks}
        metrics.pop(next(iter(metrics)))
        with self.assertRaisesRegex(ValueError, "metric coverage mismatch"):
            score_population(metrics, self.acceptance, "oos")

    def test_local_preimages_match_public_commitments_without_reveal(self) -> None:
        if not SEALED_PATH.is_file():
            self.skipTest("local sealed F2 preimages are intentionally not repository-owned")
        sealed = json.loads(SEALED_PATH.read_text(encoding="utf-8"))
        commitments = json.loads(COMMITMENTS_PATH.read_text(encoding="utf-8"))
        self.assertTrue(verify_preimages(sealed, commitments))
        self.assertFalse((ACCEPTANCE_PATH.parent / "evaluation-seeds.json").exists())


if __name__ == "__main__":
    unittest.main()
