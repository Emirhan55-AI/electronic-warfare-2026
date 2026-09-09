"""PHASE-10 tests for one-band noise and the fail-closed HackRF boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import numpy as np

from algorithms.transmission import SingleBandNoiseEngine, SingleBandNoisePlan
from platforms.transmission import (
    ETTransmitError,
    HackRFTxRunner,
    TxSafetyProfile,
    build_hackrf_tx_argv,
    discover_hackrf_serials,
    load_tx_safety_profile,
)


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)


def approved_profile() -> TxSafetyProfile:
    return TxSafetyProfile(
        enabled=True,
        device_serial="0000000000000000a32868dc35138247",
        allowed_frequency_ranges_hz=((850_000_000, 860_000_000),),
        maximum_duration_seconds=5.0,
        maximum_txvga_db=0,
        connection="CABLED_ATTENUATED",
        physical_gate_approved=True,
        minimum_attenuation_db=30.0,
        measured_attenuation_db=40.0,
        reviewed_at_utc="2026-01-01T00:00:00Z",
        expires_at_utc="2099-01-01T00:00:00Z",
        approved_by="laboratuvar-sorumlusu",
    )


class SingleBandNoiseTests(unittest.TestCase):
    def test_noise_is_deterministic_bounded_and_confined_to_one_band(self) -> None:
        plan = SingleBandNoisePlan(853_500_000, 854_500_000, 0.1, seed=19)
        engine = SingleBandNoiseEngine()
        first = engine.generate_tile(plan)
        second = engine.generate_tile(plan)
        summary = engine.summarize(plan, first)

        self.assertTrue(np.array_equal(first, second))
        self.assertTrue(np.all(np.isfinite(first)))
        self.assertLessEqual(summary.peak_magnitude, 0.6500000001)
        self.assertGreater(summary.measured_obw99_hz, 900_000)
        self.assertLess(summary.measured_obw99_hz, 1_010_000)
        self.assertEqual(854_000_000, summary.center_frequency_hz)
        self.assertEqual(800_000, summary.mission_sample_count)

    def test_exact_ci8_file_has_two_bytes_per_complex_sample(self) -> None:
        plan = SingleBandNoisePlan(853_500_000, 854_500_000, 0.1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.ci8"
            SingleBandNoiseEngine().write_mission_ci8(path, plan)
            self.assertEqual(plan.sample_count * 2, path.stat().st_size)

    def test_invalid_frequency_band_duration_and_level_are_rejected(self) -> None:
        invalid = (
            (900_000_000, 899_000_000, 1.0, 0.65),
            (900_000_000, 905_000_000, 1.0, 0.65),
            (900_000_000, 901_000_000, 31.0, 0.65),
            (900_000_000, 901_000_000, 1.0, 0.8),
        )
        for lower, upper, duration, peak in invalid:
            with self.subTest(lower=lower, upper=upper, duration=duration, peak=peak):
                with self.assertRaises(ValueError):
                    SingleBandNoisePlan(lower, upper, duration, output_peak=peak)


class TxSafetyBoundaryTests(unittest.TestCase):
    def test_runner_uses_finite_command_and_writes_start_finish_audit(self) -> None:
        observed: list[list[str]] = []

        class FakeProcess:
            returncode = 0

            def poll(self):
                return 0

            def communicate(self, timeout=None):
                return "", "Transfer complete"

            def terminate(self):
                self.returncode = 1

            def kill(self):
                self.returncode = 1

        def fake_popen(argv, **kwargs):
            observed.append(list(argv))
            return FakeProcess()

        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / "audit.jsonl"
            runner = HackRFTxRunner(popen_factory=fake_popen, audit_path=audit)
            result = runner.run(
                "hackrf_transfer",
                SingleBandNoisePlan(853_500_000, 854_500_000, 0.1),
                approved_profile(),
            )
            records = [line for line in audit.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual("TAMAMLANDI", result.status)
        self.assertEqual(1, len(observed))
        self.assertIn("-n", observed[0])
        self.assertNotIn("-R", observed[0])
        self.assertEqual(2, len(records))
        self.assertIn('"event": "STARTING"', records[0])
        self.assertIn('"event": "FINISHED"', records[1])

    def test_device_probe_returns_only_observed_serial_numbers(self) -> None:
        def fake_run(*args, **kwargs):
            return SimpleNamespace(
                stdout="Found HackRF\nSerial number: 0000000000000000a32868dc35138247\n",
                stderr="",
                returncode=0,
            )

        self.assertEqual(
            ("0000000000000000a32868dc35138247",),
            discover_hackrf_serials("hackrf_info.exe", run_factory=fake_run),
        )

    def test_emergency_stop_latches_before_any_iq_or_process_work(self) -> None:
        runner = HackRFTxRunner()
        runner.emergency_stop()
        self.assertTrue(runner.emergency_latched)
        with self.assertRaisesRegex(ETTransmitError, "Acil durdurma"):
            runner.run(
                "hackrf_transfer",
                SingleBandNoisePlan(853_500_000, 854_500_000, 0.1),
                approved_profile(),
            )

    def test_repository_profile_is_locked_and_has_no_frequency_allowlist(self) -> None:
        profile = load_tx_safety_profile(Path("config/p0/hackrf_et_tx.json"))
        self.assertFalse(profile.enabled)
        self.assertFalse(profile.physical_gate_approved)
        self.assertEqual((), profile.allowed_frequency_ranges_hz)
        self.assertEqual("", profile.device_serial)

    def test_command_is_serial_bound_finite_and_disables_auxiliary_power(self) -> None:
        plan = SingleBandNoisePlan(853_500_000, 854_500_000, 0.1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.ci8"
            SingleBandNoiseEngine().write_mission_ci8(path, plan)
            argv = build_hackrf_tx_argv(
                "hackrf_transfer.exe", path, plan, approved_profile(), now=NOW
            )
        self.assertEqual(argv[argv.index("-d") + 1], approved_profile().device_serial)
        self.assertEqual(argv[argv.index("-n") + 1], str(plan.sample_count))
        self.assertEqual(argv[argv.index("-a") + 1], "0")
        self.assertEqual(argv[argv.index("-p") + 1], "0")
        self.assertEqual(argv[argv.index("-x") + 1], "0")
        self.assertNotIn("-R", argv)
        self.assertNotIn("-F", argv)

    def test_every_missing_physical_gate_blocks_before_process_start(self) -> None:
        plan = SingleBandNoisePlan(853_500_000, 854_500_000, 0.1)
        cases = {
            "disabled": {"enabled": False},
            "unapproved": {"physical_gate_approved": False},
            "open_connection": {"connection": "OPEN_AIR"},
            "missing_serial": {"device_serial": ""},
            "no_allowlist": {"allowed_frequency_ranges_hz": ()},
            "low_attenuation": {"measured_attenuation_db": 10.0},
            "expired": {"expires_at_utc": "2026-09-08T11:59:59Z"},
        }
        base = approved_profile().__dict__
        for name, change in cases.items():
            with self.subTest(name=name):
                profile = TxSafetyProfile(**(base | change))
                with self.assertRaises(ETTransmitError):
                    profile.authorize(plan, txvga_db=0, now=NOW)

    def test_out_of_range_frequency_duration_gain_and_executable_are_rejected(self) -> None:
        allowed = SingleBandNoisePlan(853_500_000, 854_500_000, 0.1)
        outside = SingleBandNoisePlan(900_000_000, 901_000_000, 0.1)
        with self.assertRaisesRegex(ETTransmitError, "izin listesinde"):
            approved_profile().authorize(outside, txvga_db=0, now=NOW)
        with self.assertRaisesRegex(ETTransmitError, "kazancı"):
            approved_profile().authorize(allowed, txvga_db=1, now=NOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.ci8"
            SingleBandNoiseEngine().write_mission_ci8(path, allowed)
            with self.assertRaisesRegex(ETTransmitError, "hackrf_transfer"):
                build_hackrf_tx_argv("other.exe", path, allowed, approved_profile(), now=NOW)


if __name__ == "__main__":
    unittest.main()
