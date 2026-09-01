"""Create source-bound host-only evidence for 8 MHz coarse RX proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.p0.coarse_detection import CoarseSpectrumDetector


SAMPLE_RATE_HZ = 8_000_000.0
CENTER_HZ = 2_401_500_000.0
COUNT = 32
SEED_BASE = 2026090300


def _power(family: str, seed: int) -> tuple[np.ndarray, tuple[int, int] | None]:
    count = 16_384
    rng = np.random.default_rng(seed)
    expected = np.ones(count, dtype=np.float64)
    expected_support = None
    if family == "noise_slope_12db":
        expected = np.power(10.0, np.linspace(-6.0, 6.0, count) / 10.0)
    elif family == "noise_step_12db":
        expected[count // 2:] = 10.0 ** 1.2
    elif family.startswith("signal_"):
        width_hz = int(family.split("_")[1])
        width = round(width_hz / SAMPLE_RATE_HZ * count)
        # Narrow/detail targets use the product's -1.5 MHz offset position;
        # wider-than-3 MHz scale diagnostics are centered so support remains
        # inside this single finite observation.
        offset_hz = -1_500_000.0 if width_hz <= 3_000_000 else 0.0
        offset = round(offset_hz / SAMPLE_RATE_HZ * count)
        first = count // 2 + offset - width // 2
        stop = first + width
        expected[first:stop] += 25.0
        expected_support = (first, stop)
    coefficients = (
        rng.normal(size=count) + 1j * rng.normal(size=count)
    ) * np.sqrt(expected / 2.0)
    iq = np.fft.ifft(np.fft.ifftshift(coefficients))
    iq *= 0.65 / max(np.max(np.abs(iq.real)), np.max(np.abs(iq.imag)))
    packed = np.column_stack((np.rint(iq.real * 128), np.rint(iq.imag * 128))).astype(np.int8)
    decoded = (packed[:, 0].astype(float) + 1j * packed[:, 1].astype(float)) / 128.0
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(count) / count)
    return np.abs(np.fft.fftshift(np.fft.fft(decoded * window))) ** 2, expected_support


def verify() -> dict[str, object]:
    families = (
        "noise_flat", "noise_slope_12db", "noise_step_12db",
        "signal_100000", "signal_500000", "signal_1000000", "signal_2000000",
        "signal_4000000", "signal_6000000", "signal_8000000",
    )
    records = []
    timings_ms = []
    for family_index, family in enumerate(families):
        for index in range(COUNT):
            power, support = _power(family, SEED_BASE + family_index * 1000 + index)
            started = time.perf_counter()
            result = CoarseSpectrumDetector().process(
                power,
                center_frequency_hz=CENTER_HZ,
                sample_rate_hz=SAMPLE_RATE_HZ,
                sequence_number=index,
            )
            timings_ms.append((time.perf_counter() - started) * 1000.0)
            coverage = None
            if support is not None:
                first, stop = support
                expected_lower = CENTER_HZ + (first - 8192) * SAMPLE_RATE_HZ / 16_384
                expected_upper = CENTER_HZ + (stop - 8192) * SAMPLE_RATE_HZ / 16_384
                width = expected_upper - expected_lower
                coverage = max((
                    max(0.0, min(expected_upper, item.upper_frequency_hz)
                        - max(expected_lower, item.lower_frequency_hz)) / width
                    for item in result.candidates
                ), default=0.0)
            records.append({
                "family": family,
                "seed": SEED_BASE + family_index * 1000 + index,
                "candidate_count": len(result.candidates),
                "best_coverage": coverage,
            })

    summaries = []
    passed = True
    for family in families:
        rows = [item for item in records if item["family"] == family]
        if family.startswith("signal_") and family not in {"signal_6000000", "signal_8000000"}:
            recovered = sum(float(item["best_coverage"]) >= 0.8 for item in rows)
            family_passed = recovered == COUNT
            summaries.append({"family": family, "frames": COUNT,
                              "recovered_at_least_80_percent": recovered,
                              "status": "passed" if family_passed else "failed"})
        elif family == "signal_6000000":
            recovered = sum(float(item["best_coverage"]) >= 0.8 for item in rows)
            family_passed = True
            summaries.append({"family": family, "frames": COUNT,
                              "recovered_at_least_80_percent": recovered,
                              "status": "characterized_not_guaranteed"})
        elif family == "signal_8000000":
            candidates = sum(bool(item["candidate_count"]) for item in rows)
            family_passed = candidates == 0
            summaries.append({"family": family, "frames": COUNT,
                              "frames_with_candidate": candidates,
                              "status": "known_limit_passed" if family_passed else "unexpected_result"})
        else:
            false_frames = sum(bool(item["candidate_count"]) for item in rows)
            family_passed = false_frames == 0
            summaries.append({"family": family, "frames": COUNT,
                              "frames_with_false_candidate": false_frames,
                              "status": "passed" if family_passed else "failed"})
        passed = passed and family_passed

    source_paths = (
        "algorithms/p0/coarse_detection.py",
        "algorithms/p0/detection.py",
        "scripts/verify_phase08_coarse_detection.py",
    )
    return {
        "schema": "phase08-coarse-rx-detection-v1",
        "status": "passed" if passed else "failed",
        "scope": "host_only_8msps_coarse_proposal",
        "transmit_enabled": False,
        "fpga_confirmation": False,
        "profile": {
            "input_sample_rate_hz": SAMPLE_RATE_HZ,
            "input_fft_bins": 16_384,
            "energy_rebin_bins": 4,
            "detector_bins": 4_096,
            "usable_half_band_hz": 3_000_000,
            "dc_guard_hz": 100_000,
        },
        "summaries": summaries,
        "timing_ms": {
            "samples": len(timings_ms),
            "p50": float(np.percentile(timings_ms, 50)),
            "p95": float(np.percentile(timings_ms, 95)),
            "maximum": max(timings_ms),
        },
        "limits": [
            "Bu sonuç sentetik CI8/Hann spektrumları ve bağımsız tohumlarla host referans kabulüdür; RF veya FPGA kabulü değildir.",
            "Kaba RX adayı operatör arayüzünde FPGA tespitinden ayrı gösterilir.",
            "Kabul zarfı bu deneyde 100 kHz-4 MHz'tir; 6 MHz ailesi karakterize edilir ancak garanti edilmez.",
            "Tüm 8 MHz gözlemi dolduran gürültü-benzeri yayın bağımsız referans bulunmadığı için bilinçli açık sınırdır.",
            "Ölçülen süre yalnız detector çağrısıdır; FFT, USB, Qt çizimi ve tarama ayar süresi dahil değildir.",
        ],
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in source_paths
        },
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Önceki kanıtın üzerine yazılmaz.")
    report = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "summaries": report["summaries"],
                      "timing_ms": report["timing_ms"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
