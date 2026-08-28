from __future__ import annotations

import json
import unittest

from scripts.verify_p0_os_cfar_pl import EVIDENCE, OWNED_FILES, check


class P0OSCFARPLVerifierTests(unittest.TestCase):
    def test_evidence_is_current_and_machine_neutral(self) -> None:
        self.assertTrue(check())
        payload = "".join(
            (EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES
        ).casefold()
        self.assertNotIn("c:\\users", payload)
        self.assertNotIn("onedrive", payload)

    def test_summary_separates_functional_and_physical_acceptance(self) -> None:
        summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["functional_verification"])
        self.assertEqual("passed", summary["synthesis"])
        self.assertEqual("passed", summary["post_route_timing"])
        self.assertEqual("passed", summary["runtime_software_integration"])
        self.assertEqual("not_run", summary["physical_service_acceptance"])
        self.assertFalse(summary["release_ready"])


if __name__ == "__main__":
    unittest.main()
