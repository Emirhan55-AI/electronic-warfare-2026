from __future__ import annotations

import math
import unittest

from reference.p0 import (
    DFEstimate,
    DFMeasurement,
    SensorPosition,
    build_direction_presentation,
    destination_point,
    geographic_lob_geometry,
    normalize_bearing_deg,
)


class P0MapDirectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.measurement = DFMeasurement.create(
            angle_deg=75.0,
            relative_power_db=-13.0,
            frequency_hz=145_000_000.0,
            confidence=0.8,
            timestamp_utc="2026-08-16T12:00:00Z",
        )
        self.estimate = DFEstimate(75.0, 75.0, -13.0, 0.8, 24, "LOB HAZIR")

    def test_bearing_normalization(self) -> None:
        self.assertEqual(0.0, normalize_bearing_deg(0.0))
        self.assertEqual(90.0, normalize_bearing_deg(90.0))
        self.assertEqual(0.0, normalize_bearing_deg(360.0))
        self.assertEqual(15.0, normalize_bearing_deg(375.0))
        self.assertEqual(355.0, normalize_bearing_deg(-5.0))
        with self.assertRaises(ValueError):
            normalize_bearing_deg(math.nan)

    def test_heading_plus_relative_df_builds_geographic_lob(self) -> None:
        sensor = SensorPosition("Test sensörü", 39.9334, 32.8597, 900.0, 0.0, "HOST/SYNTHETIC")
        presentation = build_direction_presentation(
            sensor=sensor,
            estimate=self.estimate,
            peak_measurement=self.measurement,
            backend="HOST/REPLAY",
            source="HOST/SYNTHETIC",
        )
        self.assertEqual(75.0, presentation.relative_antenna_angle_deg)
        self.assertEqual(75.0, presentation.geographic_azimuth_deg)
        self.assertTrue(presentation.has_geographic_lob)
        self.assertEqual("Coğrafi yön hesaplandı", presentation.geographic_status)

        wrapped_sensor = SensorPosition("Test sensörü", 39.9334, 32.8597, None, 300.0, "HOST/SYNTHETIC")
        wrapped = build_direction_presentation(
            sensor=wrapped_sensor,
            estimate=self.estimate,
            peak_measurement=self.measurement,
            backend="HOST/REPLAY",
            source="HOST/SYNTHETIC",
        )
        self.assertEqual(15.0, wrapped.geographic_azimuth_deg)

    def test_missing_heading_never_produces_geographic_lob(self) -> None:
        sensor = SensorPosition("Manuel sensör", 0.0, 0.0, None, None, "MANUEL")
        presentation = build_direction_presentation(
            sensor=sensor,
            estimate=self.estimate,
            peak_measurement=self.measurement,
            backend="HOST/REPLAY",
            source="MANUEL",
        )
        self.assertIsNone(presentation.geographic_azimuth_deg)
        self.assertFalse(presentation.has_geographic_lob)
        self.assertEqual("Bağıl yön — coğrafi azimut referansı yok", presentation.geographic_status)

    def test_invalid_coordinates_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SensorPosition("Geçersiz", 90.1, 0.0, None, None, "MANUEL")
        with self.assertRaises(ValueError):
            SensorPosition("Geçersiz", 0.0, -180.1, None, None, "MANUEL")

    def test_geographic_lob_uses_cardinal_geodesic_endpoints(self) -> None:
        north_latitude, north_longitude = destination_point(0.0, 0.0, 0.0, 1_000.0)
        east_latitude, east_longitude = destination_point(0.0, 0.0, 90.0, 1_000.0)
        south_latitude, south_longitude = destination_point(0.0, 0.0, 180.0, 1_000.0)
        west_latitude, west_longitude = destination_point(0.0, 0.0, 270.0, 1_000.0)
        self.assertGreater(north_latitude, 0.0)
        self.assertAlmostEqual(0.0, north_longitude, places=8)
        self.assertAlmostEqual(0.0, east_latitude, places=8)
        self.assertGreater(east_longitude, 0.0)
        self.assertLess(south_latitude, 0.0)
        self.assertAlmostEqual(0.0, south_longitude, places=8)
        self.assertAlmostEqual(0.0, west_latitude, places=8)
        self.assertLess(west_longitude, 0.0)

    def test_lob_geometry_is_finite_rendering_only(self) -> None:
        sensor = SensorPosition("Test sensörü", 39.9334, 32.8597, 900.0, 0.0, "HOST/SYNTHETIC")
        presentation = build_direction_presentation(
            sensor=sensor,
            estimate=self.estimate,
            peak_measurement=self.measurement,
            backend="HOST/REPLAY",
            source="HOST/SYNTHETIC",
        )
        geometry = geographic_lob_geometry(presentation, display_distance_m=2_500.0)
        self.assertIsNotNone(geometry)
        assert geometry is not None
        self.assertEqual(75.0, geometry.bearing_deg)
        self.assertEqual(2_500.0, geometry.display_distance_m)
        self.assertEqual(4, len(geometry.arrowhead_coordinates))
        self.assertNotEqual(geometry.start_latitude_deg, geometry.render_endpoint_latitude_deg)

        no_heading = build_direction_presentation(
            sensor=SensorPosition("Manuel", 0.0, 0.0, None, None, "MANUEL"),
            estimate=self.estimate,
            peak_measurement=self.measurement,
            backend="HOST/REPLAY",
            source="MANUEL",
        )
        self.assertIsNone(geographic_lob_geometry(no_heading))


if __name__ == "__main__":
    unittest.main()
