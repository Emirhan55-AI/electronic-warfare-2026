"""Render and verify the APP-F Qt Quick release surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
OUTPUT = ROOT / "results" / "evidence" / "app-f"
SUMMARY = OUTPUT / "release-ui-verification.json"
QML = ROOT / "app" / "operator_console" / "qml" / "Main.qml"


CONFIGURATIONS = (
    ("minimum-1280x720", 1280, 720, 1.0, 0),
    ("standard-1366x768", 1366, 768, 1.0, 1),
    ("fullhd-1920x1080", 1920, 1080, 1.0, 2),
    ("scale-150-percent", 1280, 720, 1.5, 0),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))]


def _child_run(args: argparse.Namespace) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtQuick import QQuickWindow

    from app.operator_console.quick_application import build_quick_application

    app, engine, view_model = build_quick_application(["app-f-verification"])
    root = engine.rootObjects()[0]
    root.setWidth(args.width)
    root.setHeight(args.height)
    root.setProperty("workspace", args.workspace)
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
    heartbeat: list[float] = [time.perf_counter()]
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: heartbeat.append(time.perf_counter()))
    timer.start()

    view_model.openSigmf(str(FIXTURE))
    deadline = time.perf_counter() + 8.0
    while time.perf_counter() < deadline and (
        view_model.busy or not view_model.sourceReady or not view_model.spectrumValues
    ):
        app.processEvents()
        time.sleep(0.002)
    if not view_model.sourceReady:
        raise RuntimeError(view_model.errorMessage or "SigMF source did not become ready")

    initial_count = len(view_model._operation_samples_ms)
    started = time.perf_counter()
    view_model.startScan()
    while time.perf_counter() - started < 2.5:
        app.processEvents()
        time.sleep(0.002)
    duration = time.perf_counter() - started
    view_model.pause()
    while view_model.busy and time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(0.002)
    app.processEvents()
    timer.stop()

    if args.workspace == 0:
        confirmed = next(
            (item for item in view_model.detections if item["stateKey"] == "confirmed"),
            None,
        )
        if confirmed is not None:
            view_model.selectDetection(int(confirmed["eventId"]))
            visual_deadline = time.perf_counter() + 0.35
            while time.perf_counter() < visual_deadline:
                app.processEvents()
                time.sleep(0.002)

    operation_ms = view_model._operation_samples_ms[initial_count:]
    gaps_ms = [
        (current - previous) * 1000.0
        for previous, current in zip(heartbeat, heartbeat[1:])
    ]
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
        "processed_frames": len(operation_ms),
        "observed_update_hz": len(operation_ms) / duration,
        "processing_median_ms": statistics.median(operation_ms),
        "processing_p95_ms": _percentile(operation_ms, 0.95),
        "maximum_heartbeat_gap_ms": max(gaps_ms),
        "screenshot": screenshot.relative_to(ROOT).as_posix(),
        "screenshot_sha256": _sha256(screenshot),
    }
    view_model.shutdown()
    root.close()
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _parent_run() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, object]] = []
    for name, width, height, scale, workspace in CONFIGURATIONS:
        screenshot = OUTPUT / f"{name}.png"
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["QT_QUICK_BACKEND"] = "software"
        environment["QT_SCALE_FACTOR"] = str(scale)
        environment["PYTHONIOENCODING"] = "utf-8"
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
            return process.returncode
        runs.append(json.loads(process.stdout.strip().splitlines()[-1]))

    probe_environment = os.environ.copy()
    probe_environment["QT_QPA_PLATFORM"] = "offscreen"
    probe_environment["QT_QUICK_BACKEND"] = "software"
    probe_environment["PYTHONIOENCODING"] = "utf-8"
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

    qml_text = QML.read_text(encoding="utf-8")
    gates = {
        "all_sources_real": all(bool(run["source_ready"]) for run in runs),
        "minimum_screen": all(
            int(run["logical_width"]) >= 1180 and int(run["logical_height"]) >= 680
            for run in runs
        ),
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
        "ten_hz_update": all(float(run["observed_update_hz"]) >= 9.0 for run in runs),
        "processing_budget": all(float(run["processing_p95_ms"]) < 100.0 for run in runs),
        "responsive_gui": all(float(run["maximum_heartbeat_gap_ms"]) < 100.0 for run in runs),
        "keyboard_and_accessibility": all(
            marker in qml_text
            for marker in ("Accessible.name", 'sequence: "Ctrl+O"', 'sequence: "Space"', "Hareketi azalt")
        ),
        "honest_feature_surface": all(
            marker not in qml_text for marker in ("LIVE GNSS", "HOST/SYNTHETIC", "Simülasyon", "mock", "demo")
        ),
        "hackrf_probe_settled": bool(hackrf_probe["settled"])
        and hackrf_probe["source_mode"] == "hackrf"
        and hackrf_probe["source_state"] in {"Hazır", "Kullanılmıyor", "Hata"},
    }
    payload = {
        "schema_version": 1,
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
        },
        "runs": runs,
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
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args(argv)
    return _child_run(args) if args.child else _parent_run()


if __name__ == "__main__":
    raise SystemExit(main())
