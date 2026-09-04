from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from platforms.acquisition import CaptureResult, HackRFSearchBackend
from algorithms.p0 import (
    HackRFSearchPlanner,
    HackRFTuningProfile,
    P0SearchEngine,
    ReplaySearchBackend,
    SearchRequest,
    shifted_absolute_frequency_axis,
)
from algorithms.p0.fixtures import build_judge_demo_engine


SERIAL = "0000000000000000123456789abcdef0"
ROOT = Path(__file__).resolve().parents[1]


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
        self.assertEqual((99_500_000,), tuple(item.center_frequency_hz for item in small.windows))
        self.assertEqual(3, len(exact.windows))
        self.assertEqual(6, len(multi.windows))
        self.assertEqual(6, len(non_integral.windows))
        for plan, expected_bounds in (
            (small, (100_000_000, 101_000_000)),
            (exact, (100_000_000, 106_000_000)),
            (multi, (100_000_000, 115_000_000)),
            (non_integral, (100_000_000, 113_100_000)),
        ):
            self.assertEqual(expected_bounds[0], plan.windows[0].requested_lower_frequency_hz)
            self.assertEqual(expected_bounds[1], plan.windows[-1].requested_upper_frequency_hz)
            for left, right in zip(plan.windows, plan.windows[1:]):
                self.assertEqual(left.requested_upper_frequency_hz, right.requested_lower_frequency_hz)
            for item in plan.windows:
                self.assertLessEqual(item.covered_lower_frequency_hz, item.requested_lower_frequency_hz)
                self.assertGreaterEqual(item.covered_upper_frequency_hz, item.requested_upper_frequency_hz)
                self.assertGreaterEqual(
                    min(
                        abs(item.center_frequency_hz - item.requested_lower_frequency_hz),
                        abs(item.center_frequency_hz - item.requested_upper_frequency_hz),
                    ),
                    self.profile.offset_tuning_hz,
                )
        with self.assertRaises(ValueError):
            SearchRequest.judge_band_mhz(115.0, 100.0)

    def test_frequency_is_one_exact_tune_and_unknown_is_configured(self) -> None:
        frequency = self.planner.plan(SearchRequest.judge_frequency_mhz(100.09))
        self.assertEqual(1, len(frequency.windows))
        self.assertEqual(99_565_000, frequency.windows[0].center_frequency_hz)
        self.assertGreater(
            abs(frequency.windows[0].center_frequency_hz - 100_090_000),
            self.profile.dc_exclusion_hz,
        )
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
        self.assertEqual(99_475_000, real.configs[0].center_frequency_hz)
        self.assertEqual("LIVE_HACKRF", windows[0].provenance)
        self.assertEqual(
            ((99_375_000, 99_575_000),),
            windows[0].excluded_frequency_ranges_hz,
        )
        self.assertEqual(4, len(windows[0].frames))
        self.assertEqual((1, 1), backend.last_progress)
        self.assertEqual([(1, 1, 0)], progress)

    def test_live_dc_exclusion_rejects_center_artifact(self) -> None:
        from algorithms.p0 import P0SearchEngine, ReplaySearchBackend, TuningWindow

        frame = np.ones(4096, dtype=np.complex128) * complex(0.25, -0.125)
        window = TuningWindow(
            "live-dc",
            100_000_000,
            8_000_000,
            (frame, frame, frame, frame),
            provenance="LIVE_HACKRF",
            excluded_frequency_ranges_hz=((99_900_000, 100_100_000),),
        )
        result = P0SearchEngine(ReplaySearchBackend((window,))).execute(
            SearchRequest.judge_frequency_mhz(100.0)
        )
        self.assertEqual("COMPLETED_NO_SIGNAL", result.status)
        self.assertEqual((), result.parameters)

    def test_overlap_results_are_deduplicated(self) -> None:
        demo = build_judge_demo_engine()
        original = demo.backend.windows[0]
        engine = P0SearchEngine(ReplaySearchBackend((original, original)))
        result = engine.execute(SearchRequest.unknown())
        self.assertEqual(2, len(result.examined_window_ids))
        self.assertEqual(1, len(result.parameters))

    def test_physical_hackrf_acceptance_is_repeatable_and_source_bound(self) -> None:
        evidence = json.loads(
            (ROOT / "results/evidence/p0/hackrf-rx-physical-acceptance.json").read_text(
                encoding="utf-8"
            )
        )
        sources = {
            "hackrf_search.py": ROOT / "algorithms/p0/hackrf_search.py",
            "search.py": ROOT / "algorithms/p0/search.py",
            "acquisition_hackrf.py": ROOT / "platforms/acquisition/hackrf.py",
            "acquisition_search.py": ROOT / "platforms/acquisition/search.py",
            "hackrf_ed_rx.json": ROOT / "config/p0/hackrf_ed_rx.json",
            "verify_p0_hackrf_rx_physical.py": ROOT / "scripts/verify_p0_hackrf_rx_physical.py",
        }

        self.assertEqual("passed", evidence["status"])
        self.assertEqual(5, evidence["repeatability"]["runs"])
        self.assertEqual(5, evidence["repeatability"]["passed_runs"])
        self.assertTrue(evidence["repeatability"]["all_capture_lengths_exact"])
        self.assertEqual(0, evidence["repeatability"]["total_saturated_components"])
        self.assertFalse(evidence["transmit_api_called"])
        self.assertTrue(all(run["confirmed_signal_count"] >= 1 for run in evidence["runs"]))
        self.assertTrue(
            all(
                signal["confirmed"] is True and signal["provenance"] == "LIVE_HACKRF"
                for run in evidence["runs"]
                for signal in run["signals"]
            )
        )
        changed_since_acceptance = {
            name
            for name, source in sources.items()
            if evidence["source_sha256"][name]
            != hashlib.sha256(source.read_bytes()).hexdigest()
        }
        # Yapılandırma fiziksel kabulü geçen ED_RX cihazına bağlıdır.
        self.assertEqual(set(), changed_since_acceptance)
        self.assertEqual(
            evidence["device"]["serial"],
            json.loads(sources["hackrf_ed_rx.json"].read_text(encoding="utf-8"))["serial"],
        )


if __name__ == "__main__":
    unittest.main()
