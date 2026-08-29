from __future__ import annotations

import unittest

from platforms.acquisition import (
    AcquisitionError,
    RXConfig,
    build_continuous_receive_argv,
    parse_hackrf_buffer_statistics,
)


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
        with self.assertRaisesRegex(AcquisitionError, "kare sayısı"):
            build_continuous_receive_argv("hackrf_transfer", config, 8_193)

    def test_buffer_statistics_use_final_transfer_summary(self) -> None:
        stderr = "0 overruns, longest 0 bytes\nTransfer statistics:\n2 overruns, longest 262144 bytes\n"
        self.assertEqual(parse_hackrf_buffer_statistics(stderr), (2, 262_144))
        with self.assertRaisesRegex(AcquisitionError, "istatistiği"):
            parse_hackrf_buffer_statistics("Transfer statistics unavailable")


if __name__ == "__main__":
    unittest.main()
