"""Deterministic PHASE-06B vector tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from reference.rtl.hann_vectors import build_vector_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06b"


class Phase06BVectorTests(unittest.TestCase):
    def test_generated_vectors_match_tracked_bytes(self) -> None:
        files, _ = build_vector_files()
        for name, payload in files.items():
            self.assertEqual(payload, (FIXTURES / name).read_bytes(), name)

    def test_vector_catalog_covers_ten_frames_and_required_scenarios(self) -> None:
        golden = json.loads((FIXTURES / "golden-vectors.json").read_text(encoding="utf-8"))
        self.assertEqual((10, 40960), (golden["frame_count"], golden["total_samples"]))
        identifiers = [item["vector_id"] for item in golden["vectors"]]
        for identifier in (
            "all_zero",
            "all_minimum",
            "all_maximum",
            "alternating_extrema",
            "single_impulse",
            "constant_complex",
        ):
            self.assertIn(identifier, identifiers)
        self.assertEqual([0, 1, 6, 137, 2047, 2048, 2049, 4095], [
            item["sample_index"] for item in golden["vectors"][0]["selected_outputs"]
        ])

    def test_manifest_is_relative_and_has_honest_claim_boundary(self) -> None:
        manifest = json.loads((FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("FFT, sentez veya FPGA sonucu değildir", manifest["claim_boundary"])
        self.assertTrue(all(":" not in item["file"] and "\\" not in item["file"] for item in manifest["files"]))


if __name__ == "__main__":
    unittest.main()
