"""KTR-4.2: Replay BPSK kaydını bant enerjisi ve sabit adayla değerlendir."""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import argparse
import hashlib
import json
import sys

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters.refined_candidate import classify_candidate, measure_candidate

MODEL_SHA256 = "afa2872c6363d25e5322b6c382db32a0b9ec3d85260ef4b6ce37d9606ebc67c9"
REFERENCE_FREQUENCY_HZ = 824_989_819.3359375
REFERENCE_OBW99_HZ = 21_496.072017016937
RX_CENTER_HZ = 825_300_000
RX_RATE_HZ = 8_000_000


def _band_trace(path):
    data = np.memmap(path, dtype=np.int8, mode="r").reshape(-1, 2)
    size = 65536
    step = int(0.05 * RX_RATE_HZ)
    window = np.hanning(size)
    frequency = np.fft.fftshift(np.fft.fftfreq(size, 1 / RX_RATE_HZ))
    offset = REFERENCE_FREQUENCY_HZ - RX_CENTER_HZ
    mask = np.abs(frequency - offset) <= 18_000
    rows = []
    for first in range(int(0.1 * RX_RATE_HZ), len(data) - size, step):
        values = data[first:first + size].astype(float)
        iq = (values[:, 0] + 1j * values[:, 1]) / 128
        spectrum = np.fft.fftshift(np.fft.fft(iq * window))
        band_power = np.sum(np.abs(spectrum[mask]) ** 2) / np.sum(window ** 2)
        rows.append((first / RX_RATE_HZ, 10 * np.log10(max(band_power, 1e-30))))
    return rows


def _segments(rows, threshold):
    active = [(time_s, power) for time_s, power in rows if power > threshold]
    segments = []
    for time_s, power in active:
        # Rastgele veri ve bastırılmış taşıyıcı, kısa bant enerjisi boşlukları
        # üretir. En fazla 0,8 s boşluğu yalnız sonlu yayın zamanını bulmak için
        # birleştir; bu seçim sınıf özelliği değildir.
        if not segments or time_s - segments[-1]["last_s"] > 0.81:
            segments.append({"first_s": time_s, "last_s": time_s, "peak_db": power})
        else:
            segments[-1]["last_s"] = time_s
            segments[-1]["peak_db"] = max(segments[-1]["peak_db"], power)
    for segment in segments:
        segment["sampled_span_s"] = segment["last_s"] - segment["first_s"] + 0.05
    return segments


def run(off_folder, on_folder, output):
    off_capture = json.loads((off_folder / "capture.json").read_text(encoding="utf-8"))
    on_capture = json.loads((on_folder / "capture.json").read_text(encoding="utf-8"))
    if on_capture.get("settled_rail_components") != 0:
        raise ValueError("Kırpılmış kayıt tanıda kullanılmaz.")
    model_path = ROOT / "build/acceptance/parameter-candidate-v9-20260909/candidate-model.json"
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA256:
        raise ValueError("Sabit aday model özeti eşleşmiyor.")
    model = json.loads(model_bytes)

    off_trace = _band_trace(off_folder / "rx.ci8")
    on_trace = _band_trace(on_folder / "rx.ci8")
    threshold = float(np.quantile([row[1] for row in off_trace], 0.99) + 3.0)
    segments = _segments(on_trace, threshold)
    usable = [item for item in segments if 4.5 <= item["sampled_span_s"] <= 8.0]
    rows = []
    if usable:
        segment = max(usable, key=lambda item: item["sampled_span_s"])
        start = segment["first_s"] + 0.25
        data = np.memmap(on_folder / "rx.ci8", dtype=np.int8, mode="r").reshape(-1, 2)
        observed_bin = round(2048 + (REFERENCE_FREQUENCY_HZ - RX_CENTER_HZ) / (2_000_000 / 4096))
        half_width = 44
        for index in range(10):
            at = start + index * 0.45
            first = int(at * RX_RATE_HZ)
            values = data[first:first + 73728].astype(float)
            iq = resample_poly((values[:, 0] + 1j * values[:, 1]) / 128, 1, 4)[256:256 + 16384]
            measurement = measure_candidate(
                iq.reshape(4, 4096), sample_rate_hz=2_000_000,
                center_frequency_hz=RX_CENTER_HZ,
                lower_bin=observed_bin - half_width, upper_bin=observed_bin + half_width,
            )
            rows.append({"time_s": at, "measurement": asdict(measurement),
                         "decision": classify_candidate(measurement, model)})

    report = {
        "requirements": ["KTR-4.2", "KTR-4.2-F1"],
        "transport_valid": bool(on_capture.get("transport_valid")),
        "usb_overruns": int(on_capture.get("usb_overruns", 0)),
        "threshold_db": threshold,
        "segments": segments,
        "candidate_summary": dict(Counter(row["decision"] for row in rows)),
        "candidate_reasons": dict(Counter(row["measurement"]["reason"] for row in rows)),
        "rows": rows,
        "reference_frequency_hz": REFERENCE_FREQUENCY_HZ,
        "reference_obw99_hz": REFERENCE_OBW99_HZ,
        "off_sha256": off_capture["raw_sha256"],
        "on_sha256": on_capture["raw_sha256"],
        "model_sha256": MODEL_SHA256,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "product_acceptance": False,
        "physical_acceptance": False,
        "limits": [
            "USB taşmalı koşu yalnız tanıdır ve kabul paydasına alınmaz.",
            "Zaman seçimi önceki kapalı koşuya göre hedef bant enerjisinden yapılır.",
            "Frekans merkezi önceki CW, bant genişliği RF öncesi dosya manifestinden gelir.",
            "PC adayıdır; ürün F5, ARM ve FPGA kullanılmadı.",
        ],
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"transport_valid": report["transport_valid"], "usb_overruns": report["usb_overruns"],
                      "threshold_db": threshold, "segments": segments,
                      "summary": report["candidate_summary"], "reasons": report["candidate_reasons"],
                      "snr_db": [row["measurement"]["snr_db"] for row in rows]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", type=Path, required=True)
    parser.add_argument("--on", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.off, arguments.on, arguments.output)
