from __future__ import annotations

import unittest

import numpy as np

from host.acquisition import CaptureResult
from reference.p0 import (
    HackRFSearchBackend,
    HackRFSearchPlanner,
    HackRFTuningProfile,
    P0SearchEngine,
    ReplaySearchBackend,
    SearchRequest,
    shifted_absolute_frequency_axis,
)
from reference.p0.fixtures import build_judge_demo_engine


SERIAL = "0000000000000000123456789abcdef0"


class FakeRealBackend:
    backend_kind = "real"

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.configs = []

    def capture(self, config, cancellation=None):
        del cancellation
        self.configs.append(config)
        return CaptureResult("passed", self.payload, config, "real")

    def cancel(self) -> None:
        pass


class HackRFSearchPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = HackRFTuningProfile()
        self.planner = HackRFSearchPlanner(profile=self.profile)

    def test_small_exact_one_window_multi_and_non_integral_band(self) -> None:
        small = self.planner.plan(SearchRequest.judge_band_mhz(100.0, 101.0))
        exact = self.planner.plan(SearchRequest.judge_band_mhz(100.0, 106.0))
        multi = self.planner.plan(SearchRequest.judge_band_mhz(100.0, 115.0))
        non_integral = self.planner.plan(SearchRequest.judge_band_mhz(100.0, 113.1))
        self.assertEqual((100_500_000,), tuple(item.center_frequency_hz for item in small.windows))
        self.assertEqual((103_000_000,), tuple(item.center_frequency_hz for item in exact.windows))
        self.assertEqual((103_000_000, 108_500_000, 112_000_000), tuple(item.center_frequency_hz for item in multi.windows))
        self.assertEqual(110_100_000, non_integral.windows[-1].center_frequency_hz)
        for plan in (multi, non_integral):
            for left, right in zip(plan.windows, plan.windows[1:]):
                self.assertLessEqual(right.covered_lower_frequency_hz, left.covered_upper_frequency_hz)
        with self.assertRaises(ValueError):
            SearchRequest.judge_band_mhz(115.0, 100.0)

    def test_frequency_is_one_exact_tune_and_unknown_is_configured(self) -> None:
        frequency = self.planner.plan(SearchRequest.judge_frequency_mhz(100.09))
        self.assertEqual(1, len(frequency.windows))
        self.assertEqual(100_090_000, frequency.windows[0].center_frequency_hz)
        with self.assertRaisesRegex(ValueError, "atanmadı"):
            self.planner.plan(SearchRequest.unknown())
        configured = HackRFSearchPlanner(unknown_ranges_hz=((88_000_000, 108_000_000),))
        unknown = configured.plan(SearchRequest.unknown())
        self.assertGreater(len(unknown.windows), 1)
        self.assertEqual(((88_000_000, 108_000_000),), unknown.requested_ranges_hz)

    def test_shifted_frequency_mapping_dc_offsets_edges_and_windows(self) -> None:
        axis = shifted_absolute_frequency_axis(100_000_000.0, 8_000_000.0, 8)
        np.testing.assert_array_equal(axis, np.arange(96_000_000.0, 104_000_000.0, 1_000_000.0))
        self.assertEqual(100_000_000.0, axis[4])
        second = shifted_absolute_frequency_axis(108_500_000.0, 8_000_000.0, 8)
        self.assertEqual(104_500_000.0, second[0])
        self.assertEqual(111_500_000.0, second[-1])

    def test_backend_preserves_serial_tune_and_live_metadata(self) -> None:
        from pathlib import Path

        payload = (Path(__file__).resolve().parents[1] / "datasets/fixtures/phase01/known-tone-ci8.sigmf-data").read_bytes()
        real = FakeRealBackend(payload)
        progress = []
        backend = HackRFSearchBackend(
            real,
            device_serial=SERIAL,
            planner=self.planner,
            progress_callback=lambda completed, total, item: progress.append((completed, total, item.index)),
        )  # type: ignore[arg-type]
        windows = backend.acquire(SearchRequest.judge_frequency_mhz(100.0))
        self.assertEqual(1, len(windows))
        self.assertEqual(SERIAL, real.configs[0].device_serial)
        self.assertEqual(100_000_000, real.configs[0].center_frequency_hz)
        self.assertEqual("LIVE_HACKRF", windows[0].provenance)
        self.assertEqual(4, len(windows[0].frames))
        self.assertEqual((1, 1), backend.last_progress)
        self.assertEqual([(1, 1, 0)], progress)

    def test_overlap_results_are_deduplicated(self) -> None:
        demo = build_judge_demo_engine()
        original = demo.backend.windows[0]
        engine = P0SearchEngine(ReplaySearchBackend((original, original)))
        result = engine.execute(SearchRequest.unknown())
        self.assertEqual(2, len(result.examined_window_ids))
        self.assertEqual(1, len(result.parameters))


if __name__ == "__main__":
    unittest.main()
