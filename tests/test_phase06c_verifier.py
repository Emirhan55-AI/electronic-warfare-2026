"""PHASE-06C wrapper, evidence and honesty tests."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06c.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06c", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06C verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06CVerifierTests(unittest.TestCase):
    def test_stored_evidence_is_current_and_honest(self) -> None:
        self.assertTrue(VERIFY.check())
        summary = json.loads((VERIFY.EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        simulation = json.loads((VERIFY.EVIDENCE / "wrapper-simulation.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("passed", simulation["wrapper_compile"])
        self.assertEqual("passed", simulation["wrapper_simulation"])
        self.assertFalse(simulation["transport_stub_is_fft"])
        self.assertEqual("not_exercised", summary["real_amd_fft_ip"])
        self.assertEqual("not_exercised_unavailable", summary["vivado"])
        self.assertEqual("not_created", summary["xci"])
        self.assertEqual("passed", simulation["deterministic_rerun"])

    def test_check_mode_is_byte_read_only(self) -> None:
        before = {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES}
        self.assertTrue(VERIFY.check())
        self.assertEqual(before, {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES})

    def test_production_wrapper_has_no_custom_fft_or_vendor_primitive(self) -> None:
        source = (ROOT / "rtl" / "phase06c" / "rtl" / "axis_fft_wrapper.sv").read_text(encoding="utf-8").casefold()
        for token in ("$cos", "$sin", "butterfly", "unisim", "xpm_", "xfft", "real ", "shortreal"):
            self.assertNotIn(token, source)
        for suffix in ("*.xci", "*.xdc", "*.vhd", "*.vhdl"):
            self.assertEqual([], list((ROOT / "rtl" / "phase06c").rglob(suffix)))

    def test_testbench_checks_wrapper_control_not_fft_function(self) -> None:
        text = VERIFY.TESTBENCH.read_text(encoding="utf-8")
        for marker in (
            "allow_config_ready",
            "configuration_done",
            "input_stall_cycles",
            "output_stall_cycles",
            "status_events",
            "event_injected_while_output_stalled",
            "TLAST",
            "apply_reset",
            "measured_latency",
            "45074",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("fft-expected.mem", text)


if __name__ == "__main__":
    unittest.main()
