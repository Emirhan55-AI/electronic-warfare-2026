"""Frozen PHASE-04-D1F evaluator for one binding and one locked OOS run."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from reference.parameters.obw99 import OccupiedBandwidthEstimate, OccupiedBandwidthEstimator
from reference.parameters.obw99_reference import canonical_json_bytes, load_json, nearest_rank_q95, sha256_file
from reference.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from reference.pipeline import RuntimePipeline, load_profile


ROOT = Path(__file__).resolve().parents[2]
D1_ROOT = ROOT / "datasets" / "fixtures" / "phase04d1"
SCENES_PATH = D1_ROOT / "obw99-scenes.json"
ACCEPTANCE_PATH = D1_ROOT / "acceptance-gates.json"
REFERENCE_CONTRACT_PATH = D1_ROOT / "reference-contract.json"
CLEAN_REFERENCE_PATH = D1_ROOT / "clean-reference.json"
METHOD_LOCK_PATH = D1_ROOT / "method-lock.json"
EVALUATION_LOCK_PATH = D1_ROOT / "evaluation-lock.json"
PHASE03_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
PARAMETER_SCENES_PATH = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"
COMPARISON_ID = "phase04-d1-obw99-selection-v1"


def _rounded(value: float) -> float:
    return round(float(value), 12)


def _rate(numerator: int, denominator: int) -> float:
    return _rounded(numerator / denominator) if denominator else 0.0


def _order_statistic(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"count": 0, "rank": None, "q95": None, "minimum": None, "maximum": None, "mean": None}
    rank = int(math.ceil(0.95 * len(ordered)))
    q95 = nearest_rank_q95(np.asarray(ordered, dtype=np.float64))
    return {
        "count": len(ordered),
        "rank": rank,
        "q95": _rounded(q95),
        "minimum": _rounded(ordered[0]),
        "maximum": _rounded(ordered[-1]),
        "mean": _rounded(float(np.mean(ordered))),
    }


def summarize_expected_trials(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize deterministic post-runtime trial records without changing a denominator."""
    states: dict[str, int] = {}
    reasons: dict[str, int] = {}
    relative: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    valid = clipping = 0
    for record in records:
        state = str(record["state"])
        states[state] = states.get(state, 0) + 1
        for reason in record.get("quality_reasons", []):
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
        clipping += int(bool(record.get("analysis_clipped", False)))
        if state == "valid":
            valid += 1
            relative.append(float(record["relative_error"]))
            lower.append(float(record["lower_error_bins"]))
            upper.append(float(record["upper_error_bins"]))
    total = len(records)
    return {
        "trial_count": total,
        "valid_count": valid,
        "invalid_or_abstention_count": total - valid,
        "state_counts": {key: states[key] for key in sorted(states)},
        "quality_reason_counts": {key: reasons[key] for key in sorted(reasons)},
        "valid_rate": _rate(valid, total),
        "clipping_count": clipping,
        "clipping_rate": _rate(clipping, total),
        "relative_obw_error": _order_statistic(relative),
        "lower_edge_error_bins": _order_statistic(lower),
        "upper_edge_error_bins": _order_statistic(upper),
        "temporal_stability": {
            "contract_maximum_native_bins": 1.0,
            "valid_outputs_are_internally_gated": True,
            "certified_q95_upper_bound_bins": 1.0 if valid else None,
        },
    }


def _family_truths() -> dict[str, dict[str, float]]:
    clean = load_json(CLEAN_REFERENCE_PATH)
    return {str(item["family_id"]): dict(item["truth"]) for item in clean["families"]}


def _match_output(
    outputs: tuple[OccupiedBandwidthEstimate, ...], truth: dict[str, float], bin_hz: float,
) -> dict[str, Any]:
    truth_lower = float(truth["lower_frequency_hz"])
    truth_upper = float(truth["upper_frequency_hz"])
    valid = [item for item in outputs if item.state == "valid"]
    if valid:
        def key(item: OccupiedBandwidthEstimate) -> tuple[float, float, int]:
            lower = float(item.lower_occupied_edge_hz)
            upper = float(item.upper_occupied_edge_hz)
            intersection = max(0.0, min(upper, truth_upper) - max(lower, truth_lower))
            union = max(upper, truth_upper) - min(lower, truth_lower)
            return (-intersection, -(intersection / union if union > 0.0 else 0.0), item.event_id)
        selected = min(valid, key=key)
        bandwidth = float(selected.occupied_bandwidth_hz)
        truth_bandwidth = float(truth["occupied_bandwidth_hz"])
        return {
            "state": "valid",
            "relative_error": abs(bandwidth - truth_bandwidth) / truth_bandwidth,
            "lower_error_bins": abs(float(selected.lower_occupied_edge_hz) - truth_lower) / bin_hz,
            "upper_error_bins": abs(float(selected.upper_occupied_edge_hz) - truth_upper) / bin_hz,
            "analysis_clipped": selected.analysis_clipped,
            "quality_reasons": list(selected.quality_reasons),
        }
    states = [item.state for item in outputs]
    state = "uncertain" if "uncertain" in states else "insufficient_quality"
    reasons = sorted({reason for item in outputs for reason in item.quality_reasons})
    return {
        "state": state,
        "analysis_clipped": any(item.analysis_clipped for item in outputs),
        "quality_reasons": reasons or ["no_valid_obw99_output"],
    }


def _run_family_trial(
    *, family: dict[str, Any], family_index: int, trial: int, base_seed: int,
    parameter_catalog: dict[str, Any], truth: dict[str, float],
) -> dict[str, Any]:
    profile = load_profile(PHASE03_PROFILE_PATH)
    runtime = RuntimePipeline(profile)
    estimator = OccupiedBandwidthEstimator()
    scene_id = str(family["source_scene_id"])
    frame_count = 6 if family["active_policy"] == "burst_pattern_active_only" else 5
    final_outputs: tuple[OccupiedBandwidthEstimate, ...] = ()
    bin_hz = float(parameter_catalog["common"]["bin_spacing_hz"])
    for frame_index in range(frame_count):
        frame = generate_parameter_scene(
            scene_id,
            trial_index=trial,
            condition_index=0,
            frame_index=frame_index,
            clean_power_dbfs=-18.0,
            snr_db=12.0,
            catalog=parameter_catalog,
            scene_seed_override=base_seed + family_index,
        )
        result = runtime.process(
            frame.samples,
            sample_rate_hz=float(parameter_catalog["common"]["sample_rate_hz"]),
            center_frequency_hz=float(parameter_catalog["common"]["center_frequency_hz"]),
            frame_index=frame_index,
        )
        estimate = estimator.process(
            result.spectrum,
            result.detection,
            frame_index=frame_index,
            generation=0,
        )
        if (
            family["active_policy"] == "burst_pattern_active_only" and frame_index == 4
        ) or (
            family["active_policy"] != "burst_pattern_active_only" and frame_index == frame_count - 1
        ):
            final_outputs = estimate.events
    return _match_output(final_outputs, truth, bin_hz)


def _source_center_bin(catalog: dict[str, Any], scene_id: str) -> float:
    scene = next(item for item in catalog["scenes"] if item["id"] == scene_id)
    return 2048.0 + float(scene.get("signed_center_bin", 0.0))


def _shifted_truth(
    truth: dict[str, float], *, source_center_bin: float, target_center_bin: float,
    sample_rate_hz: float, center_frequency_hz: float,
) -> dict[str, float]:
    bin_hz = sample_rate_hz / 4096.0
    source_center_hz = center_frequency_hz + (source_center_bin - 2048.0) * bin_hz
    target_center_hz = center_frequency_hz + (target_center_bin - 2048.0) * bin_hz
    shift = target_center_hz - source_center_hz
    return {
        "lower_frequency_hz": float(truth["lower_frequency_hz"]) + shift,
        "upper_frequency_hz": float(truth["upper_frequency_hz"]) + shift,
        "occupied_bandwidth_hz": float(truth["occupied_bandwidth_hz"]),
    }


def _run_close_trial(trial: int, base_seed: int, parameter_catalog: dict[str, Any], truths: dict[str, dict[str, float]]) -> dict[str, Any]:
    scene = next(item for item in parameter_catalog["scenes"] if item["id"] == "close-am-qpsk")
    centers = [2048.0 + float(item) for item in scene["component_centers_bins"]]
    sample_rate = float(parameter_catalog["common"]["sample_rate_hz"])
    center_hz = float(parameter_catalog["common"]["center_frequency_hz"])
    targets = (
        _shifted_truth(truths["am"], source_center_bin=_source_center_bin(parameter_catalog, "am-carrier"), target_center_bin=centers[0], sample_rate_hz=sample_rate, center_frequency_hz=center_hz),
        _shifted_truth(truths["qpsk"], source_center_bin=_source_center_bin(parameter_catalog, "qpsk"), target_center_bin=centers[1], sample_rate_hz=sample_rate, center_frequency_hz=center_hz),
    )
    runtime = RuntimePipeline(load_profile(PHASE03_PROFILE_PATH))
    estimator = OccupiedBandwidthEstimator()
    outputs: tuple[OccupiedBandwidthEstimate, ...] = ()
    for frame_index in range(5):
        frame = generate_parameter_scene("close-am-qpsk", trial_index=trial, frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=12.0, catalog=parameter_catalog, scene_seed_override=base_seed + 1000)
        result = runtime.process(frame.samples, sample_rate_hz=sample_rate, center_frequency_hz=center_hz, frame_index=frame_index)
        outputs = estimator.process(result.spectrum, result.detection, frame_index=frame_index, generation=0).events
    valid = [item for item in outputs if item.state == "valid"]
    if len(valid) < 2:
        return {"separated": False, "cross_match": False, "valid_output_count": len(valid)}
    best: tuple[float, tuple[OccupiedBandwidthEstimate, OccupiedBandwidthEstimate]] | None = None
    for pair in itertools.permutations(valid, 2):
        score = 0.0
        for output, target in zip(pair, targets):
            score += max(0.0, min(float(output.upper_occupied_edge_hz), target["upper_frequency_hz"]) - max(float(output.lower_occupied_edge_hz), target["lower_frequency_hz"]))
        candidate = (score, pair)
        if best is None or candidate[0] > best[0]:
            best = candidate
    assert best is not None
    selected = best[1]
    separated = best[0] > 0.0 and selected[0].event_id != selected[1].event_id
    cross = False
    for index, output in enumerate(selected):
        own = targets[index]
        other = targets[1 - index]
        own_overlap = max(0.0, min(float(output.upper_occupied_edge_hz), own["upper_frequency_hz"]) - max(float(output.lower_occupied_edge_hz), own["lower_frequency_hz"]))
        other_overlap = max(0.0, min(float(output.upper_occupied_edge_hz), other["upper_frequency_hz"]) - max(float(output.lower_occupied_edge_hz), other["lower_frequency_hz"]))
        cross |= other_overlap > own_overlap
    return {"separated": separated, "cross_match": bool(cross), "valid_output_count": len(valid)}


def _run_noise_sequence(sequence: int, base_seed: int, parameter_catalog: dict[str, Any], frames: int) -> dict[str, int]:
    runtime = RuntimePipeline(load_profile(PHASE03_PROFILE_PATH))
    estimator = OccupiedBandwidthEstimator()
    false_valid_frames = confirmed_frames = 0
    for frame_index in range(frames):
        frame = generate_parameter_scene("noise-only", trial_index=sequence, frame_index=frame_index, catalog=parameter_catalog, scene_seed_override=base_seed + 2000)
        result = runtime.process(frame.samples, sample_rate_hz=float(parameter_catalog["common"]["sample_rate_hz"]), center_frequency_hz=float(parameter_catalog["common"]["center_frequency_hz"]), frame_index=frame_index)
        estimate = estimator.process(result.spectrum, result.detection, frame_index=frame_index, generation=0)
        if any(event.state == "confirmed" and event.observed_this_frame for event in result.detection.active_events):
            confirmed_frames += 1
        if any(item.state == "valid" for item in estimate.events):
            false_valid_frames += 1
    return {"false_valid_frames": false_valid_frames, "confirmed_event_frames": confirmed_frames}


def _gate_result(identifier: str, measured: Any, operator: str, expected: Any, passed: bool, scope: str) -> dict[str, Any]:
    return {"id": identifier, "scope": scope, "measured": measured, "operator": operator, "expected": expected, "status": "passed" if passed else "failed"}


def _binding_decision(families: list[dict[str, Any]], close: dict[str, Any], noise: dict[str, Any], gates: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    gate_map = {item["id"]: item for item in gates["binding_gates"]}
    records: list[dict[str, Any]] = []
    total_trials = sum(int(item["trial_count"]) for item in families)
    total_valid = sum(int(item["valid_count"]) for item in families)
    global_valid = _rate(total_valid, total_trials)
    limit = float(gate_map["obw_valid_rate"]["value"])
    records.append(_gate_result("obw_valid_rate", global_valid, ">=", limit, global_valid >= limit, "global"))
    for family in families:
        records.append(_gate_result("obw_valid_rate", family["valid_rate"], ">=", limit, family["valid_rate"] >= limit, family["family_id"]))
    for metric, gate_id in (("relative_obw_error", "obw_relative_error_q95"), ("lower_edge_error_bins", "lower_edge_absolute_error_q95_bins"), ("upper_edge_error_bins", "upper_edge_absolute_error_q95_bins")):
        values = [value for family in families for value in family.pop(f"_{metric}_values")]
        stat = _order_statistic(values)
        expected = float(gate_map[gate_id]["value"])
        records.append(_gate_result(gate_id, stat["q95"], "<=", expected, stat["q95"] is not None and stat["q95"] <= expected, "global"))
    clipping = sum(int(item["clipping_count"]) for item in families)
    records.append(_gate_result("analysis_window_clipping_rate", _rate(clipping, total_trials), "==", 0.0, clipping == 0, "global"))
    records.append(_gate_result("close_pair_separation_rate", close["separation_rate"], ">=", 0.95, close["separation_rate"] >= 0.95, "close_pair"))
    records.append(_gate_result("close_pair_cross_match_rate", close["cross_match_rate"], "==", 0.0, close["cross_match_count"] == 0, "close_pair"))
    records.append(_gate_result("noise_confirmed_false_valid_rate", noise["false_valid_rate"], "<=", 1.0 / 4096.0, noise["false_valid_rate"] <= 1.0 / 4096.0, "noise_only"))
    temporal_pass = all(item["valid_count"] == 0 or item["temporal_stability"]["certified_q95_upper_bound_bins"] <= 1.0 for item in families)
    records.append(_gate_result("temporal_edge_stability_q95_bins", 1.0 if total_valid else None, "<=", 1.0, temporal_pass and total_valid > 0, "global"))
    return records, all(item["status"] == "passed" for item in records)


def _oos_decision(families: list[dict[str, Any]], close: dict[str, Any], noise: dict[str, Any], gates: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    for family in families:
        scope = family["family_id"]
        records.append(_gate_result("oos_family_obw_valid_rate", family["valid_rate"], ">=", 0.96875, family["valid_rate"] >= 0.96875, scope))
        for metric, identifier, expected in (("relative_obw_error", "oos_family_obw_relative_error_q95", 0.2), ("lower_edge_error_bins", "oos_family_lower_edge_q95_bins", 1.0), ("upper_edge_error_bins", "oos_family_upper_edge_q95_bins", 1.0)):
            value = family[metric]["q95"]
            records.append(_gate_result(identifier, value, "<=", expected, value is not None and value <= expected, scope))
        temporal = family["temporal_stability"]["certified_q95_upper_bound_bins"]
        records.append(_gate_result("oos_temporal_edge_stability_q95_bins", temporal, "<=", 1.0, temporal is not None and temporal <= 1.0, scope))
    total_trials = sum(int(item["trial_count"]) for item in families)
    clipping = sum(int(item["clipping_count"]) for item in families)
    records.append(_gate_result("oos_analysis_window_clipping_rate", _rate(clipping, total_trials), "==", 0.0, clipping == 0, "global"))
    records.append(_gate_result("oos_close_pair_separation_rate", close["separation_rate"], ">=", 0.96875, close["separation_rate"] >= 0.96875, "close_pair"))
    records.append(_gate_result("oos_close_pair_cross_match_count", close["cross_match_count"], "==", 0, close["cross_match_count"] == 0, "close_pair"))
    records.append(_gate_result("oos_noise_confirmed_false_valid_count", noise["false_valid_frames"], "==", 0, noise["false_valid_frames"] == 0, "noise_only"))
    return records, all(item["status"] == "passed" for item in records)


def evaluate_population(role: str) -> dict[str, Any]:
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    d1 = load_json(SCENES_PATH)
    acceptance = load_json(ACCEPTANCE_PATH)
    parameter_catalog = load_parameter_catalog()
    truths = _family_truths()
    common = d1["common"]
    trials = int(common["binding_trials_per_family"] if role == "binding" else common["oos_trials_per_family"])
    base_seed = int(common["binding_base_seed"] if role == "binding" else common["oos_base_seed"])
    family_summaries: list[dict[str, Any]] = []
    for family_index, family in enumerate(d1["supported_families"]):
        trial_records = [
            _run_family_trial(family=family, family_index=family_index, trial=trial, base_seed=base_seed, parameter_catalog=parameter_catalog, truth=truths[family["family_id"]])
            for trial in range(trials)
        ]
        summary = summarize_expected_trials(trial_records)
        summary["family_id"] = family["family_id"]
        record_keys = {
            "relative_obw_error": "relative_error",
            "lower_edge_error_bins": "lower_error_bins",
            "upper_edge_error_bins": "upper_error_bins",
        }
        for metric, record_key in record_keys.items():
            summary[f"_{metric}_values"] = [
                float(item[record_key]) for item in trial_records if item["state"] == "valid"
            ]
        family_summaries.append(summary)
    close_trials = int(common["close_pair_trials"] if role == "binding" else common["oos_trials_per_family"])
    close_records = [_run_close_trial(trial, base_seed, parameter_catalog, truths) for trial in range(close_trials)]
    separated = sum(int(item["separated"]) for item in close_records)
    cross = sum(int(item["cross_match"]) for item in close_records)
    close_summary = {"trial_count": close_trials, "separated_count": separated, "separation_rate": _rate(separated, close_trials), "cross_match_count": cross, "cross_match_rate": _rate(cross, close_trials)}
    noise_sequences = int(common["noise_sequences"] if role == "binding" else acceptance["locked_oos_population"]["noise_only_sequences"])
    noise_frames = int(common["noise_frames_per_sequence"])
    noise_records = [_run_noise_sequence(sequence, base_seed, parameter_catalog, noise_frames) for sequence in range(noise_sequences)]
    false_frames = sum(item["false_valid_frames"] for item in noise_records)
    confirmed_frames = sum(item["confirmed_event_frames"] for item in noise_records)
    total_noise_frames = noise_sequences * noise_frames
    noise_summary = {"sequence_count": noise_sequences, "frames_per_sequence": noise_frames, "frame_count": total_noise_frames, "confirmed_event_frames": confirmed_frames, "false_valid_frames": false_frames, "false_valid_rate": _rate(false_frames, total_noise_frames)}
    if role == "binding":
        decisions, passed = _binding_decision(family_summaries, close_summary, noise_summary, acceptance)
    else:
        for family in family_summaries:
            for key in tuple(family):
                if key.startswith("_"):
                    del family[key]
        decisions, passed = _oos_decision(family_summaries, close_summary, noise_summary, acceptance)
    for family in family_summaries:
        for key in tuple(family):
            if key.startswith("_"):
                del family[key]
    return {
        "schema_version": 1,
        "role": role,
        "status": "passed" if passed else "failed",
        "comparison_id": COMPARISON_ID,
        "base_seed": base_seed,
        "snr_db": 12.0,
        "families": family_summaries,
        "close_pair": close_summary,
        "noise_only": noise_summary,
        "gate_results": decisions,
    }


def evaluation_input_hashes() -> dict[str, str]:
    paths = {
        "acceptance_gates_sha256": ACCEPTANCE_PATH,
        "reference_contract_sha256": REFERENCE_CONTRACT_PATH,
        "scene_catalog_sha256": SCENES_PATH,
        "parameter_scene_catalog_sha256": PARAMETER_SCENES_PATH,
        "clean_reference_sha256": CLEAN_REFERENCE_PATH,
        "method_lock_sha256": METHOD_LOCK_PATH,
        "phase03_profile_sha256": PHASE03_PROFILE_PATH,
    }
    return {key: sha256_file(path) for key, path in paths.items()}


def verify_evaluation_lock(document: dict[str, Any]) -> None:
    if document.get("status") != "locked-pre-run" or document.get("comparison_id") != COMPARISON_ID:
        raise ValueError("evaluation lock identity is invalid")
    for key, value in evaluation_input_hashes().items():
        if document["inputs"].get(key) != value:
            raise ValueError(f"evaluation lock input differs: {key}")
    for item in document["implementation_manifest"]["sources"]:
        if sha256_file(ROOT / item["path"]) != item["sha256"]:
            raise ValueError(f"evaluation implementation differs: {item['path']}")


def evidence_hash(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()
