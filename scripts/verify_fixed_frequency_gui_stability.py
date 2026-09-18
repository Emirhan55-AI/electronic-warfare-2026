#!/usr/bin/env python3
"""Run one bounded physical fixed-frequency RX session and record GUI health.

This verifier never starts or controls a transmitter.  It exercises the real
HackRF -> PC -> FPGA -> QML path and records detection, transport, catalogue,
and Qt event-loop timing in one JSON artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import numpy as np
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.operator_console.live_ed import LiveEDSessionResult
from app.operator_console.quick_application import QML_PATH
from app.operator_console.quick_view_model import OperatorViewModel
from app.operator_console.spectral_display import SpectrumTrace, WaterfallImage


HASHED_SOURCES = (
    ROOT / "app/operator_console/automatic_parameter.py",
    ROOT / "app/operator_console/live_ed.py",
    ROOT / "app/operator_console/parameter_catalog.py",
    ROOT / "app/operator_console/quick_runtime.py",
    ROOT / "app/operator_console/quick_view_model.py",
    ROOT / "app/operator_console/qml/Main.qml",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timing_summary(values_ms: list[float]) -> dict[str, float | int]:
    if not values_ms:
        return {"samples": 0, "p50_ms": 0.0, "p95_ms": 0.0, "maximum_ms": 0.0,
                "over_100_ms": 0}
    values = np.asarray(values_ms, dtype=np.float64)
    return {
        "samples": int(values.size),
        "p50_ms": float(np.percentile(values, 50)),
        "p95_ms": float(np.percentile(values, 95)),
        "maximum_ms": float(np.max(values)),
        "over_100_ms": int(np.count_nonzero(values > 100.0)),
    }


class CapturingViewModel(OperatorViewModel):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured_result: LiveEDSessionResult | None = None
        self.captured_error: dict[str, str] | None = None
        self.retry_errors: list[dict[str, str]] = []
        self.captured_session_diagnostics: dict[str, object] = {}

    def _capture_diagnostics(self) -> None:
        session = self._live_session
        self.captured_session_diagnostics = dict(
            getattr(session, "last_diagnostics", {}) or {}
        )

    def _live_completed(self, generation: int, result: object, elapsed: float) -> None:
        self._capture_diagnostics()
        if isinstance(result, LiveEDSessionResult):
            self.captured_result = result
        super()._live_completed(generation, result, elapsed)

    def _live_failed(self, generation: int, code: str, detail: str) -> None:
        self._capture_diagnostics()
        attempted = {"code": code, "detail": detail}
        super()._live_failed(generation, code, detail)
        if self._live_session is None:
            self.captured_error = attempted
        else:
            self.retry_errors.append(attempted)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--center-hz", type=int, default=820_000_000)
    parser.add_argument("--lna-db", type=int, default=16)
    parser.add_argument("--vga-db", type=int, default=14)
    parser.add_argument("--frames", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    qmlRegisterType(SpectrumTrace, "Teknofest.Display", 1, 0, "SpectrumTrace")
    qmlRegisterType(WaterfallImage, "Teknofest.Display", 1, 0, "WaterfallImage")
    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    view = CapturingViewModel(parameter_catalog_path=args.catalog)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("operatorViewModel", view)
    engine.rootContext().setContextProperty("startupIntroRequested", False)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        raise RuntimeError("Operatör QML arayüzü yüklenemedi.")

    started = time.perf_counter()
    session_started: float | None = None
    session_finished: float | None = None
    last_heartbeat: float | None = None
    heartbeat_ms: list[float] = []
    phase = "probe"
    timed_out = False

    heartbeat = QTimer()
    heartbeat.setInterval(20)

    def on_heartbeat() -> None:
        nonlocal last_heartbeat
        now = time.perf_counter()
        if phase == "run" and last_heartbeat is not None:
            heartbeat_ms.append((now - last_heartbeat) * 1000.0)
        last_heartbeat = now

    heartbeat.timeout.connect(on_heartbeat)
    heartbeat.start()

    poller = QTimer()
    poller.setInterval(25)

    def finish() -> None:
        heartbeat.stop()
        poller.stop()
        app.quit()

    def poll() -> None:
        nonlocal phase, session_started, session_finished, last_heartbeat, timed_out
        now = time.perf_counter()
        if now - started > args.timeout_seconds:
            timed_out = True
            view.stopLiveEDSession()
            finish()
            return
        if phase == "probe" and not view.busy:
            if not view.hackrfReady:
                finish()
                return
            session_started = now
            last_heartbeat = now
            phase = "run"
            view.startLiveEDSession(
                args.center_hz, args.lna_db, args.vga_db, args.frames
            )
            return
        if phase == "run" and not view.busy:
            session_finished = now
            phase = "catalog"
        if phase == "catalog" and view._parameter_catalog_pending_outcomes == 0:
            finish()

    poller.timeout.connect(poll)
    poller.start()
    QTimer.singleShot(0, view.probeHackrf)
    app.exec()

    result = view.captured_result
    report = {
        "schema": "fixed-frequency-gui-stability-v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "rx_only_verifier": True,
        "configuration": {
            "center_hz": args.center_hz,
            "lna_db": args.lna_db,
            "vga_db": args.vga_db,
            "requested_frames": args.frames,
            "qt_platform": os.environ.get("QT_QPA_PLATFORM"),
        },
        "outcome": {
            "timed_out": timed_out,
            "error": view.captured_error,
            "status_message": view.statusMessage,
            "source_state": view.sourceState,
            "completed_frames": result.completed_frames if result else None,
            "frames_per_second": result.frames_per_second if result else None,
            "hackrf_statistics": asdict(result.hackrf_statistics) if result else None,
            "session_elapsed_seconds": (
                session_finished - session_started
                if session_started is not None and session_finished is not None else None
            ),
            "phase": phase,
            "worker_threads_active": view._pool.activeThreadCount(),
        },
        "qt_heartbeat": _timing_summary(heartbeat_ms),
        "session_diagnostics": view.captured_session_diagnostics,
        "gain_retry_errors": view.retry_errors,
        "automatic_parameter_status": view.automaticParameterStatus,
        "parameter_catalog_rows": list(view.parameterHistory),
        "detections": list(view._live_detection_rows),
        "event_log": list(view._event_log),
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
            for path in HASHED_SOURCES
        },
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    view.shutdown()
    return 0 if result is not None and view.captured_error is None and not timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
