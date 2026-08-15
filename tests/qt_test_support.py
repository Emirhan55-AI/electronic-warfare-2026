"""Deterministic Qt fixture disposal and native-fault containment."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent


ROOT = Path(__file__).resolve().parents[1]
CHILD_ENVIRONMENT_KEY = "TEKNOFEST_QT_TEST_CHILD"
CHILD_TIMEOUT_SECONDS = 180.0


def dispose_qt_fixture(app: object, *, controller: object, window: object, timers: tuple[object, ...] = ()) -> None:
    """Stop workers first, then synchronously dispose the owned Qt graph."""

    for timer in timers:
        timer.stop()  # type: ignore[attr-defined]
        timer.timeout.disconnect()  # type: ignore[attr-defined]
    controller.close()  # type: ignore[attr-defined]
    window.close()  # type: ignore[attr-defined]
    for timer in timers:
        timer.deleteLater()  # type: ignore[attr-defined]
    window.deleteLater()  # type: ignore[attr-defined]
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()  # type: ignore[attr-defined]


class IsolatedQtModuleTest(unittest.TestCase):
    """Run one Qt integration module in a child interpreter."""

    def __init__(self, module_name: str) -> None:
        super().__init__("runTest")
        self.module_name = module_name

    def id(self) -> str:
        return f"qt_isolated.{self.module_name}.all_tests"

    def __str__(self) -> str:
        return f"all tests in {self.module_name} (isolated Qt process)"

    def runTest(self) -> None:
        environment = os.environ.copy()
        environment[CHILD_ENVIRONMENT_KEY] = "1"
        environment.setdefault("QT_QPA_PLATFORM", "offscreen")
        command = (
            sys.executable,
            "-X",
            "faulthandler",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            f"{self.module_name}.py",
            "-v",
        )
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=CHILD_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.fail(
                f"isolated Qt module timed out after {CHILD_TIMEOUT_SECONDS:.0f}s: {self.module_name}\n"
                f"stdout:\n{exc.stdout or ''}\nstderr:\n{exc.stderr or ''}"
            )
        if completed.returncode != 0:
            unsigned_code = completed.returncode & 0xFFFFFFFF
            self.fail(
                f"isolated Qt module failed: {self.module_name}\n"
                f"exit_code={completed.returncode} (0x{unsigned_code:08x})\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def isolate_qt_module(module_name: str, discovered: unittest.TestSuite) -> unittest.TestSuite:
    """Return real child tests or one strict parent-side process proxy."""

    if os.environ.get(CHILD_ENVIRONMENT_KEY) == "1":
        return discovered
    return unittest.TestSuite((IsolatedQtModuleTest(module_name),))
