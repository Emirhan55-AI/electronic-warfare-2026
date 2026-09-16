from __future__ import annotations

import threading
import unittest

from platforms.acquisition import (
    AcquisitionError,
    RXConfig,
    build_continuous_receive_argv,
    parse_hackrf_buffer_statistics,
)
from platforms.acquisition.continuous import MAX_CAPTURE_FRAMES, MAX_STREAM_FRAMES


class _FinishedProcess:
    def poll(self) -> int:
        return 1

    def wait(self, timeout: float) -> int:
        del timeout
        return 1


class _FinishedCollector:
    def __init__(self, payload: bytes) -> None:
        self.data = bytearray(payload)

    def join(self, timeout: float) -> None:
        del timeout


class HackRFContinuousTests(unittest.TestCase):
    def test_receive_command_is_serial_bound_stdout_only_and_bounded(self) -> None:
        config = RXConfig(
            center_frequency_hz=103_150_000,
            sample_count=16_384,
            device_serial="0000000000000000a32868dc35138247",
        )
        argv = build_continuous_receive_argv("hackrf_transfer.exe", config, 4_160)
        self.assertEqual(argv[argv.index("-r") + 1], "-")
        self.assertEqual(argv[argv.index("-n") + 1], str(16_384 * 4_160))
        self.assertEqual(argv[argv.index("-d") + 1], config.device_serial)
        self.assertIn("-B", argv)
        self.assertNotIn("-t", argv)
        self.assertNotIn("-R", argv)

    def test_receive_command_rejects_unapproved_executable_and_length(self) -> None:
        config = RXConfig(device_serial="0123456789abcdef")
        with self.assertRaisesRegex(AcquisitionError, "hackrf_transfer"):
            build_continuous_receive_argv("other_tool.exe", config, 1)
        endurance_argv = build_continuous_receive_argv(
            "hackrf_transfer",
            config,
            MAX_STREAM_FRAMES,
        )
        self.assertEqual(
            endurance_argv[endurance_argv.index("-n") + 1],
            str(config.sample_count * MAX_STREAM_FRAMES),
        )
        settling_argv = build_continuous_receive_argv(
            "hackrf_transfer", config, MAX_CAPTURE_FRAMES
        )
        self.assertEqual(
            settling_argv[settling_argv.index("-n") + 1],
            str(config.sample_count * MAX_CAPTURE_FRAMES),
        )
        with self.assertRaisesRegex(AcquisitionError, "kare sayısı"):
            build_continuous_receive_argv("hackrf_transfer", config, MAX_CAPTURE_FRAMES + 1)

    def test_buffer_statistics_use_final_transfer_summary(self) -> None:
        stderr = "0 overruns, longest 0 bytes\nTransfer statistics:\n2 overruns, longest 262144 bytes\n"
        self.assertEqual(parse_hackrf_buffer_statistics(stderr), (2, 262_144))
        with self.assertRaisesRegex(AcquisitionError, "istatistiği"):
            parse_hackrf_buffer_statistics("Transfer statistics unavailable")

    def test_early_eof_preserves_received_count_and_child_diagnostic(self) -> None:
        from platforms.acquisition import HackRFContinuousRX

        stream = HackRFContinuousRX.__new__(HackRFContinuousRX)
        stream.frame_count = 100
        stream._frames_received = 7
        stream._process = _FinishedProcess()
        stream._stderr = _FinishedCollector(
            b"hackrf_transfer started\nusb transfer stopped unexpectedly\n"
        )
        stream._watchdog = threading.Timer(1.0, lambda: None)

        error = stream._short_stream_error()

        self.assertEqual("short_stream", error.code)
        self.assertIn("7/100 kare", str(error))
        self.assertIn("usb transfer stopped unexpectedly", str(error))
        self.assertIsNone(stream._watchdog)


if __name__ == "__main__":
    unittest.main()
