"""Evidence-level tests for predetermined PHASE-03 statistical gates."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARISON = ROOT / "results" / "evidence" / "phase03" / "detector-comparison.json"
APPROVED_WIDEBAND_GATES = {
    "minimum_coverage": 0.60,
    "minimum_iou": 0.50,
    "maximum_overreach": 0.25,
}


class DetectionStatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(COMPARISON.read_text(encoding="utf-8"))

    def test_full_fixed_sample_counts_and_bootstrap_are_recorded(self) -> None:
        self.assertEqual(10_000, self.document["selection_contract"]["bootstrap_repetitions"])
        self.assertEqual(
            {
                "noise_frames_per_level": 1024,
                "shaped_noise_frames_per_scene": 512,
                "snr_frames_per_point": 256,
                "multi_signal_frames_per_scene": 256,
                "wideband_frames": 256,
                "edge_frames_per_scene": 128,
                "temporal_sequences_per_family": 128,
            },
            self.document["sample_counts"],
        )

    def test_all_initial_candidates_and_three_pfa_values_were_evaluated(self) -> None:
        methods = {item["method"]: item for item in self.document["methods"]}
        self.assertTrue({"regional", "ca_cfar", "os_cfar"} <= methods.keys())
        for method in ("regional", "ca_cfar", "os_cfar"):
            records = methods[method]["false_alarm"]["records"]
            self.assertEqual({1e-3, 1e-4, 1e-5}, {item["pfa_per_cut"] for item in records})
            self.assertEqual({4055, 4056}, {item["evaluated_cut_count"] for item in records})
            self.assertEqual("passed", methods[method]["implementation_gate"]["status"])
            self.assertFalse(methods[method]["implementation_gate"]["dynamic_timing_used"])

    def test_selection_is_honest_and_not_timing_based(self) -> None:
        self.assertEqual("passed", self.document["overall"])
        self.assertEqual("regional", self.document["selected_detector"])
        self.assertEqual("only eligible method", self.document["decision"]["reason"])
        self.assertFalse(self.document["selection_contract"]["dynamic_timing_used_for_selection"])
        methods = {item["method"]: item for item in self.document["methods"]}
        self.assertTrue(methods["regional"]["eligible"])
        self.assertFalse(methods["ca_cfar"]["eligible"])
        self.assertFalse(methods["os_cfar"]["eligible"])
        self.assertEqual("skipped", self.document["hybrid_status"])

    def test_wideband_and_temporal_metrics_are_separate(self) -> None:
        regional = next(item for item in self.document["methods"] if item["method"] == "regional")
        wide = regional["quality"]["wideband"]
        catalog = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase03" / "detection-scenes.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(APPROVED_WIDEBAND_GATES, catalog["evaluation_contract"]["wideband"])
        for method in self.document["methods"]:
            wideband = method["quality"]["wideband"]
            self.assertEqual(APPROVED_WIDEBAND_GATES["minimum_coverage"], wideband["minimum_coverage"])
            self.assertEqual(APPROVED_WIDEBAND_GATES["minimum_iou"], wideband["minimum_iou"])
            self.assertEqual(APPROVED_WIDEBAND_GATES["maximum_overreach"], wideband["maximum_overreach"])
        self.assertEqual(1.0, wide["successful_frame_rate"])
        self.assertIn("mean_coverage", wide)
        self.assertIn("mean_iou", wide)
        self.assertIn("mean_overflow", wide)
        temporal = regional["quality"]["temporal"]
        self.assertEqual(32, temporal["noise_frames_per_sequence"])
        self.assertIn("false_events_per_frame", temporal)


if __name__ == "__main__":
    unittest.main()
