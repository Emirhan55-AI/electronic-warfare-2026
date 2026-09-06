"""KTR-4.1 / KTR-4.1-OPS-B0: gerçek RX, FPGA ve Qt görüntüsünü birlikte ölçer.

RF doğruluğu veya ST-06 kapanış kararı üretmez. Ham başarısızlıklar da saklanır.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PySide6.QtCore import QEventLoop, QTimer, Qt
from algorithms.p0 import find_native_channelizer_library
from app.operator_console.live_ed import LiveEDSession
from app.operator_console.quick_application import build_quick_application


def distribution(values):
    return ({"samples": len(values), "p50_ms": float(np.percentile(values, 50)),
             "p95_ms": float(np.percentile(values, 95)),
             "p99_ms": float(np.percentile(values, 99)), "maximum_ms": float(max(values))}
            if len(values) else {"samples": 0})


class ObservedSession(LiveEDSession):
    """Gerçek alım/taşıma işleyişini korur; sonuç ve hata nesnesini saklar."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observation = {}
        self.stream_observed = None
        original_factory = self._stream_factory

        def create_stream(*a, **kw):
            self.stream_observed = original_factory(*a, **kw)
            return self.stream_observed

        self._stream_factory = create_stream

    def run(self, snapshot_handler=None):
        started = time.perf_counter()
        try:
            result = super().run(snapshot_handler)
            self.observation["result"] = asdict(result)
            return result
        except Exception as exc:
            self.observation["error"] = {"code": getattr(exc, "code", type(exc).__name__),
                                         "detail": str(exc)}
            raise
        finally:
            self.observation["elapsed_seconds"] = time.perf_counter() - started
            self.observation["diagnostics"] = self.last_diagnostics
            self.observation["transport"] = asdict(self._transport.stats)
            stats = getattr(self.stream_observed, "statistics", None)
            self.observation["rx"] = asdict(stats) if stats is not None else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--board-metadata", type=Path, required=True,
                        help="Bu oturumda bağımsız kimlik denetimiyle alınmış kart JSON kaydı")
    parser.add_argument("--frames", type=int, default=58_594)
    parser.add_argument("--center-hz", type=int, default=104_650_000)
    parser.add_argument("--lna-db", type=int, default=0)
    parser.add_argument("--vga-db", type=int, default=0)
    parser.add_argument("--cancel-after-seconds", type=float, default=0)
    parser.add_argument("--external-transmitter-state", default="operator_declared_off",
                        choices=["operator_declared_off", "operator_controlled_on_off"],
                        help="Harici verici durumu; alıcı yazılımının TX yetkisi değildir")
    parser.add_argument("--keep-visible", action="store_true",
                        help="Ölçüm penceresini üstte tutar; ürün ayarlarını değiştirmez")
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".zip").exists():
        parser.error("Var olan ölçümün üzerine yazılmaz.")
    board_bytes = args.board_metadata.read_bytes()
    board = json.loads(board_bytes)
    if not board.get("identity_verified") or not board.get("service_sha256"):
        parser.error("Kart kimliği ve çalışan hizmet özeti doğrulanmalıdır.")
    native = find_native_channelizer_library()
    if native is None:
        parser.error("Yerel kanal seçici bulunamadı.")
    native_bytes = native.read_bytes()
    names = subprocess.check_output(
        ["git", "ls-files", "app", "algorithms", "platforms", "config", "requirements"],
        cwd=ROOT, text=True, encoding="utf-8").splitlines()
    sources = {name: (ROOT / name).read_bytes() for name in names
               if Path(name).suffix in {".py", ".qml", ".json", ".cpp", ".h", ".txt", ".toml"}}
    sources[Path(__file__).resolve().relative_to(ROOT).as_posix()] = Path(__file__).read_bytes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": "live-gui-fpga-observation-v1",
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "requirements": ["KTR-4.1", "KTR-4.1-OPS-B0"],
              "external_transmitter_state": args.external_transmitter_state,
              "transmit_enabled": False, "rf_accuracy_acceptance": False,
              "ST06_complete": False, "board": board,
              "source_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in sources.items()},
              "native_sha256": hashlib.sha256(native_bytes).hexdigest(),
              "limits": ["Harici verici kapalı bilgisi operatör beyanıdır; ortam sessiz sayılmaz.",
                         "frameSwapped bildirimi fiziksel monitör/piksel gecikmesi değildir.",
                         "RX yaşı bilgisayarda I/Q alımından başlar; anten gecikmesi değildir.",
                         "FPGA bildirim yaşı GUI'ye aktarılan son yanıtın yaşıdır; RF ilk tespit gecikmesi değildir.",
                         "Kuyruk/işlem tanıları 16 karede bir örneklenir; kesin kuyruk tepesi ölçülmez.",
                         "Bütünlük başarısı bağımsız sürekli işlem kapasitesi veya hız payı kanıtı değildir."]}
    app, engine, view = build_quick_application(["live-gui-fpga-measurement"])
    window = engine.rootObjects()[0]
    window.setWidth(1440)
    window.setHeight(900)
    window.setProperty("rfSearchMode", False)
    window.setTitle("BÂZ · Gerçek alım ve FPGA görüntü ölçümü")
    window_closed = False

    def record_close():
        nonlocal window_closed
        window_closed = True

    window.closing.connect(record_close)
    if args.keep_visible:
        window.setFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        window.show()
    report["keep_visible"] = args.keep_visible
    sessions, submitted, presented, health = [], [], [], []
    started = time.perf_counter()

    def factory(*a, **kw):
        session = ObservedSession(*a, **kw)
        sessions.append(session)
        return session

    view._live_session_factory = factory

    def sample(destination):
        if view.liveSessionActive and view._live_received_at:
            sequence = view._frame_index
            if not destination or destination[-1][0] != sequence:
                now = time.perf_counter()
                destination.append([sequence, now - started, (now - view._live_received_at) * 1000])

    view.spectrumChanged.connect(lambda: sample(submitted))
    window.frameSwapped.connect(lambda: sample(presented))
    watch, progress, cancel = QTimer(), QTimer(), QTimer()
    timed_out = False
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        deadline = time.perf_counter() + 15
        while view.busy and time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(.002)
        if not view.hackrfReady:
            raise RuntimeError(view.errorMessage or "Alıcı ve FPGA hazır değil.")
        if not window.isVisible() or not window.isExposed():
            raise RuntimeError("Gerçek arayüz penceresi görünür değil.")
        started = time.perf_counter()
        view.startLiveEDSession(args.center_hz, args.lna_db, args.vga_db, args.frames)
        if not sessions or not view.liveSessionActive:
            raise RuntimeError(view.errorMessage or "FPGA oturumu başlamadı.")
        report["configuration"] = asdict(sessions[0].configuration)
        loop = QEventLoop()
        watch.setInterval(50)

        def poll():
            nonlocal timed_out
            now = time.perf_counter()
            health.append([now - started, view._frame_index,
                           (now - view._live_response_at) * 1000 if view._live_response_at else None,
                           window.isVisible(), window.isExposed(),
                           (now - started - presented[-1][1]) * 1000 if presented else (now - started) * 1000])
            if window_closed:
                report["measurement_error"] = "Operatör ölçüm penceresini kapattı."
                view.stopLiveEDSession()
                loop.quit()
            elif not view.busy:
                loop.quit()
            elif now - started > args.frames * 4096 / 2e6 * 1.5 + 30:
                timed_out = True
                view.stopLiveEDSession()
                loop.quit()

        watch.timeout.connect(poll)
        watch.start()
        progress.setInterval(10_000)
        progress.timeout.connect(lambda: print(json.dumps({"seconds": round(time.perf_counter()-started, 1),
            "display_sequence": view._frame_index, "fresh_presentations": len(presented),
            "fpga_response_observed": bool(view._live_response_at)}, ensure_ascii=False), flush=True))
        progress.start()
        if args.cancel_after_seconds > 0:
            cancel.setSingleShot(True)
            cancel.timeout.connect(view.stopLiveEDSession)
            cancel.start(int(args.cancel_after_seconds * 1000))
        loop.exec()
        report["ui_error"] = view.errorMessage
        report["fpga_response_observed"] = bool(view._live_response_at)
        report["fpga_enabled"] = view.liveDetectionEnabled
    except Exception as exc:
        report["measurement_error"] = str(exc)
    finally:
        watch.stop()
        progress.stop()
        cancel.stop()
        view.shutdown()
        report["timed_out"] = timed_out
        report["sessions"] = [s.observation for s in sessions]
        report["sample_columns"] = ["sequence", "seconds_since_start", "host_rx_age_ms"]
        report["submitted"], report["presented"] = submitted, presented
        report["health_columns"] = ["seconds", "display_sequence", "last_fpga_notification_age_ms", "visible", "exposed", "last_presentation_age_ms"]
        report["health"] = health
        report["presentation_interval"] = distribution(np.diff([r[1] for r in presented]) * 1000)
        report["host_rx_to_swap_notification"] = distribution([r[2] for r in presented])
        report["last_fpga_notification_age"] = distribution([r[2] for r in health if r[2] is not None])
        rate = ((len(presented)-1)/(presented[-1][1]-presented[0][1]) if len(presented)>1 else 0)
        report["fresh_presentations_per_second"] = rate
        report["presentations_per_full_session_second"] = len(presented) / health[-1][0] if health else 0
        report["last_presentation_age"] = distribution([r[5] for r in health])
        result = sessions[0].observation.get("result", {}) if len(sessions) == 1 else {}
        report["checks"] = {
            "full_single_fpga_session": bool(result.get("fpga_enabled")) and result.get("completed_frames") == args.frames,
            "actual_fpga_response": report.get("fpga_response_observed", False),
            "actual_preview_presented": bool(submitted) and bool(presented),
            "visible_throughout": bool(health) and all(r[3] and r[4] for r in health),
            "fresh_display_rate_at_least_30hz": rate >= 30,
            "full_session_display_rate_at_least_30hz": report["presentations_per_full_session_second"] >= 30,
            "no_presentation_stall_over_one_second": bool(health) and max(r[5] for r in health) <= 1000,
            "presentation_interval_p95_at_most_50ms": report["presentation_interval"].get("p95_ms", float("inf")) <= 50,
            "host_rx_age_p95_at_most_150ms": report["host_rx_to_swap_notification"].get("p95_ms", float("inf")) <= 150,
            "no_measurement_error": not report.get("measurement_error") and not report.get("ui_error") and not timed_out,
            "source_and_native_unchanged": all((ROOT/n).read_bytes() == b for n,b in sources.items()) and native.read_bytes() == native_bytes,
        }
        report["status"] = "passed" if all(report["checks"].values()) else "failed"
        raw = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        with args.output.open("xb") as output:
            output.write(raw)
        with zipfile.ZipFile(args.output.with_suffix(".zip"), "x", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("measurement.json", raw)
            archive.writestr("board.json", board_bytes)
            archive.writestr("native/" + native.name, native_bytes)
            for name, data in sources.items():
                archive.writestr(name, data)
        print(json.dumps({k: report[k] for k in ("status", "checks", "fresh_presentations_per_second")}, ensure_ascii=False), flush=True)
        window.close()
        engine.deleteLater()
        app.processEvents()
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
