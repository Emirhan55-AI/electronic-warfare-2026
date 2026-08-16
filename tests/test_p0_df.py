from __future__ import annotations

import unittest

from reference.p0 import DFMeasurement, ManualAmplitudeDF


class P0DirectionFindingTests(unittest.TestCase):
    def test_raw_maximum_and_duplicates(self) -> None:
        model = ManualAmplitudeDF()
        for angle, power in ((0, -30), (30, -22), (60, -10), (60, -12), (90, -21), (120, -29)):
            model.add(DFMeasurement.create(angle_deg=angle, relative_power_db=power, frequency_hz=145_000_000, confidence=0.9, timestamp_utc=f"2026-01-01T00:00:{angle % 60:02.0f}Z"))
        estimate = model.estimate()
        self.assertEqual(estimate.raw_maximum_angle_deg, 60.0)
        self.assertEqual(estimate.estimated_angle_deg, 60.0)
        self.assertEqual(estimate.status, "LOB HAZIR")

    def test_wrap_and_rms_error(self) -> None:
        self.assertEqual(ManualAmplitudeDF.angular_error_deg(359.0, 1.0), 2.0)
        self.assertAlmostEqual(ManualAmplitudeDF.rms_error_deg([359.0, 11.0], [1.0, 9.0]), 2.0)

    def test_flat_pattern_is_uncertain(self) -> None:
        model = ManualAmplitudeDF()
        for angle in (0, 90, 180, 270):
            model.add(DFMeasurement.create(angle_deg=angle, relative_power_db=-20.0, frequency_hz=433_000_000, confidence=0.5))
        self.assertEqual(model.estimate().status, "BELİRSİZ MAKSİMUM")


if __name__ == "__main__":
    unittest.main()
