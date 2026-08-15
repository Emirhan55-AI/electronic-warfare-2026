from __future__ import annotations

import json
import unittest

from scripts.verify_phase06j import EVIDENCE, OWNED_FILES, check, run_host_verification


class Phase06JVerifierTests(unittest.TestCase):
    def test_host_build_and_python_c_equivalence_are_real(self) -> None:
        result = run_host_verification()
        self.assertEqual(0, result["mismatch_count"])
        self.assertEqual(1501, result["candidate_records_checked"])
        self.assertGreater(result["state_bytes"], 0)
        self.assertEqual(8724, result["frame_result_bytes"])

    def test_evidence_is_current_and_machine_neutral(self) -> None:
        self.assertTrue(check())
        payload = "".join((EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES).casefold()
        self.assertNotIn("c:\\users", payload)
        self.assertNotIn("onedrive", payload)

    def test_toolchain_and_scope_claims_are_honest(self) -> None:
        toolchain = json.loads((EVIDENCE / "toolchain.json").read_text(encoding="utf-8"))
        summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        limits = json.loads((EVIDENCE / "system-limitations.json").read_text(encoding="utf-8"))
        self.assertEqual("ready_and_exercised", toolchain["host_c"])
        self.assertEqual("blocked_toolchain", toolchain["arm_build"])
        self.assertEqual("not_exercised", summary["arm_execution"])
        self.assertEqual("not_implemented", summary["physical_parameter_conversion"])
        self.assertEqual("not_verified", limits["real_pl_ps_hardware_path"])
        self.assertEqual("not_supported", limits["phase06g_continuous_throughput"])


if __name__ == "__main__":
    unittest.main()
