"""Render and check real PHASE-04-E1 operator-console visual evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from host.operator_console.application import build_application
from host.operator_console.ui_text import ERROR_TEXT, TEXT
from reference.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent, OperatorMeasurementProcessor
from reference.parameters.operator_reference import build_golden_reference, canonical_json_bytes
from reference.parameters.scenes import generate_parameter_scene
from reference.pipeline import RuntimePipeline, load_profile
from reference.pipeline.profile import load_phase04e1_capability
from reference.spectrum import SpectrumProcessor


OUT = ROOT / "results" / "evidence" / "phase04e1"
SUMMARY = OUT / "visual-summary.json"
STATES = (
    ("empty-1280x720.png", 1280, 720, "empty"),
    ("loading-1366x768.png", 1366, 768, "loading"),
    ("no-detection-1920x1080.png", 1920, 1080, "no_detection"),
    ("tentative-1366x768.png", 1366, 768, "tentative"),
    ("confirmed-selected-1366x768.png", 1366, 768, "confirmed"),
    ("auto-span-1280x720.png", 1280, 720, "auto_span"),
    ("operator-span-1366x768.png", 1366, 768, "operator_span"),
    ("fields-disabled-1920x1080.png", 1920, 1080, "fields_disabled"),
    ("validation-unavailable-1366x768.png", 1366, 768, "validation_unavailable"),
    ("uncertain-1366x768.png", 1366, 768, "uncertain"),
    ("unmeasured-1280x720.png", 1280, 720, "unmeasured"),
    ("warning-1366x768.png", 1366, 768, "warning"),
    ("error-1366x768.png", 1366, 768, "error"),
    ("multiple-events-1920x1080.png", 1920, 1080, "multiple"),
    ("scale150-1920x1080.png", 1920, 1080, "scale150"),
)


def _real_result(scene_id: str = "am-carrier") -> tuple[object, tuple[object, ...], tuple[object, ...], tuple[object, ...]]:
    pipeline = RuntimePipeline(load_profile())
    frames = tuple(generate_parameter_scene(scene_id, trial_index=0, frame_index=index) for index in range(4))
    runtime = tuple(pipeline.process(item.samples, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000, frame_index=index) for index, item in enumerate(frames))
    spectra = tuple(item.spectrum for item in runtime)
    detections = tuple(item.detection for item in runtime)
    truth_scene = "am-carrier" if scene_id == "close-am-qpsk" else scene_id
    truth = next(item for item in build_golden_reference()["families"] if item["source_scene_id"] == truth_scene)
    span = AnalysisSpan(*truth["operator_span"], "operator_adjusted")
    owner = MeasurementCandidate(1, 4, span.lower_shifted_bin, span.upper_shifted_bin)
    context = MeasurementContext(1, 1, 1, 1, 4, (True, True, True, True), (owner,))
    intent = MeasurementIntent(1, 1, 1, 1, 4, 0, span, context)
    result = OperatorMeasurementProcessor().measure(intent, tuple(item.samples for item in frames), spectra)
    return result, frames, spectra, detections


def _apply_state(window: object, state: str) -> None:
    capability = load_phase04e1_capability()
    validated = capability.validated_fields if capability else ()
    window.notification.hide()
    window.workspace_tabs.setCurrentIndex(0)
    window.clear_analysis()
    if state == "empty":
        window.show_empty()
        return
    if state == "loading":
        window.show_opening()
        return
    scene_id = "close-am-qpsk" if state == "multiple" else "am-carrier"
    result, _, spectra, detections = _real_result(scene_id)
    window.spectrum_view.update_spectrum(spectra[-1].display, spectra[-1].display)
    window.analysis_spectrum.set_spectrum(spectra[-1].display)
    if state == "no_detection":
        empty_pipeline = RuntimePipeline(load_profile())
        zeros = [0j] * 4096
        empty = empty_pipeline.process(zeros, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000, frame_index=0)
        window.spectrum_view.update_spectrum(empty.spectrum.display, empty.spectrum.display, detection_result=empty.detection, spectrum_result=empty.spectrum)
        window.set_detection_result(empty.detection)
        return
    detection_index = 0 if state == "tentative" else 3
    window.set_detection_result(detections[detection_index])
    confirmed = next((event for event in detections[detection_index].active_events if event.state == "confirmed" and event.observed_this_frame), None)
    if confirmed is not None:
        window.set_analysis_event(confirmed)
        window.measure_button.setEnabled(capability is not None)
    if state in {"auto_span", "confirmed"}:
        window.workspace_tabs.setCurrentIndex(1)
        auto = None if confirmed is None else __import__("reference.parameters", fromlist=["suggest_analysis_span"]).suggest_analysis_span(confirmed, detections[detection_index].active_events)
        if auto is not None:
            window.analysis_spectrum.set_span(auto.lower_shifted_bin, auto.upper_shifted_bin)
            window.set_analysis_span(auto.lower_shifted_bin, auto.upper_shifted_bin, "auto_suggested")
    elif state in {"operator_span", "unmeasured"}:
        window.workspace_tabs.setCurrentIndex(1)
        window.analysis_spectrum.set_span(result.intent.span.lower_shifted_bin, result.intent.span.upper_shifted_bin)
        window.set_analysis_span(result.intent.span.lower_shifted_bin, result.intent.span.upper_shifted_bin, "operator_adjusted")
    elif state in {"fields_disabled", "validation_unavailable", "uncertain", "scale150"}:
        window.workspace_tabs.setCurrentIndex(1)
        window.analysis_spectrum.set_span(result.intent.span.lower_shifted_bin, result.intent.span.upper_shifted_bin)
        window.set_analysis_span(
            result.intent.span.lower_shifted_bin,
            result.intent.span.upper_shifted_bin,
            result.intent.span.provenance,
        )
        if load_phase04e1_capability() is None:
            window.clear_measurement_result()
            window.measurement_state.setText(TEXT["e1_fallback"])
            window.quality_value.setText(TEXT["quality_not_available"])
        else:
            window.set_operator_measurement(result, validated)
            if state == "uncertain":
                window.measurement_state.setText(TEXT["uncertain"])
    elif state == "warning":
        window.show_warning(TEXT["warning_default_channel"])
    elif state == "error":
        window.show_error(ERROR_TEXT["metadata_invalid_json"])


def _summary() -> dict[str, object]:
    return {"schema_version": 1, "phase": "PHASE-04-E1", "status": "passed", "screenshots": [{"file": name, "width": width, "height": height, "state": state} for name, width, height, state in STATES], "byte_equality_gate": False}


def _assert_state(window: object, state: str) -> None:
    if state == "tentative" and window.measure_button.isEnabled():
        raise RuntimeError("tentative event must not enable measurement")
    if state in {"confirmed", "auto_span", "operator_span", "fields_disabled", "validation_unavailable", "uncertain", "unmeasured", "multiple", "scale150"} and load_phase04e1_capability() is None and window.measure_button.isEnabled():
        raise RuntimeError("missing capability must keep measurement disabled")
    if state in {"fields_disabled", "validation_unavailable", "uncertain", "scale150"} and load_phase04e1_capability() is None:
        if window.measurement_state.text() != TEXT["e1_fallback"] or window.quality_value.text() != TEXT["quality_not_available"]:
            raise RuntimeError("missing capability must not render a successful measurement")
    if state == "multiple" and window.detection_list.count() < 2:
        raise RuntimeError("multiple-event evidence does not contain two real events")
    if state in {"warning", "error"} and not window.notification.isVisible():
        raise RuntimeError(f"{state} notification is not visible")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--single-scale150", action="store_true")
    args = parser.parse_args(argv)
    summary = _summary()
    expected = canonical_json_bytes(summary)
    if args.check:
        if not SUMMARY.exists() or SUMMARY.read_bytes() != expected:
            return 1
        for name, width, height, _ in STATES:
            image = QImage(str(OUT / name))
            if image.isNull() or image.width() != width or image.height() != height:
                return 1
        return 0
    if args.single_scale150:
        app, window, controller = build_application([])
        window.resize(1280, 720)
        _apply_state(window, "scale150")
        window.show()
        app.processEvents()
        _assert_state(window, "scale150")
        window.grab().save(str(OUT / "scale150-1920x1080.png"), "PNG")
        controller.close()
        window.close()
        return 0
    app, window, controller = build_application([])
    OUT.mkdir(parents=True, exist_ok=True)
    for name, width, height, state in STATES:
        if state == "scale150":
            continue
        window.resize(width, height)
        _apply_state(window, state)
        window.show()
        app.processEvents()
        _assert_state(window, state)
        window.grab().save(str(OUT / name), "PNG")
    controller.close()
    window.close()
    environment = dict(os.environ)
    environment["QT_SCALE_FACTOR"] = "1.5"
    completed = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--single-scale150"],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode
    SUMMARY.write_bytes(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
