"""Deterministic PHASE-06A vector tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from reference.rtl.vectors import build_vector_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06a"


class Phase06AVectorTests(unittest.TestCase):
    def test_generated_vectors_match_tracked_bytes(self) -> None:
        files, _ = build_vector_files()
        for name, payload in files.items():
            self.assertEqual(payload, (FIXTURES / name).read_bytes(), name)

    def test_phase01_four_frames_are_clean_and_ordered(self) -> None:
        golden = json.loads((FIXTURES / "golden-vectors.json").read_text(encoding="utf-8"))
        self.assertEqual([0, 1, 2, 3], [item["frame_index"] for item in golden["phase01_frames"]])
        self.assertTrue(all(item["sample_count"] == 4096 for item in golden["phase01_frames"]))
        self.assertTrue(all(not item["protocol_error"] for item in golden["phase01_frames"]))
        self.assertEqual("first_peak_index", golden["tie_break"])

    def test_manifest_has_relative_paths_and_no_hardware_claim(self) -> None:
        manifest = json.loads((FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("RTL simülasyon veya FPGA sonucu değildir", manifest["claim_boundary"])
        self.assertFalse(any(":" in item["file"] or "\\" in item["file"] for item in manifest["files"]))


if __name__ == "__main__":
    unittest.main()
