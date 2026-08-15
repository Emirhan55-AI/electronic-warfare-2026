from __future__ import annotations

import unittest

from reference.rtl.detector_vectors import build_vector_files, detector_vectors


class Phase06GVectorsTests(unittest.TestCase):
    def test_required_scenarios_and_real_power_are_present(self) -> None:
        vectors = detector_vectors()
        names = {vector.vector_id for vector in vectors}
        self.assertEqual(20, len(vectors))
        self.assertTrue(
            {
                "all_zero",
                "uniform_noise",
                "one_strong_tone",
                "multiple_tones_different_regions",
                "two_tones_same_region",
                "tones_at_region_boundaries",
                "shifted_positive_frequency_region",
                "shifted_negative_frequency_region",
                "excluded_first_twenty",
                "excluded_last_twenty",
                "threshold_equal",
                "threshold_one_lsb_above",
                "threshold_one_lsb_below",
                "extreme_uq28_30",
                "real_phase06f_single_tone",
                "real_phase06f_negative_frequency_tone",
                "real_phase06f_multiple_tones",
                "real_phase06f_two_tone",
                "real_phase06f_representative_hann",
            }.issubset(names)
        )

    def test_generated_files_are_deterministic(self) -> None:
        self.assertEqual(build_vector_files(), build_vector_files())


if __name__ == "__main__":
    unittest.main()
