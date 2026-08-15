from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify_phase06g import EVIDENCE, OWNED_FILES, check


class Phase06GVerifierTests(unittest.TestCase):
    def test_evidence_is_current_and_machine_neutral(self) -> None:
        self.assertTrue(check())
        payload = "".join((EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES).casefold()
        self.assertNotIn("c:\\users", payload)
        self.assertNotIn("onedrive", payload)

    def test_summary_is_honest_about_timing_and_later_functions(self) -> None:
        summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("not_verified", summary["post_detector_timing_100mhz"])
        self.assertEqual("not_implemented", summary["cell_grouping"])
        self.assertEqual("not_implemented", summary["parameter_extraction_rtl"])


if __name__ == "__main__":
    unittest.main()
