#!/usr/bin/env python3
"""Render and validate real PHASE-03 operation-console states."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT_DIRECTORY = ROOT / "results" / "evidence" / "phase03" / "screenshots"
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase03" / "visual-summary.json"
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
FIXTURE_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"


SCENARIOS = (
    ("empty", "empty-1366x768-scale100.png", 1366, 768, 1.0),
    ("noise-only", "noise-only-1366x768-scale100.png", 1366, 768, 1.0),
    ("tentative", "tentative-1366x768-scale100.png", 1366, 768, 1.0),
    ("confirmed", "confirmed-1366x768-scale100.png", 1366, 768, 1.0),
    ("warning", "warning-1366x768-scale100.png", 1366, 768, 1.0),
    ("error", "error-1366x768-scale100.png", 1366, 768, 1.0),
    ("confirmed", "confirmed-1920x1080-scale150.png", 1280, 720, 1.5),
)


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _run(state: str, filename: str, width: int, height: int, scale: float, output: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_SCALE_FACTOR"] = str(scale)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--internal",
            "--state",
            state,
            "--logical-width",
            str(width),
            "--logical-height",
            str(height),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode:
        raise RuntimeError(f"{state} render failed: {(process.stderr or '').strip()}")
    result = json.loads([line for line in process.stdout.splitlines() if line][-1])
    result["path"] = f"results/evidence/phase03/screenshots/{filename}"
    return result


def write_outputs() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    results = [
        _run(state, filename, width, height, scale, OUTPUT_DIRECTORY / filename)
        for state, filename, width, height, scale in SCENARIOS
    ]
    summary = {
        "schema_version": 1,
        "phase": "PHASE-03",
        "rendering_contract": {
            "screenshots_are_byte_portable_gate": False,
            "real_application_and_pipeline": True,
            "physical_1920x1080_scale150_uses_logical_1280x720": True,
        },
        "screenshots": results,
    }
    SUMMARY_PATH.write_bytes(_canonical(summary))
    print(f"PHASE-03 visual evidence written: {len(results)} screenshots")


def check_outputs() -> list[str]:
    try:
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"visual summary unreadable: {type(exc).__name__}"]
    records = summary.get("screenshots")
    if not isinstance(records, list) or len(records) != len(SCENARIOS):
        return ["visual summary scenario count mismatch"]
    from PySide6.QtGui import QImage

    problems: list[str] = []
    for expected, record in zip(SCENARIOS, records, strict=True):
        state, filename, width, height, scale = expected
        path = OUTPUT_DIRECTORY / filename
        if record.get("state") != state or record.get("path") != f"results/evidence/phase03/screenshots/{filename}":
            problems.append(f"{filename}: state/path mismatch")
        if record.get("logical_width") != width or record.get("logical_height") != height:
            problems.append(f"{filename}: logical dimensions mismatch")
        image = QImage(str(path))
        if image.isNull() or image.width() != round(width * scale) or image.height() != round(height * scale):
            problems.append(f"{filename}: PNG dimensions invalid")
        checks = record.get("checks")
        if not isinstance(checks, dict) or any(value is not True for value in checks.values()):
            problems.append(f"{filename}: visual checks failed")
        if path.is_file() and not 20_000 <= path.stat().st_size <= 3_000_000:
            problems.append(f"{filename}: PNG size outside expected bound")
    return problems


def _internal_render(state: str, width: int, height: int, output: Path) -> int:
    import numpy as np
    from PySide6.QtCore import QEventLoop, QRect, Qt, QTimer
    from PySide6.QtGui import QFontMetrics, QImage
    from PySide6.QtWidgets import QLabel

    from host.operator_console.application import build_application
    from reference.detection.scenes import generate_scene

    app, window, controller = build_application(["phase03-render"])
    temporary: tempfile.TemporaryDirectory[str] | None = None

    def wait_until(predicate: Any) -> bool:
        deadline = time.perf_counter() + 3.0
        while time.perf_counter() < deadline:
            app.processEvents()
            if predicate():
                return True
            time.sleep(0.002)
        return bool(predicate())

    def write_scene_source(scene_id: str, frames: list[np.ndarray], name: str) -> Path:
        nonlocal temporary
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        metadata = root / f"{name}.sigmf-meta"
        data = root / f"{name}.sigmf-data"
        document = json.loads(FIXTURE_META.read_text(encoding="utf-8"))
        document["global"].pop("core:sha512", None)
        document["global"]["core:description"] = f"PHASE-03 {scene_id} render fixture"
        metadata.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        packed = bytearray()
        peak = max(float(np.max(np.abs(samples))) for samples in frames)
        scale = 100.0 / peak
        for samples in frames:
            clipped_i = np.clip(np.rint(samples.real * scale), -127, 127).astype(np.int8)
            clipped_q = np.clip(np.rint(samples.imag * scale), -127, 127).astype(np.int8)
            interleaved = np.empty(samples.size * 2, dtype=np.int8)
            interleaved[0::2] = clipped_i
            interleaved[1::2] = clipped_q
            packed.extend(interleaved.tobytes())
        data.write_bytes(packed)
        return metadata

    if state == "noise-only":
        frames = [generate_scene("awgn-medium", trial_index=1).samples]
        controller.open_source(write_scene_source("awgn-medium", frames, state))
        if not wait_until(lambda: controller.last_result is not None and controller.active_task_count == 0):
            return 2
    elif state == "tentative":
        frames = [generate_scene("tone-bin-centered", condition_index=4, trial_index=0).samples]
        controller.open_source(write_scene_source("tone-bin-centered", frames, state))
        if not wait_until(lambda: controller.last_detection is not None and controller.active_task_count == 0):
            return 3
    elif state == "confirmed":
        frames = [
            generate_scene("tone-bin-centered", condition_index=4, trial_index=index).samples
            for index in range(3)
        ]
        controller.open_source(write_scene_source("tone-bin-centered", frames, state))
        if not wait_until(lambda: controller.last_detection is not None and controller.active_task_count == 0):
            return 4
        controller.current_index = 1
        controller.request_current_frame()
        if not wait_until(
            lambda: controller.last_detection is not None
            and controller.last_detection.frame_index == 1
            and controller.active_task_count == 0
        ):
            return 4
    elif state == "warning":
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        metadata = root / "warning.sigmf-meta"
        data = root / "warning.sigmf-data"
        document = json.loads(FIXTURE_META.read_text(encoding="utf-8"))
        del document["global"]["core:num_channels"]
        document["global"].pop("core:sha512", None)
        metadata.write_text(json.dumps(document), encoding="utf-8")
        samples = generate_scene("awgn-medium", trial_index=1).samples
        scale = 100.0 / float(np.max(np.abs(samples)))
        interleaved = np.empty(samples.size * 2, dtype=np.int8)
        interleaved[0::2] = np.clip(np.rint(samples.real * scale), -127, 127).astype(np.int8)
        interleaved[1::2] = np.clip(np.rint(samples.imag * scale), -127, 127).astype(np.int8)
        data.write_bytes(interleaved.tobytes())
        controller.open_source(metadata)
        if not wait_until(
            lambda: controller.last_result is not None
            and controller.active_task_count == 0
            and bool(window.notification.text())
        ):
            return 5
    elif state == "error":
        temporary = tempfile.TemporaryDirectory()
        metadata = Path(temporary.name) / "error.sigmf-meta"
        metadata.write_text("{", encoding="utf-8")
        controller.open_source(metadata)
        if not wait_until(
            lambda: controller.active_task_count == 0 and bool(window.notification.text())
        ):
            return 6

    window.resize(width, height)
    window.show()
    app.processEvents()
    bounds = QRect(0, 0, window.width(), window.height())
    geometry_valid = True
    clipping_free = True
    clipped_labels: list[str] = []
    for label in window.findChildren(QLabel):
        if not label.isVisible() or not label.text():
            continue
        geometry_valid = geometry_valid and bounds.contains(label.mapTo(window, label.rect().topLeft()))
        geometry_valid = geometry_valid and bounds.contains(label.mapTo(window, label.rect().bottomRight()))
        metrics = QFontMetrics(label.font())
        if label.wordWrap():
            needed = metrics.boundingRect(label.contentsRect(), int(Qt.TextFlag.TextWordWrap), label.text())
            fits = needed.height() <= label.contentsRect().height() + 3
        else:
            fits = metrics.horizontalAdvance(label.text()) <= label.contentsRect().width() + 3
        clipping_free = clipping_free and fits
        if not fits:
            clipped_labels.append(label.objectName() or label.text()[:32])

    active = () if controller.last_detection is None else controller.last_detection.active_events
    confirmed_count = sum(event.state == "confirmed" for event in active)
    tentative_count = sum(event.state == "tentative" for event in active)
    state_truthful = {
        "empty": controller.source is None and controller.last_result is None,
        "noise-only": controller.last_detection is not None and not controller.last_detection.regions,
        "tentative": tentative_count > 0 and confirmed_count == 0,
        "confirmed": confirmed_count > 0,
        "warning": window.notification.property("kind") == "warning",
        "error": controller.source is None and window.notification.property("kind") == "error",
    }[state]
    plot_readable = window.spectrum_view.spectrum_plot.width() >= 300 and window.spectrum_view.spectrum_plot.height() >= 140
    detection_layers_real = state in {"empty", "warning", "error"} or controller.last_detection is not None
    event_bound = window.detection_list.count() <= 12

    pixmap = window.grab()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(output), "PNG"):
        return 7
    saved = QImage(str(output))
    result = {
        "state": state,
        "logical_width": window.width(),
        "logical_height": window.height(),
        "device_pixel_ratio": float(pixmap.devicePixelRatio()),
        "physical_width": saved.width(),
        "physical_height": saved.height(),
        "checks": {
            "minimum_logical_area": width >= 960 and height >= 600,
            "widget_geometry_inside_window": geometry_valid,
            "text_not_clipped": clipping_free,
            "spectrum_remains_primary": plot_readable,
            "state_truthful": state_truthful,
            "real_detection_pipeline": detection_layers_real,
            "visible_events_bounded": event_bound,
            "turkish_text_catalog_present": all(character in "".join(label.text() for label in window.findChildren(QLabel)) for character in "çğıöşü"),
        },
        "clipped_labels": clipped_labels,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    controller.close()
    window.close()
    app.processEvents()
    if temporary is not None:
        temporary.cleanup()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--internal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--state", choices=tuple({item[0] for item in SCENARIOS}))
    parser.add_argument("--logical-width", type=int)
    parser.add_argument("--logical-height", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.internal:
        if args.state is None or args.logical_width is None or args.logical_height is None or args.output is None:
            parser.error("internal rendering needs state, dimensions, and output")
        return _internal_render(args.state, args.logical_width, args.logical_height, args.output)
    if args.write:
        write_outputs()
        return 0
    problems = check_outputs()
    if problems:
        for problem in problems:
            print(f"FAILED: {problem}")
        return 1
    print("PHASE-03 visual evidence is complete and structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
