"""Render and check honest PHASE-08A software-only UI evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QImage

from host.operator_console.application import build_application
from host.operator_console.ui_text import TEXT


OUT = ROOT / "results" / "evidence" / "phase08a"
SUMMARY = OUT / "visual-summary.json"
STATES = (
    ("tools-missing-1366x768.png", 1366, 768, "tools_missing"),
    ("device-missing-1366x768.png", 1366, 768, "device_missing"),
    ("deterministic-source-1366x768.png", 1366, 768, "deterministic"),
    ("cli-error-1366x768.png", 1366, 768, "cli_error"),
    ("tools-missing-1920x1080-scale150.png", 1920, 1080, "scale150"),
)


def canonical_json_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _wait(app: object, controller: object) -> None:
    deadline = time.monotonic() + 5.0
    stable = 0
    while time.monotonic() < deadline:
        app.processEvents()
        if controller.active_task_count == 0 and controller.pending_intent_count == 0:
            stable += 1
            if stable > 3:
                return
        else:
            stable = 0
        time.sleep(0.005)
    raise RuntimeError("PHASE-08A render worker did not drain")


def _apply(app: object, window: object, controller: object, state: str) -> None:
    if state == "deterministic":
        window.source_type_combo.setCurrentIndex(2)
        controller.open_deterministic_source()
        _wait(app, controller)
        return
    window.source_type_combo.setCurrentIndex(1)
    if state in {"tools_missing", "scale150"}:
        window.set_hackrf_state("tools_missing")
    elif state == "device_missing":
        window.set_hackrf_state("device_missing")
    elif state == "cli_error":
        window.set_hackrf_state("cli_error")
        window.show_error(TEXT["hackrf_cli_error"])


def _assert_state(window: object, state: str) -> None:
    self_values = tuple(value.text() for value in window.parameter_values.values())
    if any(value != TEXT["not_validated"] for value in self_values):
        raise RuntimeError("PHASE-04 fields must remain unvalidated")
    if state != "deterministic" and window.hackrf_start_button.isEnabled():
        raise RuntimeError("hardware-absent evidence enabled live capture")
    if state == "deterministic":
        if "canlı RF değildir" not in window.notification.text() or "Deterministik" not in window.source_value.text():
            raise RuntimeError("deterministic source is not honestly labelled")
    if state == "cli_error" and not window.notification.isVisible():
        raise RuntimeError("controlled CLI error is not visible")


def _summary() -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-08A",
        "status": "passed",
        "hardware_status": "not_exercised",
        "screenshots": [
            {"file": name, "width": width, "height": height, "state": state}
            for name, width, height, state in STATES
        ],
        "byte_equality_gate": False,
    }


def _render_one(name: str, width: int, height: int, state: str) -> None:
    app, window, controller = build_application([])
    if state == "scale150":
        window.resize(1280, 720)
    else:
        window.resize(width, height)
    _apply(app, window, controller, state)
    window.show()
    app.processEvents()
    _assert_state(window, state)
    if not window.grab().save(str(OUT / name), "PNG"):
        raise RuntimeError("PNG could not be written")
    controller.close()
    window.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--single-scale150", action="store_true")
    args = parser.parse_args(argv)
    expected = canonical_json_bytes(_summary())
    if args.check:
        if not SUMMARY.is_file() or SUMMARY.read_bytes() != expected:
            return 1
        for name, width, height, _ in STATES:
            image = QImage(str(OUT / name))
            if image.isNull() or image.width() != width or image.height() != height:
                return 1
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    if args.single_scale150:
        _render_one("tools-missing-1920x1080-scale150.png", 1920, 1080, "scale150")
        return 0
    for name, width, height, state in STATES:
        if state != "scale150":
            _render_one(name, width, height, state)
    environment = dict(os.environ)
    environment["QT_SCALE_FACTOR"] = "1.5"
    completed = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--single-scale150"],
        cwd=ROOT,
        env=environment,
        check=False,
        shell=False,
    )
    if completed.returncode:
        return completed.returncode
    SUMMARY.write_bytes(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
