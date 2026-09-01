"""Compare noise-reference shortcuts on independent cases, without changing the detector."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.p0.detection import MultiscaleDetector, P0_WIDEBAND_RECOVERY_PROFILE


def global_median_supports(power):
    """Same energy/span rule, replacing regional median with one global median.

    This is deliberately a comparison, not a proposed product or calibrated CFAR.
    The median/ln(2) conversion assumes identically distributed exponential power.
    """
    cfg = P0_WIDEBAND_RECOVERY_PROFILE
    threshold = np.median(power) / np.log(2) * cfg.noise_multiplier
    prefix = np.r_[0.0, np.cumsum(power)]
    centers = np.arange(20, 4096 - 20)
    mask = (prefix[centers + 17] - prefix[centers - 15]) / 32 > threshold
    bins = centers[mask]
    if not len(bins):
        return []
    groups = np.split(bins, np.flatnonzero(np.diff(bins) > 2) + 1)
    return [(int(g[0] + 15), int(g[-1] - 16)) for g in groups
            if g[-1] - 16 - (g[0] + 15) + 1 >= cfg.minimum_span_bins]


def flanked_global_supports(power):
    """Require low-power evidence on both sides of each global proposal."""
    supports = global_median_supports(power)
    flank = 128
    accepted = []
    for first, stop in supports:
        if first < flank or stop + flank >= power.size:
            continue
        left = np.median(power[first - flank:first]) / np.log(2)
        right = np.median(power[stop + 1:stop + 1 + flank]) / np.log(2)
        support_mean = float(np.mean(power[first:stop + 1]))
        if support_mean > P0_WIDEBAND_RECOVERY_PROFILE.noise_multiplier * max(left, right):
            accepted.append((first, stop))
    return accepted


def regional_quantile_flanked_supports(power):
    """RTL-feasible comparison using only the existing 16 regional medians.

    The fourth-lowest regional median proposes contiguous support, then one
    complete region beyond each edge supplies an independent local reference.
    Supports of 256 bins or less remain owned by the current regional method.
    """
    cfg = P0_WIDEBAND_RECOVERY_PROFILE
    shaped = power.reshape(16, cfg.region_size)
    median_twice = np.partition(shaped, (127, 128), axis=1)[:, 127:129].sum(axis=1)
    frame_reference_twice = float(np.partition(median_twice, 3)[3])
    prefix = np.r_[0.0, np.cumsum(power)]
    centers = np.arange(20, 4096 - 20)
    window_sums = prefix[centers + 17] - prefix[centers - 15]
    threshold_sum = frame_reference_twice / (2 * np.log(2)) * cfg.noise_multiplier * 32
    bins = centers[window_sums > threshold_sum]
    if not len(bins):
        return []
    groups = np.split(bins, np.flatnonzero(np.diff(bins) > 2) + 1)
    accepted = []
    for group in groups:
        first, stop = int(group[0] + 15), int(group[-1] - 16)
        span = stop - first + 1
        if span <= cfg.region_size:
            continue
        left_region = first // cfg.region_size - 1
        right_region = stop // cfg.region_size + 1
        if left_region < 0 or right_region >= median_twice.size:
            continue
        flank_noise = max(median_twice[left_region], median_twice[right_region]) / (2 * np.log(2))
        if float(np.mean(power[first:stop + 1])) > cfg.noise_multiplier * flank_noise:
            accepted.append((first, stop))
    return accepted


def evaluate():
    detector = MultiscaleDetector()
    records = []
    # Separate from the original scale-diagnostic seeds; no parameter fitting.
    seed_base, count = 2026090201, 64
    families = ["noise_flat", "noise_slope_12db", "noise_step_12db",
                "signal_100", "signal_512", "signal_1024", "signal_2048", "signal_4096"]
    for family in families:
        for seed in range(count):
            rng = np.random.default_rng(seed_base + seed)
            noise = np.ones(4096)
            if family == "noise_slope_12db":
                noise = np.power(10, np.linspace(-6, 6, 4096) / 10)
            elif family == "noise_step_12db":
                noise[2048:] = 10 ** 1.2
            width = int(family.split("_")[1]) if family.startswith("signal_") else 0
            first, stop = (4096 - width) // 2, (4096 + width) // 2
            expected = noise.copy()
            expected[first:stop] += 100.0 if width else 0.0
            coefficients = (rng.normal(size=4096) + 1j * rng.normal(size=4096)) * np.sqrt(expected / 2)
            iq = np.fft.ifft(np.fft.ifftshift(coefficients))
            iq *= .65 / max(np.max(np.abs(iq.real)), np.max(np.abs(iq.imag)))
            packed = np.column_stack((np.rint(iq.real * 128), np.rint(iq.imag * 128))).astype(np.int8)
            decoded = (packed[:, 0].astype(float) + 1j * packed[:, 1].astype(float)) / 128
            power = np.abs(np.fft.fftshift(np.fft.fft(decoded * np.hanning(4096)))) ** 2
            original = [(c.start_bin, c.end_bin) for c in detector.recovery_candidates(power)]
            comparison = global_median_supports(power)
            results = {}
            flanked = flanked_global_supports(power)
            for method, candidates in (("current_regional", original),
                                       ("global_median_comparison", comparison),
                                       ("flanked_global_comparison", flanked),
                                       ("regional_quantile_flanked_comparison", regional_quantile_flanked_supports(power))):
                cover = max((max(0, min(stop, hi + 1) - max(first, lo)) / width
                             for lo, hi in candidates), default=0) if width else None
                results[method] = {"candidates": candidates, "best_coverage": cover,
                    "recovered": cover >= .8 if cover is not None else None,
                    "false_broadband_candidate": bool(candidates) if not width else None}
            records.append({"family": family, "seed": seed_base + seed,
                "iq_sha256": hashlib.sha256(packed.tobytes()).hexdigest(), "results": results})
    summaries = []
    for family in families:
        group = [r for r in records if r["family"] == family]
        for method in ("current_regional", "global_median_comparison", "flanked_global_comparison",
                       "regional_quantile_flanked_comparison"):
            summaries.append({"family": family, "method": method, "frames": count,
                "recovered_frames": sum(r["results"][method]["recovered"] is True for r in group),
                "frames_with_false_broadband_candidate": sum(r["results"][method]["false_broadband_candidate"] is True for r in group)})
    return {"schema": "noise-reference-comparison-v1", "status": "diagnostic_not_product_acceptance",
        "transmit_enabled": False, "product_algorithm_changed": False,
        "profile": asdict(P0_WIDEBAND_RECOVERY_PROFILE), "summaries": summaries, "records": records,
        "limits": ["Sentetik CI8/Hann spektrumlarıdır; RF, FPGA veya olay/dakika kabulü değildir.",
                   "Yalnız geniş bant kurtarma karşılaştırılır; dar bant OS-CFAR değiştirilmez.",
                   "Renkli gürültü aileleri hedef yayın içermeyen, tasarımcının bildiği testlerdir.",
                   "Global referansın homojen gürültü varsayımı sahada kendiliğinden sağlanmaz.",
                   "İki taraflı 128-bin referansa göre 2,5 kat bütünleşik enerji koşulu yöntem önerisi değil, karşı örnek filtresidir.",
                   "Pencere kenarına değen geniş yayın flanksızdır ve ayrı ayarla yeniden ziyaret gerektirir.",
                   "Bölgesel-kantil karşılaştırması mevcut 16 medyanın dördüncü küçüğünü ve adayın iki yanındaki tam bölgeleri kullanır; ürün değildir.",
                   "Bütün pencereyi dolduran yayın için bağımsız referans eksikliği devam eder."],
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("algorithms/p0/detection.py", "scripts/evaluate_wideband_noise_reference.py")}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geniş bant gürültü referansı karşılaştırması; ürün ayarını değiştirmez")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Önceki karşılaştırmanın üzerine yazılmaz.")
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summaries"], ensure_ascii=False))
