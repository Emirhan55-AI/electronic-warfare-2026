"""Verifier, RTL boundary and read-only tests for PHASE-06A."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase06a.py"
SPEC = importlib.util.spec_from_file_location("verify_phase06a", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-06A verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase06AVerifierTests(unittest.TestCase):
    def test_tracked_evidence_is_current_and_honest(self) -> None:
        self.assertTrue(VERIFY.check())
        summary = json.loads((VERIFY.EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        simulation = json.loads((VERIFY.EVIDENCE / "rtl-simulation.json").read_text(encoding="utf-8"))
        self.assertIn(summary["overall"], {"passed", "prepared_not_simulated"})
        self.assertEqual("not_exercised", summary["hardware_status"])
        self.assertEqual("not_implemented", summary["fft_status"])
        if simulation["status"] == "skipped":
            self.assertEqual("tool_unavailable", simulation["reason"])
            self.assertEqual("prepared_not_simulated", summary["overall"])
        else:
            self.assertEqual("passed", summary["overall"])
            self.assertEqual("passed", simulation["rtl_compile"])
            self.assertEqual("passed", simulation["rtl_simulation"])
            self.assertEqual("passed", simulation["golden_equivalence"])
            toolchain = json.loads((VERIFY.EVIDENCE / "toolchain.json").read_text(encoding="utf-8"))
            statuses = {item["name"]: item["status"] for item in toolchain["tools"]}
            self.assertEqual("available", statuses["iverilog"])
            self.assertEqual("available", statuses["vvp"])

    def test_check_is_byte_read_only(self) -> None:
        before = {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES}
        self.assertTrue(VERIFY.check())
        self.assertEqual(before, {name: (VERIFY.EVIDENCE / name).read_bytes() for name in VERIFY.OWNED_FILES})

    def test_production_rtl_is_integer_only_and_vendor_neutral(self) -> None:
        forbidden = (" real ", "shortreal", "$itor", "$bitstoreal", "xilinx", "xpm_", "unisim")
        for path in VERIFY.RTL_SOURCES:
            text = f" {path.read_text(encoding='utf-8').casefold()} "
            for token in forbidden:
                self.assertNotIn(token, text, f"{path}: {token}")
        self.assertEqual([], list((ROOT / "rtl" / "phase06a").rglob("*.vhd")))
        self.assertEqual([], list((ROOT / "rtl" / "phase06a").rglob("*.vhdl")))
        self.assertEqual([], list((ROOT / "rtl" / "phase06a").rglob("*.xci")))
        self.assertEqual([], list((ROOT / "rtl" / "phase06a").rglob("*.xdc")))

    def test_testbench_has_required_self_checks(self) -> None:
        text = VERIFY.TESTBENCH.read_text(encoding="utf-8")
        for marker in (
            "$readmemh",
            "$fatal",
            "watchdog",
            "backpressure",
            "input_stall_cycles",
            "result_stall_cycles",
            "drive_fixture_frames_contiguous",
            "PHASE06A_ERROR_EARLY_TLAST",
            "PHASE06A_ERROR_MISSING_TLAST",
            "resetn <= 1'b0",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
