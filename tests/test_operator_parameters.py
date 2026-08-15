"""Qt operator integration tests for truthful PHASE-04 parameter output."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QLabel

from host.operator_console.application import build_application
from reference.parameters.models import (
    BandwidthEstimate,
    EventParameterEstimate,
    FrequencyEstimate,
    ParameterFrameResult,
    RelativePowerEstimate,
    SignalDomainEstimate,
)
from reference.pipeline import VerifiedProfileBinding, build_phase04_profile
from qt_test_support import isolate_qt_module


METHODS = {
    "analysis_window": "analysis.clustered-regions-v1",
    "noise": "noise.winsorized-mean-10",
    "bandwidth": "band.multi-component-excess-99-v1",
    "spectral_center": "center.band-midpoint",
    "carrier": "carrier.centroid-only",
    "power_snr": "power.psd-noise-subtract-v1",
    "signal_domain": "domain.conservative-consensus",
}
BINDING = VerifiedProfileBinding(
    "phase04-r1-parameter-selection",
    "1" * 64,
    "2" * 64,
    "3" * 64,
    "4" * 64,
    tuple(METHODS.items()),
)


class OperatorParameterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app, self.window, self.controller = build_application(
            [], profile=build_phase04_profile(METHODS, binding=BINDING), verified_binding=BINDING
        )

    def tearDown(self) -> None:
        self.controller.close()
        self.window.close()

    def test_ui_never_labels_relative_power_as_dbm(self) -> None:
        event = EventParameterEstimate(
            7,
            3,
            FrequencyEstimate(100_500_000.0, "valid", None, "not_observed"),
            BandwidthEstimate(100_450_000.0, "valid", 100_550_000.0, "valid", 100_000.0, "valid", 2200, 2251),
            RelativePowerEstimate(0.01, -20.0, 0.001, 10.0, "valid", "valid"),
            SignalDomainEstimate("Sayısal", "valid", 4),
        )
        result = ParameterFrameResult(3, (event,), 67840, 1152, 1792)
        self.window.set_parameter_result(result)
        visible = " ".join(value.text() for value in self.window.parameter_values.values())
        labels = " ".join(label.text() for label in self.window.findChildren(QLabel))
        self.assertIn("Henüz doğrulanmadı", visible)
        self.assertIn("Tepe Gücü", labels)
        self.assertIn("Kanal Gücü", labels)
        calibration = self.window.findChild(type(self.window.quality_value), "calibrationNote")
        self.assertIsNotNone(calibration)
        self.assertIn("dBFS", calibration.text())
        self.assertNotIn("dBm", visible)
        self.assertNotIn("dBm", labels)
        self.assertNotIn("nominal", visible.casefold())

    def test_clear_parameters_is_honest(self) -> None:
        self.window.clear_parameters()
        self.assertIn("yok", self.window.parameter_state.text().casefold())
        self.assertTrue(all(value.text() == "Henüz doğrulanmadı" for value in self.window.parameter_values.values()))

    def test_nonvalid_fields_never_render_numeric_values_or_band_overlay(self) -> None:
        event = EventParameterEstimate(
            8,
            4,
            FrequencyEstimate(100_500_000.0, "insufficient_quality", 100_500_000.0, "not_observed"),
            BandwidthEstimate(
                100_450_000.0,
                "uncertain",
                100_550_000.0,
                "uncertain",
                100_000.0,
                "uncertain",
                2200,
                2251,
            ),
            RelativePowerEstimate(0.01, -20.0, 0.001, 10.0, "insufficient_quality", "uncertain"),
            SignalDomainEstimate("Sayısal", "uncertain", 4),
        )
        result = ParameterFrameResult(4, (event,), 67840, 1152, 1792)
        self.window.set_parameter_result(result)
        visible = " ".join(value.text() for value in self.window.parameter_values.values())
        self.assertNotIn("100,5", visible)
        self.assertNotIn("100,0 kHz", visible)
        self.assertNotIn("-20,0", visible)
        self.assertNotIn("10,0 dB", visible)
        self.assertNotIn("Sayısal", visible)
        self.window.spectrum_view.last_x_mhz = np.arange(4096, dtype=np.float64)
        self.window.spectrum_view._update_parameter_overlay(result)
        self.assertFalse(self.window.spectrum_view.parameter_overlay.isVisible())


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
