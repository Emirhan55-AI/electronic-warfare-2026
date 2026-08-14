"""Render or read-only check real PHASE-05 listening UI states."""

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

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from host.operator_console.application import build_application
from host.operator_console.audio_playback import AudioPlayback
from host.operator_console.ui_text import TEXT


OUT = ROOT / "results" / "evidence" / "phase05"
SUMMARY = OUT / "visual-summary.json"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase05"
STATES = (
    ("no-source-1280x720.png", 1280, 720, "no_source"),
    ("am-ready-1366x768.png", 1366, 768, "am_ready"),
    ("nfm-ready-1366x768.png", 1366, 768, "nfm_ready"),
    ("noise-no-event-1366x768.png", 1366, 768, "noise_no_event"),
    ("audio-unavailable-1366x768.png", 1366, 768, "audio_unavailable"),
    ("am-ready-1920x1080-scale150.png", 1920, 1080, "scale150"),
)


def _canonical(document: object) -> bytes:
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
    raise RuntimeError("PHASE-05 render worker did not drain")


def _load_frames(app: object, controller: object, metadata: Path, last_frame: int) -> None:
    controller.open_source(metadata)
    _wait(app, controller)
    for index in range(1, last_frame + 1):
        controller.current_index = index
        controller.request_current_frame()
        _wait(app, controller)


def _select_expected(window: object, controller: object, expected_offset_hz: float) -> None:
    assert controller.last_detection is not None and controller.last_result is not None
    confirmed = [
        event
        for event in controller.last_detection.active_events
        if event.state == "confirmed" and event.observed_this_frame
    ]
    if not confirmed:
        raise RuntimeError("fixture did not produce a confirmed event")
    center = controller.last_result.center_frequency_hz
    selected = min(confirmed, key=lambda event: abs((event.region.peak_frequency_hz - center) - expected_offset_hz))
    for row in range(window.detection_list.count()):
        item = window.detection_list.item(row)
        if int(item.data(Qt.ItemDataRole.UserRole)) == int(selected.event_id):
            window.detection_list.setCurrentRow(row)
            return
    raise RuntimeError("confirmed event is absent from the visible list")


def _apply(app: object, window: object, controller: object, state: str) -> None:
    window.workspace_tabs.setCurrentIndex(2)
    if state == "no_source":
        return
    if state == "noise_no_event":
        _load_frames(app, controller, FIXTURES / "noise-only-ci8.sigmf-meta", 3)
        return
    if state == "audio_unavailable":
        _load_frames(app, controller, FIXTURES / "am-tone-ci8.sigmf-meta", 1)
        _select_expected(window, controller, 24_000.0)
        return
    nfm = state == "nfm_ready"
    fixture = "nfm-tone-ci8" if nfm else "am-tone-ci8"
    expected = -24_000.0 if nfm else 24_000.0
    _load_frames(app, controller, FIXTURES / f"{fixture}.sigmf-meta", 1)
    _select_expected(window, controller, expected)
    if nfm:
        window.demod_combo.setCurrentIndex(1)
    if not controller.request_listening():
        raise RuntimeError("listening request was rejected")
    _wait(app, controller)


def _assert_state(window: object, controller: object, state: str) -> None:
    if window.workspace_tabs.tabText(2) != "Dinleme":
        raise RuntimeError("Dinleme tab is missing")
    if any(value.text() != TEXT["not_validated"] for value in window.parameter_values.values()):
        raise RuntimeError("PHASE-04 fields changed during PHASE-05 rendering")
    if state == "no_source" and window.prepare_listening_button.isEnabled():
        raise RuntimeError("no-source state enabled listening")
    if state == "noise_no_event" and window.prepare_listening_button.isEnabled():
        raise RuntimeError("noise-only state enabled listening")
    if state in {"am_ready", "nfm_ready", "scale150"}:
        if controller._listening_result is None or "48 kHz" not in window.listening_state.text():
            raise RuntimeError("prepared listening state is not real")
    if state != "no_source" and "canlı RF değildir" not in window.fixture_live_warning.text():
        raise RuntimeError("fixture is not honestly labelled")
    if state == "audio_unavailable" and TEXT["audio_backend_unavailable"] not in window.audio_backend_state.text():
        raise RuntimeError("unavailable audio backend is not visible")


def _summary() -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-05",
        "status": "passed",
        "hardware_status": "not_exercised",
        "live_rx_status": "not_exercised",
        "screenshots": [
            {"file": name, "width": width, "height": height, "state": state}
            for name, width, height, state in STATES
        ],
        "byte_equality_gate": False,
    }


def _render_one(name: str, width: int, height: int, state: str) -> None:
    playback = AudioPlayback(available_override=False)
    app, window, controller = build_application([], audio_playback=playback)
    window.resize(1280, 720) if state == "scale150" else window.resize(width, height)
    _apply(app, window, controller, state)
    window.show()
    app.processEvents()
    _assert_state(window, controller, state)
    if not window.grab().save(str(OUT / name), "PNG"):
        raise RuntimeError("PHASE-05 PNG could not be written")
    controller.close()
    window.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--single-scale150", action="store_true")
    args = parser.parse_args(argv)
    expected = _canonical(_summary())
    if args.check:
        if not SUMMARY.is_file() or SUMMARY.read_bytes() != expected:
            return 1
        return 0 if all(
            not (image := QImage(str(OUT / name))).isNull()
            and image.width() == width
            and image.height() == height
            for name, width, height, _ in STATES
        ) else 1
    OUT.mkdir(parents=True, exist_ok=True)
    if args.single_scale150:
        _render_one("am-ready-1920x1080-scale150.png", 1920, 1080, "scale150")
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
