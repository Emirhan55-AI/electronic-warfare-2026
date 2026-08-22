from __future__ import annotations

import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from host.acquisition import (
    AcquisitionError,
    BoundedCI8FrameSource,
    RXConfig,
    RealHackRFBackend,
    SafeProcessRunner,
    decode_ci8,
    build_receive_argv,
    load_ed_rx_config,
    parse_hackrf_info,
    parse_sweep_fixture,
)
from host.acquisition.mock import DeterministicMockBackend
from host.acquisition.process import ProcessResult


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
SERIAL = "0000000000000000123456789abcdef0"


class FakeRunner:
    def __init__(self, payload: bytes = b"", *, returncode: int = 0, help_payload: bytes | None = None) -> None:
        self.payload = payload
        self.returncode = returncode
        self.help_payload = help_payload or b"Usage: hackrf_info -d -r -f -s -n -a -l -g"
        self.calls: list[list[str]] = []
        self.capture_path: Path | None = None
        self.active = False

    def run(self, argv: list[str], **_: object) -> ProcessResult:
        self.calls.append(argv)
        if argv[-1] == "-h":
            return ProcessResult(self.returncode, self.help_payload, b"", False, False)
        if "-r" in argv:
            self.capture_path = Path(argv[argv.index("-r") + 1])
            self.capture_path.write_bytes(self.payload)
        return ProcessResult(
            self.returncode,
            f"Found HackRF\nSerial number: {SERIAL}\nBoard ID Number: 2 (HackRF One)".encode(),
            b"",
            False,
            False,
        )

    def close(self) -> None:
        self.active = False


class HackRFAcquisitionTests(unittest.TestCase):
    def test_ci8_exact_decode_and_frame_adapter(self) -> None:
        payload = FIXTURE.read_bytes()
        samples = decode_ci8(payload, expected_complex_samples=16_384)
        self.assertEqual((16_384,), samples.shape)
        capture = DeterministicMockBackend(payload).capture(RXConfig())
        source = BoundedCI8FrameSource(capture)
        self.assertEqual(4, source.frame_count)
        self.assertEqual((4096,), source.read_frame(3).shape)
        source.close()

    def test_ci8_preserves_interleaved_i_then_q_order_and_scale(self) -> None:
        samples = decode_ci8(bytes((0x80, 0x7F, 0xFF, 0x01, 0x00, 0x00)), expected_complex_samples=3)
        self.assertEqual(complex(-1.0, 127 / 128), samples[0])
        self.assertEqual(complex(-1 / 128, 1 / 128), samples[1])
        self.assertEqual(0j, samples[2])

    def test_ci8_rejects_odd_short_and_long_payloads(self) -> None:
        with self.assertRaisesRegex(AcquisitionError, "I/Q"):
            decode_ci8(b"\x00", expected_complex_samples=1)
        with self.assertRaises(AcquisitionError) as short:
            decode_ci8(b"\x00\x00", expected_complex_samples=2)
        self.assertEqual("short_capture", short.exception.code)
        with self.assertRaises(AcquisitionError) as long:
            decode_ci8(b"\x00" * 6, expected_complex_samples=2)
        self.assertEqual("long_capture", long.exception.code)

    def test_rx_config_has_hard_numeric_and_capture_bounds(self) -> None:
        self.assertEqual(16_384, RXConfig().sample_count)
        for kwargs in ({"sample_count": 4097}, {"sample_count": 131_072}, {"sample_rate_hz": 9_000_000}, {"lna_gain_db": 7}):
            with self.assertRaises(AcquisitionError):
                RXConfig(**kwargs)

    def test_missing_tools_and_no_device_are_typed(self) -> None:
        backend = RealHackRFBackend(which=lambda _: None)
        inventory = backend.discover_tools(inspect_help=True)
        self.assertTrue(all(item.state == "unavailable" for item in inventory.tools))
        self.assertEqual("TOOLCHAIN_UNAVAILABLE", backend.discover_device().state)

        runner = FakeRunner()
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}
        ready = RealHackRFBackend(runner=runner, which=paths.get)
        ready.discover_tools(inspect_help=True)
        runner.run = lambda *args, **kwargs: ProcessResult(1, b"No HackRF boards found", b"", False, False)  # type: ignore[method-assign]
        self.assertEqual("NO_DEVICE", ready.discover_device().state)

    def test_device_discovery_distinguishes_one_multiple_and_error(self) -> None:
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}
        runner = FakeRunner()
        backend = RealHackRFBackend(runner=runner, which=paths.get)
        backend.discover_tools(inspect_help=True)
        one = backend.discover_device()
        self.assertEqual("ONE_DEVICE", one.state)
        self.assertEqual(SERIAL, one.devices[0].serial)
        payload = (
            f"Found HackRF\nSerial number: {SERIAL}\nBoard ID Number: 2 (HackRF One)\n"
            "Found HackRF\nSerial number: 0000000000000000fedcba9876543210\nBoard ID Number: 2 (HackRF One)"
        ).encode()
        runner.run = lambda *args, **kwargs: ProcessResult(0, payload, b"", False, False)  # type: ignore[method-assign]
        multiple = backend.discover_device()
        self.assertEqual("MULTIPLE_DEVICES", multiple.state)
        self.assertEqual(2, multiple.device_count)
        self.assertEqual(2, len(parse_hackrf_info(payload)))
        runner.run = lambda *args, **kwargs: ProcessResult(0, b"unexpected", b"", False, False)  # type: ignore[method-assign]
        self.assertEqual("DEVICE_ERROR", backend.discover_device().state)

    def test_ed_rx_config_is_unassigned_and_receive_argv_is_rx_only(self) -> None:
        identity = load_ed_rx_config()
        self.assertEqual("ED_RX", identity.role)
        self.assertEqual("HackRF One", identity.device_type)
        self.assertIsNone(identity.serial)
        with self.assertRaisesRegex(AcquisitionError, "atanmadı"):
            build_receive_argv("hackrf_transfer", RXConfig(), Path("capture.ci8"))
        argv = build_receive_argv(
            "hackrf_transfer",
            RXConfig(device_serial=SERIAL),
            Path("capture.ci8"),
        )
        self.assertEqual(SERIAL, argv[argv.index("-d") + 1])
        self.assertIn("-r", argv)
        for prohibited in ("-t", "-x", "-c", "-R"):
            self.assertNotIn(prohibited, argv)

    def test_malformed_help_and_unexpected_exit_do_not_enable_capture(self) -> None:
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}
        malformed = RealHackRFBackend(runner=FakeRunner(help_payload=b"unknown syntax"), which=paths.get)
        inventory = malformed.discover_tools(inspect_help=True)
        self.assertFalse(inventory.receive_available)
        with self.assertRaises(AcquisitionError) as unverified:
            malformed.capture(RXConfig())
        self.assertEqual("tools_unavailable", unverified.exception.code)

        runner = FakeRunner(FIXTURE.read_bytes(), returncode=2)
        failed = RealHackRFBackend(runner=runner, which=paths.get)
        failed._inventory = RealHackRFBackend(runner=FakeRunner(), which=paths.get).discover_tools(inspect_help=True)
        with self.assertRaises(AcquisitionError) as process_failed:
            failed.capture(RXConfig(device_serial=SERIAL))
        self.assertEqual("capture_process_failed", process_failed.exception.code)
        self.assertFalse(runner.capture_path.exists())  # type: ignore[union-attr]

    def test_real_capture_uses_validated_argv_exact_size_and_cleans_temp(self) -> None:
        payload = FIXTURE.read_bytes()
        runner = FakeRunner(payload)
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}
        backend = RealHackRFBackend(runner=runner, which=paths.get)
        backend.discover_tools(inspect_help=True)
        result = backend.capture(RXConfig(device_serial=SERIAL))
        self.assertEqual(payload, result.payload)
        self.assertEqual("0", runner.calls[-1][runner.calls[-1].index("-a") + 1])
        self.assertEqual(SERIAL, runner.calls[-1][runner.calls[-1].index("-d") + 1])
        self.assertIsNotNone(runner.capture_path)
        self.assertFalse(runner.capture_path.exists())  # type: ignore[union-attr]

    def test_real_capture_rejects_short_and_long_and_cleans_temp(self) -> None:
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}
        for payload, code in ((b"\x00" * 10, "short_capture"), (FIXTURE.read_bytes() + b"\x00", "long_capture")):
            runner = FakeRunner(payload)
            backend = RealHackRFBackend(runner=runner, which=paths.get)
            backend.discover_tools(inspect_help=True)
            with self.assertRaises(AcquisitionError) as failure:
                backend.capture(RXConfig(device_serial=SERIAL))
            self.assertEqual(code, failure.exception.code)
            self.assertFalse(runner.capture_path.exists())  # type: ignore[union-attr]

    def test_real_capture_cleans_temp_on_cancel_and_timeout(self) -> None:
        paths = {name: name for name in ("hackrf_info", "hackrf_transfer", "hackrf_sweep")}

        class InterruptingRunner(FakeRunner):
            def __init__(self, code: str) -> None:
                super().__init__()
                self.code = code

            def run(self, argv: list[str], **kwargs: object) -> ProcessResult:
                if argv[-1] == "-h":
                    return super().run(argv, **kwargs)
                self.capture_path = Path(argv[argv.index("-r") + 1])
                self.capture_path.write_bytes(b"partial")
                raise AcquisitionError(self.code, "interrupted")

        for code in ("operation_cancelled", "operation_timeout"):
            runner = InterruptingRunner(code)
            backend = RealHackRFBackend(runner=runner, which=paths.get)
            backend.discover_tools(inspect_help=True)
            with self.assertRaises(AcquisitionError) as interrupted:
                backend.capture(RXConfig(device_serial=SERIAL))
            self.assertEqual(code, interrupted.exception.code)
            self.assertFalse(runner.capture_path.exists())  # type: ignore[union-attr]

    def test_sweep_fixture_is_bounded_ordered_and_mock_only(self) -> None:
        bins = parse_sweep_fixture(b"99000000,-70\n100000000,-20\n")
        self.assertEqual((99_000_000, 100_000_000), tuple(item.frequency_hz for item in bins))
        with self.assertRaises(AcquisitionError):
            parse_sweep_fixture(b"100000000,-20\n99000000,-70\n")
        result = DeterministicMockBackend().coarse_sweep()
        self.assertEqual("passed", result.status)
        self.assertEqual("not_exercised", RealHackRFBackend(which=lambda _: None).coarse_sweep().status)

    def test_process_runner_bounds_output_timeout_cancel_and_close(self) -> None:
        name = Path(sys.executable).name.casefold().removesuffix(".exe")
        runner = SafeProcessRunner(allowed_executables=(name,), output_limit_bytes=128)
        result = runner.run([sys.executable, "-c", "import sys;sys.stdout.write('x'*10000);sys.stderr.write('y'*10000)"], timeout_seconds=5)
        self.assertEqual(128, len(result.stdout))
        self.assertEqual(128, len(result.stderr))
        self.assertTrue(result.stdout_truncated and result.stderr_truncated)
        with self.assertRaises(AcquisitionError) as timed_out:
            runner.run([sys.executable, "-c", "import time;time.sleep(2)"], timeout_seconds=0.1)
        self.assertEqual("operation_timeout", timed_out.exception.code)
        cancellation = threading.Event()
        timer = threading.Timer(0.05, cancellation.set)
        timer.start()
        with self.assertRaises(AcquisitionError) as cancelled:
            runner.run([sys.executable, "-c", "import time;time.sleep(2)"], timeout_seconds=3, cancellation=cancellation)
        timer.join()
        self.assertEqual("operation_cancelled", cancelled.exception.code)
        runner.close()
        self.assertFalse(runner.active)

    def test_close_terminates_an_active_process(self) -> None:
        name = Path(sys.executable).name.casefold().removesuffix(".exe")
        runner = SafeProcessRunner(allowed_executables=(name,))
        outcome: list[object] = []

        def execute() -> None:
            try:
                outcome.append(runner.run([sys.executable, "-c", "import time;time.sleep(5)"], timeout_seconds=10))
            except Exception as exc:  # A terminated helper may surface as a typed failure or non-zero result.
                outcome.append(exc)

        thread = threading.Thread(target=execute)
        thread.start()
        deadline = time.monotonic() + 1
        while not runner.active and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertTrue(runner.active)
        runner.close()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(runner.active)


if __name__ == "__main__":
    unittest.main()
