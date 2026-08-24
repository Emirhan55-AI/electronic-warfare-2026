from __future__ import annotations

from dataclasses import replace
import unittest

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f1_estimator import F1ParameterEstimator
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


class Phase04F1EstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_parameter_catalog()
        cls.spectrum = SpectrumProcessor()

    def _am_case(self):
        frames = tuple(
            generate_parameter_scene(
                "am-carrier",
                trial_index=0,
                condition_index=3,
                frame_index=index,
                clean_power_dbfs=-18.0,
                snr_db=12.0,
                catalog=self.catalog,
                scene_seed_override=20261010,
            )
            for index in range(4)
        )
        spectra = tuple(
            self.spectrum.process(
                frame.samples,
                sample_rate_hz=8_000_000.0,
                center_frequency_hz=100_000_000.0,
            )
            for frame in frames
        )
        clean = tuple(
            self.spectrum.process(
                frame.clean_samples,
                sample_rate_hz=8_000_000.0,
                center_frequency_hz=100_000_000.0,
            )
            for frame in frames
        )
        truth = _truth(clean, 12)
        return frames, spectra, truth

    def test_confirmed_four_frame_measurement_has_independent_fields(self) -> None:
        frames, spectra, truth = self._am_case()
        result = F1ParameterEstimator().measure(
            _intent(truth["span"], 1, 1),
            tuple(frame.samples for frame in frames),
            spectra,
        )
        self.assertEqual("valid", result.emission_center_frequency.state)
        self.assertEqual("valid", result.carrier_line_frequency.state)
        self.assertEqual("valid", result.occupied_bandwidth.state)
        self.assertEqual("valid", result.channel_power_dbfs.state)
        self.assertEqual("valid", result.snr_estimate_db.state)
        self.assertEqual("valid", result.signal_domain.state)
        self.assertLessEqual(result.persistent_payload_bytes, 65_536)

    def test_generation_mismatch_fails_closed(self) -> None:
        frames, spectra, truth = self._am_case()
        intent = _intent(truth["span"], 1, 1)
        intent = replace(intent, source_generation=2)
        result = F1ParameterEstimator().measure(
            intent,
            tuple(frame.samples for frame in frames),
            spectra,
        )
        self.assertEqual("insufficient_quality", result.emission_center_frequency.state)
        self.assertEqual("stale_generation", result.emission_center_frequency.reason)


if __name__ == "__main__":
    unittest.main()
