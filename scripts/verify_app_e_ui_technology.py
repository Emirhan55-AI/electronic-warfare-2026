#!/usr/bin/env python3
"""Measure the APP-E Qt Widgets and Qt Quick presentation prototypes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QLibraryInfo, QUrl, qVersion


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
INPUT_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
INPUT_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
QML_PATH = ROOT / "verification" / "app_e" / "OperatorShell.qml"
OUT = ROOT / "results" / "evidence" / "app-e"
EVIDENCE = OUT / "ui-technology-comparison.json"
RUN_COUNT = 5
WARMUP_UPDATES = 5
MEASURED_UPDATES = 40
DISPLAY_POINTS = 512
TARGET_UPDATE_PERIOD_MS = 100.0


def canonical_json_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def input_frames() -> list[list[float]]:
    from algorithms.spectrum import SigMFFrameSource, SpectrumProcessor

    source = SigMFFrameSource(INPUT_META)
    processor = SpectrumProcessor()
    frames: list[list[float]] = []
    for index in range(source.frame_count):
        result = processor.process(
            source.read_frame(index),
            sample_rate_hz=source.sample_rate_hz,
            center_frequency_hz=source.center_frequency_hz,
        )
        power = np.asarray(result.display.bin_power_dbfs, dtype=np.float64)
        reduced = np.max(power.reshape(DISPLAY_POINTS, power.size // DISPLAY_POINTS), axis=1)
        normalized = np.clip((reduced + 120.0) / 120.0, 0.0, 1.0)
        frames.append([float(value) for value in normalized])
    return frames


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(np.ceil(quantile * len(ordered))) - 1))
    return float(ordered[index])


def install_ui_font(application: object) -> None:
    from PySide6.QtGui import QFont, QFontDatabase

    family = "Segoe UI"
    if not QFontDatabase.hasFamily(family):
        windows_directory = Path(os.environ.get("WINDIR", "C:/Windows"))
        for filename in ("segoeui.ttf", "arial.ttf"):
            font_path = windows_directory / "Fonts" / filename
            if not font_path.is_file():
                continue
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    family = families[0]
                    break
    application.setFont(QFont(family, 10))  # type: ignore[attr-defined]


def current_rss_mib() -> float:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = (
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            )

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD)
        get_process_memory_info.restype = wintypes.BOOL
        process = get_current_process()
        if not get_process_memory_info(process, ctypes.byref(counters), counters.cb):
            raise OSError("working set could not be read")
        return counters.WorkingSetSize / (1024.0 * 1024.0)
    import resource

    maximum_rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return maximum_rss / (1024.0 if sys.platform.startswith("linux") else 1024.0 * 1024.0)


def widget_worker(frames: list[list[float]], screenshot: Path | None) -> dict[str, object]:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

    class SpectrumCanvas(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.values: list[float] = []
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        def set_values(self, values: list[float]) -> None:
            self.values = values
            self.update()

        def paintEvent(self, _event: object) -> None:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor("#090f15"))
            painter.setPen(QPen(QColor("#1c2b3a"), 1.0))
            for line in range(9):
                y = line * self.height() / 8.0
                painter.drawLine(QPointF(0.0, y), QPointF(float(self.width()), y))
            if len(self.values) > 1:
                path = QPainterPath()
                for index, value in enumerate(self.values):
                    x = index * self.width() / (len(self.values) - 1)
                    y = (1.0 - value) * self.height()
                    if index == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                painter.setPen(QPen(QColor("#39bde8"), 1.5))
                painter.drawPath(path)

    def label(text: str, color: str = "#8fa4b7", bold: bool = False) -> QLabel:
        item = QLabel(text)
        item.setStyleSheet(f"color:{color};font-size:12px;" + ("font-weight:700;" if bold else ""))
        return item

    class PrototypeWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.canvas = SpectrumCanvas()
            root = QWidget()
            root.setStyleSheet("background:#0b1118;color:#e7edf3;")
            outer = QVBoxLayout(root)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            header = QFrame()
            header.setStyleSheet("background:#101821;border-bottom:1px solid #253646;")
            header_layout = QHBoxLayout(header)
            header_layout.addWidget(label("EH OPERATÖR KONSOLU", "#e7edf3", True))
            header_layout.addWidget(label("SİGMF KAYDI", "#39bde8"))
            header_layout.addWidget(label("100,000 MHz · 8 MS/s"))
            header_layout.addStretch(1)
            header_layout.addWidget(label("KAYIT OYNATMA", "#10b981", True))
            outer.addWidget(header)
            body = QHBoxLayout()
            body.setContentsMargins(0, 0, 0, 0)
            navigation = QFrame()
            navigation.setFixedWidth(164)
            navigation.setStyleSheet("background:#101821;border-right:1px solid #253646;")
            nav_layout = QVBoxLayout(navigation)
            for index, text in enumerate(("Sinyal Tespiti", "Parametreler", "Dinleme", "Yön Bulma", "Konum", "Sistem")):
                item = label(text, "#39bde8" if index == 0 else "#8fa4b7", index == 0)
                item.setFixedHeight(38)
                nav_layout.addWidget(item)
            nav_layout.addStretch(1)
            body.addWidget(navigation)
            center = QVBoxLayout()
            flow = QHBoxLayout()
            for index, text in enumerate(("Veri Kaynağı", "Ön İşleme", "FFT / Güç", "OS-CFAR", "Parametre")):
                block = label(text, "#e7edf3", True)
                block.setAlignment(Qt.AlignmentFlag.AlignCenter)
                block.setFixedHeight(34)
                block.setStyleSheet("background:#0e2a3a;color:#e7edf3;border:1px solid #39bde8;border-radius:4px;")
                flow.addWidget(block)
                if index < 4:
                    flow.addWidget(label("›"))
            center.addLayout(flow)
            title = label("Spektrum", "#e7edf3")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            center.addWidget(title)
            center.addWidget(self.canvas, 1)
            body.addLayout(center, 1)
            inspector = QFrame()
            inspector.setFixedWidth(286)
            inspector.setStyleSheet("background:#141f2a;border-left:1px solid #253646;")
            inspector_layout = QVBoxLayout(inspector)
            inspector_layout.addWidget(label("SEÇİLİ SİNYAL", "#8fa4b7", True))
            frequency = label("100,500 MHz", "#39bde8", True)
            frequency.setStyleSheet("color:#39bde8;font-size:24px;font-weight:700;")
            inspector_layout.addWidget(frequency)
            for caption, value in (("Durum", "Doğrulandı"), ("Bant Genişliği", "—"), ("SNR", "—"), ("Güç", "−2,2 dBFS"), ("Kaynak", "SigMF kaydı")):
                row = QHBoxLayout(); row.addWidget(label(caption)); row.addStretch(1); row.addWidget(label(value, "#e7edf3", True)); inspector_layout.addLayout(row)
            inspector_layout.addStretch(1)
            body.addWidget(inspector)
            outer.addLayout(body, 1)
            self.setCentralWidget(root)

    started = time.perf_counter()
    app = QApplication.instance() or QApplication(["app-e-widgets"])
    install_ui_font(app)
    window = PrototypeWindow()
    window.resize(1280, 720)
    window.show()
    app.processEvents()
    startup_ms = (time.perf_counter() - started) * 1000.0
    for index in range(WARMUP_UPDATES):
        window.canvas.set_values(frames[index % len(frames)])
        window.canvas.repaint()
        app.processEvents()
    timings: list[float] = []
    for index in range(MEASURED_UPDATES):
        before = time.perf_counter()
        window.canvas.set_values(frames[index % len(frames)])
        window.canvas.repaint()
        app.processEvents()
        timings.append((time.perf_counter() - before) * 1000.0)
    image = window.grab()
    if screenshot is not None and not image.save(str(screenshot), "PNG"):
        raise RuntimeError("Qt Widgets prototype screenshot could not be saved")
    payload = {
        "startup_ms": startup_ms,
        "update_median_ms": statistics.median(timings),
        "update_p95_ms": percentile(timings, 0.95),
        "update_max_ms": max(timings),
        "updates": len(timings),
        "image_width": image.width(),
        "image_height": image.height(),
        "rss_mib": current_rss_mib(),
    }
    window.close()
    return payload


def qml_worker(frames: list[list[float]], screenshot: Path | None) -> dict[str, object]:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView

    started = time.perf_counter()
    app = QGuiApplication.instance() or QGuiApplication(["app-e-qml"])
    install_ui_font(app)
    view = QQuickView()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile(str(QML_PATH)))
    if view.status() is QQuickView.Status.Error:
        raise RuntimeError("QML prototype could not be loaded")
    view.resize(1280, 720)
    view.show()
    app.processEvents()
    startup_ms = (time.perf_counter() - started) * 1000.0
    root = view.rootObject()
    if root is None:
        raise RuntimeError("QML prototype has no root object")
    for index in range(WARMUP_UPDATES):
        root.setProperty("spectrumValues", frames[index % len(frames)])
        root.setProperty("sequenceNumber", index)
        app.processEvents()
        view.grabWindow()
    timings: list[float] = []
    image = None
    for index in range(MEASURED_UPDATES):
        before = time.perf_counter()
        root.setProperty("spectrumValues", frames[index % len(frames)])
        root.setProperty("sequenceNumber", index)
        app.processEvents()
        image = view.grabWindow()
        timings.append((time.perf_counter() - before) * 1000.0)
    if image is None or image.isNull():
        raise RuntimeError("QML prototype did not render an image")
    if screenshot is not None and not image.save(str(screenshot), "PNG"):
        raise RuntimeError("QML prototype screenshot could not be saved")
    payload = {
        "startup_ms": startup_ms,
        "update_median_ms": statistics.median(timings),
        "update_p95_ms": percentile(timings, 0.95),
        "update_max_ms": max(timings),
        "updates": len(timings),
        "image_width": image.width(),
        "image_height": image.height(),
        "rss_mib": current_rss_mib(),
    }
    view.close()
    return payload


def worker(toolkit: str, screenshot: Path | None) -> int:
    frames = input_frames()
    payload = widget_worker(frames, screenshot) if toolkit == "widgets" else qml_worker(frames, screenshot)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def aggregate(runs: list[dict[str, object]]) -> dict[str, float]:
    keys = ("startup_ms", "update_median_ms", "update_p95_ms", "update_max_ms", "rss_mib")
    return {f"median_{key}": float(statistics.median(float(run[key]) for run in runs)) for key in keys}


def evaluate(document: dict[str, object]) -> dict[str, object]:
    widgets = document.get("qt_widgets")
    quick = document.get("qt_quick_qml")
    if not isinstance(widgets, dict) or not isinstance(quick, dict):
        raise ValueError("both toolkit records are required")
    widget_runs = widgets.get("runs")
    quick_runs = quick.get("runs")
    if not isinstance(widget_runs, list) or not isinstance(quick_runs, list):
        raise ValueError("run arrays are required")
    if len(widget_runs) != RUN_COUNT or len(quick_runs) != RUN_COUNT:
        raise ValueError("exactly five runs per toolkit are required")
    for run in widget_runs + quick_runs:
        if not isinstance(run, dict):
            raise ValueError("run record must be an object")
        if run.get("updates") != MEASURED_UPDATES or run.get("image_width") != 1280 or run.get("image_height") != 720:
            raise ValueError("render dimensions or update count changed")
    widget_summary = aggregate(widget_runs)
    quick_summary = aggregate(quick_runs)
    quick_p95 = quick_summary["median_update_p95_ms"]
    widget_p95 = widget_summary["median_update_p95_ms"]
    gates = {
        "qml_startup_below_2000_ms": quick_summary["median_startup_ms"] < 2000.0,
        "qml_update_within_10_hz_budget": quick_p95 < TARGET_UPDATE_PERIOD_MS,
        "qml_update_not_over_four_times_widgets": quick_p95 <= max(20.0, widget_p95 * 4.0),
    }
    qualified = all(gates.values())
    return {
        "status": "passed" if qualified else "failed",
        "qt_widgets": widget_summary,
        "qt_quick_qml": quick_summary,
        "gates": gates,
        "selected_presentation": "Qt Quick/QML" if qualified else "Qt Widgets",
        "application_backend": "Python/PySide6",
        "full_cpp_rewrite": False,
    }


def run_toolkit(toolkit: str, screenshot: Path) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_QUICK_BACKEND"] = "software"
    environment["PYTHONIOENCODING"] = "utf-8"
    for _ in range(RUN_COUNT):
        process = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", toolkit, "--screenshot", str(screenshot)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if process.returncode:
            raise RuntimeError(process.stdout + process.stderr)
        runs.append(json.loads(process.stdout.strip().splitlines()[-1]))
    return runs


def write_evidence() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    widgets_image = OUT / "qt-widgets-prototype.png"
    quick_image = OUT / "qt-quick-prototype.png"
    document: dict[str, object] = {
        "schema_version": 1,
        "package": "APP-E",
        "scope": "presentation_technology_comparison",
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "qt": qVersion(),
            "qt_library_path": QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath),
            "qpa_platform": "offscreen",
            "qt_quick_backend": "software",
        },
        "input": {
            "metadata": INPUT_META.relative_to(ROOT).as_posix(),
            "data": INPUT_DATA.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(INPUT_DATA.read_bytes()).hexdigest(),
            "source_frames": 4,
            "display_points": DISPLAY_POINTS,
        },
        "method": {
            "independent_process_runs_per_toolkit": RUN_COUNT,
            "warmup_updates": WARMUP_UPDATES,
            "measured_updates": MEASURED_UPDATES,
            "target_update_period_ms": TARGET_UPDATE_PERIOD_MS,
            "render_size": [1280, 720],
            "note": "Offscreen software rendering characterizes presentation overhead; it is not a GPU or target-hardware claim.",
        },
        "qt_widgets": {"runs": run_toolkit("widgets", widgets_image)},
        "qt_quick_qml": {"runs": run_toolkit("qml", quick_image)},
    }
    document["screenshots"] = {
        "qt_widgets": {"file": widgets_image.name, "sha256": hashlib.sha256(widgets_image.read_bytes()).hexdigest()},
        "qt_quick_qml": {"file": quick_image.name, "sha256": hashlib.sha256(quick_image.read_bytes()).hexdigest()},
    }
    document["evaluation"] = evaluate(document)
    EVIDENCE.write_bytes(canonical_json_bytes(document))
    print(json.dumps(document["evaluation"], ensure_ascii=False, indent=2))
    return 0 if document["evaluation"]["status"] == "passed" else 1  # type: ignore[index]


def check_evidence() -> bool:
    try:
        document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        if document.get("schema_version") != 1 or document.get("package") != "APP-E":
            return False
        input_record = document["input"]
        if input_record["sha256"] != hashlib.sha256(INPUT_DATA.read_bytes()).hexdigest():
            return False
        screenshots = document["screenshots"]
        for record in screenshots.values():
            path = OUT / record["file"]
            if not path.is_file() or record["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
                return False
        observed = evaluate(document)
        return document.get("evaluation") == observed and observed["status"] == "passed"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--worker", choices=("widgets", "qml"))
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args(argv)
    if args.worker:
        return worker(args.worker, args.screenshot)
    if args.write:
        return write_evidence()
    passed = check_evidence()
    print(f"APP-E UI technology evidence: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
