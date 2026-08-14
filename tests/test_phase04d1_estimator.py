"""Bounded and label-free behavior tests for the single PHASE-04-D1 estimator."""

from __future__ import annotations

import math
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from reference.detection import (
    DetectionEvent,
    DetectionFrameResult,
    DetectionRegion,
    DetectorConfig,
    LinearPowerDetector,
)
from reference.parameters.obw99 import OccupiedBandwidthEstimator
from reference.spectrum import SpectrumProcessor


def _region(start: int, end: int, peak: int) -> DetectionRegion:
    return DetectionRegion(start, end, float(start), float(end), peak, float(peak), 30.0, 1.0, 4.0, 14.0)


def _event(event_id: int, region: DetectionRegion, frame: int) -> DetectionEvent:
    return DetectionEvent(
        event_id,
        "confirmed",
        region,
        0,
        frame,
        frame + 1,
        0,
        frame * 4096,
        0.0,
        frame * 4096 / 8_000_000.0,
        True,
    )


def _spectrum(psd: np.ndarray):
    base = SpectrumProcessor().process(
        np.zeros(4096, dtype=np.complex128),
        sample_rate_hz=8_000_000.0,
        center_frequency_hz=100_000_000.0,
    )
    values = np.asarray(psd, dtype=np.float64).copy()
    values.setflags(write=False)
    return replace(base, display=replace(base.display, psd_fs2_per_hz=values))


def _detection(events: tuple[DetectionEvent, ...], frame: int) -> DetectionFrameResult:
    zero = SpectrumProcessor().process(
        np.zeros(4096, dtype=np.complex128),
        sample_rate_hz=8_000_000.0,
        center_frequency_hz=100_000_000.0,
    )
    cells = LinearPowerDetector(DetectorConfig(method="regional")).detect(zero.display.bin_power_fs2)
    regions = tuple(event.region for event in events)
    return DetectionFrameResult(frame, cells, regions, events, (), (), 0, 0)


def _power(lower: int = 1990, upper: int = 2106, level: float = 30.0) -> np.ndarray:
    values = np.ones(4096, dtype=np.float64)
    values[lower : upper + 1] = level
    return values


class Phase04D1EstimatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.estimator = OccupiedBandwidthEstimator(noise_correction=math.log(2.0))

    def test_four_frames_are_required_and_output_is_obw99(self) -> None:
        region = _region(2038, 2058, 2048)
        states = []
        result = None
        for frame in range(4):
            result = self.estimator.process(
                _spectrum(_power()),
                _detection((_event(1, region, frame),), frame),
                frame_index=frame,
                generation="source-a",
            )
            states.append(result.events[0].state)
        self.assertEqual(states[:3], ["insufficient_quality"] * 3)
        self.assertEqual(states[3], "valid")
        assert result is not None
        estimate = result.events[0]
        self.assertEqual(estimate.occupied_power_fraction, 0.99)
        self.assertGreater(float(estimate.occupied_bandwidth_hz), 0.0)
        self.assertLessEqual(float(estimate.lower_shifted_bin), 1991.0)
        self.assertGreaterEqual(float(estimate.upper_shifted_bin), 2105.0)

    def test_span_expansion_is_bounded_and_fft_edge_abstains(self) -> None:
        region = _region(2038, 2058, 2048)
        result = self.estimator.process(
            _spectrum(_power(1940, 2160)),
            _detection((_event(1, region, 0),), 0),
            frame_index=0,
        )
        self.assertIn(result.events[0].state, {"insufficient_quality", "uncertain"})
        edge = _region(20, 26, 23)
        clipped = self.estimator.process(
            _spectrum(_power(20, 40)),
            _detection((_event(2, edge, 1),), 1),
            frame_index=1,
        )
        self.assertEqual(clipped.events[0].state, "uncertain")
        self.assertTrue(clipped.events[0].analysis_clipped)

    def test_neighbor_midpoint_guard_prevents_crossing(self) -> None:
        first = _region(2038, 2058, 2048)
        second = _region(2260, 2280, 2270)
        result = None
        for frame in range(4):
            events = (_event(1, first, frame), _event(2, second, frame))
            psd = _power()
            psd[2240:2295] = 30.0
            result = self.estimator.process(_spectrum(psd), _detection(events, frame), frame_index=frame)
        assert result is not None
        by_id = {item.event_id: item for item in result.events}
        if by_id[1].state == "valid":
            midpoint = 0.5 * (first.peak_bin + second.peak_bin)
            self.assertLess(float(by_id[1].upper_shifted_bin), midpoint)

    def test_low_excess_abstains(self) -> None:
        region = _region(2038, 2058, 2048)
        psd = _power(2038, 2058, 1.2)
        result = self.estimator.process(
            _spectrum(psd), _detection((_event(1, region, 0),), 0), frame_index=0
        )
        self.assertEqual(result.events[0].state, "insufficient_quality")
        self.assertIn("insufficient_excess_power", result.events[0].quality_reasons)

    def test_miss_seek_generation_split_and_merge_clear_history(self) -> None:
        region = _region(2038, 2058, 2048)
        for frame in range(2):
            self.estimator.process(
                _spectrum(_power()), _detection((_event(1, region, frame),), frame), frame_index=frame, generation=1
            )
        self.assertEqual(self.estimator.active_history_count, 1)
        self.estimator.process(_spectrum(_power()), _detection((), 2), frame_index=2, generation=1)
        self.assertEqual(self.estimator.active_history_count, 0)
        self.estimator.notify_seek()
        self.assertEqual(self.estimator.active_history_count, 0)
        self.estimator.notify_source_change(2)
        split_a = _region(2035, 2047, 2042)
        split_b = _region(2048, 2060, 2054)
        self.estimator.process(
            _spectrum(_power()),
            _detection((_event(2, split_a, 3), _event(3, split_b, 3)), 3),
            frame_index=3,
            generation=2,
        )
        self.assertLessEqual(self.estimator.active_history_count, 2)
        merged = _region(2035, 2060, 2048)
        self.estimator.process(
            _spectrum(_power()), _detection((_event(2, merged, 4),), 4), frame_index=4, generation=2
        )
        self.assertLessEqual(self.estimator.active_history_count, 1)

    def test_memory_and_event_count_are_bounded(self) -> None:
        events = tuple(_event(index + 1, _region(100 + index * 50, 102 + index * 50, 101 + index * 50), 0) for index in range(65))
        result = self.estimator.process(_spectrum(np.ones(4096)), _detection(events, 0), frame_index=0)
        self.assertLessEqual(result.active_history_count, 64)
        self.assertEqual(result.history_payload_bytes, 659456)
        self.assertEqual(result.dropped_event_count, 1)

    def test_runtime_module_has_no_reference_or_label_input_path(self) -> None:
        source = Path("reference/parameters/obw99.py").read_text(encoding="utf-8")
        for forbidden in ("scene_id", "modulation_label", "nominal_center_frequency", "snr_label", "clean-reference.json"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
