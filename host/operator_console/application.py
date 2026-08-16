"""Application bootstrap and bounded spectrum/detection/parameter smoke entry point."""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEventLoop, QLocale, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from reference.pipeline import ProcessingProfile, VerifiedProfileBinding
from host.acquisition import EDRXDeviceConfig, HackRFBackend
from .audio_playback import AudioPlayback

from .controller import OperatorController
from .main_window import MainWindow


ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = Path(__file__).with_name("theme.qss")


def _ui_font() -> QFont:
    """Resolve Segoe UI, explicitly registering the Windows font for offscreen Qt."""
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
    return QFont(family, 10)


@dataclass(frozen=True)
class PlaybackBenchmarkResult:
    target_fps: int
    rendered_frames: int
    achieved_fps: float
    maximum_heartbeat_gap_ms: float
    waterfall_rows: int
    maximum_concurrent_tasks: int
    maximum_pending_intents: int
    active_tasks_after_stop: int
    feature_history_bytes: int


def build_application(
    argv: list[str] | None = None,
    *,
    profile: ProcessingProfile | None = None,
    verified_binding: VerifiedProfileBinding | None = None,
    acquisition_backend: HackRFBackend | None = None,
    ed_rx_config: EDRXDeviceConfig | None = None,
    test_backend_factory: Callable[[], HackRFBackend] | None = None,
    audio_playback: AudioPlayback | None = None,
) -> tuple[QApplication, MainWindow, OperatorController]:
    app = QApplication.instance() or QApplication(argv or [])
    app.setApplicationName("Elektronik Harp Operatör Konsolu")
    app.setOrganizationName("TEKNOFEST 2026 Elektronik Harp")
    app.setStyle("Fusion")
    app.setFont(_ui_font())
    QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))
    app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))
    window = MainWindow()
    controller_kwargs: dict[str, object] = {
        "profile": profile,
        "verified_binding": verified_binding,
        "acquisition_backend": acquisition_backend,
        "ed_rx_config": ed_rx_config,
        "audio_playback": audio_playback,
    }
    if test_backend_factory is not None:
        controller_kwargs["test_backend_factory"] = test_backend_factory
    controller = OperatorController(window, **controller_kwargs)
    app.aboutToQuit.connect(controller.close)
    return app, window, controller


def run_playback_benchmark(
    window: MainWindow,
    controller: OperatorController,
    *,
    target_fps: int,
    duration_seconds: float,
) -> PlaybackBenchmarkResult:
    """Measure recorded-frame UI cadence without claiming live-RF throughput."""
    if controller.source is None or controller.last_result is None:
        raise RuntimeError("a loaded source and initial result are required")
    if not 1 <= target_fps <= 30 or duration_seconds <= 0.5:
        raise ValueError("benchmark target or duration is outside the supported range")

    render_times: list[float] = []
    heartbeat_times: list[float] = [time.perf_counter()]

    def record_frame(_: int, __: float) -> None:
        render_times.append(time.perf_counter())

    def record_heartbeat() -> None:
        heartbeat_times.append(time.perf_counter())

    heartbeat = QTimer()
    heartbeat.setInterval(20)
    heartbeat.timeout.connect(record_heartbeat)
    controller.frame_rendered.connect(record_frame)
    window.spectrum_view.clear_history()
    window.speed_spin.setValue(target_fps)
    heartbeat.start()
    controller.start()
    loop = QEventLoop()
    QTimer.singleShot(round(duration_seconds * 1000), loop.quit)
    loop.exec()
    controller.pause()
    heartbeat.stop()
    controller.frame_rendered.disconnect(record_frame)

    drain_deadline = time.perf_counter() + 1.0
    app = QApplication.instance()
    while controller.active_task_count and time.perf_counter() < drain_deadline:
        assert app is not None
        app.processEvents()
        time.sleep(0.001)

    if len(render_times) >= 2:
        intervals = [current - previous for previous, current in zip(render_times, render_times[1:])]
        achieved_fps = 1.0 / statistics.median(intervals)
    else:
        achieved_fps = 0.0
    gaps = [
        (current - previous) * 1000.0
        for previous, current in zip(heartbeat_times, heartbeat_times[1:])
    ]
    maximum_gap = max(gaps, default=duration_seconds * 1000.0)
    return PlaybackBenchmarkResult(
        target_fps=target_fps,
        rendered_frames=len(render_times),
        achieved_fps=achieved_fps,
        maximum_heartbeat_gap_ms=maximum_gap,
        waterfall_rows=window.spectrum_view.waterfall_count,
        maximum_concurrent_tasks=controller.max_concurrent_tasks,
        maximum_pending_intents=controller.max_pending_intents,
        active_tasks_after_stop=controller.active_task_count,
        feature_history_bytes=(
            controller.runtime_pipeline.parameters.history.payload_bytes
            if controller.runtime_pipeline.parameters is not None
            else 0
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Türkçe SigMF spektrum inceleme uygulaması")
    parser.add_argument("--smoke-test", action="store_true", help="pencereyi kısa süre açıp kapat")
    args = parser.parse_args(argv)
    app, window, _ = build_application([sys.argv[0]])
    window.show()
    if args.smoke_test:
        QTimer.singleShot(200, app.quit)
    return app.exec()
