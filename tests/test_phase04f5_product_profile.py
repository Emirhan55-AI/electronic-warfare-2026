"""Digest binding and fail-closed tests for the PHASE-04-F5 product profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from algorithms.parameters import F5ParameterEstimator
from algorithms.pipeline import PHASE04F5_FIELDS, PHASE04F5_PROFILE_PATH, load_phase04f5_capability
from scripts.verify_phase04f5_product_integration import build_summary


ROOT = Path(__file__).resolve().parents[1]


class Phase04F5ProductProfileTests(unittest.TestCase):
    def test_tracked_profile_loads_only_the_locked_capability(self) -> None:
        capability = load_phase04f5_capability()
        self.assertIsNotNone(capability)
        assert capability is not None
        self.assertEqual(PHASE04F5_FIELDS, capability.validated_fields)
        self.assertEqual(tuple(F5ParameterEstimator.METHOD_IDS.items()), capability.methods)
        self.assertEqual(4, capability.frames_per_measurement)
        self.assertEqual(4096, capability.frame_length)
        self.assertTrue(capability.operator_confirmed_span_required)
        self.assertFalse(capability.automatic_span_validated)

    def test_profile_binds_all_f5d_evidence_digests(self) -> None:
        profile = json.loads(PHASE04F5_PROFILE_PATH.read_text(encoding="utf-8"))
        expected = {
            "method_lock_sha256": ROOT / "datasets/fixtures/phase04f5/method-lock-v6.json",
            "acceptance_contract_sha256": ROOT / "datasets/fixtures/phase04f5/acceptance-gates.json",
            "base_acceptance_contract_sha256": ROOT / "datasets/fixtures/phase04f2/acceptance-gates.json",
            "binding_results_sha256": ROOT / "results/evidence/phase04f5/binding-results-v6.json",
            "oos_results_sha256": ROOT / "results/evidence/phase04f5/oos-results-v6.json",
            "comparison_sha256": ROOT / "results/evidence/phase04f5/parameter-comparison-v6.json",
            "f5d_verification_sha256": ROOT / "results/evidence/phase04f5/f5d-verification.json",
        }
        for key, path in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), profile["evidence"][key])

    def test_any_profile_byte_change_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "operation-default.json"
            document = json.loads(PHASE04F5_PROFILE_PATH.read_text(encoding="utf-8"))
            document["validated_fields"].remove("snr_estimate_db")
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.assertIsNone(load_phase04f5_capability(path))

    def test_profile_contains_no_hardware_or_calibrated_power_claim(self) -> None:
        profile_text = PHASE04F5_PROFILE_PATH.read_text(encoding="utf-8")
        self.assertIn("FPGA", profile_text)
        self.assertIn("saha başarı iddiası değildir", profile_text)
        self.assertNotIn('"dBm"', profile_text)

    def test_product_integration_evidence_is_reproducible(self) -> None:
        summary = build_summary()
        self.assertEqual("passed", summary["status"])
        self.assertTrue(all(item["status"] == "passed" for item in summary["checks"]))


if __name__ == "__main__":
    unittest.main()
