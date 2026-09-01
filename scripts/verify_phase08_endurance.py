"""Capture and verify a bounded, receive-only PHASE-08 endurance observation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.operator_console.live_ed import (  # noqa: E402
    LIVE_CAPTURE_QUEUE_CAPACITY,
    LIVE_INPUT_SAMPLES_PER_FRAME,
    LiveEDConfiguration,
    LiveEDSession,
)

DEFAULT_REPORT = ROOT / "results/evidence/phase08/live-rx-endurance.json"
DEFAULT_FRAME_COUNT = 439_453
MINIMUM_ACCEPTANCE_FRAMES = DEFAULT_FRAME_COUNT
PROGRESS_INTERVAL_FRAMES = 4_096
SERIAL = "0000000000000000a32868dc35138247"
CAPTURE_SOURCES = (
    "app/operator_console/live_ed.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
    "scripts/verify_phase08_endurance.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def source_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in CAPTURE_SOURCES
    }


def capture(path: Path, frame_count: int) -> int:
    require(not path.exists(), "Ham dayanıklılık kaydının üzerine yazılamaz.")
    executable = shutil.which("hackrf_transfer")
    require(executable is not None, "hackrf_transfer bulunamadı.")
    configuration = LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        device_serial=SERIAL,
        lna_gain_db=0,
        vga_gain_db=0,
        frame_count=frame_count,
        board_host="192.168.7.2",
        board_port=47_007,
        display_interval_frames=PROGRESS_INTERVAL_FRAMES,
    )
    progress: list[dict[str, object]] = []
    started = time.perf_counter()
    report: dict[str, object] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(configuration),
        "source_sha256": source_hashes(),
        "backend": "real HackRFContinuousRX and TCPClientIQTransport",
        "transmit_enabled": False,
    }

    def observe(snapshot) -> None:
        progress.append(
            {
                "sequence_number": snapshot.sequence_number,
                "iq_sha256": hashlib.sha256(snapshot.output_frame.payload).hexdigest(),
                "active_event_count": len(snapshot.response.active),
                "raw_candidate_count": snapshot.response.raw_candidate_count,
                "dma_status_flags": snapshot.response.dma_status_flags,
                "dropped_candidates": snapshot.response.dropped_candidates,
            }
        )

    try:
        result = LiveEDSession(executable, configuration).run(observe)
        report["status"] = "passed"
        report["result"] = asdict(result)
    except Exception as exc:
        report["status"] = "failed"
        report["error_code"] = getattr(exc, "code", type(exc).__name__)
        report["error"] = str(exc)
    finally:
        report["elapsed_seconds"] = time.perf_counter() - started
        report["progress"] = progress
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return 0 if report.get("status") == "passed" else 1


def summarize(archive: Path) -> dict[str, object]:
    with zipfile.ZipFile(archive) as stored:
        names = stored.namelist()
        require(names == ["run.json"], "Dayanıklılık arşivi tek ham koşu içermelidir.")
        raw = stored.read("run.json")
    run = json.loads(raw)
    require(run["status"] == "passed", "Dayanıklılık koşusu başarılı değil.")
    require(run["transmit_enabled"] is False, "Dayanıklılık koşusu yalnız RX olmalıdır.")
    require(
        run["backend"] == "real HackRFContinuousRX and TCPClientIQTransport",
        "Fiziksel alım yolu doğrulanamadı.",
    )
    captured_hashes = run["source_sha256"]
    config = run["configuration"]
    result = run["result"]
    rx = result["hackrf_statistics"]
    transport = result["transport_statistics"]
    frame_count = config["frame_count"]
    require(frame_count >= MINIMUM_ACCEPTANCE_FRAMES, "Dayanıklılık süresi kabul sınırının altında.")
    require(
        result["completed_frames"] == rx["frames_received"] == frame_count,
        "HackRF kare sayısı uyuşmuyor.",
    )
    require(
        rx["bytes_received"] == frame_count * LIVE_INPUT_SAMPLES_PER_FRAME * 2,
        "HackRF bayt sayısı uyuşmuyor.",
    )
    require(
        rx["overruns"] == rx["longest_overrun_bytes"] == rx["process_returncode"] == 0,
        "HackRF USB bütünlüğü başarısız.",
    )
    require(
        transport["frames_sent"] == transport["frames_received"] == frame_count,
        "FPGA taşıma kare sayısı uyuşmuyor.",
    )
    require(
        transport["crc_errors"] == transport["sequence_errors"] == transport["queue_drops"] == 0
        and transport["last_error"] is None,
        "FPGA taşıma bütünlüğü başarısız.",
    )
    require(
        result["input_saturated_components"] == result["output_saturated_components"] == 0,
        "Canlı I/Q akışında kırpılma var.",
    )
    require(
        0 < result["capture_queue_high_watermark"] <= LIVE_CAPTURE_QUEUE_CAPACITY,
        "Ham RX kuyruğu sınırı geçersiz.",
    )
    progress = run["progress"]
    expected = [0] + list(range(PROGRESS_INTERVAL_FRAMES - 1, frame_count, PROGRESS_INTERVAL_FRAMES))
    if expected[-1] != frame_count - 1:
        expected.append(frame_count - 1)
    require([item["sequence_number"] for item in progress] == expected, "İlerleme kaydı eksik.")
    require(
        all(item["dma_status_flags"] == 7 and item["dropped_candidates"] == 0 for item in progress),
        "İlerleme kaydında DMA veya aday kaybı var.",
    )
    expected_seconds = frame_count * LIVE_INPUT_SAMPLES_PER_FRAME / 8_000_000
    return {
        "schema": "phase08-live-rx-endurance-v1",
        "status": "endurance_passed",
        "phase08_complete": False,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "run_sha256": hashlib.sha256(raw).hexdigest(),
        "captured_source_sha256": captured_hashes,
        "frame_count": frame_count,
        "input_complex_samples": frame_count * LIVE_INPUT_SAMPLES_PER_FRAME,
        "nominal_capture_seconds": expected_seconds,
        "observed_elapsed_seconds": result["elapsed_seconds"],
        "frames_per_second": result["frames_per_second"],
        "capture_queue_high_watermark": result["capture_queue_high_watermark"],
        "capture_queue_capacity": LIVE_CAPTURE_QUEUE_CAPACITY,
        "raw_candidate_total": result["raw_candidate_total"],
        "maximum_active_events": result["maximum_active_events"],
        "usb_overruns": rx["overruns"],
        "crc_errors": transport["crc_errors"],
        "sequence_errors": transport["sequence_errors"],
        "queue_drops": transport["queue_drops"],
        "input_saturated_components": result["input_saturated_components"],
        "output_saturated_components": result["output_saturated_components"],
        "limits": [
            "Bu kabul tek merkez frekansında ve 0/0 dB alıcı kazancında yapılmıştır.",
            "Ortam RF sinyalleri kontrollü referans değildir; tespit doğruluğu bu koşudan çıkarılamaz.",
            "Koşu RX-only'dir; RF yayın işlevi yoktur.",
            "Canlı parametre ve ses ürün kabulü ayrı kapıdır.",
        ],
    }


def archive_run(run_path: Path, report_path: Path) -> None:
    archive = report_path.with_suffix(".zip")
    require(not report_path.exists() and not archive.exists(), "Önceki dayanıklılık kanıtının üzerine yazılamaz.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stored:
        stored.write(run_path, "run.json")
    summary = summarize(archive)
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAME_COUNT)
    parser.add_argument("--archive-run", type=Path)
    args = parser.parse_args()
    if args.capture is not None:
        return capture(args.capture.resolve(), args.frames)
    report_path = args.report.resolve()
    if args.archive_run is not None:
        archive_run(args.archive_run.resolve(), report_path)
    else:
        require(
            json.loads(report_path.read_text(encoding="utf-8")) == summarize(report_path.with_suffix(".zip")),
            "Dayanıklılık kanıt özeti arşivle eşleşmiyor.",
        )
    print("Canlı RX dayanıklılık kanıtı doğrulandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
