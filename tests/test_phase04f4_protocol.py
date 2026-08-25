from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.lock_phase04f4_protocol import LOCK_PATH, build_lock
from scripts.prepare_phase04f4_protocol import (
    COMMITMENTS_PATH,
    DEVELOPMENT_PATH,
    SEALED_PATH,
    historical_seeds,
    verify_preimages,
)
from scripts.verify_phase04f4_protocol import SUMMARY_PATH, build_summary
from verification.phase04f4_scoring import score_development, validate_acceptance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f4"


class Phase04F4ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = json.loads((FIXTURES / "acceptance-gates.json").read_text(encoding="utf-8"))
        self.base = json.loads((ROOT / self.acceptance["base_acceptance"]["path"]).read_text(encoding="utf-8"))
        self.inherited = json.loads(
            (ROOT / self.acceptance["inherited_development_acceptance"]["path"]).read_text(encoding="utf-8")
        )

    def test_protocol_lock_and_summary_are_current_before_v5(self) -> None:
        self.assertEqual(json.loads(LOCK_PATH.read_text(encoding="utf-8")), build_lock())
        stored_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        method_lock = FIXTURES / "method-lock-v5.json"
        if method_lock.exists():
            self.assertEqual("passed", stored_summary["status"])
            self.assertFalse(stored_summary["v5_method_started"])
        else:
            self.assertEqual(stored_summary, build_summary())
            self.assertEqual("passed", build_summary()["status"])

    def test_base_inherited_and_additional_gates_are_executable(self) -> None:
        validation = validate_acceptance(self.acceptance, self.inherited, self.base)
        self.assertEqual("passed", validation["status"], validation["problems"])
        self.assertEqual({"binding": 40, "oos": 24}, validation["base_check_counts"])
        self.assertEqual(14, validation["inherited_development_check_count"])
        self.assertEqual(4, validation["additional_development_check_count"])
        self.assertEqual(18, validation["combined_development_check_count"])

    def test_nfm_failure_does_not_rewrite_inherited_or_base_decisions(self) -> None:
        base_metrics = {check["metric"]: check["threshold"] for check in self.base["checks"]["binding"]}
        inherited_metrics = {check["metric"]: check["threshold"] for check in self.inherited["development_checks"]}
        additional_metrics = {check["metric"]: check["threshold"] for check in self.acceptance["additional_development_checks"]}
        passed = score_development(
            base_metrics, inherited_metrics, additional_metrics,
            self.acceptance, self.inherited, self.base,
        )
        self.assertEqual("passed", passed["status"])
        additional_metrics["domain.nfm.seed_min_correct_count_6_db"] = 39
        failed = score_development(
            base_metrics, inherited_metrics, additional_metrics,
            self.acceptance, self.inherited, self.base,
        )
        self.assertEqual("failed", failed["status"])
        self.assertEqual("passed", failed["base_scoring"]["status"])
        self.assertTrue(all(item["status"] == "passed" for item in failed["inherited_risk_checks"]))

    def test_local_preimages_match_public_commitments(self) -> None:
        if not SEALED_PATH.is_file():
            self.skipTest("local sealed F4 preimages are intentionally not repository-owned")
        sealed = json.loads(SEALED_PATH.read_text(encoding="utf-8"))
        commitments = json.loads(COMMITMENTS_PATH.read_text(encoding="utf-8"))
        self.assertTrue(verify_preimages(sealed, commitments))
        development = json.loads(DEVELOPMENT_PATH.read_text(encoding="utf-8"))
        public = {int(value) for value in development["common"]["development_seeds"]}
        evaluation = {int(item["seed"]) for item in sealed["seeds"]}
        self.assertFalse(historical_seeds().intersection(public | evaluation))
        self.assertFalse(public.intersection(evaluation))
        self.assertFalse((FIXTURES / "evaluation-seeds.json").exists())


if __name__ == "__main__":
    unittest.main()
