from __future__ import annotations

import unittest

from host.acquisition.contracts import RXConfig
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
        self.assertEqual(first.source, "LIVE HACKRF")
        source.stop()
        self.assertIsNone(source.read())


if __name__ == "__main__":
    unittest.main()
