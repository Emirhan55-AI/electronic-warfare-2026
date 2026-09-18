from __future__ import annotations

import math
import unittest

from algorithms.p0 import DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE, ManualAmplitudeDF


def measurement(
    angle: float,
    power: float,
    *,
    frame_id: int,
    frequency_hz: float = 145_000_000.0,
    binding: str = "hackrf|145000000|2000000|24:24|channel-a",
) -> DFMeasurement:
    return DFMeasurement.create(
        angle_deg=angle,
        relative_power_db=power,
        frequency_hz=frequency_hz,
        confidence=0.95,
        channel_bandwidth_hz=12_500.0,
        receiver_binding=binding,
        frame_id=frame_id,
        source="LIVE_HACKRF",
    )


class Phase09AmplitudeDFTests(unittest.TestCase):
    def test_full_circular_sweep_reports_only_measured_raw_maximum(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        powers = {
            angle: -38.0 + 25.0 * max(math.cos(math.radians(angle - 45.0)), 0.0) ** 4
            + 3.0 * max(-math.cos(math.radians(angle - 45.0)), 0.0) ** 2
            for angle in range(0, 360, 15)
        }
        for frame_id, (angle, power) in enumerate(powers.items()):
            model.add(measurement(float(angle), power, frame_id=frame_id))
        estimate = model.estimate()
        self.assertEqual("LOB HAZIR", estimate.status)
        self.assertEqual(45.0, estimate.raw_maximum_angle_deg)
        self.assertEqual(estimate.raw_maximum_angle_deg, estimate.estimated_angle_deg)
        self.assertEqual(24, estimate.distinct_angle_count)
        self.assertEqual(15.0, estimate.maximum_angular_gap_deg)
        self.assertAlmostEqual(15.0 / math.sqrt(12.0), estimate.angular_sampling_rms_deg)
        self.assertEqual(FIELD_AMPLITUDE_DF_PROFILE.profile_id, estimate.profile_id)

    def test_sector_without_opposite_point_fails_front_back_gate(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        for frame_id, angle in enumerate(range(0, 120, 5)):
            model.add(measurement(float(angle), -10.0 - abs(angle - 40.0) / 4.0, frame_id=frame_id))
        self.assertEqual("ÖN/ARKA BELİRSİZ", model.estimate().status)

    def test_adaptive_bracket_refinement_and_opposite_point_report_lob(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        values = (
            (0.0, -30.0), (15.0, -34.0), (30.0, -42.0),
            (345.0, -33.0), (330.0, -44.0),
            (5.0, -25.0), (10.0, -20.0), (190.0, -55.0),
        )
        for frame_id, (angle, power) in enumerate(values):
            model.add(measurement(angle, power, frame_id=frame_id))
        estimate = model.estimate()
        self.assertEqual("LOB HAZIR", estimate.status)
        self.assertEqual(10.0, estimate.estimated_angle_deg)
        self.assertEqual(8, estimate.distinct_angle_count)

    def test_equal_front_and_back_lobes_are_rejected(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        for frame_id, angle in enumerate(range(0, 360, 15)):
            distance = min(angle, 360 - angle)
            back_distance = abs(angle - 180)
            power = max(-9.0 - distance / 8.0, -9.5 - back_distance / 8.0)
            model.add(measurement(float(angle), power, frame_id=frame_id))
        estimate = model.estimate()
        self.assertEqual("ÖN/ARKA BELİRSİZ", estimate.status)
        self.assertAlmostEqual(0.5, estimate.front_to_back_db)

    def test_receiver_setting_change_is_fail_closed(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        for frame_id, angle in enumerate(range(0, 360, 15)):
            binding = "gain-a" if angle != 345 else "gain-b"
            model.add(measurement(float(angle), -10.0 - angle / 20.0, frame_id=frame_id, binding=binding))
        self.assertEqual("ALICI AYARI DEĞİŞTİ", model.estimate().status)

    def test_target_frequency_change_is_fail_closed(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        for frame_id, angle in enumerate(range(0, 360, 15)):
            frequency = 145_000_000.0 if angle != 345 else 145_010_000.0
            model.add(measurement(float(angle), -10.0 - angle / 20.0, frame_id=frame_id, frequency_hz=frequency))
        self.assertEqual("HEDEF FREKANSI DEĞİŞTİ", model.estimate().status)

    def test_same_source_frame_cannot_be_counted_twice(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        model.add(measurement(0.0, -10.0, frame_id=7))
        with self.assertRaisesRegex(ValueError, "aynı kaynak karesi"):
            model.add(measurement(45.0, -12.0, frame_id=7))

    def test_repeated_db_values_are_averaged_in_linear_power(self) -> None:
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        model.add(measurement(0.0, -10.0, frame_id=1))
        model.add(measurement(0.0, -20.0, frame_id=2))
        expected = 10.0 * math.log10((10.0 ** -1.0 + 10.0 ** -2.0) / 2.0)
        self.assertAlmostEqual(expected, model.estimate().peak_power_db, places=12)


if __name__ == "__main__":
    unittest.main()
