"""Bu laboratuvar koşusunda BÂZ'ı hazırlayıp 1766 MHz alımını başlatır."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

import numpy as np
from PySide6.QtCore import QTimer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.operator_console.quick_application import build_quick_application


app, engine, view = build_quick_application(
    ["baz-live-1766"],
    auto_probe_hackrf=True,
    show_startup_intro=False,
)
window = engine.rootObjects()[0]
window.setTitle("BÂZ · 1766 MHz kontrollü sinyal tespiti")
LOG_PATH = Path(__file__).with_name("live-state-run2.jsonl")
SCREEN_DIR = Path(__file__).with_name("live-state-run2-screens")
SCREEN_DIR.mkdir(exist_ok=True)
LOG_PATH.write_text("", encoding="utf-8")
state = {"started": False, "signature": None, "last_heartbeat": 0.0, "screen_index": 0}
timer = QTimer()
timer.setInterval(250)


def serializable_rows() -> list[dict[str, object]]:
    keys = (
        "eventId",
        "title",
        "frequency",
        "lowerFrequencyHz",
        "upperFrequencyHz",
        "peakFrequencyHz",
        "stateKey",
        "observed",
        "held",
        "verificationKey",
        "contrast",
    )
    return [{key: row.get(key) for key in keys if key in row} for row in view.detections]


def record(event: str, *, capture: bool = False) -> None:
    spectrum = np.asarray(view.spectralDisplay.latest, dtype=np.float64)
    spectrum_summary: dict[str, object] = {"bins": int(spectrum.size)}
    if spectrum.size and view.spectrumSampleRateHz > 0:
        frequencies = (
            view.spectrumCenterFrequencyHz
            + (np.arange(spectrum.size) / max(1, spectrum.size - 1) - 0.5)
            * view.spectrumSampleRateHz
        )
        target_mask = (frequencies >= 1_765_500_000) & (frequencies <= 1_766_500_000)
        peak_index = int(np.argmax(spectrum))
        target_indices = np.flatnonzero(target_mask)
        target_index = int(target_indices[np.argmax(spectrum[target_mask])]) if target_indices.size else peak_index
        median_db = float(np.median(spectrum))
        spectrum_summary.update(
            {
                "median_dbfs": median_db,
                "max_dbfs": float(spectrum[peak_index]),
                "peak_frequency_hz": float(frequencies[peak_index]),
                "target_max_dbfs": float(spectrum[target_index]),
                "target_peak_frequency_hz": float(frequencies[target_index]),
                "target_margin_db": float(spectrum[target_index] - median_db),
            }
        )
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "monotonic_seconds": time.monotonic(),
        "event": event,
        "center_hz": view.spectrumCenterFrequencyHz,
        "sample_rate_hz": view.spectrumSampleRateHz,
        "active_count": view.activeDetectionCount,
        "stable_count": view.stableDetectionCount,
        "verification_active": view.fixedVerificationActive,
        "status": view.statusMessage,
        "health": view.liveHealthText,
        "error": view.errorMessage,
        "detections": serializable_rows(),
        "spectrum": spectrum_summary,
    }
    with LOG_PATH.open("a", encoding="utf-8") as output:
        output.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(payload, ensure_ascii=False, default=str), flush=True)
    # Canlı RX sırasında eşzamanlı ``grabWindow`` Qt çizim iş parçacığını
    # durdurabildiği için olay kaydı yalnız JSONL üzerinden tutulur.


def poll() -> None:
    if view.hackrfReady and not view.busy and not state["started"]:
        print(
            json.dumps(
                {
                    "event": "hardware_ready",
                    "status": view.statusMessage,
                    "receiver": getattr(view, "_active_receiver_serial", None),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        view.startLiveEDSession(1_766_000_000, 24, 24, 878_906)
        state["started"] = True
        return
    if state["started"] and view.liveSessionActive and view.busy:
        rows = serializable_rows()
        signature = json.dumps(
            {
                "active": view.activeDetectionCount,
                "stable": view.stableDetectionCount,
                "verification": view.fixedVerificationActive,
                "rows": rows,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        now = time.monotonic()
        if state["signature"] is None:
            state["signature"] = signature
            state["last_heartbeat"] = now
            record("rx_started", capture=True)
        elif signature != state["signature"]:
            state["signature"] = signature
            state["last_heartbeat"] = now
            record("detection_state_changed", capture=True)
        elif now - state["last_heartbeat"] >= 5.0:
            state["last_heartbeat"] = now
            record("heartbeat")
        return
    if view.errorMessage:
        print(
            json.dumps(
                {
                    "event": "error",
                    "message": view.errorMessage,
                    "status": view.statusMessage,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        timer.stop()


timer.timeout.connect(poll)
timer.start()
raise SystemExit(app.exec())
