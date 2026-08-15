from __future__ import annotations

import unittest

from reference.rtl.regional_detector import (
    FRAME_LENGTH,
    POWER_MAX,
    detect_frame,
    is_evaluated,
    median_twice_exact,
    natural_to_shifted,
    regional_fixed_values,
    shifted_to_natural,
)


class Phase06GModelTests(unittest.TestCase):
    def test_shift_mapping_is_involutive(self) -> None:
        for index in (0, 19, 20, 2047, 2048, 4075, 4076, 4095):
            self.assertEqual(index, shifted_to_natural(natural_to_shifted(index)))

    def test_even_median_is_arithmetic_mean_pair_without_precision_loss(self) -> None:
        values = list(range(256))
        self.assertEqual(255, median_twice_exact(values))

    def test_fixed_coefficients_and_strict_boundary(self) -> None:
        baseline = 1 << 30
        _, threshold = regional_fixed_values(2 * baseline, 1)
        natural = [baseline] * FRAME_LENGTH
        natural[1000 ^ 0x800] = threshold
        result = detect_frame(natural)
        cell = result.cells[1000 ^ 0x800]
        self.assertTrue(cell.evaluated)
        self.assertFalse(cell.detected)
        natural[1000 ^ 0x800] = threshold + 1
        self.assertTrue(detect_frame(natural).cells[1000 ^ 0x800].detected)

    def test_evaluation_mask_and_center_policy(self) -> None:
        self.assertFalse(is_evaluated(19, True))
        self.assertTrue(is_evaluated(20, True))
        self.assertTrue(is_evaluated(2048, True))
        self.assertFalse(is_evaluated(2048, False))
        self.assertTrue(is_evaluated(4075, True))
        self.assertFalse(is_evaluated(4076, True))
        frame = [0] * FRAME_LENGTH
        self.assertEqual(4056, sum(cell.evaluated for cell in detect_frame(frame).cells))
        self.assertEqual(4055, sum(cell.evaluated for cell in detect_frame(frame, evaluate_center=False).cells))

    def test_zero_identical_and_extreme_regions_are_defined(self) -> None:
        zero = detect_frame([0] * FRAME_LENGTH)
        self.assertEqual((0,) * 16, zero.region_medians_twice)
        self.assertFalse(any(cell.detected for cell in zero.cells))
        extreme = detect_frame([POWER_MAX] * FRAME_LENGTH, pfa_select=2)
        self.assertTrue(all(value == 2 * POWER_MAX for value in extreme.region_medians_twice))
        self.assertFalse(any(cell.detected for cell in extreme.cells))

    def test_invalid_frame_and_pfa_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            detect_frame([0] * (FRAME_LENGTH - 1))
        with self.assertRaises(ValueError):
            detect_frame([0] * FRAME_LENGTH, pfa_select=3)


if __name__ == "__main__":
    unittest.main()
