"""Evidence contract tests for the PHASE-02 verifier."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase02.py"
SPEC = importlib.util.spec_from_file_location("verify_phase02", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load verifier from {VERIFY_PATH}")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase02VerifierTests(unittest.TestCase):
    def test_golden_payload_uses_selected_measurements_not_array_digest(self) -> None:
        payload, passed = VERIFY.golden_payload()
        self.assertTrue(passed)
        self.assertFalse(payload["full_spectrum_digest_is_portable_gate"])
        self.assertNotIn("spectrum_sha256", json.dumps(payload).casefold())
        self.assertTrue(payload["actual"]["quantization_harmonics_present"])

    def test_verification_summary_has_fixed_safe_contract(self) -> None:
        summary = json.loads(VERIFY.SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(["schema_version", "phase", "overall", "checks"], list(summary))
        self.assertNotIn("timestamp", json.dumps(summary).casefold())
        self.assertNotIn("C:\\Users\\", json.dumps(summary))
        self.assertTrue(all(check["status"] in {"passed", "failed", "skipped"} for check in summary["checks"]))
        self.assertEqual(
            [
                "runtime-dependencies",
                "historical-evidence",
                "golden-spectrum",
                "turkish-ui-and-capability-policy",
                "visual-evidence",
                "recorded-playback-performance",
                "external-single-frame",
                "windows-packaging",
                "required-files",
                "text-integrity",
            ],
            [check["id"] for check in summary["checks"]],
        )

    def test_historical_evidence_remains_unchanged(self) -> None:
        self.assertEqual("passed", VERIFY.check_historical_evidence()["status"])


if __name__ == "__main__":
    unittest.main()
