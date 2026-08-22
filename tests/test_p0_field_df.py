from __future__ import annotations

import unittest

from reference.p0 import (
    AntennaReference,
    DFMeasurement,
    LocationFix,
    PositionSource,
    geographic_bearing_from_manual_reference,
)


class P0FieldDFTests(unittest.TestCase):
    def test_north_zero_reference_uses_manual_angle(self) -> None:
        self.assertEqual(75.0, geographic_bearing_from_manual_reference(AntennaReference.NORTH, 75.0))

    def test_manual_geographic_reference_wraps(self) -> None:
        self.assertEqual(
            15.0,
            geographic_bearing_from_manual_reference(AntennaReference.MANUAL_GEOGRAPHIC, 75.0, 300.0),
        )

    def test_missing_manual_geographic_reference_does_not_infer_bearing(self) -> None:
        self.assertIsNone(
            geographic_bearing_from_manual_reference(AntennaReference.MANUAL_GEOGRAPHIC, 75.0)
        )

    def test_unavailable_reference_does_not_produce_geographic_bearing(self) -> None:
        self.assertIsNone(geographic_bearing_from_manual_reference(AntennaReference.UNAVAILABLE, 75.0))

    def test_manual_position_is_not_live_gnss(self) -> None:
        fix = LocationFix(39.9334, 32.8597, None, None, PositionSource.MANUAL)
        self.assertEqual(PositionSource.MANUAL, fix.source)
        self.assertNotEqual(PositionSource.LIVE_GNSS_RESERVED, fix.source)

    def test_location_validation_rejects_invalid_coordinate(self) -> None:
        with self.assertRaises(ValueError):
            LocationFix(91.0, 32.0, None, None, PositionSource.MANUAL)

    def test_unknown_accuracy_is_preserved(self) -> None:
        self.assertIsNone(LocationFix(0.0, 0.0, None, None, PositionSource.AUTO_PC).accuracy_m)

    def test_measurement_keeps_manual_angle_and_source(self) -> None:
        item = DFMeasurement.create(
            angle_deg=75.0,
            relative_power_db=-40.0,
            frequency_hz=145_000_000.0,
            confidence=0.8,
            source="REPLAY",
            geographic_bearing_deg=15.0,
        )
        self.assertEqual(75.0, item.angle_deg)
        self.assertEqual(15.0, item.geographic_bearing_deg)
        self.assertEqual("REPLAY", item.source)


if __name__ == "__main__":
    unittest.main()
