#!/usr/bin/env python3
"""PÇ-03 PC adaptörünü dondurulmuş sentetik geliştirme alanında doğrula."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_analog_detection import classify_parameter_frames
from digital_analog_detection import train_classifier as training


EVIDENCE = ROOT / "results/evidence/phase08/automatic-domain-pc-wide-guard-20260912.json"
SEED = 20260912
TRIALS_PER_FAMILY = 400
SOURCES = (
    "digital_analog_detection/classifier_model.py",
    "digital_analog_detection/feature_extractor_v1.py",
    "digital_analog_detection/integration.py",
    "digital_analog_detection/train_classifier.py",
    "scripts/verify_automatic_domain_integration.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate() -> dict[str, object]:
    rng = np.random.default_rng(SEED)
    sample_count = 4 * 4096
    families = (
        ("AM", lambda: training.gen_am(sample_count, training.FS, rng), "Analog"),
        ("FM", lambda: training.gen_fm(sample_count, training.FS, rng), "Analog"),
        ("BPSK", lambda: training.gen_psk(sample_count, training.FS, rng, order=2), "Sayısal"),
        ("QPSK", lambda: training.gen_psk(sample_count, training.FS, rng, order=4), "Sayısal"),
    )
    results = []
    wide_results = []
    for name, generate, truth in families:
        correct = wrong = uncertain = 0
        wide_correct = wide_wrong = wide_uncertain = 0
        for _ in range(TRIALS_PER_FAMILY):
            snr_db = float(rng.uniform(4.0, 30.0))
            samples = training.add_noise(generate(), snr_db, rng)
            observed = classify_parameter_frames(
                tuple(samples.reshape(4, 4096)),
                sample_rate_hz=training.FS,
                lower_shifted_bin=1792,
                upper_shifted_bin=2303,
                snr_db=snr_db,
            )
            wide_observed = classify_parameter_frames(
                tuple(samples.reshape(4, 4096)),
                sample_rate_hz=training.FS,
                lower_shifted_bin=1045,
                upper_shifted_bin=3458,
                snr_db=snr_db,
            )
            if observed.state != "valid":
                uncertain += 1
            elif observed.value == truth:
                correct += 1
            else:
                wrong += 1
            if wide_observed.state != "valid":
                wide_uncertain += 1
            elif wide_observed.value == truth:
                wide_correct += 1
            else:
                wide_wrong += 1
        definite = correct + wrong
        results.append(
            {
                "family": name,
                "truth": truth,
                "trials": TRIALS_PER_FAMILY,
                "correct": correct,
                "wrong": wrong,
                "uncertain": uncertain,
                "coverage": definite / TRIALS_PER_FAMILY,
                "definite_accuracy": correct / definite if definite else 0.0,
            }
        )
        wide_definite = wide_correct + wide_wrong
        wide_results.append({
            "family": name, "truth": truth, "trials": TRIALS_PER_FAMILY,
            "correct": wide_correct, "wrong": wide_wrong, "uncertain": wide_uncertain,
            "coverage": wide_definite / TRIALS_PER_FAMILY,
            "definite_accuracy": wide_correct / wide_definite if wide_definite else 0.0,
        })
    return {
        "schema": "automatic-domain-pc-integration-v1",
        "status": "development_passed_physical_rf_open",
        "seed": SEED,
        "trials_per_family": TRIALS_PER_FAMILY,
        "input": {
            "sample_rate_hz": training.FS,
            "frames": 4,
            "samples_per_frame": 4096,
            "snr_db_range": [4.0, 30.0],
            "analysis_span": [1792, 2303],
            "wide_analysis_span": [1045, 3458],
        },
        "families": results,
        "wide_families": wide_results,
        "gates": {
            "maximum_wrong_definite_per_family": 5,
            "minimum_definite_accuracy": 0.98,
            "passed": all(
                item["wrong"] <= 5 and item["definite_accuracy"] >= 0.98
                for item in results + wide_results
            ),
        },
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
        "claim_boundary": (
            "Aynı sentetik üretici alanındaki geliştirme doğrulamasıdır. "
            "Canlı HackRF, bağımsız RF, saha doğruluğu veya ürün kabulü değildir."
        ),
    }


def check() -> bool:
    try:
        recorded = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        return recorded == evaluate() and recorded["gates"]["passed"] is True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        document = evaluate()
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    passed = check()
    print(f"PÇ-03 otomatik PC sınıflandırma: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
