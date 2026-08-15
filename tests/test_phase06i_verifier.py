from __future__ import annotations

import json
import unittest

from scripts.verify_phase06i import EVIDENCE, OWNED_FILES, check


class Phase06IVerifierTests(unittest.TestCase):
    def test_evidence_is_current_and_machine_neutral(self) -> None:
        self.assertTrue(check())
        payload = "".join((EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES).casefold()
        self.assertNotIn("c:\\users", payload)
        self.assertNotIn("onedrive", payload)

    def test_toolchain_and_scope_are_honest(self) -> None:
        toolchain = json.loads((EVIDENCE / "toolchain.json").read_text(encoding="utf-8"))
        summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        self.assertEqual("not_ready", toolchain["ps_toolchain"])
        self.assertEqual("not_exercised", toolchain["arm_target_execution"])
        self.assertEqual("not_implemented", summary["temporal_confirmation"])
        self.assertEqual("not_complete", summary["pc_independent_zynq_system"])
        self.assertEqual("not_supported", summary["phase06g_continuous_frame_acceptance"])

    def test_abi_is_fixed_and_byte_exact(self) -> None:
        abi = json.loads((EVIDENCE / "abi-contract.json").read_text(encoding="utf-8"))
        rtl = json.loads((EVIDENCE / "rtl-simulation.json").read_text(encoding="utf-8"))
        self.assertEqual(40, abi["candidate_record_bytes"])
        self.assertEqual(54144, abi["maximum_packet_bytes"])
        self.assertEqual(0, rtl["mismatch_count"])


if __name__ == "__main__":
    unittest.main()
