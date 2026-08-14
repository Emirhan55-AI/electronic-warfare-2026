"""Verifier, RTL boundary and evidence tests for PHASE-06B."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06b.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06b", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06B verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06BVerifierTests(unittest.TestCase):
    def test_stored_evidence_is_current_and_honest(self) -> None:
        self.assertTrue(VERIFY.check())
        summary = json.loads((VERIFY.EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        simulation = json.loads((VERIFY.EVIDENCE / "rtl-simulation.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("passed", simulation["rtl_compile"])
        self.assertEqual("passed", simulation["rtl_simulation"])
        self.assertEqual("passed", simulation["golden_equivalence"])
        self.assertEqual(45074, simulation["samples_checked"])
        self.assertEqual(1, simulation["latency_cycles"])
        self.assertEqual("passed", simulation["deterministic_rerun"])
        self.assertEqual(
            {"vectors": "passed", "rtl_compile_and_simulation_rerun": "passed", "comparison": "byte_identical"},
            summary["deterministic_result"],
        )
        for key in ("hardware_status", "synthesis_status", "implementation_status", "timing_status", "resource_utilization_status"):
            self.assertEqual("not_exercised", summary[key])
        self.assertEqual("not_implemented", summary["fft_status"])
        self.assertEqual("not_implemented", summary["regional_detector_rtl_status"])

    def test_check_mode_is_byte_read_only(self) -> None:
        before = {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES}
        self.assertTrue(VERIFY.check())
        self.assertEqual(before, {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES})

    def test_production_rtl_is_integer_only_vendor_neutral_and_has_no_fft(self) -> None:
        source = (ROOT / "rtl" / "phase06b" / "rtl" / "axis_hann_window.sv").read_text(encoding="utf-8").casefold()
        for token in (" real ", "shortreal", "$itor", "$bitstoreal", "xilinx", "unisim", "xpm_", "fft"):
            self.assertNotIn(token, f" {source} ")
        for suffix in ("*.vhd", "*.vhdl", "*.xci", "*.xdc"):
            self.assertEqual([], list((ROOT / "rtl" / "phase06b").rglob(suffix)))

    def test_testbench_exercises_protocol_latency_and_sample_golden(self) -> None:
        text = VERIFY.TESTBENCH.read_text(encoding="utf-8")
        for marker in (
            "$readmemh",
            "fixture_expected",
            "input_stall_cycles",
            "output_stall_cycles",
            "TLAST",
            "apply_reset",
            "measured_latency",
            "watchdog",
            "X/Z",
            "45074",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
