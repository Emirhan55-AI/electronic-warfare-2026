"""Unit tests for PHASE-04 frame-local extraction primitives."""

from __future__ import annotations

import unittest
from dataclasses import replace

import numpy as np

from reference.detection import (
    DetectionEvent,
    DetectionFrameResult,
    DetectionPipeline,
    DetectionRegion,
    DetectorConfig,
    LinearPowerDetector,
)
from reference.parameters import (
    FEATURE_HISTORY_BYTES,
    FeatureHistoryStore,
    MethodSelection,
    ParameterExtractor,
    build_analysis_candidates,
    compute_transient_guard,
    estimate_band_support,
    extract_frame_features,
    generate_parameter_scene,
    load_parameter_catalog,
)
from reference.spectrum import SpectrumProcessor


def _region(start: int, end: int, peak: int | None = None) -> DetectionRegion:
    selected = start if peak is None else peak
    return DetectionRegion(start, end, float(start), float(end), selected, float(selected), 10.0, 1.0, 4.0, 10.0)


def _detection(regions: list[DetectionRegion], *, frame_index: int = 1) -> DetectionFrameResult:
    spectrum = SpectrumProcessor().process(
        np.zeros(4096, dtype=np.complex128),
        sample_rate_hz=8_000_000.0,
        center_frequency_hz=100_000_000.0,
    )
    cells = LinearPowerDetector(DetectorConfig(method="regional")).detect(spectrum.display.bin_power_fs2)
    events = tuple(
        DetectionEvent(
            event_id=index + 1,
            state="confirmed",
            region=region,
            first_frame=0,
            last_seen_frame=frame_index,
            seen_count=2,
            first_sample=0,
            last_seen_sample=frame_index * 4096,
            first_time_seconds=0.0,
            last_seen_time_seconds=frame_index * 4096 / 8_000_000.0,
            observed_this_frame=True,
        )
        for index, region in enumerate(regions)
    )
    return DetectionFrameResult(frame_index, cells, tuple(regions), events, (), (), 0, 0)


class ParameterReferenceTests(unittest.TestCase):
    def test_transient_guard_is_derived_and_fixed(self) -> None:
        self.assertEqual(compute_transient_guard(), (1106, 2, 1152))
        self.assertEqual(4096 - 2 * 1152, 1792)

    def test_feature_history_has_exact_payload_and_four_records(self) -> None:
        history = FeatureHistoryStore()
        self.assertEqual(history.payload_bytes, 67_840)
        self.assertEqual(FEATURE_HISTORY_BYTES, 67_840)
        for frame in range(6):
            records = history.append(7, frame, np.full(32, frame + 1.0))
        self.assertEqual(records.shape, (4, 32))
        self.assertEqual(records[:, 0].tolist(), [3.0, 4.0, 5.0, 6.0])
        self.assertFalse(any(array.dtype == np.complex128 for array in (history.features, history.frame_indices, history.valid)))

    def test_frame_features_use_fixed_guard_and_remain_finite(self) -> None:
        index = np.arange(4096)
        samples = np.exp(1j * 2.0 * np.pi * 256.0 * index / 4096.0)
        features = extract_frame_features(
            samples,
            lower_bin=2302,
            upper_bin=2306,
            center_bin=2304.0,
            sample_rate_hz=8_000_000.0,
            frame_index=0,
            snr_db=12.0,
        )
        self.assertEqual(features.shape, (32,))
        self.assertEqual(features[0], 1792.0)
        self.assertTrue(np.all(np.isfinite(features)))

    def test_nonconsecutive_frame_resets_one_track_history(self) -> None:
        history = FeatureHistoryStore()
        history.append(1, 0, np.ones(32))
        records = history.append(1, 2, np.full(32, 2.0))
        self.assertEqual(records.shape, (1, 32))

    def test_feature_history_owner_queries_and_targeted_discard(self) -> None:
        history = FeatureHistoryStore()
        history.append(4, 7, np.ones(32))
        self.assertTrue(history.contains(4))
        self.assertEqual(history.last_frame(4), 7)
        history.discard(4)
        self.assertFalse(history.contains(4))
        self.assertIsNone(history.last_frame(4))

    def test_clustered_analysis_boundaries_are_atomic(self) -> None:
        one_region = _detection([_region(1000, 1005, 1002)])
        self.assertEqual(
            build_analysis_candidates(one_region, "analysis.single-region-v1"),
            build_analysis_candidates(one_region, "analysis.clustered-regions-v1"),
        )
        gap_24 = _detection([_region(100, 100), _region(125, 125)])
        gap_25 = _detection([_region(100, 100), _region(126, 126)])
        self.assertEqual(len(build_analysis_candidates(gap_24, "analysis.clustered-regions-v1")), 1)
        self.assertEqual(len(build_analysis_candidates(gap_25, "analysis.clustered-regions-v1")), 2)

        width_112 = _detection([_region(value, value) for value in (100, 125, 150, 175, 200, 211)])
        width_113 = _detection([_region(value, value) for value in (100, 125, 150, 175, 200, 212)])
        accepted = build_analysis_candidates(width_112, "analysis.clustered-regions-v1")
        rejected = build_analysis_candidates(width_113, "analysis.clustered-regions-v1")
        self.assertEqual((accepted[0].hull_start_bin, accepted[0].hull_end_bin, accepted[0].state), (100, 211, "valid"))
        self.assertEqual(
            (
                accepted[0].search_start_bin,
                accepted[0].search_end_bin,
                accepted[0].left_reference_start_bin,
                accepted[0].left_reference_end_bin,
                accepted[0].right_reference_start_bin,
                accepted[0].right_reference_end_bin,
            ),
            (68, 243, 48, 63, 248, 263),
        )
        self.assertEqual(rejected[0].invalid_reason, "analysis_candidate_overflow")

        edge = build_analysis_candidates(_detection([_region(30, 31)]), "analysis.single-region-v1")
        self.assertEqual(edge[0].invalid_reason, "reference_cells_unavailable")

        regions_32 = [_region(500 + index * 3, 500 + index * 3) for index in range(32)]
        regions_33 = [_region(500 + index * 3, 500 + index * 3) for index in range(33)]
        self.assertEqual(build_analysis_candidates(_detection(regions_32), "analysis.clustered-regions-v1")[0].state, "valid")
        self.assertEqual(
            build_analysis_candidates(_detection(regions_33), "analysis.clustered-regions-v1")[0].invalid_reason,
            "analysis_candidate_overflow",
        )

    def test_cluster_owner_prefers_continuous_history_then_event_id(self) -> None:
        detection = _detection([_region(1000, 1002, 1001), _region(1010, 1012, 1011)])
        without_history = build_analysis_candidates(detection, "analysis.clustered-regions-v1")
        self.assertEqual(without_history[0].owner_event_id, 1)
        history = FeatureHistoryStore()
        history.append(2, 0, np.ones(32))
        with_history = build_analysis_candidates(detection, "analysis.clustered-regions-v1", history)
        self.assertEqual(with_history[0].owner_event_id, 2)
        self.assertEqual(with_history[0].source_event_ids, (1, 2))

    def test_frozen_close_pair_keeps_two_exact_candidates(self) -> None:
        catalog = load_parameter_catalog()
        detector = DetectionPipeline(LinearPowerDetector(DetectorConfig(method="regional")))
        output = None
        for frame_index in range(2):
            frame = generate_parameter_scene(
                "close-am-qpsk",
                trial_index=0,
                condition_index=0,
                frame_index=frame_index,
                snr_db=12.0,
                catalog=catalog,
            )
            spectrum = SpectrumProcessor().process(
                frame.samples,
                sample_rate_hz=float(catalog["common"]["sample_rate_hz"]),
                center_frequency_hz=float(catalog["common"]["center_frequency_hz"]),
            )
            output = detector.process(spectrum, frame_index=frame_index)
        assert output is not None
        candidates = build_analysis_candidates(output, "analysis.clustered-regions-v1")
        self.assertEqual(
            [(item.owner_event_id, item.hull_start_bin, item.hull_end_bin, item.search_start_bin, item.search_end_bin) for item in candidates],
            [(1, 1839, 1857, 1807, 1889), (2, 1950, 1984, 1918, 2016)],
        )
        self.assertTrue(all(item.state == "valid" for item in candidates))

    def test_multi_component_am_support_and_expansion_order(self) -> None:
        catalog = load_parameter_catalog()
        scene = next(item for item in catalog["scenes"] if item["id"] == "am-carrier")
        center = int(round(2048.0 + float(scene["signed_center_bin"])))
        offset = int(scene["message_bins"])
        power = np.ones(4096, dtype=np.float64)
        power[[center - offset, center, center + offset]] = [12.0, 100.0, 12.0]
        support = estimate_band_support(
            power,
            center - 33,
            center + 32,
            center,
            1.0,
            "band.multi-component-excess-99-v1",
        )
        self.assertEqual(support.state, "valid")
        self.assertEqual(support.retained_component_count, 3)
        self.assertEqual(support.expansion_order, ("anchor", "left", "right"))
        self.assertEqual(support.retained_component_indices, (0, 1, 2))
        assert support.lower_shifted_bin is not None and support.upper_shifted_bin is not None
        self.assertLessEqual(support.lower_shifted_bin, center - offset)
        self.assertGreaterEqual(support.upper_shifted_bin, center + offset)

    def test_frozen_am_three_components_are_one_physical_support(self) -> None:
        catalog = load_parameter_catalog()
        scene = next(item for item in catalog["scenes"] if item["id"] == "am-carrier")
        center = 2048.0 + float(scene["signed_center_bin"])
        offset = float(scene["message_bins"])
        detector = DetectionPipeline(LinearPowerDetector(DetectorConfig(method="regional")))
        extractor = ParameterExtractor(
            MethodSelection(
                "noise.sideband-median-ln2",
                "band.multi-component-excess-99-v1",
                "center.excess-power-centroid",
                "carrier.peak-gated",
                "domain.explainable-rules",
                "analysis.clustered-regions-v1",
            )
        )
        result = None
        for frame_index in range(2):
            frame = generate_parameter_scene(
                "am-carrier",
                trial_index=0,
                frame_index=frame_index,
                snr_db=12.0,
                catalog=catalog,
            )
            spectrum = SpectrumProcessor().process(
                frame.samples,
                sample_rate_hz=float(catalog["common"]["sample_rate_hz"]),
                center_frequency_hz=float(catalog["common"]["center_frequency_hz"]),
            )
            detection = detector.process(spectrum, frame_index=frame_index)
            result = extractor.process(frame.samples, spectrum, detection, frame_index=frame_index)
        assert result is not None and len(result.events) == 1
        bandwidth = result.events[0].bandwidth
        assert bandwidth.lower_shifted_bin is not None and bandwidth.upper_shifted_bin is not None
        self.assertLessEqual(bandwidth.lower_shifted_bin, int(round(center - offset)))
        self.assertGreaterEqual(bandwidth.upper_shifted_bin, int(round(center + offset)))

    def test_multi_component_fraction_gap_and_component_bounds(self) -> None:
        exact_side_excess = 0.02 / 0.98 * 1000.0
        for below, expected in ((False, 2), (True, 1)):
            side_excess = exact_side_excess
            if below:
                side_excess = np.nextafter(np.nextafter(side_excess, 0.0), 0.0)
            power = np.ones(120, dtype=np.float64)
            power[60] = 1001.0
            power[50] = 1.0 + side_excess
            support = estimate_band_support(power, 0, 119, 60, 1.0, "band.multi-component-excess-99-v1")
            self.assertEqual(support.retained_component_count, expected)

        for gap, expected in ((16, 2), (17, 1)):
            power = np.ones(140, dtype=np.float64)
            power[70:73] = 100.0
            left_end = 70 - (gap + 2) - 1
            power[left_end - 2 : left_end + 1] = 20.0
            support = estimate_band_support(power, 0, 139, 71, 1.0, "band.multi-component-excess-99-v1")
            self.assertEqual(support.retained_component_count, expected)

        power = np.ones(176, dtype=np.float64)
        power[5:170:5] = 20.0
        overflow = estimate_band_support(power, 0, 175, 85, 1.0, "band.multi-component-excess-99-v1")
        self.assertEqual(overflow.invalid_reason, "support_component_overflow")

    def test_parameter_output_requires_confirmed_and_observed_event(self) -> None:
        catalog = load_parameter_catalog()
        frame = generate_parameter_scene("am-carrier", trial_index=3, catalog=catalog)
        spectrum = SpectrumProcessor().process(
            frame.samples,
            sample_rate_hz=float(catalog["common"]["sample_rate_hz"]),
            center_frequency_hz=float(catalog["common"]["center_frequency_hz"]),
        )
        detector = DetectionPipeline(LinearPowerDetector(DetectorConfig(method="regional")))
        first = detector.process(spectrum, frame_index=0)
        extractor = ParameterExtractor(
            MethodSelection(
                "noise.sideband-median-ln2",
                "band.multi-component-excess-99-v1",
                "center.excess-power-centroid",
                "carrier.peak-gated",
                "domain.explainable-rules",
                "analysis.clustered-regions-v1",
            )
        )
        tentative = extractor.process(frame.samples, spectrum, first, frame_index=0)
        self.assertEqual(tentative.events, ())
        self.assertGreater(tentative.dropped_owner_candidate_count, 0)
        second = detector.process(spectrum, frame_index=1)
        self.assertGreater(len(extractor.process(frame.samples, spectrum, second, frame_index=1).events), 0)
        missed = replace(
            second,
            frame_index=2,
            regions=(),
            active_events=tuple(replace(event, observed_this_frame=False) for event in second.active_events),
        )
        self.assertEqual(extractor.process(frame.samples, spectrum, missed, frame_index=2).events, ())


if __name__ == "__main__":
    unittest.main()
