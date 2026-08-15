"""PHASE-06E Vivado implementation evidence tests."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06e.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06e", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06E verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06EVerifierTests(unittest.TestCase):
    def document(self, name: str) -> dict[str, object]:
        return json.loads((VERIFY.EVIDENCE / name).read_text(encoding="utf-8"))

    def test_stored_evidence_is_current_and_passes_frozen_gates(self) -> None:
        self.assertTrue(VERIFY.check())
        timing = self.document("timing.json")
        self.assertGreaterEqual(timing["setup"]["wns_ns"], 0)
        self.assertEqual(0, timing["setup"]["failing_endpoints"])
        self.assertGreaterEqual(timing["hold"]["whs_ns"], 0)
        self.assertEqual(0, timing["hold"]["failing_endpoints"])
        self.assertEqual(0, timing["unconstrained_or_incomplete_constraint_checks"])

    def test_real_ip_hierarchy_and_resources_are_evidenced(self) -> None:
        synthesis = self.document("synthesis.json")
        resources = self.document("resource-utilization.json")
        self.assertTrue(synthesis["real_generated_amd_fft_ip"])
        self.assertEqual(3793, resources["fft_ip_post_route"]["slice_luts"])
        self.assertEqual(30, resources["post_route"]["dsp48"]["used"])
        self.assertEqual(14.5, resources["post_route"]["block_ram_tiles"]["used"])

    def test_scope_claims_remain_honest(self) -> None:
        summary = self.document("verification-summary.json")
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("not_generated", summary["bitstream"])
        for boundary in ("hardware", "power_analysis", "live_hackrf"):
            self.assertEqual("not_exercised", summary[boundary])
        for deferred in ("linear_power", "psd", "regional_detector_rtl"):
            self.assertEqual("not_implemented", summary[deferred])

    def test_axi_boundary_register_slice_is_verified(self) -> None:
        boundary = self.document("rtl-boundary-test.json")
        self.assertEqual("passed", boundary["simulation"])
        self.assertEqual(20, boundary["checked_transfers"])
        self.assertIn("payload_stability", boundary["scenarios"])
        self.assertEqual("external_temporary_directory", boundary["build_location"])


if __name__ == "__main__":
    unittest.main()
