from __future__ import annotations

import json
import unittest

from algorithms.rtl.p0_os_cfar_vectors import build_vector_files, p0_os_cfar_vectors


class P0OSCFARPLVectorTests(unittest.TestCase):
    def test_required_scenarios_and_real_power_are_present(self) -> None:
        names = {vector.vector_id for vector in p0_os_cfar_vectors()}
        self.assertEqual(11, len(names))
        self.assertTrue(
            {
                "all_zero",
                "uniform_noise",
                "multiple_tones",
                "excluded_shifted_edges",
                "duplicate_reference_transitions",
                "threshold_floor",
                "threshold_floor_plus_one",
                "extreme_unsigned_range",
                "real_phase06f_single_tone",
                "real_phase06f_multiple_tones",
                "real_phase06f_representative_hann",
            }.issubset(names)
        )

    def test_generated_files_are_deterministic_and_match_float_reference(self) -> None:
        first = build_vector_files()
        self.assertEqual(first, build_vector_files())
        golden = json.loads(first["golden-vectors.json"])
        self.assertEqual("passed", golden["status"])
        self.assertEqual(0, golden["non_boundary_decision_mismatches"])
        self.assertEqual(0, golden["evaluation_mask_mismatches"])


if __name__ == "__main__":
    unittest.main()
