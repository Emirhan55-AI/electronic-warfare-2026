"""Deterministic acceptance tests for the transmit-disabled ET task models."""

from __future__ import annotations

import unittest

import numpy as np

from algorithms.et import (
    AnalogDeceptionConfig,
    AnalogDeceptionEngine,
    ContinuousJammingConfig,
    ContinuousJammingEngine,
    GNSSScenario,
    GNSSScenarioValidator,
    InterleavedConfig,
    InterleavedTaskController,
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

    def test_obw99_uses_equal_half_percent_power_tails(self) -> None:
        sample_rate = 48_000
        count = 4_800
        time = np.arange(count, dtype=np.float64) / sample_rate
        samples = (
            np.sqrt(0.0055) * np.exp(-2j * np.pi * 10_000.0 * time)
            + np.sqrt(0.989) * np.ones(count, dtype=np.complex128)
            + np.sqrt(0.0055) * np.exp(2j * np.pi * 10_000.0 * time)
        )
        self.assertEqual(20_000.0, self.engine._occupied_bandwidth(samples, sample_rate))

    def test_sweep_progresses_across_real_complex_samples(self) -> None:
        result = self.engine.generate(ContinuousJammingConfig("sweep", 48_000, 0.5, sweep_start_hz=-9_000.0, sweep_stop_hz=9_000.0))
        instantaneous = np.angle(result.samples[1:] * np.conj(result.samples[:-1])) * result.sample_rate_hz / (2.0 * np.pi)
        self.assertLess(float(np.mean(instantaneous[:100])), -8_800.0)
        self.assertGreater(float(np.mean(instantaneous[-100:])), 8_800.0)
        self.assertEqual(8, len(result.sweep_sub_bands_hz))
        self.assertTrue(np.all(np.isfinite(result.samples)))


class InterleavedOfflineModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = InterleavedTaskController()

    def test_absent_target_never_activates_a_task(self) -> None:
        result = self.engine.run(InterleavedConfig(scenario="absent"))
        self.assertEqual("DİNLE", result.final_state)
        self.assertEqual(0, result.task_activation_count)
        self.assertTrue(all(window.decision == "PASİF" for window in result.windows))
        self.assertEqual(0.0, result.task_duty_cycle)
        self.assertFalse(np.any(result.task_gate))
        self.assertTrue(np.all(result.task_output_samples == 0.0))

    def test_present_target_requires_consecutive_confirmation_then_tasks(self) -> None:
        config = InterleavedConfig(scenario="present", consecutive_windows=2)
        result = self.engine.run(config)
        activation_indices = [window.index for window in result.windows if window.task_active]
        self.assertGreaterEqual(len(activation_indices), 1)
        self.assertEqual(config.consecutive_windows + config.response_delay_windows, activation_indices[0])
        self.assertEqual(("DİNLE", "DİNLE", "GECİKME", "GÖREV", "KORUMA"), result.timeline[:5])
        self.assertIn("GÖREV", result.timeline)
        self.assertIn("KORUMA", result.timeline)
        self.assertEqual(result.task_window_count / config.windows, result.task_duty_cycle)
        self.assertEqual(config.window_samples * result.task_window_count, int(np.count_nonzero(result.task_gate)))
        self.assertAlmostEqual(config.output_peak, float(np.max(np.abs(result.task_output_samples))), places=12)

    def test_intermittent_and_edge_cases_are_deterministic_and_hysteretic(self) -> None:
        intermittent = self.engine.run(InterleavedConfig(scenario="intermittent"))
        edge_first = self.engine.run(InterleavedConfig(scenario="edge"))
        edge_second = self.engine.run(InterleavedConfig(scenario="edge"))
        self.assertGreaterEqual(intermittent.task_activation_count, 1)
        self.assertGreaterEqual(edge_first.task_activation_count, 1)
        self.assertEqual(edge_first.timeline, edge_second.timeline)
        self.assertFalse(edge_first.analysis_samples.flags.writeable)
        self.assertFalse(edge_first.task_output_samples.flags.writeable)
        self.assertFalse(edge_first.task_gate.flags.writeable)
        self.assertTrue(np.array_equal(edge_first.samples, edge_second.samples))
        listened = [window for window in edge_first.windows if window.state == "DİNLE"]
        self.assertTrue(all(window.measured_band_power is not None for window in listened))
        self.assertTrue(all(window.decision in {"PASİF", "AKTİF", "ONAYLANDI", "SÜRE YETERSİZ"} for window in listened))
        self.assertEqual("ONAYLANDI", listened[1].decision)

    def test_listen_and_task_windows_are_mutually_exclusive(self) -> None:
        config = InterleavedConfig(scenario="present", task_windows=2, guard_windows=1)
        result = self.engine.run(config)
        for window in result.windows:
            start = window.index * config.window_samples
            stop = start + config.window_samples
            gated = bool(np.any(result.task_gate[start:stop]))
            if window.state == "DİNLE":
                self.assertIsNotNone(window.measured_band_power)
                self.assertFalse(gated)
            elif window.state == "GÖREV":
                self.assertIsNone(window.measured_band_power)
                self.assertTrue(gated)
                self.assertTrue(window.task_active)
            else:
                self.assertIsNone(window.measured_band_power)
                self.assertFalse(gated)
        self.assertTrue(np.all(result.task_output_samples[~result.task_gate] == 0.0))

    def test_task_output_frequency_and_configuration_bounds_are_independently_checked(self) -> None:
        config = InterleavedConfig(scenario="present")
        result = self.engine.run(config)
        active = result.task_output_samples[result.task_gate]
        phase_step = np.angle(active[1:] * np.conj(active[:-1]))
        measured_hz = float(np.median(phase_step) * config.sample_rate_hz / (2.0 * np.pi))
        self.assertAlmostEqual(config.target_offset_hz, measured_hz, places=9)
        for invalid in (
            {"response_delay_windows": 0},
            {"task_windows": 0},
            {"guard_windows": 0},
            {"output_peak": 0.0},
            {"output_peak": 0.91},
        ):
            with self.assertRaises(ValueError):
                InterleavedConfig(**invalid)

    def test_incomplete_cycle_is_rejected_at_the_record_boundary(self) -> None:
        config = InterleavedConfig(scenario="present", windows=4)
        result = self.engine.run(config)
        self.assertEqual(0, result.task_activation_count)
        self.assertEqual(0.0, result.task_duty_cycle)
        self.assertIn("SÜRE YETERSİZ", [window.decision for window in result.windows])
        self.assertFalse(np.any(result.task_gate))


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
        accepted = validator.validate(GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (3, 8, 63)))
        rejected = validator.validate(GNSSScenario(91.0, 32.8597, "not-a-time", ()))
        self.assertTrue(accepted.valid)
        self.assertTrue(accepted.metadata_contract_valid)
        self.assertFalse(accepted.waveform_available)
        self.assertFalse(accepted.waveform_source_contract_valid)
        self.assertEqual("KİLİTLİ", accepted.tx_state)
        self.assertFalse(rejected.valid)
        self.assertGreaterEqual(len(rejected.errors), 3)
        self.assertEqual("KİLİTLİ", rejected.tx_state)
        self.assertFalse(hasattr(validator, "transmit"))

    def test_gnss_rejects_non_utc_time_and_out_of_range_prn(self) -> None:
        validator = GNSSScenarioValidator()
        non_utc = validator.validate(GNSSScenario(39.9334, 32.8597, "2026-08-16T15:00:00+03:00", (3,)))
        invalid_prn = validator.validate(GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (64,)))
        self.assertFalse(non_utc.valid)
        self.assertIn("senaryo zamanı Z veya +00:00 biçiminde UTC olmalıdır", non_utc.errors)
        self.assertFalse(invalid_prn.valid)
        self.assertIn("GPS L1 C/A PRN kodları 1..63 ve benzersiz olmalıdır", invalid_prn.errors)

    def test_gnss_rejects_missing_metadata_source_with_an_explicit_reason(self) -> None:
        result = GNSSScenarioValidator.validate(
            GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (3,), metadata_source="  ")
        )
        self.assertFalse(result.valid)
        self.assertIn("senaryo metadata kaynağı boş olamaz", result.errors)

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
