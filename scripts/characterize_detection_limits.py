"""Deterministic detector scale diagnostics; not RF or FPGA acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from algorithms.p0 import MultiscaleDetector
from algorithms.spectrum import SpectrumProcessor


def describe(result, first, stop):
    def coverage(candidate):
        return max(0, min(stop, candidate.end_bin + 1) - max(first, candidate.start_bin)) / (stop - first)
    return {"os_candidates": len(result.os_cfar.candidates),
            "wideband_candidates": len(result.recovery_candidates),
            "final_candidates": len(result.candidates),
            "best_single_candidate_coverage": max((coverage(c) for c in result.candidates), default=0),
            "candidates": [[c.start_bin, c.end_bin] for c in result.candidates]}


def characterize():
    detector = MultiscaleDetector()
    processor = SpectrumProcessor()
    records = []
    for width in (100, 256, 512, 2048, 4096):
        first = (4096 - width) // 2
        stop = first + width
        power = np.ones(4096)
        power[first:stop] = 100
        result = detector.process(power, frame_id=0)
        records.append({"input": "ideal_power_plateau", "width_bins": width,
                        "nominal_width_hz_at_2msps": width * 2e6 / 4096,
                        "power_sha256": hashlib.sha256(power.astype('<f8').tobytes()).hexdigest(),
                        **describe(result, first, stop)})
        for seed in range(16):
            rng = np.random.default_rng(31082026 + seed + width)
            coefficients = (rng.normal(size=4096) + 1j * rng.normal(size=4096)) * np.sqrt(power / 2)
            iq = np.fft.ifft(np.fft.ifftshift(coefficients))
            iq *= .65 / max(np.max(np.abs(iq.real)), np.max(np.abs(iq.imag)))
            packed = np.column_stack((np.rint(iq.real * 128), np.rint(iq.imag * 128))).astype(np.int8)
            decoded = (packed[:, 0].astype(float) + 1j * packed[:, 1].astype(float)) / 128
            spectrum = processor.process(decoded, sample_rate_hz=2e6, center_frequency_hz=2.4e9)
            measured = detector.process(spectrum.display.bin_power_fs2, frame_id=seed)
            records.append({"input": "generated_CI8_Hann_FFT", "width_bins": width, "seed": seed,
                            "iq_sha256": hashlib.sha256(packed.tobytes()).hexdigest(),
                            **describe(measured, first, stop)})
    return {"schema": "detection-scale-characterization-v1", "status": "characterized_not_accepted",
            "scope": "host_only_scale_limit_diagnostics", "transmit_enabled": False,
            "limits": ["İdeal düz güç girdisi fiziksel RF modeli değildir.",
                       "CI8 sahneleri sentetiktir; alıcı, FPGA ve saha kabulü değildir.",
                       "Yeni eşik seçilmedi; sonuçlardan ürün kabul eşiği türetilmedi.",
                       "Bütün pencereyi dolduran güç artışı yerel gürültü artışından tek başına ayrılamaz."],
            "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ("algorithms/p0/detection.py", "algorithms/spectrum/dsp.py",
                                           "scripts/characterize_detection_limits.py")},
            "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tespit ölçek sınırını karakterize et")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = characterize()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": len(report["records"])}, ensure_ascii=False))
