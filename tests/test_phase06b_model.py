"""Bit-true fixed-point Hann tests for PHASE-06B."""

from __future__ import annotations

import unittest

from reference.rtl import (
    FRAME_LENGTH,
    build_word_length_study,
    pack_windowed_word,
    quantized_hann_coefficients,
    round_shift_away_from_zero,
    unpack_windowed_word,
    window_component,
    window_frame,
    window_word,
)


class Phase06BHannModelTests(unittest.TestCase):
    def test_periodic_coefficients_have_frozen_symmetry_and_endpoints(self) -> None:
        coefficients = quantized_hann_coefficients()
        self.assertEqual(FRAME_LENGTH, len(coefficients))
        self.assertEqual((0, 0, 32768, 0), (coefficients[0], coefficients[1], coefficients[2048], coefficients[-1]))
        self.assertEqual(coefficients[1:], coefficients[:0:-1])
        self.assertEqual(11, sum(value == 0 for value in coefficients))

    def test_word_length_selection_is_quantitatively_locked(self) -> None:
        study = build_word_length_study()
        selected = study["selected_characterization"]
        self.assertEqual(15, selected["fractional_bits"])
        self.assertEqual(16, selected["coefficient_bits"])
        self.assertLessEqual(selected["maximum_output_error_fs"], 3.04e-5)
        metric = "enumerated_rms_signal_to_error_ratio_db"
        self.assertGreaterEqual(selected[metric], 90.8)
        candidates = {item["fractional_bits"]: item for item in study["candidate_formats"]}
        self.assertLess(candidates[16][metric] - selected[metric], 1.0)
        self.assertNotIn("output_snr_db", selected)
        self.assertIn("not a measured SNR", study["metric_definitions"][metric])

    def test_rounding_is_nearest_with_ties_away_from_zero(self) -> None:
        self.assertEqual(0, round_shift_away_from_zero(63))
        self.assertEqual(1, round_shift_away_from_zero(64))
        self.assertEqual(1, round_shift_away_from_zero(127))
        self.assertEqual(-1, round_shift_away_from_zero(-64))
        self.assertEqual(-1, round_shift_away_from_zero(-127))

    def test_signed_extrema_and_complex_layout(self) -> None:
        self.assertEqual(-32768, window_component(-128, 32768))
        self.assertEqual(32512, window_component(127, 32768))
        self.assertEqual(0, window_component(-128, 0))
        word = pack_windowed_word(-32768, 32512)
        self.assertEqual((-32768, 32512), unpack_windowed_word(word))
        self.assertEqual((-32768, -32768), unpack_windowed_word(window_word(0x8080, 2048)))
        self.assertEqual((32512, 32512), unpack_windowed_word(window_word(0x7F7F, 2048)))

    def test_all_input_values_and_coefficients_remain_in_sq1_15(self) -> None:
        coefficients = quantized_hann_coefficients()
        for component in range(-128, 128):
            for coefficient in coefficients:
                result = window_component(component, coefficient)
                self.assertGreaterEqual(result, -32768)
                self.assertLessEqual(result, 32767)

    def test_zero_impulse_alternation_and_constant_frames(self) -> None:
        zero = window_frame((0,) * FRAME_LENGTH)
        self.assertEqual({0}, set(zero))
        impulse = window_frame(tuple(0x8080 if index == 137 else 0 for index in range(FRAME_LENGTH)))
        self.assertEqual((-360, -360), unpack_windowed_word(impulse[137]))
        self.assertEqual(1, sum(word != 0 for word in impulse))
        alternating = window_frame(tuple(0x8080 if index % 2 == 0 else 0x7F7F for index in range(FRAME_LENGTH)))
        self.assertEqual((-32768, -32768), unpack_windowed_word(alternating[2048]))
        constant = window_frame((0x40C0,) * FRAME_LENGTH)
        self.assertEqual((-16384, 16384), unpack_windowed_word(constant[2048]))


if __name__ == "__main__":
    unittest.main()
