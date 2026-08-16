from __future__ import annotations

import unittest

import numpy as np

from reference.et import (
    AnalogDeceptionConfig,
    AnalogDeceptionEngine,
    ContinuousJammingConfig,
    ContinuousJammingEngine,
    ETMissionController,
    SafetyMode,
)


class P0ETTests(unittest.TestCase):
    def test_single_multiple_and_barrage_are_bounded(self) -> None:
        engine = ContinuousJammingEngine()
        configs = (
            ContinuousJammingConfig("single", 48_000, 0.1, (4_000.0,)),
            ContinuousJammingConfig("multiple", 48_000, 0.1, (-6_000.0, 6_000.0)),
            ContinuousJammingConfig("barrage", 48_000, 0.1),
        )
        for config in configs:
            result = engine.generate(config)
            self.assertEqual(result.samples.size, 4_800)
            self.assertLessEqual(result.peak_magnitude, 0.7000000001)
            self.assertEqual(result.provenance, "OFFLINE BASEBAND")

    def test_fm_nfm_loopback(self) -> None:
        rate = 48_000
        time = np.arange(rate, dtype=np.float64) / rate
        audio = np.sin(2 * np.pi * 1_000 * time)
        engine = AnalogDeceptionEngine()
        for mode in ("FM", "NFM"):
            result = engine.generate(audio, AnalogDeceptionConfig(mode=mode, duration_seconds=0.25))
            self.assertGreater(result.loopback_correlation, 0.999)
            self.assertAlmostEqual(result.peak_magnitude, 0.7, places=12)

    def test_safety_modes_fail_closed(self) -> None:
        controller = ETMissionController(SafetyMode.HARDWARE_TX_LOCKED)
        with self.assertRaises(PermissionError):
            controller.start(duration_seconds=1.0, detail="test")
        controller.set_mode(SafetyMode.LOOPBACK)
        controller.start(duration_seconds=1.0, detail="taban bant")
        self.assertEqual(controller.state, "ÇALIŞIYOR")
        controller.emergency_stop()
        with self.assertRaises(RuntimeError):
            controller.start(duration_seconds=1.0, detail="yeniden")


if __name__ == "__main__":
    unittest.main()
