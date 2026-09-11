"""Verify the receive-only PHASE-08 live parameter product evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "results/evidence/phase08/live-parameter-functional.json"
CAPTURE_SOURCES = (
    "app/operator_console/detection_model.py",
    "app/operator_console/live_ed.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/quick_application.py",
    "app/operator_console/qml/Main.qml",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
    "scripts/capture_phase08_product.py",
)
EXPECTED_PARAMETER_LABELS = (
    "Emisyon merkez frekansı",
    "Gözlenen taşıyıcı frekansı",
    "Alt OBW sınırı",
    "Üst OBW sınırı",
    "İşgal edilen bant genişliği (OBW %99)",
    "Kanal gücü (dBFS)",
    "Bant içi SNR kestirimi",
    "Sinyal türü",
    "Güç referansı",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def source_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in CAPTURE_SOURCES
    }


def summarize(archive: Path) -> dict[str, object]:
    with zipfile.ZipFile(archive) as stored:
        require(stored.namelist() == ["run.json", "ui-state.json"], "Kanıt arşivi iki beklenen kaydı içermelidir.")
        raw_run = stored.read("run.json")
        raw_ui = stored.read("ui-state.json")
    run = json.loads(raw_run)
    ui = json.loads(raw_ui)

    require(run["backend"] == "real HackRFContinuousRX and TCPClientIQTransport", "Fiziksel alım yolu doğrulanamadı.")
    require(run["transmit_enabled"] is False, "Canlı parametre kabulü yalnız RX olmalıdır.")
    require(run["ui_triggered"] is True, "Ölçüm ürün arayüzünden başlatılmamış.")
    require(run["status"] == "failed" and run.get("error_code") == "operation_cancelled", "Ölçüm için beklenen kontrollü alım durdurması yok.")
    require(run["configuration"]["lna_gain_db"] == run["configuration"]["vga_gain_db"] == 0, "Alıcı kazancı kabul koşuluyla eşleşmiyor.")
    require(run["configuration"]["frame_count"] == 878_906, "Ürün oturumu sınırlı 30 dakika yapılandırmasında değil.")
    require(len(run["snapshots"]) > 0, "Gerçek FPGA görünüm yanıtı kaydedilmemiş.")
    require(all(item["response"]["dma_status_flags"] == 7 for item in run["snapshots"]), "FPGA DMA durumu geçersiz.")
    require(all(item["response"]["dropped_candidates"] == 0 for item in run["snapshots"]), "FPGA aday kaybı oluşmuş.")

    require(ui["source_state"] == "Hazır" and ui["error"] == "", "Ürün arayüzü ölçümü hatasız tamamlamamış.")
    require("parametre ölçümü tamamlandı" in ui["status"], "Ürün ölçüm tamamlanma durumu yok.")
    require(ui["analysis_span_confirmed"] is True, "Analiz aralığı operatörce onaylanmamış.")
    selected_event = int(ui["selected_event_id"])
    require(selected_event >= 0, "Ölçüm bir FPGA olay kimliğine bağlı değil.")

    window = ui["measurement_window"]
    require(len(window) == 4, "Ölçüm tam dört ardışık FPGA karesine bağlı değil.")
    sequences = [int(item["sequence_number"]) for item in window]
    frame_ids = [int(item["frame_id"]) for item in window]
    require(sequences == list(range(sequences[0], sequences[0] + 4)), "Ölçüm sıra numaraları ardışık değil.")
    require(frame_ids == list(range(frame_ids[0], frame_ids[0] + 4)), "Ölçüm kare kimlikleri ardışık değil.")
    require(all(item["event_id"] == selected_event and item["confirmed_and_observed"] is True for item in window), "Ölçüm penceresi seçili doğrulanmış olaya bağlı değil.")
    revisions = [int(item["event_revision"]) for item in window]
    require(revisions == list(range(revisions[0], revisions[0] + 4)), "Olay gözlem revizyonları ardışık değil.")
    iq_hashes = [item["iq_sha256"] for item in window]
    require(len(set(iq_hashes)) == 4 and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in iq_hashes), "Ölçüm I/Q kare kimlikleri geçersiz.")

    rows = ui["parameter_rows"]
    require(tuple(row["label"] for row in rows) == EXPECTED_PARAMETER_LABELS, "Ürün parametre alanları eksik veya sırası değişmiş.")
    require(all(str(row["value"]).strip() for row in rows), "Ürün parametre sonucu boş alan içeriyor.")

    return {
        "schema": "phase08-live-parameter-functional-v1",
        "status": "functional_binding_passed",
        "phase08_complete": False,
        "accuracy_proven": False,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "run_sha256": hashlib.sha256(raw_run).hexdigest(),
        "ui_state_sha256": hashlib.sha256(raw_ui).hexdigest(),
        "captured_source_sha256": run["source_sha256"],
        "selected_event_id": selected_event,
        "measurement_sequence_numbers": sequences,
        "measurement_frame_ids": frame_ids,
        "measurement_iq_sha256": iq_hashes,
        "parameter_field_count": len(rows),
        "captured_display_snapshots": len(run["snapshots"]),
        "transmit_enabled": False,
        "limits": [
            "Bu kanıt canlı HackRF→ZedBoard→ürün parametre bağının çalıştığını gösterir.",
            "Ortam sinyali kontrollü referans değildir; frekans, bant genişliği, güç veya sınıf doğruluğu çıkarılamaz.",
            "dBm kalibrasyonu ve canlı analog ses kabulü ayrı kapılardır.",
            "Koşu RX-only'dir; RF yayın işlevi yoktur.",
        ],
    }


def archive_run(run_path: Path, ui_path: Path, report_path: Path) -> None:
    archive = report_path.with_suffix(".zip")
    require(not report_path.exists() and not archive.exists(), "Önceki canlı parametre kanıtının üzerine yazılamaz.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stored:
        stored.write(run_path, "run.json")
        stored.write(ui_path, "ui-state.json")
    report = summarize(archive)
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--archive-run", type=Path)
    parser.add_argument("--ui-state", type=Path)
    args = parser.parse_args()
    report_path = args.report.resolve()
    if args.archive_run is not None:
        require(args.ui_state is not None, "Arşivleme için UI durum kaydı gerekir.")
        archive_run(args.archive_run.resolve(), args.ui_state.resolve(), report_path)
    else:
        require(json.loads(report_path.read_text(encoding="utf-8")) == summarize(report_path.with_suffix(".zip")), "Canlı parametre özeti arşivle eşleşmiyor.")
    print("Canlı parametre ürün kanıtı doğrulandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
