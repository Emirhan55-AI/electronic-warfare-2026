from __future__ import annotations

import json
from pathlib import Path
import unittest

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f3_estimator import F3ParameterEstimator
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


ROOT = Path(__file__).resolve().parents[1]


class Phase04F3EstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_parameter_catalog()
        cls.processor = SpectrumProcessor()
        development = json.loads(
            (ROOT / "datasets" / "fixtures" / "phase04f3" / "development-catalog.json").read_text(encoding="utf-8")
        )
        cls.seed = int(development["common"]["development_seeds"][0])

    def _case(self, scene_id: str, family_index: int):
        frames = tuple(
            generate_parameter_scene(
                scene_id, trial_index=0, condition_index=3, frame_index=index,
                clean_power_dbfs=-18.0, snr_db=12.0, catalog=self.catalog,
                scene_seed_override=self.seed + family_index * 10_000,
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
        truth = _truth(clean, 12)
        result = F3ParameterEstimator().measure(
            _intent(truth["span"], family_index + 1, 1), tuple(frame.samples for frame in frames), spectra,
        )
        return result

    def test_ook_has_carrier_and_digital_domain_with_bounded_payload(self) -> None:
        result = self._case("ook", 2)
        self.assertEqual("valid", result.carrier_line_frequency.state)
        self.assertEqual("valid", result.signal_domain.state)
        self.assertEqual("Sayısal", result.signal_domain.value)
        self.assertLessEqual(result.persistent_payload_bytes, 65_536)

    def test_bpsk_does_not_report_a_carrier_line(self) -> None:
        result = self._case("bpsk", 4)
        self.assertNotEqual("valid", result.carrier_line_frequency.state)


if __name__ == "__main__":
    unittest.main()
