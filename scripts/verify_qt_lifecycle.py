"""Repeat the minimal cross-test Qt/GC lifecycle reproducer."""

from __future__ import annotations

import argparse
import gc
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHILD_ENVIRONMENT_KEY = "TEKNOFEST_QT_TEST_CHILD"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def _child() -> int:
    gc.disable()
    analysis = unittest.defaultTestLoader.discover("tests", pattern="test_operator_analysis.py")
    hackrf = unittest.defaultTestLoader.discover("tests", pattern="test_operator_hackrf.py")
    tests = list(_flatten(analysis)) + list(_flatten(hackrf))
    prior = next(
        item for item in tests if item.id().endswith("test_measurement_worker_is_responsive_and_queue_is_bounded")
    )
    target = next(
        item for item in tests if item.id().endswith("test_capture_and_fixture_read_run_outside_ui_thread")
    )
    first = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite((prior,)))
    if not first.wasSuccessful():
        return 2

    def forced_drain(controller: object, timeout: float = 3.0) -> None:
        deadline = time.monotonic() + timeout
        stable = 0
        gc.enable()
        while time.monotonic() < deadline:
            target.app.processEvents()  # type: ignore[attr-defined]
            if controller.active_task_count:  # type: ignore[attr-defined]
                gc.collect()
            if controller.active_task_count == 0 and controller.pending_intent_count == 0:  # type: ignore[attr-defined]
                stable += 1
                if stable > 3:
                    return
            else:
                stable = 0
            time.sleep(0.005)
        target.fail("worker did not drain")

    target._drain = forced_drain  # type: ignore[attr-defined]
    second = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite((target,)))
    return 0 if second.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Qt worker/GC lifecycle reproducer")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if args.child:
        return _child()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    environment = os.environ.copy()
    environment[CHILD_ENVIRONMENT_KEY] = "1"
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    command = (sys.executable, "-X", "faulthandler", "-B", str(Path(__file__).resolve()), "--child")
    for iteration in range(1, args.iterations + 1):
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30.0,
            check=False,
        )
        elapsed = time.perf_counter() - started
        print(f"iteration={iteration} exit_code={completed.returncode} elapsed_seconds={elapsed:.3f}")
        if completed.returncode != 0:
            print(completed.stdout, file=sys.stderr)
            print(completed.stderr, file=sys.stderr)
            return completed.returncode or 1
    print(f"Qt lifecycle reproducer PASS: {args.iterations}/{args.iterations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
