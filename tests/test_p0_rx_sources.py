from __future__ import annotations

import unittest
import time

from host.acquisition.contracts import AcquisitionError, CaptureResult, RXConfig
from host.acquisition.hackrf import DeterministicMockBackend
from host.acquisition.rx_sources import HackRFHostRxSource


class P0RxSourceTests(unittest.TestCase):
    def test_hackrf_host_source_emits_normalized_frames(self) -> None:
        source = HackRFHostRxSource(DeterministicMockBackend(), RXConfig())
        first = source.read()
        second = source.read()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None
        self.assertEqual(first.sequence_number, 0)
        self.assertEqual(second.sequence_number, 1)
        self.assertEqual(first.samples.size, 4096)
        self.assertEqual(RXConfig().center_frequency_hz, first.center_frequency_hz)
        self.assertEqual(RXConfig().sample_rate_hz, first.sample_rate_hz)
        self.assertEqual(first.source, "DETERMINISTIC TEST")
        self.assertGreaterEqual(source.statistics.frames_produced, 2)
        self.assertEqual(0, source.statistics.capture_errors)
        source.stop()
        self.assertIsNone(source.read())
        self.assertEqual("STOPPED", source.statistics.state)

    def test_hackrf_host_source_bounds_queue_and_counts_drops(self) -> None:
        source = HackRFHostRxSource(DeterministicMockBackend(), RXConfig(), queue_capacity=1)
        source.start()
        deadline = time.monotonic() + 2
        while source.statistics.dropped_frames == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        statistics = source.statistics
        self.assertEqual(1, statistics.queue_depth)
        self.assertGreater(statistics.dropped_frames, 0)
        source.stop()
        self.assertEqual("STOPPED", source.statistics.state)

    def test_hackrf_host_source_surfaces_disconnect_error(self) -> None:
        class DisconnectedBackend:
            backend_kind = "real"

            def capture(self, config: RXConfig, cancellation: object = None) -> CaptureResult:
                raise AcquisitionError("device_not_found", "Cihaz bağlantısı yok.")

            def cancel(self) -> None:
                pass

        source = HackRFHostRxSource(DisconnectedBackend(), RXConfig(), queue_capacity=1)  # type: ignore[arg-type]
        with self.assertRaises(AcquisitionError) as failure:
            source.read(timeout_seconds=0.2)
        self.assertEqual("device_not_found", failure.exception.code)
        self.assertEqual("DISCONNECTED", source.statistics.state)
        self.assertEqual(1, source.statistics.capture_errors)
        source.stop()


if __name__ == "__main__":
    unittest.main()
