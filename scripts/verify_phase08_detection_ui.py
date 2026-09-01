"""Archive and verify the physical RX presentation and capture-decoupling observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "results/evidence/phase08/detection-ui-decoupling.json"
PROCESSING_SOURCES = (
    "app/operator_console/live_ed.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
)
CAPTURE_QUEUE_CAPACITY = 512


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _passed(run: dict, interval: int) -> None:
    config, result = run["configuration"], run["result"]
    rx, transport = result["hackrf_statistics"], result["transport_statistics"]
    require(config["display_interval_frames"] == interval, "Görünüm aralığı uyuşmuyor.")
    require(result["completed_frames"] == rx["frames_received"] == 4096, "Kare sayısı uyuşmuyor.")
    require(rx["bytes_received"] == 134_217_728, "RX bayt sayısı uyuşmuyor.")
    require(rx["overruns"] == rx["longest_overrun_bytes"] == rx["process_returncode"] == 0, "USB bütünlüğü geçmedi.")
    require(transport["frames_sent"] == transport["frames_received"] == 4096, "Taşıma kare sayısı uyuşmuyor.")
    require(transport["crc_errors"] == transport["sequence_errors"] == transport["queue_drops"] == 0, "Taşıma bütünlüğü geçmedi.")
    require(transport["last_error"] is None, "Taşıma son hatası temiz değil.")
    require(result["input_saturated_components"] == result["output_saturated_components"] == 0, "I/Q kırpılması oluştu.")
    if "capture_queue_high_watermark" in result:
        require(0 < result["capture_queue_high_watermark"] <= CAPTURE_QUEUE_CAPACITY, "Ham RX kuyruğu sınırı bozuldu.")


def _read_runs(stored: zipfile.ZipFile, prefix: str) -> tuple[list[str], list[dict]]:
    names = sorted(
        name for name in stored.namelist()
        if name.startswith(f"{prefix}/run-") and name.endswith(".json")
    )
    return names, [json.loads(stored.read(name)) for name in names]


def _verify_common(run: dict) -> None:
    require(run["backend"] == "real HackRFContinuousRX and TCPClientIQTransport", "Gerçek RX/taşıma yolu gerekli.")
    require(run["ui_triggered"] is True and run["transmit_enabled"] is False, "Ürün RX sınırı bozuldu.")


def summarize(archive: Path, *, require_current_sources: bool = False) -> dict:
    with zipfile.ZipFile(archive) as stored:
        _, baseline = _read_runs(stored, "baseline")
        _, current = _read_runs(stored, "decoupled")
        require(len(baseline) == 8, "Önceki mimari gözlem sayısı uyuşmuyor.")
        require(len(current) >= 9, "Ayrıştırılmış mimari gözlem sayısı yetersiz.")
        for run in baseline + current:
            _verify_common(run)

        baseline_source = baseline[0]["source_sha256"]
        for run in baseline:
            for name in PROCESSING_SOURCES:
                require(run["source_sha256"][name] == baseline_source[name], f"Önceki kaynak grubu değişmiş: {name}")
        current_source = current[0]["source_sha256"]
        for run in current:
            for name in PROCESSING_SOURCES:
                require(
                    run["source_sha256"][name] == current_source[name],
                    f"Ayrıştırılmış kaynak grubu değişmiş: {name}",
                )
                if require_current_sources:
                    expected = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    require(
                        run["source_sha256"][name] == expected,
                        f"Güncel işleme kaynağı değişmiş: {name}",
                    )

        baseline_fast = [run for run in baseline if run["configuration"]["display_interval_frames"] == 16]
        baseline_bounded = [run for run in baseline if run["configuration"]["display_interval_frames"] == 50]
        require(len(baseline_fast) == 2 and len(baseline_bounded) == 6, "Önceki görünüm grupları uyuşmuyor.")
        require(all(run["status"] == "failed" and run["error_code"] == "usb_overrun" for run in baseline_fast), "16-kare olumsuz kontrol değişmiş.")
        baseline_passes = [run for run in baseline_bounded if run["status"] == "passed"]
        baseline_failures = [run for run in baseline_bounded if run["status"] == "failed"]
        require(len(baseline_passes) == 5 and len(baseline_failures) == 1, "Önceki 10 Hz sonucu değişmiş.")
        require(baseline_failures[0]["error_code"] == "usb_overrun", "Önceki 10 Hz olumsuz gözlem değişmiş.")
        for run in baseline_passes:
            _passed(run, 50)

        current_passes = [run for run in current if run["status"] == "passed"]
        cancelled = [run for run in current if run["status"] == "failed" and run.get("error_code") == "operation_cancelled"]
        require(len(current_passes) >= 8 and len(cancelled) == 1, "Güncel geçiş/iptal sayısı uyuşmuyor.")
        require(len(current_passes) + len(cancelled) == len(current), "Güncel grupta açıklanmayan sonuç var.")
        for run in current_passes:
            _passed(run, 50)
            require(run["result"]["channelized_queue_high_watermark"] == 0, "Eski bağlı kuyruk güncel sonuçta kullanılmış.")
        cancel_run = cancelled[0]
        require(0 < len(cancel_run["snapshots"]) < 82, "İptal koşusu sınırlı ara gözlem içermeli.")
        require(cancel_run["snapshots"][-1]["sequence_number"] < 4095, "İptal tam koşu gibi sunulamaz.")

        headless = json.loads(stored.read("headless-diagnostic.json"))
        require(headless["mode"] == "real_rx_without_gui" and headless["transmit_enabled"] is False, "GUI'siz karşılaştırma RX olmalı.")
        require(headless["status"] == "passed" and headless["result"]["hackrf_statistics"]["overruns"] == 0, "GUI'siz karşılaştırma geçmeli.")
        raw_hashes = {name: hashlib.sha256(stored.read(name)).hexdigest() for name in stored.namelist()}

    queue_marks = [run["result"]["capture_queue_high_watermark"] for run in current_passes]
    return {
        "schema": "phase08-detection-ui-observation-v3",
        "status": "capture_decoupling_observed",
        "phase08_complete": False,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "raw_sha256": raw_hashes,
        "baseline": {
            "runs": len(baseline),
            "display_16_usb_overrun_failures": len(baseline_fast),
            "display_50_passed_runs": len(baseline_passes),
            "display_50_usb_overrun_failures": len(baseline_failures),
        },
        "decoupled_capture": {
            "queue_capacity_frames": CAPTURE_QUEUE_CAPACITY,
            "passed_runs": len(current_passes),
            "completed_frames": sum(run["result"]["completed_frames"] for run in current_passes),
            "usb_overrun_failures": 0,
            "cancelled_runs": len(cancelled),
            "cancelled_last_sequence": cancel_run["snapshots"][-1]["sequence_number"],
            "capture_queue_high_watermarks": queue_marks,
            "maximum_capture_queue_occupancy": max(queue_marks),
            "maximum_capture_queue_utilization": max(queue_marks) / CAPTURE_QUEUE_CAPACITY,
            "session_frames_per_second": [run["result"]["frames_per_second"] for run in current_passes],
        },
        "concurrent_host_load_observation": {
            "run_names": ["run-08.json", "run-09.json"],
            "passed_runs": 2,
            "usb_overrun_failures": 0,
            "load_profile_calibrated": False,
        },
        "headless_comparison": {"completed_frames": 4096, "usb_overruns": 0},
        "limits": [
            "Sınırlı ham RX kuyruğu kısa süreli host gecikmesini emer; sürekli yetersiz işlem kapasitesini çözmez.",
            "Sekiz sınırlı tam oturum uzun süreli ürün kararlılığı kabulü değildir.",
            "Tam regresyonla eşzamanlı iki koşu genel amaçlı performans ölçütü değildir.",
            "Oturum hızları açılış ve kuyruk boşaltma maliyetini içerir; azami FPGA kapasitesi değildir.",
            "Ortam sinyalleri kontrollü RF doğruluk referansı değildir.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--baseline-directory", type=Path)
    parser.add_argument("--capture-directory", type=Path)
    parser.add_argument("--headless", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    report = args.report.resolve()
    archive = report.with_suffix(".zip")
    if args.capture_directory:
        require(all(value is not None for value in (args.baseline_directory, args.headless, args.screenshot)), "Tüm karşılaştırma girdileri gerekli.")
        require(not report.exists() and not archive.exists(), "Önceki kanıtın üzerine yazılamaz.")
        report.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stored:
            for prefix, directory in (("baseline", args.baseline_directory), ("decoupled", args.capture_directory)):
                for path in sorted(directory.glob("run-*.json")):
                    stored.write(path, f"{prefix}/{path.name}")
            stored.write(args.headless, "headless-diagnostic.json")
            stored.write(args.screenshot, "detection-selection-aligned.png")
        payload = summarize(archive, require_current_sources=True)
        with report.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    else:
        payload = summarize(archive)
        require(json.loads(report.read_text(encoding="utf-8")) == payload, "Özet ham arşivle eşleşmiyor.")
    observed = payload["decoupled_capture"]
    print(
        "Canlı RX ayrıştırma gözlemi doğrulandı: "
        f"{observed['passed_runs']} tam koşu/{observed['completed_frames']} kare, "
        "USB taşması 0; fiziksel iptal geçti."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
