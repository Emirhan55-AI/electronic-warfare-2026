#!/usr/bin/env python3
"""Compare PHASE-03 detectors and establish one validated operation profile."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.detection import (  # noqa: E402
    ALLOWED_PFA_VALUES,
    COST_MODELS,
    DetectionPipeline,
    DetectorConfig,
    LinearPowerDetector,
    OS_EXPECTED_RATIO,
    ca_threshold_multiplier,
    os_threshold_multiplier,
    regional_threshold_multiplier,
)
from reference.detection.scenes import (  # noqa: E402
    generate_scene,
    generate_temporal_frame,
    load_scene_catalog,
)
from reference.pipeline import build_operation_profile, canonical_profile_bytes  # noqa: E402
from reference.spectrum import SpectrumProcessor  # noqa: E402


COMPARISON_PATH = ROOT / "results" / "evidence" / "phase03" / "detector-comparison.json"
PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
SINGLE_METHODS = ("regional", "ca_cfar", "os_cfar")
HYBRID_METHOD = "os_regional_cap"
METHOD_LABELS = {
    "regional": "Bölgesel sağlam taban",
    "ca_cfar": "CA-CFAR",
    "os_cfar": "OS-CFAR",
    "os_regional_cap": "OS-CFAR + bölgesel tavan",
}


@dataclass(frozen=True)
class EvaluationCounts:
    noise_per_level: int
    shaped_noise_per_scene: int
    snr_per_point: int
    multi_per_scene: int
    wideband: int
    edge_per_scene: int
    temporal_sequences: int
    bootstrap_repetitions: int


FULL_COUNTS = EvaluationCounts(1024, 512, 256, 256, 256, 128, 128, 10_000)
QUICK_COUNTS = EvaluationCounts(16, 8, 8, 8, 8, 8, 4, 200)


@dataclass
class MethodEvaluation:
    method: str
    payload: dict[str, Any]
    gate_without_wideband: bool
    eligible: bool
    layers: dict[str, Any]


def _processor() -> SpectrumProcessor:
    return SpectrumProcessor()


def _spectrum(samples: np.ndarray, catalog: dict[str, Any]) -> Any:
    common = catalog["common"]
    return _processor().process(
        samples,
        sample_rate_hz=float(common["sample_rate_hz"]),
        center_frequency_hz=float(common["center_frequency_hz"]),
    )


def _round(value: float) -> float:
    return round(float(value), 12)


def coefficient_table() -> list[dict[str, float]]:
    return [
        {
            "pfa_per_cut": pfa,
            "regional_multiplier": _round(regional_threshold_multiplier(pfa)),
            "ca_multiplier": _round(ca_threshold_multiplier(pfa)),
            "os_multiplier": _round(os_threshold_multiplier(pfa)),
        }
        for pfa in ALLOWED_PFA_VALUES
    ]


def _bootstrap_mean_interval(
    values: np.ndarray,
    *,
    repetitions: int,
    seed_parts: Iterable[int],
) -> tuple[float, float]:
    if values.ndim != 1 or values.size == 0:
        raise ValueError("bootstrap requires a non-empty one-dimensional sample")
    generator = np.random.default_rng(np.random.SeedSequence(list(seed_parts)))
    means = np.empty(repetitions, dtype=np.float64)
    offset = 0
    while offset < repetitions:
        batch = min(256, repetitions - offset)
        indices = generator.integers(0, values.size, size=(batch, values.size))
        means[offset : offset + batch] = values[indices].mean(axis=1)
        offset += batch
    low, high = np.percentile(means, (2.5, 97.5))
    return float(low), float(high)


def _wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("Wilson interval requires trials")
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    margin = (
        z
        * math.sqrt((proportion * (1.0 - proportion) / trials) + (z * z / (4.0 * trials * trials)))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _detector(method: str, pfa: float = 1e-4, evaluate_center: bool = True) -> LinearPowerDetector:
    return LinearPowerDetector(
        DetectorConfig(
            method=method,  # type: ignore[arg-type]
            pfa=pfa,
            evaluate_center=evaluate_center,
        )
    )


def _target_pairs(regions: tuple[Any, ...], targets: tuple[dict[str, Any], ...]) -> dict[int, int]:
    candidates: dict[int, list[tuple[int, int, int, float, int]]] = {}
    for target_index, target in enumerate(targets):
        if target.get("role") not in {"target", "policy_probe"}:
            continue
        support_start = int(target["main_lobe_start_shifted_bin"])
        support_end = int(target["main_lobe_end_shifted_bin"])
        expected_peak = int(target["expected_peak_shifted_bin"])
        tolerance = int(target["peak_tolerance_bins"])
        options: list[tuple[int, int, int, float, int]] = []
        for region_index, region in enumerate(regions):
            overlap = max(0, min(region.end_bin, support_end) - max(region.start_bin, support_start) + 1)
            error = abs(region.peak_bin - expected_peak)
            if overlap and error <= tolerance:
                options.append((region_index, overlap, error, float(region.peak_to_noise_db), region.start_bin))
        candidates[target_index] = options

    target_indices = sorted(candidates)
    best_score: tuple[int, int, int, float, int] | None = None
    best_mapping: dict[int, int] = {}

    def visit(position: int, used: set[int], mapping: dict[int, int], values: list[tuple[int, int, float, int]]) -> None:
        nonlocal best_score, best_mapping
        if position == len(target_indices):
            score = (
                len(mapping),
                sum(item[0] for item in values),
                -sum(item[1] for item in values),
                sum(item[2] for item in values),
                -sum(item[3] for item in values),
            )
            if best_score is None or score > best_score:
                best_score = score
                best_mapping = dict(mapping)
            return
        target_index = target_indices[position]
        visit(position + 1, used, mapping, values)
        for region_index, overlap, error, delta, start in candidates[target_index]:
            if region_index in used:
                continue
            used.add(region_index)
            mapping[target_index] = region_index
            values.append((overlap, error, delta, start))
            visit(position + 1, used, mapping, values)
            values.pop()
            del mapping[target_index]
            used.remove(region_index)

    visit(0, set(), {}, [])
    return best_mapping


def _wideband_metrics(regions: tuple[Any, ...], start: int, end: int) -> tuple[float, float, float]:
    predicted = np.zeros(4096, dtype=np.bool_)
    for region in regions:
        predicted[region.start_bin : region.end_bin + 1] = True
    truth = np.zeros(4096, dtype=np.bool_)
    truth[start : end + 1] = True
    intersection = int(np.count_nonzero(predicted & truth))
    union = int(np.count_nonzero(predicted | truth))
    predicted_count = int(np.count_nonzero(predicted))
    coverage = intersection / int(np.count_nonzero(truth))
    iou = intersection / union if union else 0.0
    overflow = int(np.count_nonzero(predicted & ~truth)) / predicted_count if predicted_count else 1.0
    return coverage, iou, overflow


def _false_alarm_metrics(method: str, counts: EvaluationCounts, catalog: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    scene_specs = (
        ("awgn-low", counts.noise_per_level, "homogeneous"),
        ("awgn-medium", counts.noise_per_level, "homogeneous"),
        ("awgn-high", counts.noise_per_level, "homogeneous"),
        ("sloped-noise", counts.shaped_noise_per_scene, "shaped"),
        ("stepped-noise", counts.shaped_noise_per_scene, "shaped"),
    )
    records: list[dict[str, Any]] = []
    all_passed = True
    for scene_index, (scene_id, frame_count, category) in enumerate(scene_specs):
        spectra = [
            _spectrum(generate_scene(scene_id, trial_index=index, catalog=catalog).samples, catalog)
            for index in range(frame_count)
        ]
        for pfa_index, pfa in enumerate(ALLOWED_PFA_VALUES):
            for center_index, evaluate_center in enumerate((True, False)):
                detector = _detector(method, pfa, evaluate_center)
                denominator = 4056 if evaluate_center else 4055
                rates = np.asarray(
                    [
                        np.count_nonzero(detector.detect(spectrum.display.bin_power_fs2).detected_mask)
                        / denominator
                        for spectrum in spectra
                    ],
                    dtype=np.float64,
                )
                low, high = _bootstrap_mean_interval(
                    rates,
                    repetitions=counts.bootstrap_repetitions,
                    seed_parts=(20260302, scene_index, pfa_index, center_index),
                )
                passed = (
                    low >= 0.5 * pfa and high <= 3.0 * pfa
                    if category == "homogeneous"
                    else high <= 5.0 * pfa
                )
                all_passed = all_passed and passed
                records.append(
                    {
                        "scene": scene_id,
                        "pfa_per_cut": pfa,
                        "evaluate_center": evaluate_center,
                        "evaluated_cut_count": denominator,
                        "frame_count": frame_count,
                        "empirical_pfa": _round(rates.mean()),
                        "bootstrap_95": [_round(low), _round(high)],
                        "status": "passed" if passed else "failed",
                    }
                )
    return {"status": "passed" if all_passed else "failed", "records": records}, all_passed


def _quality_metrics(method: str, counts: EvaluationCounts, catalog: dict[str, Any]) -> tuple[dict[str, Any], bool, bool, dict[str, Any]]:
    detector = _detector(method)
    narrow_trials: list[bool] = []
    narrow_records: list[dict[str, Any]] = []
    false_candidates = 0
    signal_frames = 0
    narrow_gate = True
    for scene_id in ("tone-bin-centered", "tone-off-bin"):
        for condition_index, snr_db in enumerate((-30.0, -24.0, -18.0, -12.0, -6.0)):
            successes = 0
            for trial_index in range(counts.snr_per_point):
                frame = generate_scene(
                    scene_id,
                    trial_index=trial_index,
                    condition_index=condition_index,
                    catalog=catalog,
                )
                spectrum = _spectrum(frame.samples, catalog)
                regions = DetectionPipeline(detector).process(spectrum, frame_index=0).regions
                mapping = _target_pairs(regions, frame.ground_truth)
                success = len(mapping) == len(frame.ground_truth)
                narrow_trials.append(success)
                successes += int(success)
                false_candidates += len(regions) - len(set(mapping.values()))
                signal_frames += 1
            probability = successes / counts.snr_per_point
            wilson = _wilson_interval(successes, counts.snr_per_point)
            required = 0.90 if snr_db == -18.0 else 0.99 if snr_db in {-12.0, -6.0} else None
            passed = required is None or probability >= required
            narrow_gate = narrow_gate and passed
            narrow_records.append(
                {
                    "scene": scene_id,
                    "snr_db": snr_db,
                    "trials": counts.snr_per_point,
                    "detection_probability": _round(probability),
                    "wilson_95": [_round(wilson[0]), _round(wilson[1])],
                    "status": "passed" if passed else "failed",
                }
            )

    multi_trials: list[bool] = []
    multi_records: list[dict[str, Any]] = []
    multi_gate = True
    for scene_id in ("two-equal-tones", "two-unequal-tones"):
        separate = 0
        merges = 0
        masking = 0
        for trial_index in range(counts.multi_per_scene):
            frame = generate_scene(scene_id, trial_index=trial_index, catalog=catalog)
            spectrum = _spectrum(frame.samples, catalog)
            regions = DetectionPipeline(detector).process(spectrum, frame_index=0).regions
            mapping = _target_pairs(regions, frame.ground_truth)
            supports = [
                (int(item["main_lobe_start_shifted_bin"]), int(item["main_lobe_end_shifted_bin"]))
                for item in frame.ground_truth
            ]
            merged = any(
                all(region.start_bin <= end and region.end_bin >= start for start, end in supports)
                for region in regions
            )
            both = len(mapping) == 2 and len(set(mapping.values())) == 2
            weak_masked = scene_id == "two-unequal-tones" and 0 in mapping and 1 not in mapping
            success = both and not merged and not weak_masked
            multi_trials.append(success)
            separate += int(both)
            merges += int(merged)
            masking += int(weak_masked)
            false_candidates += len(regions) - len(set(mapping.values()))
            signal_frames += 1
        separate_rate = separate / counts.multi_per_scene
        merge_rate = merges / counts.multi_per_scene
        masking_rate = masking / counts.multi_per_scene
        passed = separate_rate >= 0.90 and merge_rate <= 0.05 and masking_rate <= 0.10
        multi_gate = multi_gate and passed
        multi_records.append(
            {
                "scene": scene_id,
                "trials": counts.multi_per_scene,
                "separate_detection_rate": _round(separate_rate),
                "false_merge_rate": _round(merge_rate),
                "weak_masking_rate": _round(masking_rate),
                "status": "passed" if passed else "failed",
            }
        )

    wide_trials: list[bool] = []
    coverage_values: list[float] = []
    iou_values: list[float] = []
    overflow_values: list[float] = []
    wide_contract = catalog["evaluation_contract"]["wideband"]
    minimum_coverage = float(wide_contract["minimum_coverage"])
    minimum_iou = float(wide_contract["minimum_iou"])
    maximum_overreach = float(wide_contract["maximum_overreach"])
    for trial_index in range(counts.wideband):
        frame = generate_scene("wideband-noise-like", trial_index=trial_index, catalog=catalog)
        spectrum = _spectrum(frame.samples, catalog)
        regions = DetectionPipeline(detector).process(spectrum, frame_index=0).regions
        truth = frame.ground_truth[0]
        start = int(truth["shifted_start_bin"])
        end = int(truth["shifted_end_bin"])
        coverage, iou, overflow = _wideband_metrics(regions, start, end)
        success = (
            coverage >= minimum_coverage
            and iou >= minimum_iou
            and overflow <= maximum_overreach
        )
        wide_trials.append(success)
        coverage_values.append(coverage)
        iou_values.append(iou)
        overflow_values.append(overflow)
        false_candidates += sum(region.end_bin < start or region.start_bin > end for region in regions)
        signal_frames += 1
    wide_rate = float(np.mean(wide_trials))
    wide_gate = wide_rate >= 0.90

    policy_records: list[dict[str, Any]] = []
    policy_gate = True
    for scene_id, expected_peak, expected_evaluated in (
        ("center-tone", 2048, True),
        ("first-valid-edge-tone", 20, True),
        ("unevaluated-edge-tone", 8, False),
    ):
        successes = 0
        for trial_index in range(counts.edge_per_scene):
            frame = generate_scene(scene_id, trial_index=trial_index, catalog=catalog)
            spectrum = _spectrum(frame.samples, catalog)
            output = DetectionPipeline(detector).process(spectrum, frame_index=0)
            if expected_evaluated:
                successes += int(len(_target_pairs(output.regions, frame.ground_truth)) == 1)
            else:
                successes += int(not bool(output.cells.evaluated_mask[expected_peak]))
        rate = successes / counts.edge_per_scene
        passed = rate >= 0.99
        policy_gate = policy_gate and passed
        policy_records.append(
            {
                "scene": scene_id,
                "trials": counts.edge_per_scene,
                "success_rate": _round(rate),
                "status": "passed" if passed else "failed",
            }
        )

    temporal_payload, temporal_gate, temporal_layers = _temporal_metrics(method, counts, catalog)
    false_candidate_rate = false_candidates / signal_frames
    false_candidate_gate = false_candidate_rate <= 0.75
    gate_without_wideband = narrow_gate and multi_gate and policy_gate and temporal_gate and false_candidate_gate
    eligible = gate_without_wideband and wide_gate
    payload = {
        "narrowband": {"status": "passed" if narrow_gate else "failed", "records": narrow_records},
        "multiple_signals": {"status": "passed" if multi_gate else "failed", "records": multi_records},
        "wideband": {
            "status": "passed" if wide_gate else "failed",
            "trials": counts.wideband,
            "minimum_coverage": minimum_coverage,
            "minimum_iou": minimum_iou,
            "maximum_overreach": maximum_overreach,
            "successful_frame_rate": _round(wide_rate),
            "mean_coverage": _round(np.mean(coverage_values)),
            "mean_iou": _round(np.mean(iou_values)),
            "mean_overflow": _round(np.mean(overflow_values)),
        },
        "center_and_edges": {"status": "passed" if policy_gate else "failed", "records": policy_records},
        "false_candidates_in_signal_scenes": {
            "status": "passed" if false_candidate_gate else "failed",
            "mean_per_frame": _round(false_candidate_rate),
            "limit": 0.75,
        },
        "temporal": temporal_payload,
    }
    layers = {
        "narrowband": np.asarray(narrow_trials, dtype=np.float64),
        "multiple_signals": np.asarray(multi_trials, dtype=np.float64),
        "wideband": np.asarray(wide_trials, dtype=np.float64),
        "temporal": temporal_layers,
    }
    return payload, gate_without_wideband, eligible, layers


def _event_overlaps(event: Any, start: int, end: int) -> bool:
    return event.region.start_bin <= end and event.region.end_bin >= start


def _temporal_metrics(
    method: str,
    counts: EvaluationCounts,
    catalog: dict[str, Any],
) -> tuple[dict[str, Any], bool, dict[str, np.ndarray]]:
    scene_by_id = {scene["id"]: scene for scene in catalog["scenes"]}
    transient_tone = scene_by_id["transient-tone"]["tones"][0]
    persistent_tone = scene_by_id["persistent-tone"]["tones"][0]
    transient_support = (
        int(transient_tone["main_lobe_start_shifted_bin"]),
        int(transient_tone["main_lobe_end_shifted_bin"]),
    )
    persistent_support = (
        int(persistent_tone["main_lobe_start_shifted_bin"]),
        int(persistent_tone["main_lobe_end_shifted_bin"]),
    )
    noise_success: list[bool] = []
    noise_event_counts: list[int] = []
    transient_success: list[bool] = []
    persistent_success: list[bool] = []
    false_confirmations = 0
    total_noise_frames = counts.temporal_sequences * 32
    for sequence_index in range(counts.temporal_sequences):
        pipeline = DetectionPipeline(_detector(method))
        confirmed_ids: set[int] = set()
        sequence_false = 0
        for frame_index in range(32):
            frame = generate_scene(
                "awgn-medium",
                trial_index=sequence_index * 32 + frame_index,
                catalog=catalog,
            )
            output = pipeline.process(_spectrum(frame.samples, catalog), frame_index=frame_index)
            for event in output.active_events:
                if event.state == "confirmed" and event.event_id not in confirmed_ids:
                    confirmed_ids.add(event.event_id)
                    sequence_false += 1
        false_confirmations += sequence_false
        noise_event_counts.append(sequence_false)
        noise_success.append(sequence_false == 0)

    for sequence_index in range(counts.temporal_sequences):
        pipeline = DetectionPipeline(_detector(method))
        confirmed = False
        for frame_index in range(5):
            frame = generate_temporal_frame(
                "transient-tone",
                sequence_index=sequence_index,
                frame_index=frame_index,
                catalog=catalog,
            )
            output = pipeline.process(_spectrum(frame.samples, catalog), frame_index=frame_index)
            confirmed = confirmed or any(
                event.state == "confirmed" and _event_overlaps(event, *transient_support)
                for event in output.active_events
            )
        transient_success.append(not confirmed)

    for sequence_index in range(counts.temporal_sequences):
        pipeline = DetectionPipeline(_detector(method))
        confirmed_at_two = False
        retained_at_five = False
        ended_at_six = False
        for frame_index in range(7):
            frame = generate_temporal_frame(
                "persistent-tone",
                sequence_index=sequence_index,
                frame_index=frame_index,
                catalog=catalog,
            )
            output = pipeline.process(_spectrum(frame.samples, catalog), frame_index=frame_index)
            if frame_index == 2:
                confirmed_at_two = any(
                    event.state == "confirmed" and _event_overlaps(event, *persistent_support)
                    for event in output.active_events
                )
            elif frame_index == 5:
                retained_at_five = any(
                    event.state == "confirmed"
                    and not event.observed_this_frame
                    and _event_overlaps(event, *persistent_support)
                    for event in output.active_events
                )
            elif frame_index == 6:
                ended_at_six = any(_event_overlaps(event, *persistent_support) for event in output.ended_events)
        persistent_success.append(confirmed_at_two and retained_at_five and ended_at_six)

    false_rate = false_confirmations / total_noise_frames
    noise_frame_values = np.asarray(noise_event_counts, dtype=np.float64) / 32.0
    _, false_upper = _bootstrap_mean_interval(
        noise_frame_values,
        repetitions=counts.bootstrap_repetitions,
        seed_parts=(20260302, 99),
    )
    noise_gate = false_upper <= 0.01
    transient_gate = all(transient_success)
    persistent_gate = float(np.mean(persistent_success)) >= 0.99
    passed = noise_gate and transient_gate and persistent_gate
    payload = {
        "status": "passed" if passed else "failed",
        "noise_sequences": counts.temporal_sequences,
        "noise_frames_per_sequence": 32,
        "false_confirmed_events": false_confirmations,
        "false_events_per_frame": _round(false_rate),
        "bootstrap_95_upper": _round(false_upper),
        "single_frame_rejection_rate": _round(np.mean(transient_success)),
        "persistent_exact_transition_rate": _round(np.mean(persistent_success)),
    }
    return payload, passed, {
        "noise": np.asarray(noise_success, dtype=np.float64),
        "transient": np.asarray(transient_success, dtype=np.float64),
        "persistent": np.asarray(persistent_success, dtype=np.float64),
    }


def _implementation_gate(method: str, catalog: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Check bounded, finite work without using machine timing in selection."""
    frame = generate_scene("two-unequal-tones", trial_index=0, catalog=catalog)
    spectrum = _spectrum(frame.samples, catalog)
    output = DetectionPipeline(_detector(method)).process(spectrum, frame_index=0)
    cells = output.cells
    cost = COST_MODELS[method]
    finite = bool(
        np.all(np.isfinite(cells.noise_power))
        and np.all(np.isfinite(cells.threshold_power))
    )
    passed = (
        cells.evaluated_count == 4056
        and cells.detected_mask.size == 4096
        and finite
        and len(output.active_events) <= DetectionPipeline.MAX_ACTIVE_TRACKS
        and len(output.ended_history) <= DetectionPipeline.MAX_ENDED_HISTORY
        and 0 <= cost.selection_inputs_per_frame <= max(item.selection_inputs_per_frame for item in COST_MODELS.values())
        and 0 <= cost.stream_state_slots <= max(item.stream_state_slots for item in COST_MODELS.values())
        and 0 <= cost.maximum_selection_width <= max(item.maximum_selection_width for item in COST_MODELS.values())
        and 0 <= cost.basic_arithmetic_ops <= max(item.basic_arithmetic_ops for item in COST_MODELS.values())
    )
    return {
        "status": "passed" if passed else "failed",
        "dynamic_timing_used": False,
        "finite_vectors": finite,
        "spectrum_cells": int(cells.detected_mask.size),
        "evaluated_cut_count": cells.evaluated_count,
        "maximum_active_tracks": DetectionPipeline.MAX_ACTIVE_TRACKS,
        "maximum_ended_history": DetectionPipeline.MAX_ENDED_HISTORY,
    }, passed


def evaluate_method(method: str, counts: EvaluationCounts, catalog: dict[str, Any]) -> MethodEvaluation:
    false_alarm_payload, false_alarm_passed = _false_alarm_metrics(method, counts, catalog)
    quality_payload, quality_without_wideband, quality_eligible, layers = _quality_metrics(method, counts, catalog)
    implementation_payload, implementation_passed = _implementation_gate(method, catalog)
    gate_without_wideband = false_alarm_passed and quality_without_wideband and implementation_passed
    eligible = false_alarm_passed and quality_eligible and implementation_passed
    layer_score = _layer_score(layers)
    payload = {
        "method": method,
        "label": METHOD_LABELS[method],
        "status": "passed" if eligible else "failed",
        "eligible": eligible,
        "balanced_detection_score": _round(layer_score),
        "false_alarm": false_alarm_payload,
        "quality": quality_payload,
        "implementation_gate": implementation_payload,
        "resource_cost": {
            "selection_inputs_per_frame": COST_MODELS[method].selection_inputs_per_frame,
            "stream_state_slots": COST_MODELS[method].stream_state_slots,
            "maximum_selection_width": COST_MODELS[method].maximum_selection_width,
            "basic_arithmetic_ops": COST_MODELS[method].basic_arithmetic_ops,
        },
    }
    return MethodEvaluation(method, payload, gate_without_wideband, eligible, layers)


def _layer_score(layers: dict[str, Any]) -> float:
    temporal = layers["temporal"]
    temporal_score = float(np.mean([np.mean(temporal[name]) for name in ("noise", "transient", "persistent")]))
    return float(
        np.mean(
            [
                np.mean(layers["narrowband"]),
                np.mean(layers["multiple_signals"]),
                np.mean(layers["wideband"]),
                temporal_score,
            ]
        )
    )


def _paired_score_interval(
    first: MethodEvaluation,
    second: MethodEvaluation,
    repetitions: int,
) -> tuple[float, float]:
    generator = np.random.default_rng(np.random.SeedSequence([20260303]))
    differences = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        layer_differences: list[float] = []
        for layer in ("narrowband", "multiple_signals", "wideband"):
            size = first.layers[layer].size
            indices = generator.integers(0, size, size=size)
            layer_differences.append(
                float(first.layers[layer][indices].mean() - second.layers[layer][indices].mean())
            )
        temporal_differences: list[float] = []
        for family in ("noise", "transient", "persistent"):
            size = first.layers["temporal"][family].size
            indices = generator.integers(0, size, size=size)
            temporal_differences.append(
                float(
                    first.layers["temporal"][family][indices].mean()
                    - second.layers["temporal"][family][indices].mean()
                )
            )
        layer_differences.append(float(np.mean(temporal_differences)))
        differences[repetition] = float(np.mean(layer_differences))
    low, high = np.percentile(differences, (2.5, 97.5))
    return float(low), float(high)


def choose_method(
    evaluations: list[MethodEvaluation],
    *,
    bootstrap_repetitions: int,
) -> tuple[str | None, dict[str, Any]]:
    eligible = [item for item in evaluations if item.eligible]
    if not eligible:
        return None, {"status": "failed", "reason": "no method passed every mandatory gate", "comparisons": []}
    eligible.sort(key=lambda item: (-float(item.payload["balanced_detection_score"]), item.method))
    comparisons: list[dict[str, Any]] = []
    winner = eligible[0]
    meaningful_against_all = True
    tie_candidates = [winner]
    for other in eligible[1:]:
        low, high = _paired_score_interval(winner, other, bootstrap_repetitions)
        difference = float(winner.payload["balanced_detection_score"]) - float(
            other.payload["balanced_detection_score"]
        )
        meaningful = difference >= 0.02 and low > 0.0
        meaningful_against_all = meaningful_against_all and meaningful
        if not meaningful:
            tie_candidates.append(other)
        comparisons.append(
            {
                "first": winner.method,
                "second": other.method,
                "point_difference": _round(difference),
                "paired_bootstrap_95": [_round(low), _round(high)],
                "meaningful_superiority": meaningful,
            }
        )
    if len(eligible) == 1 or meaningful_against_all:
        selected = winner
        basis = "only eligible method" if len(eligible) == 1 else "meaningful paired detection superiority"
    else:
        selected = min(tie_candidates, key=lambda item: COST_MODELS[item.method].key)
        basis = "deterministic FPGA resource-cost tie-break"
    return selected.method, {"status": "passed", "reason": basis, "comparisons": comparisons}


def evaluate_all(*, full: bool = True) -> tuple[dict[str, Any], str | None]:
    counts = FULL_COUNTS if full else QUICK_COUNTS
    catalog = load_scene_catalog()
    evaluations = [evaluate_method(method, counts, catalog) for method in SINGLE_METHODS]
    hybrid_needed = not any(item.eligible for item in evaluations) and any(
        item.gate_without_wideband for item in evaluations
    )
    if hybrid_needed:
        hybrid = evaluate_method(HYBRID_METHOD, counts, catalog)
        best_single_wide = max(
            float(item.payload["quality"]["wideband"]["successful_frame_rate"]) for item in evaluations
        )
        hybrid_wide = float(hybrid.payload["quality"]["wideband"]["successful_frame_rate"])
        if hybrid_wide - best_single_wide < 0.10:
            hybrid.eligible = False
            hybrid.payload["eligible"] = False
            hybrid.payload["status"] = "failed"
            hybrid.payload["hybrid_improvement_gate"] = "failed"
        else:
            hybrid.payload["hybrid_improvement_gate"] = "passed"
        evaluations.append(hybrid)

    selected, decision = choose_method(evaluations, bootstrap_repetitions=counts.bootstrap_repetitions)
    payload = {
        "schema_version": 1,
        "phase": "PHASE-03",
        "overall": "passed" if selected is not None else "failed",
        "selection_contract": {
            "default_pfa_per_cut": 0.0001,
            "default_evaluate_center": True,
            "minimum_meaningful_score_difference": 0.02,
            "paired_bootstrap_seed": 20260303,
            "bootstrap_repetitions": counts.bootstrap_repetitions,
            "bootstrap_interval": "95% percentile; paired frame or sequence identity",
            "detection_rate_interval": "95% Wilson score",
            "balanced_layers": ["narrowband", "multiple_signals", "wideband", "temporal"],
            "balanced_layer_weights": [0.25, 0.25, 0.25, 0.25],
            "dynamic_timing_used_for_selection": False,
            "hybrid_evaluated_only_if_needed": True,
        },
        "coefficient_table": coefficient_table(),
        "os_expected_ratio": _round(OS_EXPECTED_RATIO),
        "sample_counts": {
            "noise_frames_per_level": counts.noise_per_level,
            "shaped_noise_frames_per_scene": counts.shaped_noise_per_scene,
            "snr_frames_per_point": counts.snr_per_point,
            "multi_signal_frames_per_scene": counts.multi_per_scene,
            "wideband_frames": counts.wideband,
            "edge_frames_per_scene": counts.edge_per_scene,
            "temporal_sequences_per_family": counts.temporal_sequences,
        },
        "methods": [item.payload for item in evaluations],
        "hybrid_status": "passed" if hybrid_needed else "skipped",
        "decision": decision,
        "selected_detector": selected,
    }
    return payload, selected


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def establish(*, reestablish: bool = False, full: bool = True) -> tuple[int, dict[str, Any]]:
    comparison, selected = evaluate_all(full=full)
    comparison_bytes = _canonical_json_bytes(comparison)
    if selected is None:
        if not PROFILE_PATH.exists() and not COMPARISON_PATH.exists():
            _atomic_write(COMPARISON_PATH, comparison_bytes)
        return 1, comparison

    profile = build_operation_profile(selected, lifecycle="validated")
    profile_bytes = canonical_profile_bytes(profile)
    comparison_exists = COMPARISON_PATH.is_file()
    profile_exists = PROFILE_PATH.is_file()
    if comparison_exists and profile_exists:
        same = COMPARISON_PATH.read_bytes() == comparison_bytes and PROFILE_PATH.read_bytes() == profile_bytes
        if same:
            return 0, comparison
        if not reestablish:
            return 2, comparison
    elif comparison_exists or profile_exists:
        if not reestablish:
            return 2, comparison
    _atomic_write(COMPARISON_PATH, comparison_bytes)
    _atomic_write(PROFILE_PATH, profile_bytes)
    return 0, comparison


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="establish the comparison/profile pair")
    parser.add_argument("--reestablish", action="store_true", help="explicitly replace a differing established pair")
    parser.add_argument("--quick", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.write:
        parser.error("--write is required")
    code, payload = establish(reestablish=args.reestablish, full=not args.quick)
    selected = payload.get("selected_detector")
    if code == 0:
        print(f"PHASE-03 detector selection passed: {selected}")
        print("Comparison/profile pair created or already byte-identical.")
    elif code == 2:
        print("PHASE-03 detector selection differs from the established pair; no file was changed.")
    else:
        print("PHASE-03 detector selection failed; no validated profile was established.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
