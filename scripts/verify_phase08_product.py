"""Archive or recheck physical product observations, without claiming RF accuracy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "results/evidence/phase08/product-live-acceptance.json"
PROCESSING_SOURCES = (
    "app/operator_console/live_ed.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def summarize(archive: Path, *, require_current_sources: bool = False) -> dict:
    runs = []
    with zipfile.ZipFile(archive) as stored:
        source_hashes = json.loads(stored.read("source-sha256.json"))
        if require_current_sources:
            for name in PROCESSING_SOURCES:
                require(
                    hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == source_hashes[name],
                    f"İşleme kaynağı değişmiş: {name}",
                )
        names = sorted(name for name in stored.namelist() if name.startswith("run-") and name.endswith(".json"))
        for name in names:
            raw = stored.read(name)
            run = json.loads(raw)
            require(run["transmit_enabled"] is False and run["ui_triggered"] is True, f"RX/ürün kapsamı: {name}")
            require(run["backend"] == "real HackRFContinuousRX and TCPClientIQTransport", f"Alım yolu: {name}")
            summary = {key: run[key] for key in ("recorded_at", "configuration", "status", "elapsed_seconds")}
            summary.update(file=name, sha256=hashlib.sha256(raw).hexdigest(), snapshots=len(run["snapshots"]))
            if run["status"] != "passed":
                summary.update(error_code=run["error_code"], error=run["error"])
                runs.append(summary)
                continue
            result = run["result"]
            cfg = run["configuration"]
            count = cfg["frame_count"]
            rx = result["hackrf_statistics"]
            tcp = result["transport_statistics"]
            require(count == 4096 and result["completed_frames"] == count, f"Kare sayısı: {name}")
            require(rx["frames_received"] == count and rx["bytes_received"] == count * 32768, f"RX uzunluğu: {name}")
            require(rx["overruns"] == rx["longest_overrun_bytes"] == rx["process_returncode"] == 0, f"USB bütünlüğü: {name}")
            require(tcp["frames_sent"] == tcp["frames_received"] == count, f"TCP kare sayısı: {name}")
            require(tcp["crc_errors"] == tcp["sequence_errors"] == tcp["queue_drops"] == 0 and tcp["last_error"] is None, f"TCP bütünlüğü: {name}")
            require(result["input_saturated_components"] == result["output_saturated_components"] == 0, f"Kırpılma: {name}")
            require(0 < result["channelized_queue_high_watermark"] <= 64, f"Kuyruk sınırı: {name}")
            sequences = [s["sequence_number"] for s in run["snapshots"]]
            expected = [0] + list(range(cfg["display_interval_frames"] - 1, count, cfg["display_interval_frames"]))
            require(sequences == expected, f"Görünüm kareleri: {name}")
            for snapshot in run["snapshots"]:
                response = snapshot["response"]
                require(response["frame_id"] == snapshot["sequence_number"], f"Görünüm/yanıt bağı: {name}")
                require(response["dma_status_flags"] == 7 and response["dropped_candidates"] == 0, f"DMA/adayı koruma: {name}")
                require(len(snapshot["iq_sha256"]) == 64, f"I/Q özeti: {name}")
            summary["result"] = result
            summary["last_snapshot"] = run["snapshots"][-1]
            runs.append(summary)
        screenshot_hashes = {name: hashlib.sha256(stored.read(name)).hexdigest() for name in stored.namelist() if name.endswith(".png")}
    require(len(runs) >= 6, "Beş tekrar ve olumsuz kontrol kaydı gerekli.")
    cohort = runs[1:6]
    require(runs[0].get("error_code") == "iq_saturation" and runs[0]["snapshots"] == 0, "Kırpılma olumsuz kontrolü korunmalı.")
    require(all(run["status"] == "passed" for run in cohort), "Ardışık beş tam oturum geçmeli.")
    require(all(run["configuration"] == cohort[0]["configuration"] for run in cohort), "Tekrarlarda yapılandırma aynı olmalı.")
    require(cohort[0]["configuration"]["lna_gain_db"] == cohort[0]["configuration"]["vga_gain_db"] == 0, "Ölçülen kabul kazançları 0/0 dB.")
    return {
        "schema": "phase08-product-observation-v1",
        "status": "bounded_receive_passed",
        "phase08_complete": False,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "captured_source_sha256": source_hashes,
        "screenshot_sha256": screenshot_hashes,
        "acceptance_cohort": [run["file"] for run in cohort],
        "cohort_completed_frames": sum(run["result"]["completed_frames"] for run in cohort),
        "all_observed_completed_frames": sum(run["result"]["completed_frames"] for run in runs if run["status"] == "passed"),
        "runs": runs,
        "limits": [
            "Alıcı kaynaklı yaklaşık 8,5 saniyelik oturumlar; uzun süreli kesintisiz çalışma kabulü değildir.",
            "Kare/s oturum açılışını ve gözlemci maliyetini içerir; kararlı durum kapasitesi veya C/C++ hızlanma ölçümü değildir.",
            "Antenle alınan ortam sinyallerinin referans doğruluğu bilinmiyor; tespit olasılığı ve yanlış alarm başarısı bu kayıttan çıkarılamaz.",
            "Canlı parametre/ses ürün yolu, dBm kalibrasyonu ve saha doğruluğu bu kabulde yoktur.",
            "Durdurma düğmesine ulaşılmadan biten ek tekrarlar iptal başarısı sayılmamıştır; fiziksel iptal kabulü açıktır.",
            "Sistem ekranının çalışma yeri/kaynak bağlantısı düzeltmesi ilk fiziksel kayıttan sonradır; işleme yolu değişmemiştir.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--capture-directory", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--observer-script", type=Path)
    args = parser.parse_args()
    report_path = args.report.resolve()
    archive = report_path.with_suffix(".zip")
    if args.capture_directory:
        require(args.source_manifest is not None and args.observer_script is not None, "Kayıt sırasında kullanılan kaynak özeti ve gözlemci gerekli.")
        require(not report_path.exists() and not archive.exists(), "Önceki kanıtın üzerine yazılamaz.")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stored:
            for path in sorted(args.capture_directory.glob("run-*.json")):
                stored.write(path, path.name)
            for path in sorted(args.capture_directory.glob("*.png")):
                stored.write(path, path.name)
            stored.write(args.source_manifest, "source-sha256.json")
            stored.write(args.observer_script, "capture-observer.py")
        summary = summarize(archive, require_current_sources=True)
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    else:
        require(json.loads(report_path.read_text(encoding="utf-8")) == summarize(archive), "Kanıt özeti arşivle eşleşmiyor.")
    print("Fiziksel ürün kaydı doğrulandı: beş tekrar, 20.480 kare. PHASE-08 bütünü henüz tamamlanmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
