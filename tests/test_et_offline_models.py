"""Deterministic acceptance tests for the transmit-disabled ET task models."""

from __future__ import annotations

import unittest

import numpy as np

from reference.et import (
    AnalogDeceptionConfig,
    AnalogDeceptionEngine,
    ContinuousJammingConfig,
    ContinuousJammingEngine,
    GNSSScenario,
    GNSSScenarioValidator,
    InterleavedConfig,
    InterleavedJammingEngine,
    new_task_result,
)


class ContinuousOfflineModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ContinuousJammingEngine()

    def test_single_and_multiple_have_expected_distinct_spectral_structure(self) -> None:
        single = self.engine.generate(ContinuousJammingConfig("single", 48_000, 0.25, (4_000.0,)))
        multiple = self.engine.generate(ContinuousJammingConfig("multiple", 48_000, 0.25, (-8_000.0, 0.0, 8_000.0)))
        single_frequency, single_power = self.engine.spectrum(single.samples, single.sample_rate_hz)
        multiple_frequency, multiple_power = self.engine.spectrum(multiple.samples, multiple.sample_rate_hz)
        self.assertAlmostEqual(single_frequency[int(np.argmax(single_power))], 4_000.0, places=6)
        strongest = np.argpartition(multiple_power, -3)[-3:]
        self.assertEqual([-8_000.0, 0.0, 8_000.0], sorted(float(multiple_frequency[index]) for index in strongest))
        self.assertGreater(multiple.occupied_bandwidth_hz, single.occupied_bandwidth_hz)

    def test_barrage_is_seeded_band_limited_and_normalized(self) -> None:
        config = ContinuousJammingConfig("barrage", 48_000, 0.25, barrage_bandwidth_hz=12_000.0, seed=11)
        first = self.engine.generate(config)
        second = self.engine.generate(config)
        self.assertTrue(np.array_equal(first.samples, second.samples))
        self.assertTrue(np.all(np.isfinite(first.samples)))
        self.assertLessEqual(first.peak_magnitude, 0.7000000001)
        self.assertGreater(first.occupied_bandwidth_hz, 10_000.0)
        self.assertLess(first.occupied_bandwidth_hz, 14_000.0)

    def test_sweep_progresses_across_real_complex_samples(self) -> None:
        result = self.engine.generate(ContinuousJammingConfig("sweep", 48_000, 0.5, sweep_start_hz=-9_000.0, sweep_stop_hz=9_000.0))
        instantaneous = np.angle(result.samples[1:] * np.conj(result.samples[:-1])) * result.sample_rate_hz / (2.0 * np.pi)
        self.assertLess(float(np.mean(instantaneous[:100])), -8_800.0)
        self.assertGreater(float(np.mean(instantaneous[-100:])), 8_800.0)
        self.assertEqual(8, len(result.sweep_sub_bands_hz))
        self.assertTrue(np.all(np.isfinite(result.samples)))


class InterleavedOfflineModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = InterleavedJammingEngine()

    def test_absent_target_never_activates_a_task(self) -> None:
        result = self.engine.run(InterleavedConfig(scenario="absent"))
        self.assertEqual("DİNLE", result.final_state)
        self.assertEqual(0, result.task_activation_count)
        self.assertTrue(all(window.decision == "PASİF" for window in result.windows))

    def test_present_target_requires_consecutive_confirmation_then_tasks(self) -> None:
        result = self.engine.run(InterleavedConfig(scenario="present", consecutive_windows=2))
        activation_indices = [window.index for window in result.windows if window.task_active]
        self.assertGreaterEqual(len(activation_indices), 1)
        self.assertEqual(1, activation_indices[0])
        self.assertIn("GÖREV", result.timeline)
        self.assertIn("GUARD", result.timeline)

    def test_intermittent_and_edge_cases_are_deterministic_and_hysteretic(self) -> None:
        intermittent = self.engine.run(InterleavedConfig(scenario="intermittent"))
        edge_first = self.engine.run(InterleavedConfig(scenario="edge"))
        edge_second = self.engine.run(InterleavedConfig(scenario="edge"))
        self.assertGreaterEqual(intermittent.task_activation_count, 1)
        self.assertGreaterEqual(edge_first.task_activation_count, 1)
        self.assertEqual(edge_first.timeline, edge_second.timeline)
        self.assertTrue(np.array_equal(edge_first.samples, edge_second.samples))
        self.assertTrue(all(window.decision == "AKTİF" for window in edge_first.windows))


class AnalogAndGNSSOfflineModelTests(unittest.TestCase):
    def test_analog_modes_are_band_limited_finite_and_loopback_valid(self) -> None:
        rate = 48_000
        time = np.arange(rate, dtype=np.float64) / rate
        audio = np.sin(2.0 * np.pi * 1_000.0 * time) + 0.1 * np.sin(2.0 * np.pi * 10_000.0 * time)
        engine = AnalogDeceptionEngine()
        for mode in ("AM", "FM", "NFM"):
            result = engine.generate(audio, AnalogDeceptionConfig(mode=mode, duration_seconds=0.25))
            self.assertTrue(np.all(np.isfinite(result.samples)))
            self.assertTrue(np.all(np.isfinite(result.normalized_audio)))
            self.assertLessEqual(result.peak_magnitude, 0.7000000001)
            self.assertGreaterEqual(result.loopback_correlation, 0.999)
            self.assertEqual(3_000.0, result.audio_bandwidth_hz)

    def test_gnss_metadata_validation_is_safe_and_deterministic(self) -> None:
        validator = GNSSScenarioValidator()
        accepted = validator.validate(GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (3, 8, 14)))
        rejected = validator.validate(GNSSScenario(91.0, 32.8597, "not-a-time", ()))
        self.assertTrue(accepted.valid)
        self.assertTrue(accepted.waveform_source_contract_valid)
        self.assertEqual("KİLİTLİ", accepted.tx_state)
        self.assertFalse(rejected.valid)
        self.assertGreaterEqual(len(rejected.errors), 3)
        self.assertEqual("KİLİTLİ", rejected.tx_state)
        self.assertFalse(hasattr(validator, "transmit"))

    def test_task_result_contract_is_data_not_interface_text(self) -> None:
        result = new_task_result(
            task_type="continuous_jamming",
            mode="OFFLINE",
            source="DETERMİNİSTİK OFFLINE TABAN BANT",
            duration=0.25,
            waveform_type="single",
            sample_rate=48_000,
            sample_count=12_000,
            normalization_status="PASS",
            validation_status="PASS",
        )
        record = result.as_dict()
        for key in ("task_type", "mode", "source", "started_at", "duration", "waveform_type", "sample_rate", "sample_count", "normalization_status", "validation_status", "tx_state"):
            self.assertIn(key, record)
        self.assertEqual("KİLİTLİ", record["tx_state"])


if __name__ == "__main__":
    unittest.main()
