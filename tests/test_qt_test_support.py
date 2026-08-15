"""Strict failure-propagation tests for Qt subprocess containment."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

import qt_test_support as support


class QtTestSupportTests(unittest.TestCase):
    def test_child_success_is_success(self) -> None:
        completed = subprocess.CompletedProcess(("python",), 0, "ok", "")
        with patch("qt_test_support.subprocess.run", return_value=completed):
            support.IsolatedQtModuleTest("synthetic").runTest()

    def test_child_failure_reports_exact_exit_and_output(self) -> None:
        completed = subprocess.CompletedProcess(("python",), 7, "child stdout", "child stderr")
        with patch("qt_test_support.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(AssertionError, r"exit_code=7 \(0x00000007\)") as raised:
                support.IsolatedQtModuleTest("synthetic").runTest()
        self.assertIn("child stdout", str(raised.exception))
        self.assertIn("child stderr", str(raised.exception))

    def test_native_windows_exit_is_failure_with_unsigned_code(self) -> None:
        completed = subprocess.CompletedProcess(("python",), -1073741819, "", "faulthandler trace")
        with patch("qt_test_support.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(AssertionError, r"exit_code=-1073741819 \(0xc0000005\)") as raised:
                support.IsolatedQtModuleTest("synthetic").runTest()
        self.assertIn("faulthandler trace", str(raised.exception))

    def test_child_timeout_is_failure_with_diagnostics(self) -> None:
        timeout = subprocess.TimeoutExpired(("python",), 180.0, output="partial stdout", stderr="partial stderr")
        with patch("qt_test_support.subprocess.run", side_effect=timeout):
            with self.assertRaisesRegex(AssertionError, "timed out") as raised:
                support.IsolatedQtModuleTest("synthetic").runTest()
        self.assertIn("partial stdout", str(raised.exception))
        self.assertIn("partial stderr", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
