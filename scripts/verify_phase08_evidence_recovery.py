"""Tarihsel kanıt bütünlüğü ve sınırlı RX gözlemi; yeni donanım kabulü değildir."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_phase08_endurance import summarize

# Özgün 559d496 kaydının bayt özetleri. Yeni ölçüm yeni dosyaya yazılır;
# kaynak değişikliği bu sabitleri veya tarihsel kanıtları güncellemez.
FROZEN_EVIDENCE = {
    "results/evidence/phase08/native-channelizer-v3.json":
        "3316681d6eed9a5d358f900ae47ed06b87834835da3efae6dc2e7a51c7db586d",
    "results/evidence/phase08/st06-parallel-product-v1.json":
        "0bc494625e4382581f17ace80df37033a00b95b457798162cb0b51174201bd2a",
    "results/evidence/phase08/st06-parallel-product-v1.zip":
        "62844c02221acbba9fb2424e041fc50394b5f407ad9734e590eaab8a0e79fb34",
}
REPORT = "results/evidence/phase08/rx-evidence-recovery-v1.json"
NATIVE_REPORT = "results/evidence/phase08/native-channelizer-v3.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_frozen_file(relative, *, root=ROOT):
    require(file_hash(root / relative) == FROZEN_EVIDENCE[relative],
            f"Tarihsel kanıt değiştirildi: {relative}")


def load_recovery(*, root=ROOT):
    report = json.loads((root / REPORT).read_text(encoding="utf-8"))
    require(report["schema"] == "phase08-evidence-recovery-v1", "İnceleme şeması geçersiz.")
    require(report["scope"] == "historical_evidence_recovery_no_new_hardware_measurement",
            "İnceleme yeni ölçüm olarak sunulamaz.")
    require(report["frozen_evidence"] == FROZEN_EVIDENCE, "Özgün kanıt bağları değiştirildi.")
    archive = root / report["archive"]["path"]
    require(file_hash(archive) == report["archive"]["sha256"], "İnceleme arşivi değiştirildi.")
    return report, archive


def verify_native_history(*, root=ROOT):
    verify_frozen_file(NATIVE_REPORT, root=root)
    native = json.loads((root / NATIVE_REPORT).read_text(encoding="utf-8"))
    _, archive = load_recovery(root=root)
    with zipfile.ZipFile(archive) as stored:
        for name, digest in native["source_sha256"].items():
            require(hashlib.sha256(stored.read("native-sources/" + name)).hexdigest() == digest,
                    f"Tarihsel kanal seçici kaynağı uyuşmuyor: {name}")
    return native


def verify(*, root=ROOT):
    for relative in FROZEN_EVIDENCE:
        verify_frozen_file(relative, root=root)
    verify_native_history(root=root)
    report, archive = load_recovery(root=root)
    runs = []
    with zipfile.ZipFile(archive) as stored:
        require([item["id"] for item in report["runs"]] == ["prior-1", "prior-2", "headless-1"],
                "Başarılı ve başarısız koşular birlikte korunmalıdır.")
        for item in report["runs"]:
            raw = stored.read(item["path"])
            require(hashlib.sha256(raw).hexdigest() == item["sha256"], "Ham RX kaydı değiştirildi.")
            run = json.loads(raw)
            require(run["status"] == item["status"] and run["recorded_at"] == item["recorded_at"],
                    "Koşunun durumu veya ölçüm tarihi değiştirildi.")
            require(run["configuration"]["frame_count"] == 439453, "Uzun koşu kapsamı değiştirildi.")
            require(run["transmit_enabled"] is False, "Koşu yalnız RX olmalıdır.")
            for name, digest in run["source_sha256"].items():
                entry = f"runs/{item['id']}/sources/{name}"
                require(hashlib.sha256(stored.read(entry)).hexdigest() == digest,
                        f"Koşunun arşivlenmiş kaynağı uyuşmuyor: {entry}")
            runs.append(run)
        require(all(run["status"] == "failed" and run["error_code"] == "usb_overrun"
                    for run in runs[:2]), "Önceki USB taşması başarısızlıkları korunmalıdır.")
        last = runs[-1]
        require(last["status"] == "passed" and last["result"]["preview_frames"] == 0,
                "Son koşu arayüz içermeyen bir RX gözlemidir.")
        live_name = "app/operator_console/live_ed.py"
        require(runs[0]["source_sha256"][live_name] == runs[1]["source_sha256"][live_name]
                != last["source_sha256"][live_name], "Koşuların kaynak sürümleri ayrılmalıdır.")
        v3_path = root / "results/evidence/phase08/live-rx-endurance-v3.json"
        v3 = json.loads(v3_path.read_text(encoding="utf-8"))
        require(v3 == summarize(v3_path.with_suffix(".zip")), "RX özeti ham arşivle uyuşmuyor.")
        require(v3["run_sha256"] == report["runs"][-1]["sha256"], "Son koşunun bağı farklı.")
        with zipfile.ZipFile(v3_path.with_suffix(".zip")) as original:
            require(original.read("run.json") == stored.read(report["runs"][-1]["path"]),
                    "Son koşunun ham baytları farklı.")
    expected_acceptance = {
        "single_headless_rx_integrity_observed": True,
        "gui_acceptance": False, "rf_detection_acceptance": False,
        "nominal_throughput_margin_proven": False, "cold_boot_acceptance": False,
        "ST06_complete": False,
    }
    require(report["acceptance"] == expected_acceptance, "Kanıt kapsamı genişletilemez.")
    return {
        "scope": report["scope"], "historical_integrity": "passed",
        "prior_usb_overrun_runs": 2, "headless_integrity_runs": 1,
        "observed_fps": v3["frames_per_second"], "required_fps": 2000000 / 4096,
        "acceptance": expected_acceptance,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
