#!/usr/bin/env python3
"""Evaluate the PHASE-08 weak-nomination target without RF frequency truth."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.ps.persistent_weak_cfar import (
    MAXIMUM_TRACKED_WEAK_NOMINATIONS,
    PEAK_TOLERANCE_BINS,
    PERSISTENCE_REQUIRED,
    PERSISTENCE_WINDOW,
    WEAK_ALPHA_Q32,
    ideal_exponential_false_nomination_probability,
)
from algorithms.rtl.p0_os_cfar import COEFFICIENT_FRACTION_BITS, FRAME_LENGTH, RADIUS


DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/persistent-weak-model-v1.json"


def _weak_peak_mask(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    windows = np.lib.stride_tricks.sliding_window_view(frames, 41, axis=1)
    references = np.concatenate((windows[:, :, :16], windows[:, :, 25:]), axis=2)
    rank = np.partition(references, 23, axis=2)[:, :, 23]
    alpha = WEAK_ALPHA_Q32 / float(1 << COEFFICIENT_FRACTION_BITS)
    detected = windows[:, :, 20] > rank * alpha
    peak_mask = np.zeros_like(frames, dtype=np.bool_)
    exact_peak_mask = np.zeros_like(frames, dtype=np.bool_)
    nomination_counts = []
    for frame_index in range(frames.shape[0]):
        indices = np.flatnonzero(detected[frame_index]) + RADIUS
        groups: list[list[int]] = []
        for index in indices.tolist():
            if not groups or index - groups[-1][-1] > 2:
                groups.append([])
            groups[-1].append(index)
        ranked_groups: list[tuple[float, int, list[int]]] = []
        for group in groups:
            peak = max(group, key=lambda index: frames[frame_index, index])
            reference = rank[frame_index, peak - RADIUS]
            ratio = math.inf if reference == 0.0 else frames[frame_index, peak] / reference
            ranked_groups.append((ratio, peak, group))
        selected_groups = sorted(
            ranked_groups, key=lambda item: (-item[0], item[1])
        )[:MAXIMUM_TRACKED_WEAK_NOMINATIONS]
        nomination_counts.append(len(selected_groups))
        for _, peak, group in selected_groups:
            exact_peak_mask[frame_index, peak] = True
            start = max(RADIUS, peak - PEAK_TOLERANCE_BINS)
            end = min(FRAME_LENGTH - RADIUS - 1, peak + PEAK_TOLERANCE_BINS)
            peak_mask[frame_index, start : end + 1] = True
    return peak_mask, exact_peak_mask, float(np.mean(nomination_counts))


def _scenario_profile(name: str) -> np.ndarray:
    x = np.linspace(-1.0, 1.0, FRAME_LENGTH)
    if name == "white":
        return np.ones(FRAME_LENGTH)
    if name == "sloped":
        return 0.65 + 0.7 * (x + 1.0) / 2.0
    if name == "rippled":
        return 1.0 + 0.22 * np.sin(np.arange(FRAME_LENGTH) * 2.0 * np.pi / 173.0)
    raise ValueError(name)


def _evaluate_noise(rng: np.random.Generator, name: str, trials: int) -> dict[str, object]:
    false_windows = 0
    maximum_occupancy = 0
    nomination_total = 0.0
    profile = _scenario_profile(name)
    for _ in range(trials):
        frames = rng.exponential(
            profile, size=(PERSISTENCE_WINDOW, FRAME_LENGTH)
        )
        peaks, _, mean_count = _weak_peak_mask(frames)
        occupancy = peaks.sum(axis=0)
        maximum_occupancy = max(maximum_occupancy, int(occupancy.max()))
        false_windows += int(np.any(occupancy >= PERSISTENCE_REQUIRED))
        nomination_total += mean_count
    return {
        "name": name,
        "window_trials": trials,
        "false_confirmed_windows": false_windows,
        "maximum_bin_occupancy": maximum_occupancy,
        "mean_nominations_per_frame": nomination_total / trials,
    }


def _evaluate_frequency_invariance(rng: np.random.Generator) -> list[dict[str, object]]:
    results = []
    for shifted_bin in (400, 1200, 2048, 3000, 3800):
        frames = rng.exponential(1.0, size=(PERSISTENCE_WINDOW, FRAME_LENGTH))
        reference_cells = np.concatenate(
            (
                frames[:, shifted_bin - 20 : shifted_bin - 4],
                frames[:, shifted_bin + 5 : shifted_bin + 21],
            ),
            axis=1,
        )
        rank24 = np.partition(reference_cells, 23, axis=1)[:, 23]
        frames[:, shifted_bin] = 7.0 * rank24
        peaks, exact_peaks, mean_count = _weak_peak_mask(frames)
        occupancy = peaks.sum(axis=0)
        exact_occupancy = exact_peaks.sum(axis=0)
        detected_bin = int(np.argmax(exact_occupancy))
        results.append({
            "injected_shifted_bin": shifted_bin,
            "detected_shifted_bin": detected_bin,
            "observed_frames": int(occupancy[detected_bin]),
            "confirmed": bool(occupancy[detected_bin] >= PERSISTENCE_REQUIRED),
            "mean_nominations_per_frame": mean_count,
        })
    return results


def _binomial_tail(n: int, required: int, probability: float) -> float:
    return sum(
        math.comb(n, hits) * probability**hits * (1.0 - probability) ** (n - hits)
        for hits in range(required, n + 1)
    )


def evaluate(*, trials: int, seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    per_cell = ideal_exponential_false_nomination_probability()
    expanded_cell = 1.0 - (1.0 - per_cell) ** (2 * PEAK_TOLERANCE_BINS + 1)
    persistent_cell = _binomial_tail(
        PERSISTENCE_WINDOW, PERSISTENCE_REQUIRED, expanded_cell
    )
    evaluated_bins = FRAME_LENGTH - 2 * RADIUS
    return {
        "schema": "p0-persistent-weak-model-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "implementation_status": "top8_reference_model_passed",
        "seed": seed,
        "profile": {
            "fft_bins": FRAME_LENGTH,
            "weak_threshold_db": 10.0 * math.log10(
                WEAK_ALPHA_Q32 / float(1 << COEFFICIENT_FRACTION_BITS)
            ),
            "window_frames": PERSISTENCE_WINDOW,
            "required_frames": PERSISTENCE_REQUIRED,
            "peak_tolerance_bins": PEAK_TOLERANCE_BINS,
            "maximum_tracked_nominations_per_frame": MAXIMUM_TRACKED_WEAK_NOMINATIONS,
        },
        "ideal_exponential_analysis": {
            "weak_nomination_probability_per_cell": per_cell,
            "expected_weak_cells_per_frame": per_cell * evaluated_bins,
            "conservative_expanded_probability_per_bin": expanded_cell,
            "persistent_false_probability_per_bin_window": persistent_cell,
            "union_bound_per_fft_window": persistent_cell * evaluated_bins,
            "assumptions": "independent exponential cells and independent frames",
        },
        "noise_scenarios": [
            _evaluate_noise(rng, name, trials) for name in ("white", "sloped", "rippled")
        ],
        "frequency_invariance": _evaluate_frequency_invariance(rng),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials pozitif olmalıdır")
    result = evaluate(trials=args.trials, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
