"""Seçili kanal modelini ayrı tohumlu sentetik eğitim ve sınamayla üret."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from digital_analog_detection import train_classifier as legacy
from digital_analog_detection.channel_features import selected_channel_features, PREPROCESSING_ID
from digital_analog_detection.classifier_model import FEATURE_ORDER


def dataset(seed, count):
    rng = np.random.default_rng(seed)
    vectors, labels, families = [], [], []
    n, fs = 16384, 2_000_000.
    t = np.arange(n) / fs
    for family in ("AM", "FM", "NFM", "BPSK", "QPSK"):
        for _ in range(count):
            if family == "AM":
                clean = legacy.gen_am(n, fs, rng)
            elif family == "FM":
                clean = legacy.gen_fm(n, fs, rng)
            elif family == "NFM":
                mod = rng.uniform(300, 4000)
                dev = rng.uniform(1500, 10000)
                clean = np.exp(2j * np.pi * rng.uniform(-5000, 5000) * t + 1j * dev / mod * np.sin(2 * np.pi * mod * t))
            else:
                clean = legacy.gen_psk(n, fs, rng, order=2 if family == "BPSK" else 4)
            # Bağımsız temiz örnek yalnız eğitim aralığını tanımlar; modele verilmez.
            offset = rng.uniform(-400000, 400000)
            clean *= np.exp(2j * np.pi * offset * t)
            psd = np.mean(np.abs(np.fft.fftshift(np.fft.fft(clean.reshape(4, 4096) * np.hanning(4096), axis=1), axes=1)) ** 2, axis=0)
            cumulative = np.cumsum(psd) / psd.sum()
            margin = int(rng.integers(24, 129))
            lower = max(56, int(np.searchsorted(cumulative, .0005)) - margin)
            upper = min(4039, int(np.searchsorted(cumulative, .9995)) + margin)
            samples = legacy.add_noise(clean, float(rng.uniform(4, 30)), rng)
            channel = selected_channel_features(samples.reshape(4, 4096), lower, upper)
            vectors.append([channel.features[key] for key in FEATURE_ORDER])
            labels.append(int(family in ("BPSK", "QPSK")))
            families.append(family)
    return np.asarray(vectors), np.asarray(labels), np.asarray(families)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    x, y, _ = dataset(2026091601, 400)
    scaler = StandardScaler().fit(x)
    scaled = scaler.transform(x)
    model = LogisticRegression(max_iter=2000, random_state=0).fit(scaled, y)
    # Eğitim gözlemlerinin kapsam zarfı; bilinmeyen aile tanıma garantisi değildir.
    lower, upper = scaled.min(axis=0) - .5, scaled.max(axis=0) + .5
    test, truth, families = dataset(2026091602, 200)
    xt = scaler.transform(test)
    p = model.predict_proba(xt)[:, 1]
    accepted = (np.maximum(p, 1 - p) >= .90) & np.all((xt >= lower) & (xt <= upper), axis=1)
    reports = []
    for family in np.unique(families):
        mask = families == family
        right = int(np.sum(mask & accepted & ((p >= .5) == truth)))
        wrong = int(np.sum(mask & accepted & ((p >= .5) != truth)))
        reports.append({"family": str(family), "correct": right, "wrong": wrong,
                        "uncertain": int(np.sum(mask & ~accepted))})
    document = {"profile_id": "selected-channel-synthetic-logreg-v2", "preprocessing_id": PREPROCESSING_ID,
                "feature_order": FEATURE_ORDER, "scaler_mean": scaler.mean_.tolist(),
                "scaler_scale": scaler.scale_.tolist(), "coefficients": model.coef_[0].tolist(),
                "intercept": float(model.intercept_[0]), "feature_lower": lower.tolist(),
                "feature_upper": upper.tolist(), "confidence_threshold": .90,
                "physical_acceptance": False, "product_acceptance": False,
                "training_seed": 2026091601, "training_samples": len(y),
                "training_source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                    for path in ("digital_analog_detection/channel_features.py", "digital_analog_detection/feature_extractor_v1.py",
                                 "digital_analog_detection/train_classifier.py", "scripts/train_selected_channel_domain.py")}}
    report = {"families": reports, "test_seed": 2026091602, "test_samples": len(truth),
              "claim": "Ayrı tohum, aynı sentetik aile üreticileri; gerçek RF kabulü değildir."}
    # Kapı test sonucu görülmeden sabittir; başarısız model ürün dosyasına yazılmaz.
    report["passed"] = all(row["wrong"] <= 4 and row["correct"] >= 150 and
                           row["correct"] / max(1, row["correct"] + row["wrong"]) >= .98 for row in reports)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit("Model geliştirme kapısını geçmedi; ürün modeli yazılmadı.")
    with args.model.open("x", encoding="utf-8") as stream:
        stream.write('"""Seçili kanal deneysel modeli; gerçek RF kabulü açık."""\nMODEL = ' + repr(document) + '\n')


if __name__ == "__main__":
    main()
