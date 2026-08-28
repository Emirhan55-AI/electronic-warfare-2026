from __future__ import annotations

import unittest

from algorithms.rtl.p0_os_cfar import (
    ALPHA_Q32,
    COEFFICIENT_FRACTION_BITS,
    FRAME_LENGTH,
    OUTPUT_MARKER,
    RADIUS,
    detect_frame,
    fixed_decision,
    natural_to_shifted,
    shifted_to_natural,
)


class P0OSCFARPLModelTests(unittest.TestCase):
    def test_shift_mapping_is_involutive(self) -> None:
        for index in (0, 19, 20, 2047, 2048, 4075, 4076, 4095):
            self.assertEqual(index, shifted_to_natural(natural_to_shifted(index)))

    def test_strict_fixed_point_boundary(self) -> None:
        reference = 1 << 30
        threshold_floor = (reference * ALPHA_Q32) >> COEFFICIENT_FRACTION_BITS
        self.assertFalse(fixed_decision(threshold_floor, reference))
        self.assertTrue(fixed_decision(threshold_floor + 1, reference))

    def test_frame_mask_marker_and_edge_policy(self) -> None:
        result = detect_frame([0] * FRAME_LENGTH)
        self.assertEqual(FRAME_LENGTH - 2 * RADIUS, sum(result.evaluated_shifted))
        self.assertFalse(any(result.detected_shifted))
        for natural_index, word in enumerate(result.dma_words_natural):
            shifted_index = natural_to_shifted(natural_index)
            self.assertEqual(OUTPUT_MARKER, word >> 60)
            self.assertEqual(result.evaluated_shifted[shifted_index], bool((word >> 58) & 1))
            self.assertEqual(result.detected_shifted[shifted_index], bool((word >> 59) & 1))

    def test_invalid_frame_and_integer_ranges_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            detect_frame([0] * (FRAME_LENGTH - 1))
        with self.assertRaises(ValueError):
            detect_frame([0] * (FRAME_LENGTH - 1) + [1 << 58])
        with self.assertRaises(ValueError):
            fixed_decision(-1, 0)


if __name__ == "__main__":
    unittest.main()
