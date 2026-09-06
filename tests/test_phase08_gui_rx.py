"""Ham ölçümde kayıp veya görünmez pencere başarıya dönüştürülemez."""
import copy
import json
import unittest

from scripts.verify_phase08_gui_rx import summarize


def fixture():
    count = 1000
    result = {"fpga_enabled": True, "completed_frames": count, "preview_frames": 67,
              "input_saturated_components": 0, "output_saturated_components": 0}
    return {"configuration": {"frame_count": count}, "fpga_response_observed": True,
            "checks": {"source_and_native_unchanged": True},
            "sessions": [{"result": result,
                          "rx": {"frames_received": count, "bytes_received": count * 32768,
                                 "overruns": 0, "longest_overrun_bytes": 0, "process_returncode": 0,
                                 "stderr_text": "Transfer statistics:\n0 overruns, longest 0 bytes"},
                          "transport": {"frames_sent": count, "frames_received": count,
                                        "crc_errors": 0, "sequence_errors": 0, "queue_drops": 0,
                                        "last_error": None}}],
            "presented": [[i * 15, .02 + i * .03072, 10] for i in range(66)],
            "health": [[2.048, 999, 20, True, True]]}


class GUIRXEvidenceTests(unittest.TestCase):
    def test_complete_visible_observation_can_pass_only_its_scope(self):
        result = summarize(fixture())
        self.assertTrue(result["measurement_passed"])
        self.assertFalse(result["ST06_complete"])
        self.assertFalse(result["rf_accuracy_acceptance"])
        self.assertFalse(result["fpga_image_identity_verified"])

    def test_final_usb_error_cannot_be_hidden_by_success_summary(self):
        run = fixture()
        run["status"] = "passed"
        run["sessions"][0]["rx"]["stderr_text"] = "Transfer statistics:\n1 overruns, longest 66496 bytes"
        self.assertFalse(summarize(run)["measurement_passed"])

    def test_full_frame_count_does_not_override_crc_failure(self):
        run = fixture()
        run["sessions"][0]["transport"]["crc_errors"] = 1
        self.assertFalse(summarize(run)["measurement_passed"])

    def test_partial_gui_interval_cannot_use_good_prefix_rate(self):
        run = fixture()
        run["presented"] = run["presented"][:20]
        self.assertFalse(summarize(run)["measurement_passed"])

    def test_internal_display_gap_failure_is_json_serializable(self):
        run = fixture()
        run["presented"] = run["presented"][:5] + run["presented"][50:]
        result = summarize(run)
        self.assertFalse(result["measurement_passed"])
        self.assertFalse(json.loads(json.dumps(result))["checks"]["no_presentation_gap_over_one_second"])

    def test_hidden_window_is_not_display_acceptance(self):
        run = fixture()
        run["health"][0][4] = False
        self.assertFalse(summarize(run)["measurement_passed"])

    def test_missing_counts_and_nonfinite_samples_fail_closed(self):
        for kind in ("count", "nan", "duplicate"):
            run = copy.deepcopy(fixture())
            if kind == "count":
                del run["sessions"][0]["rx"]["frames_received"]
            elif kind == "nan":
                run["presented"][0][2] = float("nan")
            else:
                run["presented"][1][0] = run["presented"][0][0]
            with self.subTest(kind=kind):
                self.assertFalse(summarize(run)["measurement_passed"])


if __name__ == "__main__":
    unittest.main()
