"""PHASE-06F exact integer power model tests."""

from __future__ import annotations

import unittest

from reference.rtl.fft_power import (
    COMPONENT_MAX,
    COMPONENT_MIN,
    POWER_MAX_REACHABLE,
    linear_power,
    pack_fft_word,
    power_from_fft_word,
    power_real_value,
    unpack_fft_word,
    width_proof,
)


class Phase06FModelTests(unittest.TestCase):
    def test_width_proof_is_independent_and_exact(self) -> None:
        proof = width_proof()
        self.assertEqual(1 << 56, proof["minimum_negative_square"])
        self.assertEqual(57, proof["single_square_minimum_unsigned_width"])
        self.assertEqual(1 << 57, proof["worst_case_exact_sum"])
        self.assertEqual(58, proof["sum_minimum_unsigned_width"])
        self.assertEqual("UQ28.30", proof["output_format"])

    def test_all_extrema_are_exact_without_saturation(self) -> None:
        self.assertEqual(0, linear_power(0, 0))
        self.assertEqual(1 << 56, linear_power(COMPONENT_MIN, 0))
        self.assertEqual(COMPONENT_MAX * COMPONENT_MAX, linear_power(COMPONENT_MAX, 0))
        self.assertEqual(POWER_MAX_REACHABLE, linear_power(COMPONENT_MIN, COMPONENT_MIN))

    def test_physical_lane_padding_is_not_a_new_numeric_width(self) -> None:
        for values in ((COMPONENT_MIN, COMPONENT_MAX), (-1, 1), (0, 0)):
            word = pack_fft_word(*values)
            self.assertEqual(values, unpack_fft_word(word))
            self.assertEqual(linear_power(*values), power_from_fft_word(word))
        with self.assertRaises(ValueError):
            unpack_fft_word(0x0000000020000000)

    def test_real_value_keeps_thirty_fractional_bits(self) -> None:
        self.assertEqual(1.0, power_real_value(1 << 30))
        self.assertEqual(float(1 << 27), power_real_value(POWER_MAX_REACHABLE))

    def test_out_of_range_components_are_rejected(self) -> None:
        for value in (COMPONENT_MIN - 1, COMPONENT_MAX + 1):
            with self.assertRaises(ValueError):
                linear_power(value, 0)


if __name__ == "__main__":
    unittest.main()
