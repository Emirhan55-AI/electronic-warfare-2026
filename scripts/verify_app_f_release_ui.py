"""Render and verify the APP-F Qt Quick release surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
LISTENING_FIXTURE = ROOT / "datasets" / "fixtures" / "phase05" / "am-tone-ci8.sigmf-meta"
OUTPUT = ROOT / "results" / "evidence" / "app-f"
SUMMARY = OUTPUT / "release-ui-verification.json"
QML = ROOT / "app" / "operator_console" / "qml" / "Main.qml"


CONFIGURATIONS = (
    ("minimum-1280x720", 1280, 720, 1.0, 0, 0, False, False),
    ("measurement-1280x720", 1280, 720, 1.0, 0, 1, False, False),
    ("standard-1366x768", 1366, 768, 1.0, 1, 0, True, False),
    ("fullhd-1920x1080", 1920, 1080, 1.0, 3, 0, False, False),
    ("scale-150-percent", 1280, 720, 1.5, 2, 0, False, True),
)

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))]


def _child_run(args: argparse.Namespace) -> int:
    from PySide6.QtCore import QEventLoop, QObject, QTimer
    from PySide6.QtQuick import QQuickWindow

    from app.operator_console.quick_application import build_quick_application

    app, engine, view_model = build_quick_application(["app-f-verification"])
    root = engine.rootObjects()[0]
    root.setWidth(args.width)
    root.setHeight(args.height)
    root.setProperty("workspace", args.workspace)
    root.setProperty("spectrumTaskTab", args.spectrum_task_tab)
    root.show()
    if args.probe_only:
        view_model.setSourceMode("hackrf")
        view_model.probeHackrf()
        deadline = time.perf_counter() + 12.0
        while view_model.busy and time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(0.005)
        payload = {
            "source_mode": view_model.sourceMode,
            "source_state": view_model.sourceState,
            "source_ready": view_model.sourceReady,
            "status": view_model.statusMessage,
            "settled": not view_model.busy,
        }
        view_model.shutdown()
        root.close()
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    if args.empty_source:
        settle_deadline = time.perf_counter() + 0.35
        while time.perf_counter() < settle_deadline:
            app.processEvents()
            time.sleep(0.002)
        image = QQuickWindow.grabWindow(root)
        screenshot = Path(args.screenshot)
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        if image.isNull() or not image.save(str(screenshot)):
            raise RuntimeError("Empty-state QML screenshot could not be saved")
        payload = {
            "name": args.name,
            "logical_width": int(root.width()),
            "logical_height": int(root.height()),
            "captured_width": image.width(),
            "captured_height": image.height(),
            "source_ready": view_model.sourceReady,
            "source_state": view_model.sourceState,
            "visible_detections": len(view_model.detections),
            "screenshot": (OUTPUT / f"{args.name}.png").relative_to(ROOT).as_posix(),
            "screenshot_sha256": _sha256(screenshot),
        }
        view_model.shutdown()
        root.close()
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    heartbeat: list[float] = []
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: heartbeat.append(time.perf_counter()))

    view_model.openSigmf(str(FIXTURE))
    deadline = time.perf_counter() + 8.0
    while time.perf_counter() < deadline and (
        view_model.busy or not view_model.sourceReady or not view_model.spectrumValues
    ):
        app.processEvents()
        time.sleep(0.002)
    if not view_model.sourceReady:
        raise RuntimeError(view_model.errorMessage or "SigMF source did not become ready")

    settle_deadline = time.perf_counter() + 0.35
    while time.perf_counter() < settle_deadline:
        app.processEvents()
        time.sleep(0.002)

    heartbeat.append(time.perf_counter())
    timer.start()
    initial_count = len(view_model._operation_samples_ms)
    started = time.perf_counter()
    view_model.startScan()
    measurement_loop = QEventLoop()
    QTimer.singleShot(2_500, measurement_loop.quit)
    measurement_loop.exec()
    duration = time.perf_counter() - started
    view_model.pause()
    while view_model.busy and time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(0.002)
    app.processEvents()
    timer.stop()

    operation_ms = view_model._operation_samples_ms[initial_count:]
    gaps_ms = [
        (current - previous) * 1000.0
        for previous, current in zip(heartbeat, heartbeat[1:])
    ]

    if args.prepare_listening:
        view_model.openSigmf(str(LISTENING_FIXTURE))
        listening_deadline = time.perf_counter() + 8.0
        while time.perf_counter() < listening_deadline and (
            view_model.busy or not view_model.sourceReady or not view_model.spectrumValues
        ):
            app.processEvents()
            time.sleep(0.002)
        view_model.startScan()
        while time.perf_counter() < listening_deadline and not any(
            item["stateKey"] == "confirmed" for item in view_model.detections
        ):
            app.processEvents()
            time.sleep(0.002)
        view_model.pause()
        while view_model.busy and time.perf_counter() < listening_deadline:
            app.processEvents()
            time.sleep(0.002)

    if args.prepare_direction:
        confirmed = next(
            (item for item in view_model.detections if item["stateKey"] == "confirmed"),
            None,
        )
        if confirmed is not None:
            view_model.selectDetection(int(confirmed["eventId"]))
        for angle in (0.0, 15.0, 30.0):
            view_model.addDirectionMeasurement(angle, "north", 0.0)
        direction_visual_deadline = time.perf_counter() + 0.35
        while time.perf_counter() < direction_visual_deadline:
            app.processEvents()
            time.sleep(0.002)

    if args.workspace in {0, 1}:
        confirmed = next(
            (item for item in view_model.detections if item["stateKey"] == "confirmed"),
            None,
        )
        if confirmed is not None:
            view_model.selectDetection(int(confirmed["eventId"]))
            if args.workspace == 0:
                root.zoomSpectrum(0.5, 0.25)
                root.setProperty("spectrumCursorNormalized", view_model.selectedRegionPeakNormalized)
                root.setProperty("spectrumCursorVisible", True)
            elif args.prepare_listening:
                view_model.requestListening("am", view_model.selectedDetectionOffsetKHz, 16.0, 0.8)
                listening_deadline = time.perf_counter() + 8.0
                while view_model.busy and time.perf_counter() < listening_deadline:
                    app.processEvents()
                    time.sleep(0.002)
            visual_deadline = time.perf_counter() + 0.35
            while time.perf_counter() < visual_deadline:
                app.processEvents()
                time.sleep(0.002)

    image = QQuickWindow.grabWindow(root)
    screenshot = Path(args.screenshot)
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    if image.isNull() or not image.save(str(screenshot)):
        raise RuntimeError("QML screenshot could not be saved")

    payload = {
        "name": args.name,
        "logical_width": int(root.width()),
        "logical_height": int(root.height()),
        "scale_factor": args.scale,
        "captured_width": image.width(),
        "captured_height": image.height(),
        "workspace": args.workspace,
        "spectrum_task_tab": args.spectrum_task_tab,
        "prepare_listening": args.prepare_listening,
        "prepare_direction": args.prepare_direction,
        "source_ready": view_model.sourceReady,
        "source_state": view_model.sourceState,
        "spectrum_points": len(view_model.spectrumValues),
        "visible_detections": len(view_model.detections),
        "selected_detection_id": view_model.selectedDetectionId,
        "selected_region": [
            view_model.selectedRegionStartNormalized,
            view_model.selectedRegionPeakNormalized,
            view_model.selectedRegionEndNormalized,
        ],
        "analysis_span": [
            view_model.analysisSpanStartNormalized,
            view_model.analysisSpanEndNormalized,
        ],
        "spectrum_view": [
            float(root.property("spectrumViewStart")),
            float(root.property("spectrumViewEnd")),
        ],
        "processed_frames": len(operation_ms),
        "observed_update_hz": len(operation_ms) / duration,
        "processing_median_ms": statistics.median(operation_ms),
        "processing_p95_ms": _percentile(operation_ms, 0.95),
        "maximum_heartbeat_gap_ms": max(gaps_ms),
        "developer_mode": view_model.developerMode,
        "pipeline_blocks": view_model.pipelineBlocks,
        "event_log_fields": sorted(view_model.eventLog[-1].keys()) if view_model.eventLog else [],
        "listening_ready": view_model.listeningReady,
        "listening_short_preview": view_model.listeningShortPreview,
        "listening_waveform_points": len(view_model.listeningWaveform),
        "listening_playback_state": view_model.listeningPlaybackState,
        "listening_playback_duration": view_model.listeningPlaybackDurationText,
        "direction_measurement_count": view_model.directionMeasurementCount,
        "direction_distinct_angle_count": view_model.directionDistinctAngleCount,
        "direction_ready": view_model.directionReady,
        "direction_status": view_model.directionStatusText,
        "direction_reference": view_model.directionReferenceText,
        "direction_source_bound": all(
            item["source"] == view_model.sourceName for item in view_model.directionPoints
        ),
        "screenshot": (OUTPUT / f"{args.name}.png").relative_to(ROOT).as_posix(),
        "screenshot_sha256": _sha256(screenshot),
    }
    view_model.shutdown()
    root.close()
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _parent_run() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, object]] = []
    temporary_output_handle = tempfile.TemporaryDirectory(prefix="app-f-ui-")
    temporary_output = Path(temporary_output_handle.name)
    for name, width, height, scale, workspace, spectrum_task_tab, prepare_listening, prepare_direction in CONFIGURATIONS:
        screenshot = temporary_output / f"{name}.png"
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["QT_QUICK_BACKEND"] = "software"
        environment["QT_SCALE_FACTOR"] = str(scale)
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["EH_CONSOLE_DEVELOPER_MODE"] = "0"
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--child",
                "--name",
                name,
                "--width",
                str(width),
                "--height",
                str(height),
                "--scale",
                str(scale),
                "--workspace",
                str(workspace),
                "--spectrum-task-tab",
                str(spectrum_task_tab),
                *(["--prepare-listening"] if prepare_listening else []),
                *(["--prepare-direction"] if prepare_direction else []),
                "--screenshot",
                str(screenshot),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if process.returncode:
            print(process.stdout)
            print(process.stderr, file=sys.stderr)
            temporary_output_handle.cleanup()
            return process.returncode
        runs.append(json.loads(process.stdout.strip().splitlines()[-1]))

    empty_name = "empty-1280x720"
    empty_screenshot = temporary_output / f"{empty_name}.png"
    empty_environment = os.environ.copy()
    empty_environment["QT_QPA_PLATFORM"] = "offscreen"
    empty_environment["QT_QUICK_BACKEND"] = "software"
    empty_environment["QT_SCALE_FACTOR"] = "1.0"
    empty_environment["PYTHONIOENCODING"] = "utf-8"
    empty_environment["EH_CONSOLE_DEVELOPER_MODE"] = "0"
    empty_process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--child",
            "--empty-source",
            "--name",
            empty_name,
            "--width",
            "1280",
            "--height",
            "720",
            "--screenshot",
            str(empty_screenshot),
        ],
        cwd=ROOT,
        env=empty_environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if empty_process.returncode:
        print(empty_process.stdout)
        print(empty_process.stderr, file=sys.stderr)
        temporary_output_handle.cleanup()
        return empty_process.returncode
    empty_run = json.loads(empty_process.stdout.strip().splitlines()[-1])

    for run in runs:
        name = str(run["name"])
        shutil.copyfile(temporary_output / f"{name}.png", OUTPUT / f"{name}.png")
    shutil.copyfile(empty_screenshot, OUTPUT / f"{empty_name}.png")
    temporary_output_handle.cleanup()

    probe_environment = os.environ.copy()
    probe_environment["QT_QPA_PLATFORM"] = "offscreen"
    probe_environment["QT_QUICK_BACKEND"] = "software"
    probe_environment["PYTHONIOENCODING"] = "utf-8"
    probe_environment["EH_CONSOLE_DEVELOPER_MODE"] = "0"
    probe_process = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--probe-only"],
        cwd=ROOT,
        env=probe_environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if probe_process.returncode:
        print(probe_process.stdout)
        print(probe_process.stderr, file=sys.stderr)
        return probe_process.returncode
    hackrf_probe = json.loads(probe_process.stdout.strip().splitlines()[-1])

    qml_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(QML.parent.glob("*.qml"))
    )
    gates = {
        "all_sources_real": all(bool(run["source_ready"]) for run in runs),
        "minimum_screen": all(
            int(run["logical_width"]) >= 1180 and int(run["logical_height"]) >= 680
            for run in runs
        ),
        "empty_source_surface": not bool(empty_run["source_ready"])
        and int(empty_run["visible_detections"]) == 0
        and int(empty_run["logical_width"]) == 1280
        and int(empty_run["logical_height"]) == 720
        and all(
            marker in qml_text
            for marker in (
                'objectName: "emptySpectrumMessage"',
                'objectName: "emptyDetectionMessage"',
                "Taramayı başlatınca spektrum burada görünür",
                "Taramayı başlatın",
            )
        ),
        "workspace_coverage": {int(run["workspace"]) for run in runs} == {0, 1, 2, 3},
        "bounded_spectrum": all(1 < int(run["spectrum_points"]) <= 1600 for run in runs),
        "selection_bound_to_fft": all(
            int(run["selected_detection_id"]) >= 0
            and 0.0 <= float(run["selected_region"][0])
            <= float(run["selected_region"][1])
            <= float(run["selected_region"][2])
            <= 1.0
            and 0.0 <= float(run["analysis_span"][0])
            <= float(run["analysis_span"][1])
            <= 1.0
            for run in runs
            if int(run["workspace"]) == 0
        ),
        "linked_frequency_view": all(
            0.0 < float(run["spectrum_view"][0])
            < float(run["spectrum_view"][1])
            < 1.0
            for run in runs
            if int(run["workspace"]) == 0
        ),
        "stable_task_layout": all(
            marker in qml_text
            for marker in (
                'objectName: "measurementScroll"',
                'objectName: "detectionList"',
                'objectName: "listeningSettingsScroll"',
                "property int spectrumTaskTab: 0",
            )
        ),
        "spectrum_task_views": {
            (int(run["workspace"]), int(run["spectrum_task_tab"])) for run in runs
        }.issuperset({(0, 0), (0, 1)}),
        "listening_task_ready": any(
            bool(run["prepare_listening"])
            and bool(run["listening_ready"])
            and int(run["listening_waveform_points"]) > 100
            and run["listening_playback_state"] == "Oynatmaya hazır"
            and run["listening_playback_duration"] != "00:00.0"
            for run in runs
        )
        and all(
            marker in qml_text
            for marker in (
                'objectName: "listeningTransport"',
                'objectName: "listeningResultList"',
                "Oynatma konumu, salt okunur",
                "operatorViewModel.listeningOutputState",
            )
        ),
        "direction_task_guarded": any(
            bool(run["prepare_direction"])
            and int(run["direction_measurement_count"]) == 1
            and int(run["direction_distinct_angle_count"]) == 1
            and not bool(run["direction_ready"])
            and run["direction_status"] == "15° adımlı 24 anten açısı gerekli"
            and run["direction_reference"] == "Gerçek kuzey · anten 0°"
            and bool(run["direction_source_bound"])
            for run in runs
        )
        and all(
            marker in qml_text
            for marker in (
                'objectName: "directionClockwiseGuide"',
                'objectName: "directionCompass"',
                'objectName: "directionMeasurementList"',
                'objectName: "directionStartMeasurement"',
            )
        ),
        "system_diagnostics": all(
            marker in qml_text
            for marker in (
                'objectName: "pipelineList"',
                'objectName: "systemLog"',
                "BİLEŞEN AYRINTISI",
                "OPERASYON GÜNLÜĞÜ",
                "Salt okunur · komut çalıştırmaz",
            )
        ),
        "release_source_navigation_disabled": all(
            not bool(run["developer_mode"])
            and len(run["pipeline_blocks"]) == 7
            and all(block["runtime"] == "HOST" for block in run["pipeline_blocks"])
            for run in runs
        ),
        "structured_operation_log": all(
            set(run["event_log_fields"])
            == {"component", "level", "message", "sequence", "time"}
            for run in runs
        ),
        "spectrum_interaction_model": all(
            marker in qml_text
            for marker in (
                "spectrumViewBack",
                "spectrumViewForward",
                "setAnalysisSpanDraftNormalized",
            )
        ),
        "ten_hz_update": all(float(run["observed_update_hz"]) >= 9.0 for run in runs),
        "processing_budget": all(float(run["processing_p95_ms"]) < 100.0 for run in runs),
        "responsive_gui": all(float(run["maximum_heartbeat_gap_ms"]) < 100.0 for run in runs),
        "keyboard_and_accessibility": all(
            marker in qml_text
            for marker in (
                "Accessible.name",
                "Accessible.role: Accessible.StaticText",
                'sequence: "Space"',
                "operatorViewModel.sourceReady && !operatorViewModel.busy",
                'sequence: "Ctrl+4"',
                'sequence: "Ctrl+5"',
                'objectName: "workspaceNavigation" + index',
            )
        ),
        "cross_workspace_consistency": all(
            marker in qml_text
            for marker in (
                "property int uiBodyTextSize: width >= 1600 ? 11 : 10",
                "root.systemLogMatchCount() + \" kayıt\"",
                "Bu filtreyle eşleşen olay yok",
                'objectName: "systemLog"',
            )
        ),
        "honest_feature_surface": all(
            marker not in qml_text for marker in ("LIVE GNSS", "HOST/SYNTHETIC", "Simülasyon", "mock", "demo")
        ),
        "hackrf_probe_settled": bool(hackrf_probe["settled"])
        and hackrf_probe["source_mode"] == "hackrf"
        and hackrf_probe["source_state"] in {"Hazır", "Kullanılmıyor", "Hata"},
    }
    payload = {
        "schema_version": 3,
        "work_package": "APP-F",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "qt_platform": "offscreen",
            "qt_quick_backend": "software",
            "claim_scope": "Bu sonuçlar mevcut Windows geliştirme bilgisayarındaki offscreen yazılım çizimine aittir.",
        },
        "input": {
            "metadata": FIXTURE.relative_to(ROOT).as_posix(),
            "metadata_sha256": _sha256(FIXTURE),
            "data_sha256": _sha256(FIXTURE.with_suffix(".sigmf-data")),
            "listening_metadata": LISTENING_FIXTURE.relative_to(ROOT).as_posix(),
            "listening_metadata_sha256": _sha256(LISTENING_FIXTURE),
            "listening_data_sha256": _sha256(LISTENING_FIXTURE.with_suffix(".sigmf-data")),
        },
        "runs": runs,
        "empty_run": empty_run,
        "hackrf_probe": hackrf_probe,
        "gates": gates,
        "overall": "passed" if all(gates.values()) else "failed",
    }
    SUMMARY.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for name, passed in gates.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(SUMMARY)
    return 0 if payload["overall"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--name", default="")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--workspace", type=int, default=0)
    parser.add_argument("--spectrum-task-tab", type=int, choices=(0, 1), default=0)
    parser.add_argument("--prepare-listening", action="store_true")
    parser.add_argument("--prepare-direction", action="store_true")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--empty-source", action="store_true")
    args = parser.parse_args(argv)
    return _child_run(args) if args.child else _parent_run()


if __name__ == "__main__":
    raise SystemExit(main())
