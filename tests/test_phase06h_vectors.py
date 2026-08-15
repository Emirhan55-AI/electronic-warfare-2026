from __future__ import annotations

import json
import unittest

from reference.rtl.candidate_vectors import build_vector_files, grouping_vectors


class Phase06HVectorsTests(unittest.TestCase):
    def test_required_scenarios_and_frozen_phase06g_output_are_present(self) -> None:
        names = {vector.vector_id for vector in grouping_vectors()}
        self.assertTrue({
            "no_candidate",
            "one_bin",
            "multi_bin",
            "two_separated",
            "one_missing_bin_bridged",
            "region_boundary",
            "equal_peak_first_wins",
            "first_evaluated",
            "last_evaluated",
            "shifted_half_order",
            "center_exclusion_bridged",
            "maximum_candidate_count",
            "real_phase06g_representative_hann",
        }.issubset(names))

    def test_generated_files_are_byte_deterministic(self) -> None:
        first = build_vector_files()
        second = build_vector_files()
        self.assertEqual(first, second)
        golden = json.loads(first["golden-vectors.json"])
        self.assertEqual(53248, golden["input_records"])
        self.assertEqual(1773, golden["output_records"])
        self.assertEqual(1772, golden["semantic_candidates"])

    def test_manifest_is_relative_and_reuses_frozen_phase06g_by_hash(self) -> None:
        manifest = json.loads(build_vector_files()["fixture-manifest.json"])
        source = manifest["frozen_phase06g_source"]
        self.assertEqual("datasets/fixtures/phase06g/detector-expected.mem", source["path"])
        self.assertNotIn(":\\", json.dumps(manifest))


if __name__ == "__main__":
    unittest.main()
