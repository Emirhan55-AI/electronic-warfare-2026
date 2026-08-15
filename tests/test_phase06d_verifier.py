"""PHASE-06D real-vendor evidence and honesty tests."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06d.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06d", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06D verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06DVerifierTests(unittest.TestCase):
    def test_stored_evidence_is_current_and_honest(self) -> None:
        self.assertTrue(VERIFY.check())
        summary = json.loads((VERIFY.EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        equivalence = json.loads((VERIFY.EVIDENCE / "golden-equivalence.json").read_text(encoding="utf-8"))
        xsim = json.loads((VERIFY.EVIDENCE / "xsim-result.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["overall"])
        self.assertEqual(0, equivalence["maximum_absolute_component_error"])
        self.assertEqual("passed", xsim["deterministic_rerun"])
        self.assertTrue(xsim["real_generated_amd_fft_ip"])
        self.assertFalse(xsim["transport_stub_used"])
        for boundary in ("synthesis", "implementation", "timing", "resource_utilization", "hardware"):
            self.assertEqual("not_exercised", summary[boundary])

    def test_adapter_is_thin_and_real_ip_is_instantiated(self) -> None:
        adapter = (ROOT / "rtl" / "phase06d" / "rtl" / "amd_xfft_adapter.sv").read_text(encoding="utf-8")
        self.assertIn("phase06d_fft_4096 fft_ip", adapter)
        self.assertIn("amd_m_axis_data_tuser[11:0]", adapter)
        self.assertNotIn("fft_ip_transport_stub", adapter)
        for token in ("$cos", "$sin", "real ", "shortreal"):
            self.assertNotIn(token, adapter)

    def test_xci_is_real_vendor_product_and_path_clean(self) -> None:
        text = VERIFY.XCI.read_text(encoding="utf-8")
        self.assertEqual(VERIFY.EXPECTED_XCI_SHA256, VERIFY.sha256(VERIFY.XCI))
        self.assertIn("xilinx.com:ip:xfft:9.1", text)
        self.assertNotRegex(text, r"[A-Za-z]:[\\/]")


if __name__ == "__main__":
    unittest.main()
