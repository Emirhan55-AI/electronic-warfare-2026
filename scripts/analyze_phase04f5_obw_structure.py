#!/usr/bin/env python3
"""Measure signed NFM OBW edge behavior for structural F5 recovery candidates."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f1_estimator import _fractional_edge
from algorithms.parameters.f4_estimator import F4ParameterEstimator
from algorithms.parameters.operator_reference import canonical_json_bytes, load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


DEVELOPMENT_PATH = ROOT / "datasets" / "fixtures" / "phase04f5" / "development-catalog.json"
RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "obw-structure-diagnostics-v6.json"


def _nearest_q(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[max(0, int(math.ceil(q * len(ordered))) - 1)])


def _summary(records: list[dict[str, Any]], seed_count: int) -> dict[str, Any]:
    valid = [item for item in records if item["valid"]]
    return {
        "valid_count": len(valid),
        "seed_valid_counts": [sum(item["valid"] and item["seed_index"] == seed for item in records) for seed in range(seed_count)],
        "lower_signed_q05_bins": _nearest_q([item["lower_signed_error"] for item in valid], 0.05),
        "lower_signed_q50_bins": _nearest_q([item["lower_signed_error"] for item in valid], 0.50),
        "lower_signed_q95_bins": _nearest_q([item["lower_signed_error"] for item in valid], 0.95),
        "upper_signed_q05_bins": _nearest_q([item["upper_signed_error"] for item in valid], 0.05),
        "upper_signed_q50_bins": _nearest_q([item["upper_signed_error"] for item in valid], 0.50),
        "upper_signed_q95_bins": _nearest_q([item["upper_signed_error"] for item in valid], 0.95),
        "lower_absolute_q95_bins": _nearest_q([abs(item["lower_signed_error"]) for item in valid], 0.95),
        "upper_absolute_q95_bins": _nearest_q([abs(item["upper_signed_error"]) for item in valid], 0.95),
        "relative_q95": _nearest_q([item["relative_error"] for item in valid], 0.95),
        "temporal_range_q95_bins": _nearest_q([item["temporal_range"] for item in records if item["temporal_range"] is not None], 0.95),
    }


def _candidate_edges(
    psd_frames: np.ndarray,
    lower: int,
    upper: int,
    fraction: float,
) -> tuple[float, float, list[tuple[float, float]]] | None:
    kernel = np.asarray([0.25, 0.5, 0.25], dtype=np.float64)

    def edges(frames: np.ndarray) -> tuple[float, float] | None:
        averaged = np.mean(frames, axis=0)
        left = float(np.mean(averaged[lower - 36 : lower - 4]))
        right = float(np.mean(averaged[upper + 5 : upper + 37]))
        noise = 0.5 * (left + right)
        sigma = noise / math.sqrt(float(frames.shape[0])) * math.sqrt(float(np.sum(kernel**2)))
        weights = np.maximum(
            np.convolve(averaged[lower : upper + 1] - noise, kernel, mode="same")
            - F4ParameterEstimator.OBW_SHRINK_SIGMA * sigma,
            0.0,
        )
        if float(np.sum(weights)) <= 0.0:
            return None
        return _fractional_edge(weights, lower, fraction), _fractional_edge(weights, lower, 1.0 - fraction)

    aggregate = edges(psd_frames)
    leave_one_out = [edges(np.delete(psd_frames, omitted, axis=0)) for omitted in range(4)]
    if aggregate is None or any(item is None for item in leave_one_out):
        return None
    return aggregate[0], aggregate[1], [item for item in leave_one_out if item is not None]


def build_diagnostics() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    catalog = load_parameter_catalog()
    common = development["common"]
    family_index, family = next(
        (index, item) for index, item in enumerate(development["families"]) if item["id"] == "nfm"
    )
    processor = SpectrumProcessor()
    estimator = F4ParameterEstimator()
    records: dict[str, list[dict[str, Any]]] = {
        "current_v5": [],
        "aggregate_fraction_0_005": [],
        "aggregate_fraction_0_0075": [],
        "aggregate_fraction_0_010": [],
        "loo_median_fraction_0_005": [],
        "hybrid_fraction_0_005": [],
    }
    for seed_index, seed in enumerate(common["development_seeds"]):
        scene_seed = int(seed) + family_index * 10_000
        for trial in range(int(common["trials_per_seed_per_family"])):
            frames = tuple(
                generate_parameter_scene(
                    str(family["scene_id"]), trial_index=trial, condition_index=3,
                    frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=12.0,
                    catalog=catalog, scene_seed_override=scene_seed,
                )
                for frame_index in (0, 1, 2, 3)
            )
            spectra = tuple(
                processor.process(
                    frame.samples, sample_rate_hz=float(common["sample_rate_hz"]),
                    center_frequency_hz=float(common["center_frequency_hz"]),
                )
                for frame in frames
            )
            clean = tuple(
                processor.process(
                    frame.clean_samples, sample_rate_hz=float(common["sample_rate_hz"]),
                    center_frequency_hz=float(common["center_frequency_hz"]),
                )
                for frame in frames
            )
            truth = _truth(clean, int(common["operator_span_truth_margin_bins_per_side"]))
            span = tuple(int(value) for value in truth["span"])
            intent = _intent(span, seed_index + 1, trial)
            result = estimator.measure(intent, tuple(frame.samples for frame in frames), spectra)
            spacing = spectra[0].bin_spacing_hz
            center = float(common["center_frequency_hz"])
            temporal_range = result.quality.temporal_edge_range_bins

            def append(
                name: str,
                edge_pair: tuple[float, float] | None,
                candidate_temporal_range: float | None = None,
            ) -> None:
                valid = edge_pair is not None and edge_pair[0] > span[0] + 0.5 and edge_pair[1] < span[1] - 0.5
                lower_error = None if not valid else float(edge_pair[0]) - float(truth["lower_bin"])
                upper_error = None if not valid else float(edge_pair[1]) - float(truth["upper_bin"])
                records[name].append({
                    "seed_index": seed_index,
                    "trial": trial,
                    "valid": valid,
                    "temporal_range": temporal_range if candidate_temporal_range is None else candidate_temporal_range,
                    "lower_signed_error": lower_error,
                    "upper_signed_error": upper_error,
                    "relative_error": None if not valid else abs(
                        (float(edge_pair[1]) - float(edge_pair[0])) - float(truth["width_bins"])
                    ) / float(truth["width_bins"]),
                })

            current = None
            if result.occupied_bandwidth.state == "valid":
                current = (
                    (float(result.lower_band_edge.value) - center) / spacing + 2048.0,
                    (float(result.upper_band_edge.value) - center) / spacing + 2048.0,
                )
            append("current_v5", current)
            candidates = {
                fraction: _candidate_edges(
                    np.stack([np.asarray(item.display.psd_fs2_per_hz) for item in spectra]),
                    span[0], span[1], fraction,
                )
                for fraction in (0.005, 0.0075, 0.01)
            }
            for fraction, name in (
                (0.005, "aggregate_fraction_0_005"),
                (0.0075, "aggregate_fraction_0_0075"),
                (0.01, "aggregate_fraction_0_010"),
            ):
                candidate = candidates[fraction]
                candidate_range = None if candidate is None else max(
                    float(np.median([abs(item[0] - candidate[0]) for item in candidate[2]])),
                    float(np.median([abs(item[1] - candidate[1]) for item in candidate[2]])),
                )
                append(name, None if candidate is None else (candidate[0], candidate[1]), candidate_range)
            base = candidates[0.005]
            if base is None:
                append("loo_median_fraction_0_005", None)
                append("hybrid_fraction_0_005", None)
            else:
                loo_lower = float(np.median([item[0] for item in base[2]]))
                loo_upper = float(np.median([item[1] for item in base[2]]))
                append("loo_median_fraction_0_005", (loo_lower, loo_upper))
                append("hybrid_fraction_0_005", ((base[0] + loo_lower) / 2.0, (base[1] + loo_upper) / 2.0))
    summaries = {name: _summary(items, len(common["development_seeds"])) for name, items in records.items()}
    return {
        "schema_version": 1,
        "artifact_id": "phase04f5-obw-structure-diagnostics-v6",
        "role": "development-only",
        "family": "nfm",
        "population": {
            "seed_count": len(common["development_seeds"]),
            "total_trials": len(common["development_seeds"]) * int(common["trials_per_seed_per_family"]),
            "snr_db": 12.0,
            "frames_per_measurement": 4,
        },
        "candidates": summaries,
        "claim_boundary": "Yalnız açık F5 NFM geliştirme örneklerinin signed kenar tanısıdır; yöntem seçimi, binding/OOS veya ürün sonucu değildir.",
    }


def main() -> int:
    document = build_diagnostics()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(canonical_json_bytes(document))
    print("PHASE-04-F5 OBW structure diagnostics: completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
