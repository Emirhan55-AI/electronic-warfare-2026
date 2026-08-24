from __future__ import annotations

from dataclasses import replace
import unittest

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f2_estimator import F2ParameterEstimator
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


class Phase04F2EstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_parameter_catalog()
        cls.processor = SpectrumProcessor()

    def _case(self, scene_id: str, snr_db: float, condition_index: int):
        frames = tuple(
            generate_parameter_scene(
                scene_id, trial_index=0, condition_index=condition_index, frame_index=index,
                clean_power_dbfs=-18.0, snr_db=snr_db, catalog=self.catalog,
                scene_seed_override=3502604761305543594,
            )
            for index in range(4)
        )
        spectra = tuple(
            self.processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            for frame in frames
        )
        clean = tuple(
            self.processor.process(frame.clean_samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            for frame in frames
        )
        return frames, spectra, _truth(clean, 12)

    def test_v3_measures_confirmed_am_with_bounded_payload(self) -> None:
        frames, spectra, truth = self._case("am-carrier", 12.0, 3)
        result = F2ParameterEstimator().measure(
            _intent(truth["span"], 1, 1), tuple(frame.samples for frame in frames), spectra,
        )
        self.assertEqual("valid", result.emission_center_frequency.state)
        self.assertEqual("valid", result.carrier_line_frequency.state)
        self.assertEqual("valid", result.occupied_bandwidth.state)
        self.assertEqual("Analog", result.signal_domain.value)
        self.assertLessEqual(result.persistent_payload_bytes, 65_536)

    def test_noise_measurement_fails_closed(self) -> None:
        frames = tuple(
            generate_parameter_scene(
                "noise-only", trial_index=0, condition_index=0, frame_index=index,
                catalog=self.catalog, scene_seed_override=3502604761305633594,
            )
            for index in range(4)
        )
        spectra = tuple(
            self.processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            for frame in frames
        )
        result = F2ParameterEstimator().measure(
            _intent((1792, 2303), 2, 1), tuple(frame.samples for frame in frames), spectra,
        )
        self.assertNotEqual("valid", result.channel_power_dbfs.state)
        self.assertNotEqual("valid", result.snr_estimate_db.state)
        self.assertNotEqual("valid", result.signal_domain.state)

    def test_generation_mismatch_remains_fail_closed(self) -> None:
        frames, spectra, truth = self._case("am-carrier", 12.0, 3)
        intent = replace(_intent(truth["span"], 1, 1), source_generation=2)
        result = F2ParameterEstimator().measure(intent, tuple(frame.samples for frame in frames), spectra)
        self.assertEqual("insufficient_quality", result.emission_center_frequency.state)
        self.assertEqual("stale_generation", result.emission_center_frequency.reason)


if __name__ == "__main__":
    unittest.main()
