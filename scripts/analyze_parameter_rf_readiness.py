"""KTR-4.2: özgün Replay RF kayıtlarında bant/gürültü/seviye tanısı.

Yeni RF üretmez, model eğitmez ve ürün kabulü vermez. Bütün aralıklar aynı
üç kayıtta raporlanır; iyi görünen aralık seçilerek başarı sayılmaz.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import scipy
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters.operator_assisted import project_to_simplex

FS = 8_000_000
NFFT = 65_536
RX_CENTER = 825_300_000
# Önceki CW gözlemi; mutlak kalibre referans veya aday taşıyıcı sonucu değil.
BAND_CENTER = 824_989_819.3359375
SPANS = (8_000, 16_000, 32_000, 64_000, 100_000)
DURATION = .25
# Önceden incelenmiş kayıtlar geliştirme/tanı verisidir. Seçimler eski
# etkinlik kayıtlarındaki yayın bölümlerinin içindedir; kör test değildir.
CASES = (
    ("AM", "amg8", 14.55, "replay-amg8-evaluation-20260909",
     "teknofest-rx-newport-amg8-rx24-20260909", 3417.2090640837005),
    ("NFM", "nfmg8", 21.75, "replay-nfmg8-evaluation-20260909",
     "capture", 16997.210371965244),
    ("BPSK", "bpskg8", 20.60, "replay-bpskg8-diagnostic-20260909",
     "on", 21496.072017016937),
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def db(value):
    return float(10 * np.log10(value)) if value > 0 else None


def spectrum(raw, start_s):
    first = round(start_s * FS)
    last = first + round(DURATION * FS)
    if first < 0 or last > len(raw):
        raise ValueError("Seçilen gerçek I/Q penceresi kayıt dışında.")
    codes = np.asarray(raw[first:last], dtype=np.float64)
    rails = int(np.count_nonzero((codes == -128) | (codes == 127)))
    x = (codes[:, 0] + 1j * codes[:, 1]) / 128
    frequency, psd = welch(x, fs=FS, window="hann", nperseg=NFFT,
        noverlap=NFFT // 2, detrend="constant", return_onesided=False,
        scaling="density", average="mean")
    # Parseval karşılaştırması aynı gerçek örneklerin pencere ağırlıklı
    # zaman alanı enerjisinden bağımsız olarak hesaplanır.
    starts = range(0, len(x) - NFFT + 1, NFFT // 2)
    window = .5 - .5 * np.cos(2 * np.pi * np.arange(NFFT) / NFFT)
    energy = []
    for first in starts:
        segment = x[first:first + NFFT]
        segment = segment - segment.mean()
        energy.append(float(np.sum(abs(segment * window) ** 2) / np.sum(window ** 2)))
    parseval_relative_error = abs(float(psd.sum() * FS / NFFT) / np.mean(energy) - 1)
    if parseval_relative_error > 1e-10:
        raise ValueError("Gerçek I/Q PSD güç normalizasyonu eşleşmedi.")
    return np.fft.fftshift(frequency) + RX_CENTER, np.fft.fftshift(psd), {
        "start_s": start_s, "duration_s": DURATION,
        "rail_components": rails, "averaged_segments": len(energy),
        "parseval_relative_error": float(parseval_relative_error),
    }


def band_diagnostic(frequency, psd, span_hz):
    lower, upper = BAND_CENTER - span_hz / 2, BAND_CENTER + span_hz / 2
    inside = (frequency >= lower) & (frequency <= upper)
    # 10 kHz koruma ve iki yanda 20 kHz referans. Tüm ailelerde aynı kural.
    left = (frequency >= lower - 30_000) & (frequency < lower - 10_000)
    right = (frequency > upper + 10_000) & (frequency <= upper + 30_000)
    nl, nr = float(np.mean(psd[left])), float(np.mean(psd[right]))
    noise_density = (nl + nr) / 2
    signed = psd[inside] - noise_density
    signal_density_sum = float(signed.sum())
    signal_power = signal_density_sum * FS / NFFT
    noise_power = noise_density * np.count_nonzero(inside) * FS / NFFT
    # Ortalama Welch PSD'sinde tek periodograma ait median/log(2) düzeltmesi yok.
    snr_db = db(signal_power / noise_power)
    projected = project_to_simplex(signed, max(0., signal_density_sum))
    centroid, edges = None, None
    if projected.sum() > 0:
        f = frequency[inside]
        centroid = float(np.sum(f * projected) / projected.sum())
        edges = np.interp([.005, .995], np.cumsum(projected) / projected.sum(), f)
    return {
        "requested_span_hz": span_hz,
        "integration_band_hz": [float(frequency[inside][0]), float(frequency[inside][-1])],
        "integrated_bin_width_hz": float(np.count_nonzero(inside) * FS / NFFT),
        "signal_excess_dbfs": db(signal_power), "noise_dbfs": db(noise_power),
        "noise_density_dbfs_per_hz": db(noise_density),
        "side_reference_difference_db": db(nl / nr), "snr_db": snr_db,
        "diagnostic_margin_to_12db": max(0., 12 - snr_db) if snr_db is not None else None,
        "spectral_center_diagnostic_hz": centroid,
        "conditional_in_span_obw99_hz": float(edges[1] - edges[0]) if edges is not None else None,
        "full_emission_obw_valid": False,
        "carrier_valid": False, "classification": None,
        "classification_status": "not_evaluated",
        "limits": "Aralık içi tanı; dış enerji sahipliği, taşıyıcı ve tam OBW doğrulanmadı.",
    }


def finite_range(values):
    present = [v for v in values if v is not None and np.isfinite(v)]
    return [float(min(present)), float(np.median(present)), float(max(present))] if present else None


def obtain_capture(captures_root, output, case):
    family, slug, _, evidence_name, archive_folder, _ = case
    evidence_path = ROOT / "results/evidence/phase08" / f"{evidence_name}.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    folder = captures_root / f"teknofest-rx-newport-{slug}-rx24-20260909" if captures_root else None
    if folder is None or not (folder / "rx.ci8").exists():
        folder = output / "recovered" / family
        folder.mkdir(parents=True, exist_ok=False)
        archive = evidence_path.with_suffix(".zip")
        # Yalnız iki sabit adlı girdi; arşiv yolları diske doğrudan çıkarılmaz.
        with zipfile.ZipFile(archive) as source:
            for name in ("rx.ci8", "capture.json"):
                with source.open(f"{archive_folder}/{name}") as src, (folder / name).open("xb") as dest:
                    while block := src.read(1_048_576):
                        dest.write(block)
    hashes = {}
    for name in ("rx.ci8", "capture.json"):
        actual = digest(folder / name)
        expected = evidence["files"][f"{archive_folder}/{name}"]
        if actual != expected:
            raise ValueError(f"{family}: özgün {name} SHA-256 özeti eşleşmedi.")
        hashes[name] = actual
    capture = json.loads((folder / "capture.json").read_text(encoding="utf-8"))
    if capture["raw_sha256"] != hashes["rx.ci8"]:
        raise ValueError("Kayıt manifesti ham I/Q özetiyle eşleşmiyor.")
    if capture["sample_rate_hz"] != FS or capture["center_frequency_hz"] != RX_CENTER:
        raise ValueError("Özgün alıcı frekans/örnekleme bağlamı eşleşmiyor.")
    raw_path = folder / "rx.ci8"
    if raw_path.stat().st_size != capture["bytes"] or capture["bytes"] % 2:
        raise ValueError("Ham I/Q boyutu veya bileşen eşleşmesi geçersiz.")
    return raw_path, capture, {
        "evidence": evidence_path.relative_to(ROOT).as_posix(),
        "evidence_sha256": digest(evidence_path), "archive_member_prefix": archive_folder,
        "verified_input_sha256": hashes,
    }


def run(output, captures_root=None):
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "requirements": ["KTR-4.2", "KTR-4.2-F1"],
        "method": "recorded-rf-welch-readiness-v1",
        "selection_status": "Önceden incelenmiş RF geliştirme/tanı verisi; kör kabul değildir.",
        "frequency_bin_hz": FS / NFFT, "hann_enbw_hz": 1.5 * FS / NFFT,
        "spans_hz": SPANS, "window_duration_s": DURATION,
        "window_count_per_capture": 10,
        "snr_target_note": "12 dB yalnız geliştirme bağlantısı hedefi; başarı veya ITU şartı değildir.",
        "source_sha256": {"scripts/analyze_parameter_rf_readiness.py": digest(Path(__file__)),
            "algorithms/parameters/operator_assisted.py": digest(ROOT / "algorithms/parameters/operator_assisted.py")},
        "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
        "physical_acceptance": False, "product_acceptance": False, "dbm_calibrated": False,
        "cases": [],
    }
    for case in CASES:
        family, _, start, _, _, file_width = case
        path, capture, provenance = obtain_capture(captures_root, output, case)
        raw = np.memmap(path, dtype=np.int8, mode="r").reshape(-1, 2)
        rows, spectra = [], []
        # Önce ve sonra örnekleri, hedef yayın öncesi/sonrası tanıdır;
        # bütün RF ortamının sessiz olduğu varsayılmaz.
        times = [1.] + [start + .45 * index for index in range(10)] + [28.5]
        for index, at in enumerate(times):
            frequency, psd, quality = spectrum(raw, at)
            rows.append({"role": "pre" if index == 0 else "post" if index == 11 else "on",
                "quality": quality, "bands": [band_diagnostic(frequency, psd, width) for width in SPANS]})
            spectra.append(psd)
        np.savez_compressed(output / f"{family}-spectra.npz", frequency_hz=frequency,
            psd_fs2_per_hz=np.asarray(spectra), times_s=np.asarray(times))
        summary = []
        for index, width in enumerate(SPANS):
            bands = [row["bands"][index] for row in rows[1:-1]]
            summary.append({"span_hz": width,
                "smaller_than_reference_file_obw": width < file_width,
                "snr_db_min_median_max": finite_range([v["snr_db"] for v in bands]),
                "signal_dbfs_min_median_max": finite_range([v["signal_excess_dbfs"] for v in bands]),
                "conditional_obw_hz_min_median_max": finite_range([v["conditional_in_span_obw99_hz"] for v in bands]),
                "noise_on_minus_pre_db_min_median_max": finite_range([
                    v["noise_dbfs"] - rows[0]["bands"][index]["noise_dbfs"] for v in bands]),
                "side_difference_abs_db_max": max(abs(v["side_reference_difference_db"]) for v in bands),
            })
        case_report = {"family_label_for_reporting_only": family,
            "reference_file_obw99_hz": file_width,
            "reference_note": "RF öncesi dosya OBW'si; gerçek RF bant sınırı değildir.",
            **provenance, "transport_valid": bool(capture.get("transport_valid")),
            "usb_overruns": capture.get("usb_overruns"),
            "capture_settled_rail_components": capture.get("settled_rail_components"),
            "eligible_as_continuous_record": bool(capture.get("transport_valid")) and capture.get("settled_rail_components") == 0,
            "independent_capture_count": 1, "summary": summary, "rows": rows}
        report["cases"].append(case_report)
        print(json.dumps({"family": family, "transport_valid": case_report["transport_valid"],
            "spans": [{"hz": r["span_hz"], "snr": r["snr_db_min_median_max"]} for r in summary]}, ensure_ascii=False), flush=True)
        del raw
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--captures-root", type=Path,
        help="Özgün yerel kayıt klasörleri; verilmezse mevcut kanıt ZIP'lerinden güvenli kurtarma.")
    args = parser.parse_args()
    run(args.output, args.captures_root)
