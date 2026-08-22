from __future__ import annotations

from pathlib import Path
import os
import unittest

from reference.p0 import analyze_two_point_hackrf_df


class TwoPointRecordedDFTests(unittest.TestCase):
    def test_real_sigmf_pair_uses_multiple_frames_after_half_second(self) -> None:
        default_root = Path(__file__).resolve().parents[1] / "datasets" / "external" / "local" / "video_data"
        root = Path(os.environ.get("TEKNOFEST_RECORDED_DATA_DIR", default_root))
        required = (root / "df_000.sigmf-meta", root / "df_090.sigmf-meta")
        if not all(path.is_file() for path in required):
            self.skipTest("Yerel gerçek kayıt seti sağlanmadı")
        result = analyze_two_point_hackrf_df(root / "df_000.sigmf-meta", root / "df_090.sigmf-meta")
        self.assertEqual(2_600_000_000.0, result.frequency_hz)
        self.assertGreater(result.zero.analyzed_frame_count, 8)
        self.assertGreater(result.ninety.analyzed_frame_count, 8)
        self.assertEqual(0, result.zero.angle_deg)
        self.assertEqual(90, result.ninety.angle_deg)
        self.assertIsNone(result.stronger)
        self.assertGreater(result.comparison_uncertainty_db, abs(result.power_difference_db))


if __name__ == "__main__":
    unittest.main()
