"""Pre-binding PHASE-04-R2 mathematical calibration and locked constants."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from reference.spectrum import periodic_hann


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"
PHASE03_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"

R2_COMPARISON_ID = "phase04-r2-band-recovery"
R2_METHOD_LOCK_SCHEMA = 1
IID_TRIMMED_MEAN_EXPECTATION = 0.7827495643569612
IID_TRIMMED_MEAN_CORRECTION = 1.2775478205746595
HANN_CALIBRATION_SEED = 20260421
HANN_END_TO_END_SEED = 20260422
HANN_CALIBRATION_FRAMES = 1_048_576
HANN_CALIBRATION_BATCH = 4096
HANN_EXPECTED_MEAN = 0.7935582839535308
HANN_EXPECTED_VARIANCE = 0.045195218989907526
HANN_CORRECTION = 1.2601468855166762
HANN_EXPECTED_CI95 = (0.7931578114136613, 0.7939587564933988)
HANN_END_TO_END_FRAMES = 16_384
HANN_END_TO_END_EXPECTED_MEAN = 0.7932933253285658
HANN_END_TO_END_EXPECTED_VARIANCE = 0.045791680516721535
NOMINAL_SEED_RATIO = 6.907755278982137
NOMINAL_GROW_RATIO = 2.995732273553991
MORPHOLOGY_FRACTION_STEPS = 32
MORPHOLOGY_PEAK_RATIOS = (NOMINAL_SEED_RATIO, 10.0, 100.0)
MORPHOLOGY_REQUIRED_GAP = 0.5
MORPHOLOGY_EXPECTED_LINE_MAX = 0.7745641838351786
MORPHOLOGY_EXPECTED_BROAD_MIN = 4.626610599941332
MORPHOLOGY_MOMENT_THRESHOLD = 2.7005873918882553
R2_OOS_BASE_SEED = 20260423
R2_OOS_TRIALS_PER_FAMILY = 32


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def iid_trimmed_mean_expectation() -> float:
    """Exact finite-sample E[mean(X_(7)..X_(26))] for 32 Exp(mean=1)."""
    harmonic = [0.0]
    for value in range(1, 33):
        harmonic.append(harmonic[-1] + 1.0 / value)
    order_means = [harmonic[32] - harmonic[32 - rank] for rank in range(7, 27)]
    return float(sum(order_means) / len(order_means))


def hann_complex_covariance(block_length: int = 16) -> np.ndarray:
    """Exact normalized covariance of contiguous periodic-Hann FFT noise bins."""
    matrix = np.zeros((block_length, block_length), dtype=np.float64)
    for row in range(block_length):
        for column in range(block_length):
            lag = abs(row - column)
            matrix[row, column] = (
                1.0 if lag == 0 else -2.0 / 3.0 if lag == 1 else 1.0 / 6.0 if lag == 2 else 0.0
            )
    return matrix


def _trimmed(values: np.ndarray) -> np.ndarray:
    ordered = np.sort(np.asarray(values, dtype=np.float64), axis=1)
    return np.mean(ordered[:, 6:26], axis=1)


def hann_covariance_calibration(*, full: bool = True) -> dict[str, Any]:
    """Fixed-seed Monte Carlo over the analytic Hann covariance model."""
    frames = HANN_CALIBRATION_FRAMES if full else 16_384
    batch = HANN_CALIBRATION_BATCH
    covariance = hann_complex_covariance()
    eigenvalues = np.linalg.eigvalsh(covariance)
    factor = np.linalg.cholesky(covariance)
    rng = np.random.default_rng(HANN_CALIBRATION_SEED)
    total = total_square = 0.0
    count = 0
    batch_means: list[float] = []
    for start in range(0, frames, batch):
        size = min(batch, frames - start)
        blocks: list[np.ndarray] = []
        for _ in range(2):
            real = rng.normal(size=(size, 16))
            imaginary = rng.normal(size=(size, 16))
            complex_bins = (real @ factor.T + 1j * (imaginary @ factor.T)) / math.sqrt(2.0)
            blocks.append(np.abs(complex_bins) ** 2)
        estimates = _trimmed(np.concatenate(blocks, axis=1))
        batch_means.append(float(np.mean(estimates)))
        total += float(np.sum(estimates))
        total_square += float(np.dot(estimates, estimates))
        count += size
    mean = total / count
    variance = (total_square - count * mean * mean) / (count - 1)
    means = np.asarray(batch_means, dtype=np.float64)
    batch_se = float(np.std(means, ddof=1) / math.sqrt(means.size))
    # 256-batch t critical value; quick mode is diagnostic and does not pass the full gate.
    t_critical = 1.969273 if means.size == 256 else 1.96
    interval = (float(np.mean(means) - t_critical * batch_se), float(np.mean(means) + t_critical * batch_se))
    passed = (
        full
        and abs(mean - HANN_EXPECTED_MEAN) <= 5e-6
        and abs(variance - HANN_EXPECTED_VARIANCE) <= 5e-4
        and 0.5 * (interval[1] - interval[0]) <= 0.0006
        and float(eigenvalues[0]) > 0.0
    )
    return {
        "status": "passed" if passed else "failed" if full else "diagnostic",
        "model": "periodic-hann-complex-gaussian-covariance",
        "seed": HANN_CALIBRATION_SEED,
        "frames": frames,
        "batch_size": batch,
        "batch_count": len(batch_means),
        "trimmed_order_statistics": [7, 26],
        "mean_ratio": mean,
        "variance_ratio_squared": variance,
        "batch_t_ci95": list(interval),
        "correction": 1.0 / mean,
        "minimum_covariance_eigenvalue": float(eigenvalues[0]),
        "expected_mean_ratio": HANN_EXPECTED_MEAN,
        "expected_variance_ratio_squared": HANN_EXPECTED_VARIANCE,
        "locked_correction_candidate": HANN_CORRECTION,
    }


def hann_end_to_end_calibration(*, frames: int = HANN_END_TO_END_FRAMES) -> dict[str, Any]:
    """Stream the real periodic-Hann/FFT normalization on an independent seed."""
    length = 4096
    batch = 128
    window = periodic_hann(length)
    power_sum = float(np.sum(window * window))
    rng = np.random.default_rng(HANN_END_TO_END_SEED)
    values: list[np.ndarray] = []
    batch_means: list[float] = []
    for start in range(0, frames, batch):
        size = min(batch, frames - start)
        samples = (rng.normal(size=(size, length)) + 1j * rng.normal(size=(size, length))) / math.sqrt(2.0)
        power = np.abs(np.fft.fft(samples * window, axis=1)) ** 2 / power_sum
        references = np.concatenate((power[:, 1000:1016], power[:, 1200:1216]), axis=1)
        estimates = _trimmed(references)
        values.append(estimates)
        batch_means.append(float(np.mean(estimates)))
    combined = np.concatenate(values)
    means = np.asarray(batch_means, dtype=np.float64)
    mean = float(np.mean(combined))
    variance = float(np.var(combined, ddof=1))
    batch_se = float(np.std(means, ddof=1) / math.sqrt(means.size))
    interval = (float(np.mean(means) - 1.97882 * batch_se), float(np.mean(means) + 1.97882 * batch_se))
    corrected_interval = (interval[0] * HANN_CORRECTION, interval[1] * HANN_CORRECTION)
    passed = (
        frames == HANN_END_TO_END_FRAMES
        and max(interval[0], HANN_EXPECTED_CI95[0]) <= min(interval[1], HANN_EXPECTED_CI95[1])
        and corrected_interval[0] <= 1.0 <= corrected_interval[1]
        and abs(mean * HANN_CORRECTION - 1.0) <= 0.005
    )
    return {
        "status": "passed" if passed else "failed",
        "pipeline": "phase02-periodic-hann-fft-power",
        "seed": HANN_END_TO_END_SEED,
        "frames": frames,
        "reference_blocks": [[1000, 1015], [1200, 1215]],
        "mean_ratio": mean,
        "variance_ratio_squared": variance,
        "batch_t_ci95": list(interval),
        "corrected_mean_bias": mean * HANN_CORRECTION - 1.0,
        "corrected_ci95": list(corrected_interval),
    }


def _bridge(mask: np.ndarray) -> np.ndarray:
    result = mask.copy()
    if result.size >= 3:
        result[1:-1] |= mask[:-2] & mask[2:]
    return result


def _component_moment(raw_ratio: np.ndarray, peak_index: int, bins: np.ndarray) -> float:
    mask = _bridge(raw_ratio >= NOMINAL_GROW_RATIO)
    if not bool(mask[peak_index]):
        raise ValueError("analytic component does not reach the nominal grow ratio")
    lower = upper = peak_index
    while lower > 0 and mask[lower - 1]:
        lower -= 1
    while upper + 1 < mask.size and mask[upper + 1]:
        upper += 1
    smoothed = np.convolve(raw_ratio, np.asarray([0.25, 0.5, 0.25]), mode="same")
    weights = np.zeros_like(smoothed)
    weights[lower : upper + 1] = np.maximum(smoothed[lower : upper + 1] - 1.0, 0.0)
    total = float(np.sum(weights))
    center = float(np.sum(weights * bins) / total)
    return float(np.sum(weights * (bins - center) ** 2) / total)


def _raised_cosine_psd(frequency_bins: np.ndarray, symbol_rate_bins: float, beta: float = 0.35) -> np.ndarray:
    absolute = np.abs(frequency_bins)
    flat = (1.0 - beta) * symbol_rate_bins / 2.0
    stop = (1.0 + beta) * symbol_rate_bins / 2.0
    result = np.zeros_like(absolute)
    result[absolute <= flat] = 1.0
    transition = (absolute > flat) & (absolute <= stop)
    result[transition] = 0.5 * (
        1.0 + np.cos(np.pi * (absolute[transition] - flat) / (beta * symbol_rate_bins))
    )
    return result


def morphology_calibration() -> dict[str, Any]:
    """Derive the line/broad split from a fixed analytic suite, never binding trials."""
    length = 4096
    window = periodic_hann(length)
    local_bins = np.arange(-88, 89, dtype=np.float64)
    line_moments: list[float] = []
    broad_moments: list[float] = []
    sample_index = np.arange(length, dtype=np.float64)
    for step in range(MORPHOLOGY_FRACTION_STEPS + 1):
        offset = step / 64.0
        tone = np.exp(1j * 2.0 * np.pi * offset * sample_index / length)
        tone_power = np.abs(np.fft.fftshift(np.fft.fft(tone * window))) ** 2
        local = tone_power[length // 2 - 88 : length // 2 + 89]
        local /= float(np.max(local))
        rrc = _raised_cosine_psd(local_bins - offset, 8.0)
        for ratio in MORPHOLOGY_PEAK_RATIOS:
            line_raw = 1.0 + (ratio - 1.0) * local
            broad_raw = 1.0 + (ratio - 1.0) * rrc
            line_moments.append(_component_moment(line_raw, int(np.argmax(line_raw)), local_bins))
            broad_moments.append(_component_moment(broad_raw, int(np.argmax(broad_raw)), local_bins))
    line_max = max(line_moments)
    broad_min = min(broad_moments)
    threshold = 0.5 * (line_max + broad_min)
    passed = (
        broad_min - line_max >= MORPHOLOGY_REQUIRED_GAP
        and abs(line_max - MORPHOLOGY_EXPECTED_LINE_MAX) <= 1e-9
        and abs(broad_min - MORPHOLOGY_EXPECTED_BROAD_MIN) <= 1e-9
        and abs(threshold - MORPHOLOGY_MOMENT_THRESHOLD) <= 1e-9
    )
    return {
        "status": "passed" if passed else "failed",
        "fractional_offsets": [0.0, 0.5, 1.0 / 64.0],
        "peak_to_noise_ratios": list(MORPHOLOGY_PEAK_RATIOS),
        "line_maximum_second_moment_bins2": line_max,
        "broad_minimum_second_moment_bins2": broad_min,
        "separation_margin_bins2": broad_min - line_max,
        "required_margin_bins2": MORPHOLOGY_REQUIRED_GAP,
        "locked_threshold_bins2": threshold,
        "threshold_rule": "arithmetic-midpoint-of-fixed-analytic-extrema",
    }


def build_method_lock(calibration: dict[str, Any], end_to_end: dict[str, Any], morphology: dict[str, Any]) -> dict[str, Any]:
    if any(item.get("status") != "passed" for item in (calibration, end_to_end, morphology)):
        raise ValueError("R2 method lock requires every pre-binding calibration gate")
    document: dict[str, Any] = {
        "schema_version": R2_METHOD_LOCK_SCHEMA,
        "phase": "PHASE-04-R2",
        "comparison_id": R2_COMPARISON_ID,
        "methods": {
            "analysis_window": "analysis.clustered-regions-v1",
            "noise": "noise.trimmed-mean-20-hann-calibrated-v1",
            "bandwidth": "band.temporal-morphology-envelope-v1",
        },
        "noise_calibration": calibration,
        "noise_end_to_end_validation": end_to_end,
        "nominal_ratios": {
            "seed": NOMINAL_SEED_RATIO,
            "grow": NOMINAL_GROW_RATIO,
            "exact_pfa_claimed": False,
            "mask_domain": "raw-psd",
        },
        "morphology_calibration": morphology,
        "component_contract": {
            "single_bin_bridge": 1,
            "maximum_gap_bins": 24,
            "maximum_components": 32,
            "maximum_search_bins": 176,
            "unsupported_grow_components_retained": False,
        },
        "temporal_contract": {
            "minimum_confirmed_observed_frames": 2,
            "maximum_history_frames": 3,
            "band_history_payload_bytes": 6528,
            "combined_parameter_history_payload_bytes": 74368,
        },
        "out_of_sample": {
            "base_seed": R2_OOS_BASE_SEED,
            "trials_per_family": R2_OOS_TRIALS_PER_FAMILY,
            "snr_db_order": [12.0, -6.0, 0.0, 6.0],
            "binding": False,
        },
        "catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest(),
        "phase03_profile_sha256": hashlib.sha256(PHASE03_PROFILE_PATH.read_bytes()).hexdigest(),
    }
    document["identity_sha256"] = hashlib.sha256(canonical_json_bytes(document)).hexdigest()
    return document
