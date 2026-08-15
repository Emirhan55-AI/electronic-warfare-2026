from __future__ import annotations

import json
import unittest

from reference.ps.transport_vectors import build_vector_files


class Phase06IVectorTests(unittest.TestCase):
    def test_vectors_are_deterministic_and_reuse_phase06h(self) -> None:
        first = build_vector_files()
        self.assertEqual(first, build_vector_files())
        golden = json.loads(first["golden-vectors.json"])
        self.assertEqual(13, golden["frame_count"])
        self.assertEqual(1773, golden["input_candidate_axis_records"])
        self.assertEqual(1772, golden["semantic_candidates"])
        self.assertEqual(8964, golden["output_axis64_beats"])

    def test_manifest_is_relative_and_machine_neutral(self) -> None:
        manifest = json.loads(build_vector_files()["fixture-manifest.json"])
        self.assertEqual("datasets/fixtures/phase06h/candidate-expected.mem", manifest["frozen_phase06h_source"]["path"])
        self.assertNotIn(":\\", json.dumps(manifest))


if __name__ == "__main__":
    unittest.main()
