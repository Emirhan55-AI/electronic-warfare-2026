"""PHASE-06F evidence, RTL, and honesty tests."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06f.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06f", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06F verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06FVerifierTests(unittest.TestCase):
    def document(self, name: str) -> dict[str, object]:
        return json.loads((VERIFY.EVIDENCE / name).read_text(encoding="utf-8"))

    def test_stored_evidence_is_current_and_passed(self) -> None:
        self.assertTrue(VERIFY.check())
        simulation = self.document("rtl-simulation.json")
        self.assertEqual(45_068, simulation["checked_results"])
        self.assertEqual(0, simulation["mismatch_count"])
        self.assertEqual("passed", simulation["deterministic_rerun"])

    def test_rtl_extracts_29_bits_and_preserves_axi_metadata(self) -> None:
        rtl = (ROOT / "rtl/phase06f/rtl/axis_fft_linear_power.sv").read_text(encoding="utf-8")
        self.assertIn("s_axis_tdata[28:0]", rtl)
        self.assertIn("s_axis_tdata[60:32]", rtl)
        self.assertIn("stage2_last <= stage1_last", rtl)
        self.assertIn("stage2_index <= stage1_index", rtl)
        self.assertNotIn("s_axis_tdata[31:0] *", rtl)

    def test_scope_and_timing_claims_are_honest(self) -> None:
        summary = self.document("verification-summary.json")
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("not_implemented", summary["psd"])
        self.assertEqual("not_implemented", summary["regional_detector_rtl"])
        self.assertEqual("not_reverified", summary["post_power_timing_100mhz"])
        self.assertEqual("not_generated", summary["bitstream"])
        self.assertEqual("not_exercised", summary["hardware"])

    def test_real_fft_integration_is_full_frame_exact(self) -> None:
        integration = self.document("integration.json")
        self.assertEqual(11, integration["frames"])
        self.assertEqual(45_056, integration["samples"])
        self.assertEqual(0, integration["mismatch_count"])


if __name__ == "__main__":
    unittest.main()
