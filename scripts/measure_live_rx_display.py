"""Physical RX/display timing evidence; never FPGA detection or RF accuracy acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import PySide6
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtQuick import QQuickWindow
from algorithms.p0 import find_native_channelizer_library
from app.operator_console.quick_application import build_quick_application

SOURCES = (
    "app/operator_console/live_ed.py", "app/operator_console/quick_view_model.py",
    "app/operator_console/spectral_display.py", "app/operator_console/quick_application.py",
    "app/operator_console/qml/Main.qml", "app/operator_console/qml/RxSurveyView.qml",
    "app/operator_console/rx_survey.py", "app/operator_console/survey_controller.py",
    "algorithms/p0/channelizer.py", "algorithms/p0/native_channelizer.py",
    "algorithms/p0/native/CMakeLists.txt", "algorithms/p0/native/channelizer_native.cpp",
    "algorithms/p0/transport.py", "algorithms/spectrum/dsp.py",
    "platforms/acquisition/continuous.py", "platforms/acquisition/windows_pipe.py",
    "scripts/measure_live_rx_display.py",
)


def main():
    parser = argparse.ArgumentParser(description="Gerçek HackRF alımı ve taze ekran güncellemesi ölçümü; TX yok")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=32768)
    parser.add_argument("--center-hz", type=int, default=104650000)
    parser.add_argument("--lna-db", type=int, default=0)
    parser.add_argument("--vga-db", type=int, default=0)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".zip").exists():
        parser.error("Var olan ölçümün üzerine yazılmaz.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    native_library = find_native_channelizer_library()
    if native_library is None:
        parser.error("8 MS/s kabulü için derlenmiş P0 yerel kanal seçici bulunamadı.")
    native_library_bytes = native_library.read_bytes()
    source_bytes = {name: (ROOT / name).read_bytes() for name in SOURCES}
    app, engine, view = build_quick_application(["physical-rx-display-measurement"])
    window = engine.rootObjects()[0]
    window.setWidth(args.width)
    window.setHeight(args.height)
    window.setProperty("rfSearchMode", False)
    window.setProperty("sourcePanelOpen", False)
    window.setTitle("Gerçek RX görüntü ölçümü · FPGA tespiti kapalı")
    view.setSourceMode("hackrf")
    view.probeHackrf()
    deadline = time.perf_counter() + 12
    while view.busy and time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(.002)
    if not view.hackrfReady:
        view.shutdown()
        raise RuntimeError(view.errorMessage or "HackRF hazır değil.")
    submitted, presented = [], []
    started = time.perf_counter()

    def sample(destination):
        if view.liveSessionActive and view._live_received_at:
            sequence = view._frame_index
            if not destination or destination[-1][0] != sequence:
                now = time.perf_counter()
                destination.append((sequence, now - started, (now - view._live_received_at) * 1000))

    view.spectrumChanged.connect(lambda: sample(submitted))
    window.frameSwapped.connect(lambda: sample(presented))
    view.startRXPreview(args.center_hz, args.lna_db, args.vga_db, args.frames)
    session = view._live_session
    if session is None:
        view.shutdown()
        raise RuntimeError(view.errorMessage or "RX oturumu başlatılamadı.")
    loop, watch = QEventLoop(), QTimer()
    watch.setInterval(50)
    watch.timeout.connect(lambda: loop.quit() if not view.busy else None)
    watch.start()
    QTimer.singleShot(int((args.frames * 4096 / 2e6 * 1.5 + 20) * 1000), loop.quit)
    # No synchronous grabWindow inside the threaded render loop: it can block
    # Python QQuickPaintedItem callbacks and would contaminate RX timing.
    loop.exec()
    watch.stop()
    timed_out = view.busy
    error = view.errorMessage
    display_bins = int(view.spectralDisplay.latest.size)
    display_center_hz = float(view.spectrumCenterFrequencyHz)
    display_sample_rate_hz = float(view.spectrumSampleRateHz)
    fpga_sample_rate_hz = float(view.sampleRateHz)
    expected_input_center_hz = float(session.configuration.input_center_frequency_hz)
    view.shutdown()
    diagnostics = session.last_diagnostics
    interval = np.diff([item[1] for item in presented]) * 1000
    age = [item[2] for item in presented]
    rate = (len(presented) - 1) / (presented[-1][1] - presented[0][1]) if len(presented) > 1 else 0.0
    p95_interval = float(np.percentile(interval, 95)) if len(interval) else None
    p95_age = float(np.percentile(age, 95)) if age else None
    stats = diagnostics.get("hackrf_statistics") or {}
    checks = {
        "session_completed": not timed_out and not error and diagnostics.get("completed_frames") == args.frames,
        "zero_usb_overruns": stats.get("overruns") == 0,
        "at_least_30_fresh_updates_per_second": rate >= 30.0,
        "presentation_interval_p95_at_most_50ms": p95_interval is not None and p95_interval <= 50,
        "host_receive_to_present_p95_at_most_150ms": p95_age is not None and p95_age <= 150,
        "no_fpga_detection_claim": not view.liveDetectionEnabled and not view.detections and not view._live_response_at,
        "wide_rx_spectrum_is_16384_bins_at_8_msps": display_bins == 16_384 and display_sample_rate_hz == 8_000_000,
        "wide_rx_axis_uses_actual_input_center": display_center_hz == expected_input_center_hz,
        "fpga_processing_rate_preserved_at_2_msps": fpga_sample_rate_hz == 2_000_000,
        "native_cpp_channelizer_used": diagnostics.get("channelizer_backend") == "native-cpp",
        "native_library_unchanged_during_measurement": native_library.read_bytes() == native_library_bytes,
        "sources_unchanged_during_measurement": all((ROOT / name).read_bytes() == data for name, data in source_bytes.items()),
    }
    report = {
        "schema": "physical-rx-display-v2", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "physical_RX_display_only_not_FPGA_detection_or_detection_probability",
        "status": "passed" if all(checks.values()) else "failed", "checks": checks,
        "transmit_enabled": False, "fpga_enabled": False,
        "configuration": {key: value for key, value in vars(args).items() if key != "output"},
        "runtime": {"python": sys.version, "pyside6": PySide6.__version__, "numpy": np.__version__},
        "view_size": [window.width(), window.height()], "diagnostics": diagnostics,
        "display": {"bins": display_bins, "center_frequency_hz": display_center_hz,
                    "sample_rate_hz": display_sample_rate_hz,
                    "fpga_processing_sample_rate_hz": fpga_sample_rate_hz},
        "error": error, "timed_out": timed_out, "fresh_updates_per_second": rate,
        "render_interval_p95_ms": p95_interval, "host_receive_to_present_p95_ms": p95_age,
        "render_interval_max_ms": float(max(interval)) if len(interval) else None,
        "host_receive_to_present_max_ms": max(age, default=None),
        "sample_columns": ["sequence", "seconds_since_start", "host_receive_age_ms"],
        "submitted": submitted, "presented": presented,
        "native_channelizer": {
            "archive_path": f"native/{native_library.name}",
            "source_path": str(native_library.resolve()),
            "sha256": hashlib.sha256(native_library_bytes).hexdigest(),
        },
        "limits": ["Ortamın yalnız gürültü olduğu varsayılmaz; Pd/Pfa ölçülmez.",
                   "Yaşın başlangıcı bilgisayarda I/Q bloğunun alınmasıdır; RF anten gecikmesi ölçülmez.",
                   "Görüntü 15 DSP karesinde bir seçilir; bütün I/Q kareleri kanal seçicide işlenir.",
                   "Başlangıç ve bitiş dışında taze kare sunum hızı ölçülür; tekrar çizimler sayılmaz."],
        "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in source_bytes.items()},
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(args.output.with_suffix(".zip"), "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in source_bytes.items():
            archive.writestr(name, data)
        archive.writestr(f"native/{native_library.name}", native_library_bytes)
        archive.writestr("measurement.json", args.output.read_bytes())
    print(json.dumps({key: report[key] for key in ("status", "checks", "fresh_updates_per_second",
        "render_interval_p95_ms", "host_receive_to_present_p95_ms", "error")}, ensure_ascii=False), flush=True)
    window.close()
    engine.deleteLater()
    app.processEvents()
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
