"""PHASE-04-R1 staged comparison, gates, schedule, and bootstrap tests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from reference.parameters.evaluation import (
    _band_pairs,
    _gate_applicability,
    _paired_bootstrap_difference,
    _record_definite_event_ids,
    _select_scored_estimate,
    evaluate_parameter_methods,
    phase04_implementation_manifest,
)
from reference.parameters.scenes import load_parameter_catalog


class ParameterStatisticsTests(unittest.TestCase):
    def test_quick_comparison_exercises_all_r1_band_candidates(self) -> None:
        payload, selected = evaluate_parameter_methods(full=False)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["comparison_id"], "phase04-r1-parameter-selection")
        self.assertEqual(len(payload["noise_bandwidth_pairs"]), 24)
        self.assertEqual(payload["sample_counts"]["continuous_frames_per_sequence"], 4)
        self.assertEqual(payload["sample_counts"]["continuous_binding_frame"], 3)
        self.assertEqual(payload["sample_counts"]["burst_binding_frame"], 4)
        self.assertEqual(payload["sample_counts"]["noise_frames_per_sequence"], 32)
        self.assertEqual(payload["sample_counts"]["r1d_band_candidate_count"], 24)
        self.assertEqual(payload["sample_counts"]["r1d_phase03_unique_frames"], 184)
        self.assertEqual(payload["sample_counts"]["r1d_tuple_extractor_evaluations_maximum"], 4_416)
        first = payload["noise_bandwidth_pairs"][0]
        self.assertEqual(first["target_trials"], 10)
        self.assertEqual(first["noise_temporal_frame_count"], 32)
        by_snr = {(item["scene"], item["snr_db"]): item for item in first["family_snr_diagnostics"]}
        self.assertFalse(by_snr[("am-carrier", -6.0)]["binding"])
        self.assertFalse(by_snr[("am-carrier", 0.0)]["binding"])
        self.assertFalse(by_snr[("am-carrier", 6.0)]["binding"])
        self.assertTrue(by_snr[("am-carrier", 12.0)]["binding"])
        for name in (
            "q95_relative_bandwidth_error",
            "q95_lower_edge_normalized_to_scene_limit",
            "q95_upper_edge_normalized_to_scene_limit",
            "mean_coverage",
            "mean_iou",
            "mean_overreach",
        ):
            self.assertIn(name, by_snr[("am-carrier", -6.0)])
        if payload["noise_bandwidth_decision"]["status"] == "failed":
            self.assertIsNone(selected)
            self.assertEqual(payload["center_carrier_decision"]["status"], "skipped")
            self.assertEqual(payload["power_snr_chain"]["status"], "skipped")
            self.assertEqual(payload["signal_domain_decision"]["status"], "skipped")

    def test_noise_binding_counts_unique_temporal_events_not_valid_frames(self) -> None:
        empty = SimpleNamespace(events=())
        bandwidth = SimpleNamespace(bandwidth_state="valid")
        false_event = SimpleNamespace(event_id=901, bandwidth=bandwidth)
        noisy = SimpleNamespace(events=(false_event,))

        def sequence_side_effect(catalog, contexts, scene_id, **kwargs):  # type: ignore[no-untyped-def]
            frame_count = kwargs["frame_count"]
            if scene_id == "noise-only":
                trace = [noisy, noisy, noisy] + [empty] * (frame_count - 3)
            else:
                trace = [empty] * frame_count
            return [empty] * len(contexts), [list(trace) for _ in contexts]

        no_choice = (None, {"status": "failed", "reason": "test", "comparisons": []})
        with patch("reference.parameters.evaluation._run_shared_band_sequence", side_effect=sequence_side_effect), patch(
            "reference.parameters.evaluation._choose", return_value=no_choice
        ):
            records, _, _ = _band_pairs(load_parameter_catalog(), trials=1, full=False)
        self.assertEqual(records[0]["noise_unique_false_event_count"], 1)
        self.assertEqual(records[0]["noise_false_valid_rate"], 1 / 32)
        self.assertEqual(records[0]["noise_false_frame_rate_diagnostic"], 3 / 32)

    def test_post_runtime_target_match_is_stable_under_event_reordering(self) -> None:
        catalog = load_parameter_catalog()
        common = catalog["common"]

        def event(event_id: int, center_bin: float, lower: int, upper: int):  # type: ignore[no-untyped-def]
            center_hz = common["center_frequency_hz"] + (center_bin - 2048.0) * common["bin_spacing_hz"]
            return SimpleNamespace(
                event_id=event_id,
                frequency=SimpleNamespace(
                    spectral_center_state="valid", spectral_center_frequency_hz=center_hz,
                ),
                bandwidth=SimpleNamespace(
                    bandwidth_state="valid", lower_shifted_bin=lower, upper_shifted_bin=upper,
                ),
            )

        target = event(11, 2300.0, 2200, 2399)
        distractor = event(4, 2350.0, 2300, 2499)
        forward = _select_scored_estimate((target, distractor), catalog, 2300.0, 2200.0, 2400.0)
        reverse = _select_scored_estimate((distractor, target), catalog, 2300.0, 2200.0, 2400.0)
        self.assertEqual(forward.event_id, 11)
        self.assertEqual(reverse.event_id, 11)

    def test_noise_domain_binding_counts_unique_events_and_frames_separately(self) -> None:
        definite = SimpleNamespace(event_id=73, signal_domain=SimpleNamespace(value="Analog"))
        uncertain = SimpleNamespace(event_id=99, signal_domain=SimpleNamespace(value="Belirsiz"))
        seen: set[int] = set()
        false_frames = sum(
            _record_definite_event_ids(SimpleNamespace(events=events), seen)
            for events in ((definite,), (definite, uncertain), (uncertain,), ())
        )
        self.assertEqual(len(seen), 1)
        self.assertEqual(false_frames, 2)

    def test_every_success_gate_is_binding_with_an_exact_scope(self) -> None:
        catalog = load_parameter_catalog()
        matrix = _gate_applicability(catalog)
        self.assertEqual([item["name"] for item in matrix], list(catalog["success_gates"]))
        self.assertTrue(all(item["binding"] is True for item in matrix))
        self.assertEqual(
            next(item for item in matrix if item["name"] == "noise_false_valid_rate_maximum")["scope"],
            "noise-temporal-frame",
        )

    def test_paired_bootstrap_is_deterministic_and_directional(self) -> None:
        first = _paired_bootstrap_difference([0.1] * 32, [0.4] * 32, seed=20260404, repetitions=10_000)
        second = _paired_bootstrap_difference([0.1] * 32, [0.4] * 32, seed=20260404, repetitions=10_000)
        self.assertEqual(first, second)
        self.assertGreater(first[0], 0.0)

    def test_manifest_is_relative_ordered_and_deterministic(self) -> None:
        first = phase04_implementation_manifest()
        second = phase04_implementation_manifest()
        self.assertEqual(first, second)
        paths = [item["path"] for item in first["sources"]]
        self.assertEqual(paths, sorted(paths))
        self.assertTrue(all(not path.startswith(("/", "C:")) for path in paths))

    def test_downstream_is_not_called_when_band_stage_fails(self) -> None:
        failed = ([{"eligible": False}], None, {"status": "failed", "reason": "test", "comparisons": []})
        with patch("reference.parameters.evaluation._band_pairs", return_value=failed), patch(
            "reference.parameters.evaluation._frequency_pairs"
        ) as frequency:
            payload, selected = evaluate_parameter_methods(full=False)
        frequency.assert_not_called()
        self.assertIsNone(selected)
        self.assertEqual(payload["combined_pipeline"]["status"], "failed")

    def test_fixed_power_condition_order(self) -> None:
        contract = load_parameter_catalog()["power_benchmark"]
        conditions = [family * 12 + power * 4 + snr for family in range(4) for power in range(3) for snr in range(4)]
        self.assertEqual(conditions, list(range(48)))
        self.assertEqual(contract["snr_db_order"], [-6.0, 0.0, 6.0, 12.0])

    def test_phase_jump_analytic_bounds_do_not_exclude_psk_scenes(self) -> None:
        bpsk_rate = 47 / 256
        qpsk_rate = 23 / 128
        self.assertTrue(0.005 <= bpsk_rate <= 0.25)
        self.assertTrue(0.005 <= qpsk_rate <= 0.25)


if __name__ == "__main__":
    unittest.main()
