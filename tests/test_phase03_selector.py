"""Safe establishment tests for the PHASE-03 selector."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.select_phase03_profile as selector


class Phase03SelectorTests(unittest.TestCase):
    def test_create_noop_mismatch_and_failed_selection_are_safe(self) -> None:
        passed = {"schema_version": 1, "phase": "PHASE-03", "overall": "passed", "selected_detector": "regional"}
        changed = {"schema_version": 1, "phase": "PHASE-03", "overall": "passed", "selected_detector": "ca_cfar"}
        failed = {"schema_version": 1, "phase": "PHASE-03", "overall": "failed", "selected_detector": None}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comparison = root / "detector-comparison.json"
            profile = root / "operation-default.json"
            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(
                selector, "PROFILE_PATH", profile
            ), patch.object(selector, "evaluate_all", return_value=(passed, "regional")):
                code, _ = selector.establish()
                self.assertEqual(0, code)
                original_comparison = comparison.read_bytes()
                original_profile = profile.read_bytes()
                code, _ = selector.establish()
                self.assertEqual(0, code)
                self.assertEqual(original_comparison, comparison.read_bytes())
                self.assertEqual(original_profile, profile.read_bytes())

            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(
                selector, "PROFILE_PATH", profile
            ), patch.object(selector, "evaluate_all", return_value=(changed, "ca_cfar")):
                code, _ = selector.establish()
                self.assertEqual(2, code)
                self.assertEqual(original_comparison, comparison.read_bytes())
                self.assertEqual(original_profile, profile.read_bytes())

            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(
                selector, "PROFILE_PATH", profile
            ), patch.object(selector, "evaluate_all", return_value=(failed, None)):
                code, _ = selector.establish()
                self.assertEqual(1, code)
                self.assertEqual(original_comparison, comparison.read_bytes())
                self.assertEqual(original_profile, profile.read_bytes())

    def test_failed_initial_selection_never_creates_validated_profile(self) -> None:
        failed = {"schema_version": 1, "phase": "PHASE-03", "overall": "failed", "selected_detector": None}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(selector, "COMPARISON_PATH", root / "comparison.json"), patch.object(
                selector, "PROFILE_PATH", root / "profile.json"
            ), patch.object(selector, "evaluate_all", return_value=(failed, None)):
                code, _ = selector.establish()
                self.assertEqual(1, code)
                self.assertFalse((root / "profile.json").exists())


if __name__ == "__main__":
    unittest.main()
