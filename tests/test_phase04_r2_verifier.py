"""PHASE-04-R2 evidence ownership and failure-preservation tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.verify_phase04_r2 as verifier
from reference.parameters.evaluation import canonical_json_bytes, evaluate_phase04_r2


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"


def _diagnostic() -> dict[str, object]:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "phase": "PHASE-04-R2",
        "status": "passed",
        "noise_calibration": lock["noise_calibration"],
        "noise_end_to_end_validation": lock["noise_end_to_end_validation"],
        "morphology_calibration": lock["morphology_calibration"],
    }


def _oos() -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-04-R2",
        "status": "passed",
        "purpose": "non-binding out-of-sample characterization",
        "base_seed": 20260423,
        "trials_per_family": 32,
        "snr_db_order": [12.0, -6.0, 0.0, 6.0],
        "used_for_selection": False,
        "used_for_gate_changes": False,
        "rows": [{"binding": False, "index": index} for index in range(40)],
    }


class Phase04R2VerifierTests(unittest.TestCase):
    def test_failed_algorithm_is_valid_evidence_without_profile(self) -> None:
        lock_sha = verifier._sha(LOCK)
        comparison, _ = evaluate_phase04_r2(full=False, method_lock_sha256=lock_sha)
        comparison["overall"] = "failed"
        comparison["selected_methods"] = None
        comparison["combined_pipeline"]["status"] = "failed"
        comparison["noise_bandwidth_decision"]["status"] = "failed"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = [directory / name for name in ("comparison.json", "diagnostic.json", "oos.json")]
            for path, document in zip(paths, (comparison, _diagnostic(), _oos())):
                path.write_bytes(canonical_json_bytes(document))
            with (
                patch.object(verifier, "PROFILE", directory / "missing-profile.json"),
                patch.dict("os.environ", {}, clear=True),
            ):
                golden, summary = verifier.build(paths[0], paths[1], paths[2])
            self.assertEqual("passed", golden["evidence_status"])
            self.assertEqual("failed", golden["algorithm_status"])
            self.assertEqual("skipped", golden["profile_binding_status"])
            self.assertEqual("passed", summary["evidence_status"])

    def test_oos_cannot_be_reclassified_as_binding(self) -> None:
        lock_sha = verifier._sha(LOCK)
        comparison, _ = evaluate_phase04_r2(full=False, method_lock_sha256=lock_sha)
        oos = _oos()
        oos["used_for_selection"] = True
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = [directory / name for name in ("comparison.json", "diagnostic.json", "oos.json")]
            for path, document in zip(paths, (comparison, _diagnostic(), oos)):
                path.write_bytes(canonical_json_bytes(document))
            with self.assertRaisesRegex(ValueError, "OOS"):
                verifier.build(paths[0], paths[1], paths[2])

    def test_failed_comparison_rejects_any_stale_profile(self) -> None:
        lock_sha = verifier._sha(LOCK)
        comparison, _ = evaluate_phase04_r2(full=False, method_lock_sha256=lock_sha)
        comparison["overall"] = "failed"
        comparison["selected_methods"] = None
        comparison["combined_pipeline"]["status"] = "failed"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = [directory / name for name in ("comparison.json", "diagnostic.json", "oos.json")]
            stale = directory / "operation-default.json"
            stale.write_text("{}\n", encoding="utf-8")
            for path, document in zip(paths, (comparison, _diagnostic(), _oos())):
                path.write_bytes(canonical_json_bytes(document))
            with (
                patch.object(verifier, "PROFILE", stale),
                patch.dict("os.environ", {}, clear=True),
            ):
                golden, summary = verifier.build(paths[0], paths[1], paths[2])
            self.assertEqual("failed", golden["evidence_status"])
            self.assertEqual("profile_must_be_absent_for_failed_comparison", golden["profile_binding_error_code"])
            self.assertEqual("failed", summary["evidence_status"])


if __name__ == "__main__":
    unittest.main()
