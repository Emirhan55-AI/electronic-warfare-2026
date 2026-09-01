"""Repeatable recorded-I/Q display benchmark; never a live RF acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import PySide6
from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtQuick import QQuickWindow
from app.operator_console.quick_application import build_quick_application


def main() -> None:
    parser = argparse.ArgumentParser(description="Kayıtlı I/Q ile spektrum çizim ölçümü")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app, engine, view = build_quick_application(["display-measurement"])
    window = engine.rootObjects()[0]
    window.setWidth(args.width)
    window.setHeight(args.height)
    window.setTitle("Kayıtlı I/Q çizim ölçümü — RF kabulü değildir")
    window.setProperty("rfSearchMode", False)
    window.setProperty("sourcePanelOpen", False)
    fixture = ROOT / "datasets/fixtures/phase01/known-tone-ci8.sigmf-meta"
    view.openSigmf(str(fixture))
    ready = time.perf_counter() + 10
    while (view.busy or not view.spectrumValues) and time.perf_counter() < ready:
        app.processEvents()
        time.sleep(.002)
    if not view.spectrumValues:
        raise RuntimeError("Kayıtlı I/Q görüntüsü hazırlanamadı.")
    spectrum = view._last_result.spectrum
    # Same finite recorded frame for both renderers; no detector or RF claims.
    for _ in range(128):
        view._update_spectrum_result(spectrum)
    warm = QEventLoop()
    QTimer.singleShot(500, warm.quit)
    warm.exec()
    runs = []
    for run_index in range(args.runs):
        state = {"submitted": 0, "rendered": 0, "last_drawn": 0}
        heartbeat_gaps = []
        previous = time.perf_counter()

        def tick():
            state["submitted"] += 1
            view._update_spectrum_result(spectrum)

        def swapped():
            if state["submitted"] > state["last_drawn"]:
                state["rendered"] += 1
                state["last_drawn"] = state["submitted"]

        def heartbeat():
            nonlocal previous
            current = time.perf_counter()
            heartbeat_gaps.append((current - previous) * 1000)
            previous = current

        timer, beat = QTimer(), QTimer()
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.timeout.connect(tick)
        beat.timeout.connect(heartbeat)
        window.frameSwapped.connect(swapped)
        timer.start(33)
        beat.start(10)
        loop = QEventLoop()
        start = time.perf_counter()
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        elapsed = time.perf_counter() - start
        timer.stop()
        beat.stop()
        window.frameSwapped.disconnect(swapped)
        runs.append({**state, "elapsed_seconds": elapsed,
                     "rendered_updates_per_second": state["rendered"] / elapsed,
                     "heartbeat_max_ms": max(heartbeat_gaps, default=0),
                     "heartbeat_p95_ms": float(np.percentile(heartbeat_gaps, 95))})
        print(json.dumps(runs[-1]), flush=True)
    screenshot = window.grabWindow()
    screenshot.save(str(args.output / "display.png"))
    names = ["app/operator_console/qml/Main.qml", "app/operator_console/quick_view_model.py",
             "app/operator_console/quick_application.py", "app/operator_console/spectral_display.py",
             "scripts/measure_detection_display.py"]
    report = {"scope": "recorded_IQ_rendering_only", "target_updates_per_second": 1000 / 33,
              "size": [window.width(), window.height()], "requested_size": [args.width, args.height],
              "image_pixels": [screenshot.width(), screenshot.height()],
              "environment": {"python": sys.version, "qt": PySide6.__version__,
                              "numpy": np.__version__, "platform": app.platformName()}, "runs": runs,
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in names if (ROOT / name).exists()},
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest()}
    (args.output / "measurement.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    view.shutdown()
    window.close()
    engine.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
