#!/usr/bin/env python3
"""Render and validate real PHASE-02 operator-console states."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT_DIRECTORY = ROOT / "results" / "evidence" / "phase02" / "screenshots"
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase02" / "visual-summary.json"
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
FIXTURE_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"

SCENARIOS = (
    {
        "state": "empty",
        "filename": "empty-1366x768-scale100.png",
        "logical_width": 1366,
        "logical_height": 768,
        "scale": 1.0,
    },
    {
        "state": "loaded",
        "filename": "loaded-1366x768-scale100.png",
        "logical_width": 1366,
        "logical_height": 768,
        "scale": 1.0,
    },
    {
        "state": "loaded",
        "filename": "loaded-1920x1080-scale150.png",
        "logical_width": 1280,
        "logical_height": 720,
        "scale": 1.5,
    },
    {
        "state": "warning",
        "filename": "warning-1366x768-scale100.png",
        "logical_width": 1366,
        "logical_height": 768,
        "scale": 1.0,
    },
    {
        "state": "error",
        "filename": "error-1366x768-scale100.png",
        "logical_width": 1366,
        "logical_height": 768,
        "scale": 1.0,
    },
)


def _run_scenario(scenario: dict[str, object], output_path: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_SCALE_FACTOR"] = str(scenario["scale"])
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--internal",
        "--state",
        str(scenario["state"]),
        "--logical-width",
        str(scenario["logical_width"]),
        "--logical-height",
        str(scenario["logical_height"]),
        "--output",
        str(output_path),
    ]
    process = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )
    if process.returncode != 0:
        raise RuntimeError(f"render failed for {scenario['state']}: {process.stderr.strip()}")
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"render returned no result for {scenario['state']}")
    result = json.loads(lines[-1])
    result["path"] = f"results/evidence/phase02/screenshots/{scenario['filename']}"
    return result


def _visual_summary(results: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-02",
        "rendering_contract": {
            "screenshots_are_byte_portable_gate": False,
            "minimum_logical_width": 960,
            "minimum_logical_height": 600,
            "physical_1920x1080_scale150_uses_logical_1280x720": True,
        },
        "screenshots": results,
    }


def write_outputs() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    results = [_run_scenario(scenario, OUTPUT_DIRECTORY / str(scenario["filename"])) for scenario in SCENARIOS]
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(_visual_summary(results), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"PHASE-02 visual evidence written: {len(results)} screenshots")


def check_outputs() -> list[str]:
    problems: list[str] = []
    try:
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"visual summary unreadable: {type(exc).__name__}"]
    screenshots = summary.get("screenshots")
    if not isinstance(screenshots, list) or len(screenshots) != len(SCENARIOS):
        return ["visual summary does not contain the fixed scenario list"]

    from PySide6.QtGui import QImage

    for expected, actual in zip(SCENARIOS, screenshots):
        filename = str(expected["filename"])
        path = OUTPUT_DIRECTORY / filename
        if actual.get("state") != expected["state"] or actual.get("path") != (
            f"results/evidence/phase02/screenshots/{filename}"
        ):
            problems.append(f"{filename}: state or relative path mismatch")
        if actual.get("logical_width") != expected["logical_width"] or actual.get("logical_height") != expected[
            "logical_height"
        ]:
            problems.append(f"{filename}: logical dimensions mismatch")
        expected_physical_width = round(float(expected["logical_width"]) * float(expected["scale"]))
        expected_physical_height = round(float(expected["logical_height"]) * float(expected["scale"]))
        if actual.get("physical_width") != expected_physical_width or actual.get("physical_height") != expected_physical_height:
            problems.append(f"{filename}: physical dimensions mismatch")
        if not path.is_file():
            problems.append(f"{filename}: screenshot missing")
            continue
        image = QImage(str(path))
        if image.isNull() or image.width() != expected_physical_width or image.height() != expected_physical_height:
            problems.append(f"{filename}: PNG dimensions invalid")
        checks = actual.get("checks")
        if not isinstance(checks, dict) or any(value is not True for value in checks.values()):
            problems.append(f"{filename}: one or more visual checks failed")
    return problems


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        values = [int(color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def _internal_render(state: str, logical_width: int, logical_height: int, output: Path) -> int:
    from PySide6.QtCore import QEventLoop, QRect, Qt, QTimer
    from PySide6.QtGui import QFontMetrics, QImage
    from PySide6.QtWidgets import QApplication, QLabel

    from host.operator_console.application import build_application

    app, window, controller = build_application(["phase02-render"])
    temporary: tempfile.TemporaryDirectory[str] | None = None

    def wait_for_frame() -> bool:
        if controller.last_result is not None and controller.active_task_count == 0:
            return True
        loop = QEventLoop()
        controller.frame_rendered.connect(loop.quit)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        controller.frame_rendered.disconnect(loop.quit)
        return controller.last_result is not None and controller.active_task_count == 0

    def append_fixture_history() -> bool:
        """Append all four tracked frames without relying on playback timing."""
        if not wait_for_frame():
            return False
        for frame_index in range(1, 4):
            completed_before = controller.completed_task_count
            controller.current_index = frame_index
            if not controller.request_current_frame():
                return False
            deadline = QEventLoop()

            def finish_when_rendered(index: int, _: float) -> None:
                if index == frame_index:
                    deadline.quit()

            controller.frame_rendered.connect(finish_when_rendered)
            QTimer.singleShot(3000, deadline.quit)
            deadline.exec()
            controller.frame_rendered.disconnect(finish_when_rendered)
            if controller.completed_task_count <= completed_before or controller.current_index != frame_index:
                return False
        return window.spectrum_view.waterfall_count == 4

    if state == "loaded":
        if not controller.open_source(FIXTURE_META) or not append_fixture_history():
            return 2
    elif state in {"warning", "error"}:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        metadata = root / f"{state}.sigmf-meta"
        data = root / f"{state}.sigmf-data"
        if state == "warning":
            document = json.loads(FIXTURE_META.read_text(encoding="utf-8"))
            del document["global"]["core:num_channels"]
            metadata.write_text(json.dumps(document), encoding="utf-8")
            data.write_bytes(FIXTURE_DATA.read_bytes())
            if not controller.open_source(metadata) or not wait_for_frame():
                return 3
        else:
            metadata.write_text("{", encoding="utf-8")
            data.write_bytes(bytes(8192))
            if not controller.open_source(metadata):
                return 4
            loop = QEventLoop()
            controller.task_counters_changed.connect(
                lambda: loop.quit() if controller.active_task_count == 0 else None
            )
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            if controller.source is not None or controller.active_task_count != 0:
                return 4

    window.resize(logical_width, logical_height)
    window.show()
    app.processEvents()

    clipping_free = True
    window_rect = QRect(0, 0, window.width(), window.height())
    geometry_valid = logical_width >= 960 and logical_height >= 600
    for label in window.findChildren(QLabel):
        if not label.isVisible() or not label.text():
            continue
        top_left = label.mapTo(window, label.rect().topLeft())
        bottom_right = label.mapTo(window, label.rect().bottomRight())
        geometry_valid = geometry_valid and window_rect.contains(top_left) and window_rect.contains(bottom_right)
        metrics = QFontMetrics(label.font())
        if label.wordWrap():
            required = metrics.boundingRect(
                label.contentsRect(),
                int(Qt.TextFlag.TextWordWrap),
                label.text(),
            )
            clipping_free = clipping_free and required.height() <= label.contentsRect().height() + 2
        else:
            clipping_free = clipping_free and (
                metrics.horizontalAdvance(label.text()) <= label.contentsRect().width() + 2
            )

    plot_readable = (
        window.spectrum_view.spectrum_plot.width() >= 300
        and window.spectrum_view.spectrum_plot.height() >= 150
        and window.spectrum_view.waterfall_plot.width() >= 300
        and window.spectrum_view.waterfall_plot.height() >= 100
    )
    state_truthful = {
        "empty": controller.source is None and window.spectrum_view.waterfall_count == 0,
        "loaded": controller.source is not None and window.spectrum_view.waterfall_count > 0,
        "warning": window.notification.isVisible() and window.notification.property("kind") == "warning",
        "error": controller.source is None and window.notification.isVisible() and window.notification.property("kind") == "error",
    }[state]
    waterfall_real_rows = (
        state != "loaded"
        or (
            window.spectrum_view.waterfall_count == 4
            and window.spectrum_view.last_waterfall_values.shape == (4, 4096)
            and window.spectrum_view.waterfall_image.image is not None
            and window.spectrum_view.waterfall_image.image.shape == (4, 4096)
        )
    )
    contrast_valid = (
        _contrast_ratio("#E8EEF5", "#0B0F14") >= 7.0
        and _contrast_ratio("#98A7B7", "#121922") >= 4.5
        and _contrast_ratio("#3A9DFF", "#0B0F14") >= 4.5
    )

    pixmap = window.grab()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(output), "PNG"):
        return 5
    saved = QImage(str(output))
    result = {
        "state": state,
        "logical_width": window.width(),
        "logical_height": window.height(),
        "device_pixel_ratio": float(pixmap.devicePixelRatio()),
        "physical_width": saved.width(),
        "physical_height": saved.height(),
        "checks": {
            "minimum_logical_area": logical_width >= 960 and logical_height >= 600,
            "widget_geometry_inside_window": geometry_valid,
            "text_not_clipped": clipping_free,
            "plots_readable": plot_readable,
            "contrast_valid": contrast_valid,
            "state_truthful": state_truthful,
            "four_real_waterfall_rows": waterfall_real_rows,
        },
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
    parser.add_argument("--write", action="store_true", help="render tracked visual evidence")
    parser.add_argument("--check", action="store_true", help="validate tracked visual evidence")
    parser.add_argument("--internal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--state", choices=("empty", "loaded", "warning", "error"))
    parser.add_argument("--logical-width", type=int)
    parser.add_argument("--logical-height", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.internal:
        if args.state is None or args.logical_width is None or args.logical_height is None or args.output is None:
            parser.error("internal rendering requires state, dimensions, and output")
        return _internal_render(args.state, args.logical_width, args.logical_height, args.output)
    if args.write == args.check:
        parser.error("select exactly one of --write or --check")
    if args.write:
        write_outputs()
        return 0
    problems = check_outputs()
    if problems:
        for problem in problems:
            print(f"FAILED: {problem}")
        return 1
    print("PHASE-02 visual evidence is complete and structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
