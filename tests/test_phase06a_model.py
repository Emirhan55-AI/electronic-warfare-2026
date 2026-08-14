"""Bit-width, protocol and arithmetic tests for PHASE-06A."""

from __future__ import annotations

import unittest

from reference.rtl import (
    ERROR_EARLY_TLAST,
    ERROR_MISSING_TLAST,
    FRAME_LENGTH,
    AxisFrameStatsModel,
    frame_stats,
    sample_power,
    unpack_ci8_word,
)


class Phase06AModelTests(unittest.TestCase):
    def test_ci8_unpack_and_power_cover_extrema(self) -> None:
        self.assertEqual((-128, -128), unpack_ci8_word(0x8080))
        self.assertEqual((127, 127), unpack_ci8_word(0x7F7F))
        self.assertEqual(32768, sample_power(0x8080))
        self.assertEqual(32258, sample_power(0x7F7F))
        self.assertEqual(0, sample_power(0))

    def test_energy_width_covers_worst_case_without_saturation(self) -> None:
        result = frame_stats((0x8080,) * FRAME_LENGTH)
        self.assertEqual(134_217_728, result.total_energy)
        self.assertEqual(32768, result.peak_power)
        self.assertEqual(0, result.peak_index)
        self.assertFalse(result.protocol_error)

    def test_peak_tie_uses_first_index(self) -> None:
        words = tuple(0x7F7F if index in (23, 99) else 0 for index in range(FRAME_LENGTH))
        self.assertEqual(23, frame_stats(words).peak_index)

    def test_early_missing_and_late_tlast_are_controlled(self) -> None:
        early = AxisFrameStatsModel()
        result = None
        for index in range(3):
            result = early.accept(0x0001, tlast=index == 2)
        self.assertIsNotNone(result)
        self.assertEqual(ERROR_EARLY_TLAST, result.error_code)
        self.assertEqual(3, result.sample_count)

        missing = AxisFrameStatsModel()
        for _ in range(FRAME_LENGTH):
            result = missing.accept(0, tlast=False)
        self.assertEqual(ERROR_MISSING_TLAST, result.error_code)
        self.assertTrue(missing.dropping_late_frame)
        self.assertIsNone(missing.accept(0, tlast=False))
        self.assertIsNone(missing.accept(0, tlast=True))
        self.assertEqual(1, missing.late_tlast_recoveries)
        recovered = None
        for index in range(FRAME_LENGTH):
            recovered = missing.accept(0, tlast=index == FRAME_LENGTH - 1)
        self.assertIsNotNone(recovered)
        self.assertEqual(0, recovered.error_code)
        self.assertEqual(FRAME_LENGTH, recovered.sample_count)

    def test_reset_discards_partial_frame_and_consecutive_frames_work(self) -> None:
        model = AxisFrameStatsModel()
        for _ in range(128):
            self.assertIsNone(model.accept(0x0001, tlast=False))
        model.reset()
        results = []
        for frame in range(2):
            for index in range(FRAME_LENGTH):
                value = model.accept(frame, tlast=index == FRAME_LENGTH - 1)
                if value is not None:
                    results.append(value)
        self.assertEqual(2, len(results))
        self.assertEqual((0, FRAME_LENGTH), (results[0].total_energy, results[0].sample_count))
        self.assertEqual(FRAME_LENGTH, results[1].total_energy)


if __name__ == "__main__":
    unittest.main()
