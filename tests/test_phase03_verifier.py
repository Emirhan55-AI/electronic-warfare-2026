"""Read-only and deterministic evidence tests for the PHASE-03 verifier."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.verify_phase03 as verifier


ROOT = Path(__file__).resolve().parents[1]


class Phase03VerifierTests(unittest.TestCase):
    def test_golden_detection_and_historical_evidence_pass(self) -> None:
        _, passed = verifier._golden_detection()
        self.assertTrue(passed)
        self.assertEqual("passed", verifier._historical_evidence_check()["status"])

    def test_external_configuration_is_skipped_or_failed_deterministically(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            status, detail = verifier._external_integration(0, 4)
            self.assertEqual("skipped", status["status"])
            self.assertEqual({}, detail)
        with patch.dict(os.environ, {verifier.EXTERNAL_METADATA_ENV: "only-meta"}, clear=True):
            status, _ = verifier._external_integration(0, 4)
            self.assertEqual("failed", status["status"])

    def test_stored_summary_has_fixed_status_and_no_sensitive_path(self) -> None:
        summary = json.loads(verifier.SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("timestamp", json.dumps(summary).casefold())
        self.assertNotIn("c:\\users", json.dumps(summary).casefold())
        self.assertTrue(
            all(item["status"] in {"passed", "failed", "skipped"} for item in summary["checks"])
        )

    def test_wideband_contract_rejects_a_tampered_temporary_catalog(self) -> None:
        catalog = json.loads(verifier.CATALOG_PATH.read_text(encoding="utf-8"))
        comparison = verifier.COMPARISON_PATH.read_bytes()
        catalog["evaluation_contract"]["wideband"]["minimum_coverage"] = 0.61
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            catalog_path = temporary_root / "detection-scenes.json"
            comparison_path = temporary_root / "detector-comparison.json"
            catalog_path.write_text(
                json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            comparison_path.write_bytes(comparison)
            result = verifier._wideband_contract_check(catalog_path, comparison_path)
        self.assertEqual("failed", result["status"])

    def test_check_mode_does_not_modify_owned_evidence(self) -> None:
        paths = (verifier.GOLDEN_PATH, verifier.SUMMARY_PATH)
        before = {path: path.read_bytes() for path in paths}
        environment = os.environ.copy()
        environment.pop(verifier.EXTERNAL_METADATA_ENV, None)
        environment.pop(verifier.EXTERNAL_DATA_ENV, None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "verify_phase03.py"), "--check"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})


if __name__ == "__main__":
    unittest.main()
