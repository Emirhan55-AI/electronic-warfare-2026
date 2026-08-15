from __future__ import annotations

import json
import unittest

from scripts.verify_phase06h import EVIDENCE, OWNED_FILES, check


class Phase06HVerifierTests(unittest.TestCase):
    def test_evidence_is_current_and_machine_neutral(self) -> None:
        self.assertTrue(check())
        payload = "".join((EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES).casefold()
        self.assertNotIn("c:\\users", payload)
        self.assertNotIn("onedrive", payload)

    def test_summary_is_honest_about_unexercised_and_deferred_work(self) -> None:
        summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("not_supported", summary["continuous_pipeline"])
        self.assertEqual("not_verified", summary["post_detector_timing_100mhz"])
        self.assertEqual("not_implemented", summary["temporal_confirmation"])
        self.assertEqual("not_exercised", summary["hardware"])

    def test_resource_evidence_is_synthesis_only(self) -> None:
        resource = json.loads((EVIDENCE / "resource-feasibility.json").read_text(encoding="utf-8"))
        self.assertEqual("not_run", resource["implementation"])
        self.assertEqual("not_verified", resource["post_route_timing"])
        self.assertEqual(6.0, resource["resources"]["bram_tiles"])


if __name__ == "__main__":
    unittest.main()
