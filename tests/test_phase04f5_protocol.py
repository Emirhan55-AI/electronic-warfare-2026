from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.lock_phase04f5_protocol import LOCK_PATH, build_lock
from scripts.prepare_phase04f5_protocol import (
    COMMITMENTS_PATH,
    DEVELOPMENT_PATH,
    SEALED_PATH,
    historical_seeds,
    verify_preimages,
)
from scripts.verify_phase04f5_protocol import SUMMARY_PATH, build_summary
from verification.phase04f5_scoring import score_additional, validate_acceptance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"


class Phase04F5ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = json.loads((FIXTURES / "acceptance-gates.json").read_text(encoding="utf-8"))
        self.base = json.loads((ROOT / self.acceptance["base_acceptance"]["path"]).read_text(encoding="utf-8"))
        self.f3 = json.loads((ROOT / self.acceptance["f3_development_acceptance"]["path"]).read_text(encoding="utf-8"))
        self.f4 = json.loads((ROOT / self.acceptance["f4_development_acceptance"]["path"]).read_text(encoding="utf-8"))

    def test_protocol_lock_and_summary_are_current_before_v6(self) -> None:
        self.assertEqual(json.loads(LOCK_PATH.read_text(encoding="utf-8")), build_lock())
        self.assertEqual(json.loads(SUMMARY_PATH.read_text(encoding="utf-8")), build_summary())
        self.assertEqual("passed", build_summary()["status"])

    def test_inherited_and_f5_gates_are_executable(self) -> None:
        validation = validate_acceptance(self.acceptance, self.f4, self.f3, self.base)
        self.assertEqual("passed", validation["status"], validation["problems"])
        self.assertEqual({"binding": 40, "oos": 24}, validation["base_check_counts"])
        self.assertEqual(18, validation["inherited_combined_development_check_count"])
        self.assertEqual(7, validation["f5_additional_development_check_count"])
        self.assertEqual(25, validation["combined_development_check_count"])

    def test_obw_margin_boundary_is_fail_closed(self) -> None:
        metrics = {item["metric"]: item["threshold"] for item in self.acceptance["additional_development_checks"]}
        self.assertEqual("passed", score_additional(metrics, self.acceptance)["status"])
        metrics["obw.family_min_valid_count_12_db"] = 378
        failed = score_additional(metrics, self.acceptance)
        self.assertEqual("failed", failed["status"])
        self.assertEqual("failed", next(item for item in failed["checks"] if item["id"] == "obw-family-valid")["status"])

    def test_local_preimages_match_commitments_and_prior_seeds_are_excluded(self) -> None:
        if not SEALED_PATH.is_file():
            self.skipTest("local sealed F5 preimages are intentionally not repository-owned")
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
