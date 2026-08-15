"""PHASE-06F deterministic power-vector tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from reference.rtl.power_vectors import REAL_FFT_SOURCE, build_vector_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06f"


class Phase06FVectorTests(unittest.TestCase):
    def test_generated_vectors_are_byte_current_and_deterministic(self) -> None:
        first = build_vector_files()
        second = build_vector_files()
        self.assertEqual(first, second)
        for name, payload in first.items():
            self.assertEqual(payload, (FIXTURES / name).read_bytes(), name)

    def test_real_amd_fft_source_is_reused_by_hash(self) -> None:
        manifest = json.loads((FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("datasets/fixtures/phase06d/cmodel-expected.mem", manifest["external_source"]["path"])
        self.assertEqual(hashlib.sha256(REAL_FFT_SOURCE.read_bytes()).hexdigest(), manifest["external_source"]["sha256"])
        self.assertEqual(45_056, len(REAL_FFT_SOURCE.read_text(encoding="ascii").splitlines()))

    def test_required_edge_and_fft_scenarios_are_declared(self) -> None:
        golden = json.loads((FIXTURES / "golden-vectors.json").read_text(encoding="utf-8"))
        edge_ids = {item["id"] for item in golden["edge_vectors"]}
        self.assertTrue({"zero", "i_max_positive", "i_min_negative", "q_max_positive", "q_min_negative", "both_min_negative", "equal_positive", "equal_negative", "small_mixed"} <= edge_ids)
        self.assertTrue({"zero", "impulse", "dc", "exact_bin_tone", "negative_frequency_tone", "two_tone", "representative_hann"} <= set(golden["real_amd_fft"]["includes"]))


if __name__ == "__main__":
    unittest.main()
