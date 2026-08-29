from __future__ import annotations

import unittest

import numpy as np

from algorithms.p0 import P0SearchEngine, ReplaySearchBackend, SearchRequest, TuningWindow
from algorithms.p0.fixtures import CENTER_FREQUENCY_HZ, SAMPLE_RATE_HZ, build_fixtures, build_judge_demo_engine


def build_engine() -> P0SearchEngine:
    engine = build_judge_demo_engine()
    assert isinstance(engine, P0SearchEngine)
    return engine


class P0SearchRequestTests(unittest.TestCase):
    def test_mhz_conversion_is_explicit(self) -> None:
        band = SearchRequest.judge_band_mhz(100.08, 100.10)
        self.assertEqual(band.analysis_bounds_hz(), (100_080_000.0, 100_100_000.0))
        frequency = SearchRequest.judge_frequency_mhz(100.09, window_khz=50.0)
        self.assertEqual(frequency.center_frequency_hz, 100_090_000.0)
        self.assertEqual(frequency.analysis_bounds_hz(), (100_065_000.0, 100_115_000.0))

    def test_invalid_numeric_reversed_and_out_of_range_values_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "sonlu"):
            SearchRequest.judge_band_mhz(float("nan"), 100.1)
        with self.assertRaisesRegex(ValueError, "küçük"):
            SearchRequest.judge_band_mhz(100.1, 100.0)
        with self.assertRaisesRegex(ValueError, "sınır"):
            SearchRequest.judge_frequency_mhz(7000.0)
        with self.assertRaisesRegex(ValueError, "span"):
            SearchRequest.judge_band_mhz(100.0, 121.0)


class P0SearchExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine()

    def test_unknown_mode_discovers_signal_without_frequency_hint(self) -> None:
        result = self.engine.execute(SearchRequest.unknown())
        self.assertEqual(result.status, "COMPLETED_SIGNAL_FOUND")
        self.assertEqual(len(result.parameters), 1)
        self.assertAlmostEqual(result.parameters[0].emission_center_frequency_hz, 100_090_000.0, delta=250.0)
        self.assertEqual(result.parameters[0].provenance, "REPLAY")

    def test_judge_band_restricts_analysis(self) -> None:
        included = self.engine.execute(SearchRequest.judge_band_mhz(100.08, 100.10))
        excluded = self.engine.execute(SearchRequest.judge_band_mhz(99.95, 99.96))
        self.assertEqual(len(included.parameters), 1)
        self.assertEqual(excluded.status, "COMPLETED_NO_SIGNAL")
        self.assertEqual(excluded.parameters, ())

    def test_judge_frequency_still_requires_detection_and_confirmation(self) -> None:
        correct = self.engine.execute(SearchRequest.judge_frequency_mhz(100.09))
        wrong = self.engine.execute(SearchRequest.judge_frequency_mhz(100.20))
        self.assertEqual(len(correct.parameters), 1)
        self.assertTrue(correct.parameters[0].confirmed)
        self.assertEqual(wrong.status, "COMPLETED_NO_SIGNAL")

    def test_confirmed_observation_is_retained_when_capture_ends_with_misses(self) -> None:
        fixture = next(item for item in build_fixtures() if item.fixture_id == "nfm-like")
        quiet = np.zeros_like(fixture.iq)
        window = TuningWindow(
            "bounded-burst",
            CENTER_FREQUENCY_HZ,
            SAMPLE_RATE_HZ,
            (fixture.iq, fixture.iq, quiet, quiet),
        )
        engine = P0SearchEngine(ReplaySearchBackend((window,)))

        result = engine.execute(SearchRequest.judge_frequency_mhz(100.09))

        self.assertEqual("COMPLETED_SIGNAL_FOUND", result.status)
        self.assertEqual(1, len(result.parameters))
        self.assertTrue(result.parameters[0].confirmed)


if __name__ == "__main__":
    unittest.main()
