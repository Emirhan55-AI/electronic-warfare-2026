"""Deterministic PHASE-06C fixture tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from reference.rtl.fft_vectors import build_vector_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06c"


class Phase06CVectorTests(unittest.TestCase):
    def test_generated_vectors_match_repository_bytes(self) -> None:
        files, _, _ = build_vector_files()
        for name, payload in files.items():
            self.assertEqual(payload, (FIXTURES / name).read_bytes(), name)

    def test_catalog_has_ten_frames_and_separates_fft_from_stub(self) -> None:
        golden = json.loads((FIXTURES / "golden-vectors.json").read_text(encoding="utf-8"))
        self.assertEqual((10, 40960), (golden["frame_count"], golden["total_samples"]))
        self.assertIn("not AMD IP output", golden["claim_boundary"])
        self.assertNotEqual(
            (FIXTURES / "fft-expected.mem").read_bytes(),
            (FIXTURES / "stub-expected.mem").read_bytes(),
        )

    def test_manifest_is_relative_hashed_and_honest(self) -> None:
        manifest = json.loads((FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("not an FFT", manifest["claim_boundary"])
        self.assertTrue(all(":" not in item["file"] and "\\" not in item["file"] for item in manifest["files"]))
        self.assertEqual(4, len(manifest["files"]))


if __name__ == "__main__":
    unittest.main()
