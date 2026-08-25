from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from scripts.lock_phase04f3_protocol import LOCK_PATH, build_lock
from scripts.prepare_phase04f3_protocol import COMMITMENTS_PATH, SEALED_PATH, verify_preimages
from scripts.reveal_phase04f3_seeds import verify_reveal
from scripts.verify_phase04f3_protocol import SUMMARY_PATH, build_summary
from verification.phase04f3_scoring import score_development, validate_acceptance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"


class Phase04F3ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        self.base = json.loads((ROOT / self.acceptance["base_acceptance"]["path"]).read_text(encoding="utf-8"))

    def test_protocol_lock_and_summary_are_current_before_v4(self) -> None:
        stored = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        method_lock = FIXTURES / "method-lock-v4.json"
        if not method_lock.exists():
            self.assertEqual(stored, build_lock())
            self.assertEqual(json.loads(SUMMARY_PATH.read_text(encoding="utf-8")), build_summary())
        else:
            for path, digest in stored["inputs"].items():
                self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
            for path, digest in stored["protected_historical_inputs"].items():
                self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertEqual("passed", json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))["status"])

    def test_base_gates_are_byte_bound_and_development_gates_are_executable(self) -> None:
        validation = validate_acceptance(self.acceptance, self.base)
        self.assertEqual("passed", validation["status"], validation["problems"])
        self.assertEqual({"binding": 40, "oos": 24}, validation["base_check_counts"])
        self.assertEqual(14, validation["development_check_count"])
        digest = hashlib.sha256((ROOT / self.acceptance["base_acceptance"]["path"]).read_bytes()).hexdigest()
        self.assertEqual(self.acceptance["base_acceptance"]["sha256"], digest)

    def test_risk_gate_failure_does_not_rewrite_base_decisions(self) -> None:
        base_metrics = {check["metric"]: check["threshold"] for check in self.base["checks"]["binding"]}
        risk_metrics = {check["metric"]: check["threshold"] for check in self.acceptance["development_checks"]}
        passed = score_development(base_metrics, risk_metrics, self.acceptance, self.base)
        self.assertEqual("passed", passed["status"])
        risk_metrics["domain.ook.seed_max_wrong_count_6_db"] = 2
        failed = score_development(base_metrics, risk_metrics, self.acceptance, self.base)
        self.assertEqual("failed", failed["status"])
        self.assertEqual("passed", failed["base_scoring"]["status"])

    def test_local_preimages_or_public_reveal_match_commitments(self) -> None:
        if not SEALED_PATH.is_file():
            self.skipTest("local sealed F3 preimages are intentionally not repository-owned")
        sealed = json.loads(SEALED_PATH.read_text(encoding="utf-8"))
        commitments = json.loads(COMMITMENTS_PATH.read_text(encoding="utf-8"))
        self.assertTrue(verify_preimages(sealed, commitments))
        reveal_path = FIXTURES / "evaluation-seeds.json"
        if reveal_path.exists():
            self.assertTrue(verify_reveal(json.loads(reveal_path.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
