from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from algorithms.et import (
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

    def test_faraday_lab_mode_is_admitted_but_has_no_transmit_api(self) -> None:
        controller = ETMissionController(SafetyMode.CABLED_LAB)
        controller.start(duration_seconds=1.0, detail="kısa kontrollü görev")
        self.assertEqual("ÇALIŞIYOR", controller.state)
        self.assertIn("FARADAY LAB", controller.log[-1].detail)
        self.assertFalse(hasattr(controller, "transmit"))

    def test_product_header_reports_environment_without_claiming_transmit(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "app/operator_console/qml/Main.qml").read_text(encoding="utf-8")
        self.assertIn('root.operatingDomain === "ET" ? "ET ORTAMI"', source)
        self.assertIn('root.operatingDomain === "ET" ? "FARADAY LAB"', source)
        self.assertNotIn('root.operatingDomain === "ET" ? "DEVRE DIŞI"', source)


if __name__ == "__main__":
    unittest.main()
