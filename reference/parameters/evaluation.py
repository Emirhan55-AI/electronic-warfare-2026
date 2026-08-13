"""Deterministic staged PHASE-04-R1 comparison and acceptance metrics."""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from itertools import permutations
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .extraction import ANALYSIS_METHODS, BANDWIDTH_METHODS, MethodSelection, ParameterExtractor
from .scenes import generate_parameter_scene, load_parameter_catalog


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"
PHASE03_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
COMPARISON_ID = "phase04-r1-parameter-selection"
POWER_SNR_METHOD = "power.psd-noise-subtract-v1"
CONTINUOUS_BAND_SCENES = (
    "am-carrier", "nfm", "ook", "two-fsk", "bpsk", "qpsk", "wideband-noise-like",
)
FREQUENCY_SCENES = (
    "tone-bin-centered", "tone-off-bin", "am-carrier", "nfm", "ook", "two-fsk",
    "bpsk", "qpsk", "wideband-noise-like",
)
CLASS_SCENES = ("am-carrier", "nfm", "ook", "two-fsk", "bpsk", "qpsk", "dsb-sc", "mixed-boundary")
MANIFEST_SOURCES = (
    "reference/parameters/__init__.py", "reference/parameters/classification.py",
    "reference/parameters/evaluation.py", "reference/parameters/extraction.py",
    "reference/parameters/models.py", "reference/parameters/scenes.py",
    "reference/detection/__init__.py", "reference/detection/cfar.py", "reference/detection/pipeline.py",
    "reference/spectrum/__init__.py", "reference/spectrum/dsp.py", "reference/spectrum/source.py",
    "reference/pipeline/__init__.py", "reference/pipeline/profile.py",
)
R1_COST_MODELS: dict[str, tuple[int, ...]] = {
    "analysis.single-region-v1": (0, 1, 1, 0, 0, 0),
    "analysis.clustered-regions-v1": (0, 1, 32, 1, 1, 0),
    "band.multi-component-excess-99-v1": (0, 4, 32, 2, 1, 0),
    POWER_SNR_METHOD: (0, 1, 0, 0, 1, 0),
}


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def phase04_implementation_manifest() -> dict[str, object]:
    sources = [
        {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
        for path in sorted(MANIFEST_SOURCES)
    ]
    identity = {"schema_version": 1, "sources": sources}
    return {
        "schema_version": 1,
        "implementation_manifest_sha256": hashlib.sha256(canonical_json_bytes(identity)).hexdigest(),
        "catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest(),
        "phase03_profile_sha256": hashlib.sha256(PHASE03_PROFILE_PATH.read_bytes()).hexdigest(),
        "sources": sources,
    }


@lru_cache(maxsize=1)
def _phase03_profile() -> Any:
    from reference.pipeline import load_profile

    return load_profile(PHASE03_PROFILE_PATH)


def _round(value: float) -> float:
    return round(float(value), 12)


def _q95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return _round(float(np.quantile(np.asarray(values, dtype=np.float64), 0.95, method="linear")))


def _finite_gate(value: float | None, limit: float) -> bool:
    return value is not None and math.isfinite(value) and value <= limit


def _scene(catalog: dict[str, Any], scene_id: str) -> dict[str, Any]:
    return next(item for item in catalog["scenes"] if item["id"] == scene_id)


def _truth_bins(catalog: dict[str, Any], scene: dict[str, Any]) -> tuple[float, float | None, float | None]:
    if scene["family"] == "wideband":
        lower = float(scene["band_definition"]["lower_shifted_edge"])
        upper = float(scene["band_definition"]["upper_shifted_edge"])
        return 0.5 * (lower + upper), lower, upper
    center = 2048.0 + float(scene.get("signed_center_bin", 0.0))
    band = scene.get("band_definition")
    if band is None:
        return center, None, None
    return center, center + float(band["lower_offset_bins"]), center + float(band["upper_offset_bins"])


def _close_truth(catalog: dict[str, Any]) -> tuple[tuple[float, float, float], ...]:
    close = _scene(catalog, "close-am-qpsk")
    am = _scene(catalog, "am-carrier")["band_definition"]
    qpsk = _scene(catalog, "qpsk")["band_definition"]
    centers = [2048.0 + float(value) for value in close["component_centers_bins"]]
    return (
        (centers[0], centers[0] + float(am["lower_offset_bins"]), centers[0] + float(am["upper_offset_bins"])),
        (centers[1], centers[1] + float(qpsk["lower_offset_bins"]), centers[1] + float(qpsk["upper_offset_bins"])),
    )


def _run_sequence(
    selection: MethodSelection,
    scene_id: str,
    *,
    trial: int,
    condition: int,
    frame_count: int,
    score_frame: int,
    power_dbfs: float,
    snr_db: float,
    catalog: dict[str, Any],
    trace: list[Any] | None = None,
) -> tuple[Any, Any]:
    common = catalog["common"]
    from reference.pipeline import RuntimePipeline

    runtime = RuntimePipeline(_phase03_profile())
    extractor = ParameterExtractor(selection)
    scored_frame = scored_result = None
    for frame_index in range(frame_count):
        frame = generate_parameter_scene(
            scene_id,
            trial_index=trial,
            condition_index=condition,
            frame_index=frame_index,
            clean_power_dbfs=power_dbfs,
            snr_db=snr_db,
            catalog=catalog,
        )
        runtime_result = runtime.process(
            frame.samples,
            sample_rate_hz=float(common["sample_rate_hz"]),
            center_frequency_hz=float(common["center_frequency_hz"]),
            frame_index=frame_index,
        )
        result = extractor.process(
            frame.samples, runtime_result.spectrum, runtime_result.detection, frame_index=frame_index,
        )
        if trace is not None:
            trace.append(result)
        if frame_index == score_frame:
            scored_frame, scored_result = frame, result
    assert scored_frame is not None and scored_result is not None
    return scored_frame, scored_result


def _cost(catalog: dict[str, Any], methods: Iterable[str]) -> tuple[int, ...]:
    records = [
        R1_COST_MODELS[name] if name in R1_COST_MODELS else tuple(catalog["cost_models"][name])
        for name in methods
    ]
    return (
        sum(item[0] for item in records), sum(item[1] for item in records), max(item[2] for item in records),
        sum(item[3] for item in records), sum(item[4] for item in records), sum(item[5] for item in records),
    )


def _paired_bootstrap_difference(
    best: Sequence[float], other: Sequence[float], *, seed: int, repetitions: int,
) -> tuple[float, float]:
    if len(best) != len(other) or not best:
        raise ValueError("paired bootstrap vectors must be non-empty and equal-length")
    delta = np.asarray(other, dtype=np.float64) - np.asarray(best, dtype=np.float64)
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions, dtype=np.float64)
    batch = 256
    for start in range(0, repetitions, batch):
        count = min(batch, repetitions - start)
        indices = rng.integers(0, delta.size, size=(count, delta.size))
        means[start : start + count] = np.mean(delta[indices], axis=1)
    return (
        _round(float(np.quantile(means, 0.025, method="linear"))),
        _round(float(np.quantile(means, 0.975, method="linear"))),
    )


def _paired_bootstrap_layer_difference(
    best: dict[str, Sequence[float]], other: dict[str, Sequence[float]], *, seed: int, repetitions: int,
) -> tuple[float, float]:
    if tuple(best) != tuple(other) or not best:
        raise ValueError("paired bootstrap layers differ")
    deltas = {
        name: np.asarray(other[name], dtype=np.float64) - np.asarray(best[name], dtype=np.float64)
        for name in best
    }
    if any(values.size == 0 or values.size != len(best[name]) for name, values in deltas.items()):
        raise ValueError("paired bootstrap layer is empty or unpaired")
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions, dtype=np.float64)
    batch = 128
    for start in range(0, repetitions, batch):
        count = min(batch, repetitions - start)
        layer_means = []
        for name, values in deltas.items():
            indices = rng.integers(0, values.size, size=(count, values.size))
            layer_means.append(np.mean(values[indices], axis=1))
        means[start : start + count] = np.mean(np.stack(layer_means, axis=1), axis=1)
    return (
        _round(float(np.quantile(means, 0.025, method="linear"))),
        _round(float(np.quantile(means, 0.975, method="linear"))),
    )


def _choose(
    records: list[dict[str, Any]], catalog: dict[str, Any], method_fields: tuple[str, ...],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    eligible = [record for record in records if record["eligible"]]
    if not eligible:
        return None, {"status": "failed", "reason": "no candidate passed every fixed gate", "comparisons": []}
    eligible.sort(key=lambda item: (item["normalized_loss"], tuple(item[field] for field in method_fields)))
    best = eligible[0]
    threshold = float(catalog["selection_contract"]["minimum_meaningful_loss_difference"])
    seed = int(catalog["selection_contract"]["paired_bootstrap_seed"])
    repetitions = int(catalog["selection_contract"]["bootstrap_repetitions"])
    comparisons: list[dict[str, Any]] = []
    tied = [best]
    for index, other in enumerate(eligible[1:], start=1):
        if "_paired_layers" in best:
            lower, upper = _paired_bootstrap_layer_difference(
                best["_paired_layers"], other["_paired_layers"], seed=seed, repetitions=repetitions,
            )
        else:
            lower, upper = _paired_bootstrap_difference(
                best["_paired_losses"], other["_paired_losses"], seed=seed, repetitions=repetitions,
            )
        mean_difference = _round(float(other["normalized_loss"]) - float(best["normalized_loss"]))
        significant = mean_difference >= threshold and lower > 0.0
        comparisons.append({
            "candidate": {field: other[field] for field in method_fields},
            "loss_difference_from_best": mean_difference,
            "paired_bootstrap_ci95": [lower, upper],
            "best_significantly_better": significant,
        })
        if not significant:
            tied.append(other)
    selected = min(
        tied,
        key=lambda item: (_cost(catalog, (item[field] for field in method_fields)), tuple(item[field] for field in method_fields)),
    )
    return selected, {
        "status": "passed",
        "reason": "paired-bootstrap quality then deterministic cost tie-break",
        "minimum_meaningful_difference": threshold,
        "paired_bootstrap_seed": seed,
        "bootstrap_repetitions": repetitions,
        "bootstrap_interval": "percentile-95",
        "comparisons": comparisons,
    }


def _gate_applicability(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    gates = catalog["success_gates"]
    scopes = {
        "carrier_valid_rate_minimum": "global-expected-carrier",
        "carrier_q95_error_bins_maximum": "global-valid-carrier",
        "spectral_center_q95_error_bins_maximum": "global-valid-spectral-center",
        "false_carrier_rate_maximum": "global-carrier-not-observed",
        "carrier_abstention_rate_minimum": "global-carrier-not-observed",
        "band_edge_q95_error_bins_floor": "per-estimate-lower-and-upper",
        "band_edge_q95_error_width_fraction": "per-estimate-lower-and-upper",
        "bandwidth_q95_relative_error_maximum": "global-valid-bandwidth",
        "bandwidth_valid_rate_minimum": "global-bandwidth-valid-ground-truth",
        "region_success_rate_minimum": "global-bandwidth-valid-ground-truth",
        "region_coverage_minimum": "per-estimate",
        "region_iou_minimum": "per-estimate",
        "region_overreach_maximum": "per-estimate",
        "close_pair_separate_rate_minimum": "close-pair-frame",
        "close_pair_cross_match_rate_maximum": "close-pair-frame",
        "noise_false_valid_rate_maximum": "noise-temporal-frame",
        "power_q95_error_db_maximum": "global-valid-power-snr-ge-6",
        "snr_q95_error_db_maximum": "global-valid-snr-snr-ge-6",
        "zero_snr_power_median_error_db_maximum": "global-valid-power-snr-0",
        "zero_snr_median_error_db_maximum": "global-valid-snr-snr-0",
        "classification_wrong_definite_total_maximum": "global-definite-family-snr-ge-6",
        "classification_wrong_definite_family_maximum": "per-definite-family-snr-ge-6",
        "classification_correct_definite_total_minimum": "global-definite-family-snr-ge-6",
        "classification_correct_definite_family_minimum": "per-definite-family-snr-ge-6",
        "zero_snr_wrong_definite_maximum": "global-definite-family-snr-0",
        "uncertain_rejection_rate_minimum": "uncertain-family-and-snr-minus-6",
        "noise_definite_count_maximum": "noise-only-count",
    }
    return [
        {"name": name, "value": value, "scope": scopes[name], "binding": True}
        for name, value in gates.items()
    ]


def _match_estimates(estimates: Sequence[Any], truths: Sequence[tuple[float, float, float]]) -> list[Any | None]:
    valid = [item for item in estimates if item.bandwidth.bandwidth_state == "valid"]
    if not valid:
        return [None] * len(truths)

    def pair_cost(truth_index: int, estimate_index: int) -> tuple[float, float, int] | None:
        center, truth_lo, truth_hi = truths[truth_index]
        item = valid[estimate_index]
        predicted_lo = float(item.bandwidth.lower_shifted_bin)
        predicted_hi = float(item.bandwidth.upper_shifted_bin + 1)
        intersection = max(0.0, min(predicted_hi, truth_hi) - max(predicted_lo, truth_lo))
        union = max(predicted_hi, truth_hi) - min(predicted_lo, truth_lo)
        iou = intersection / union if union else 0.0
        predicted_center = 0.5 * (predicted_lo + predicted_hi)
        if abs(predicted_center - center) > max(predicted_hi - predicted_lo, truth_hi - truth_lo):
            return None
        return -iou, abs(predicted_center - center), int(item.event_id)

    assignment_size = min(len(truths), len(valid))
    best: tuple[tuple[float, float, tuple[int, ...]], tuple[int, ...]] | None = None
    for truth_indices in permutations(range(len(truths)), assignment_size):
        for estimate_indices in permutations(range(len(valid)), assignment_size):
            costs = [pair_cost(t, e) for t, e in zip(truth_indices, estimate_indices)]
            if any(cost is None for cost in costs):
                continue
            concrete = [cost for cost in costs if cost is not None]
            key = (sum(cost[0] for cost in concrete), sum(cost[1] for cost in concrete), tuple(cost[2] for cost in concrete))
            if best is None or key < best[0]:
                encoded = tuple(value for pair in zip(truth_indices, estimate_indices) for value in pair)
                best = (key, encoded)
    matched: list[Any | None] = [None] * len(truths)
    if best is not None:
        encoded = best[1]
        for index in range(0, len(encoded), 2):
            matched[encoded[index]] = valid[encoded[index + 1]]
    return matched


def _select_scored_estimate(
    estimates: Sequence[Any], catalog: dict[str, Any], truth_center: float,
    truth_lo: float | None, truth_hi: float | None,
) -> Any | None:
    """Match a post-runtime estimate to frozen truth without influencing extraction."""
    common = catalog["common"]
    candidates: list[tuple[tuple[float, ...], Any]] = []
    for estimate in estimates[:64]:
        frequency = estimate.frequency
        if frequency.spectral_center_state != "valid" or frequency.spectral_center_frequency_hz is None:
            continue
        center_bin = 2048.0 + (
            float(frequency.spectral_center_frequency_hz) - float(common["center_frequency_hz"])
        ) / float(common["bin_spacing_hz"])
        center_error = abs(center_bin - truth_center)
        if truth_lo is not None and truth_hi is not None:
            bandwidth = estimate.bandwidth
            if bandwidth.bandwidth_state != "valid":
                continue
            predicted_lo = float(bandwidth.lower_shifted_bin)
            predicted_hi = float(bandwidth.upper_shifted_bin + 1)
            intersection = max(0.0, min(predicted_hi, truth_hi) - max(predicted_lo, truth_lo))
            if intersection <= 0.0:
                continue
            union = max(predicted_hi, truth_hi) - min(predicted_lo, truth_lo)
            iou = intersection / union if union else 0.0
            key = (-iou, center_error, float(estimate.event_id))
        else:
            key = (center_error, float(estimate.event_id))
        candidates.append((key, estimate))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def _new_band_accumulator(selection: MethodSelection) -> dict[str, Any]:
    return {
        "selection": selection,
        "target_count": 0, "valid_count": 0, "region_success_count": 0,
        "width_errors": [], "lower_errors": [], "upper_errors": [],
        "lower_normalized": [], "upper_normalized": [],
        "coverages": [], "ious": [], "overreaches": [],
        "invalid_reasons": {},
        "layers": {"continuous": [], "burst": [], "close": [], "noise": []},
        "diagnostics": {}, "burst_passive_valid": 0,
        "close_frames": 0, "close_separate": 0, "close_cross": 0,
        "noise_frames": 0, "noise_false_frames": 0,
        "noise_unique_events": 0, "noise_false_sequences": 0,
    }


def _band_measurements(result: Any, truths: Sequence[tuple[float, float, float]], gates: dict[str, Any]) -> list[dict[str, Any]]:
    measured: list[dict[str, Any]] = []
    for estimate, (_, truth_lo, truth_hi) in zip(_match_estimates(result.events, truths), truths):
        if estimate is None:
            measured.append({"valid": False, "reason": "no_valid_estimate", "loss": 1.0})
            continue
        predicted_lo = float(estimate.bandwidth.lower_shifted_bin)
        predicted_hi = float(estimate.bandwidth.upper_shifted_bin + 1)
        truth_width = truth_hi - truth_lo
        predicted_width = predicted_hi - predicted_lo
        limit = max(float(gates["band_edge_q95_error_bins_floor"]), truth_width * float(gates["band_edge_q95_error_width_fraction"]))
        width_error = abs(predicted_width - truth_width) / truth_width
        lower_error = abs(predicted_lo - truth_lo)
        upper_error = abs(predicted_hi - truth_hi)
        intersection = max(0.0, min(predicted_hi, truth_hi) - max(predicted_lo, truth_lo))
        union = max(predicted_hi, truth_hi) - min(predicted_lo, truth_lo)
        coverage = intersection / truth_width
        iou = intersection / union if union else 0.0
        overreach = max(0.0, predicted_width - intersection) / predicted_width if predicted_width else 1.0
        region_ok = coverage >= gates["region_coverage_minimum"] and iou >= gates["region_iou_minimum"] and overreach <= gates["region_overreach_maximum"]
        measured.append({
            "valid": True, "width_error": width_error, "lower_error": lower_error,
            "upper_error": upper_error, "lower_normalized": lower_error / limit,
            "upper_normalized": upper_error / limit, "coverage": coverage, "iou": iou,
            "overreach": overreach, "region_ok": region_ok,
            "loss": float(np.mean((min(width_error / 0.2, 2.0), min(lower_error / limit, 2.0), min(upper_error / limit, 2.0), 0.0 if region_ok else 1.0))),
        })
    return measured


def _record_band_measurements(acc: dict[str, Any], measurements: Sequence[dict[str, Any]], layer: str) -> None:
    for item in measurements:
        acc["target_count"] += 1
        acc["layers"][layer].append(float(item["loss"]))
        if not item["valid"]:
            reason = str(item["reason"])
            acc["invalid_reasons"][reason] = acc["invalid_reasons"].get(reason, 0) + 1
            continue
        acc["valid_count"] += 1
        acc["region_success_count"] += int(item["region_ok"])
        for name in ("width_error", "lower_error", "upper_error", "lower_normalized", "upper_normalized", "coverage", "iou", "overreach"):
            acc[{"width_error": "width_errors", "lower_error": "lower_errors", "upper_error": "upper_errors", "lower_normalized": "lower_normalized", "upper_normalized": "upper_normalized", "coverage": "coverages", "iou": "ious", "overreach": "overreaches"}[name]].append(float(item[name]))


def _record_band_diagnostic(
    acc: dict[str, Any], key: tuple[str, float], measurements: Sequence[dict[str, Any]],
) -> None:
    diagnostic = acc["diagnostics"].setdefault(
        key,
        {
            "targets": 0,
            "valid": 0,
            "region_success": 0,
            "width_errors": [],
            "lower_normalized": [],
            "upper_normalized": [],
            "coverages": [],
            "ious": [],
            "overreaches": [],
        },
    )
    diagnostic["targets"] += len(measurements)
    for item in measurements:
        if not item["valid"]:
            continue
        diagnostic["valid"] += 1
        diagnostic["region_success"] += int(item["region_ok"])
        for target_name, source_name in (
            ("width_errors", "width_error"),
            ("lower_normalized", "lower_normalized"),
            ("upper_normalized", "upper_normalized"),
            ("coverages", "coverage"),
            ("ious", "iou"),
            ("overreaches", "overreach"),
        ):
            diagnostic[target_name].append(float(item[source_name]))


def _band_diagnostic_row(scene: str, snr_db: float, values: dict[str, Any]) -> dict[str, Any]:
    targets = int(values["targets"])
    return {
        "scene": scene,
        "snr_db": snr_db,
        "targets": targets,
        "valid_rate": _round(values["valid"] / targets),
        "region_success_rate": _round(values["region_success"] / targets),
        "q95_relative_bandwidth_error": _q95(values["width_errors"]),
        "q95_lower_edge_normalized_to_scene_limit": _q95(values["lower_normalized"]),
        "q95_upper_edge_normalized_to_scene_limit": _q95(values["upper_normalized"]),
        "mean_coverage": _round(float(np.mean(values["coverages"]))) if values["coverages"] else None,
        "mean_iou": _round(float(np.mean(values["ious"]))) if values["ious"] else None,
        "mean_overreach": _round(float(np.mean(values["overreaches"]))) if values["overreaches"] else None,
        "binding": snr_db == 12.0,
    }


def _run_shared_band_sequence(
    catalog: dict[str, Any], contexts: list[dict[str, Any]], scene_id: str, *, trial: int,
    condition: int, frame_count: int, score_frame: int, snr_db: float,
) -> tuple[list[Any], list[list[Any]]]:
    from reference.pipeline import RuntimePipeline

    runtime = RuntimePipeline(_phase03_profile())
    extractors = [ParameterExtractor(item["selection"]) for item in contexts]
    scored: list[Any] = [None] * len(contexts)
    traces: list[list[Any]] = [[] for _ in contexts]
    common = catalog["common"]
    for frame_index in range(frame_count):
        frame = generate_parameter_scene(
            scene_id, trial_index=trial, condition_index=condition, frame_index=frame_index,
            clean_power_dbfs=-18.0, snr_db=snr_db, catalog=catalog,
        )
        runtime_result = runtime.process(
            frame.samples, sample_rate_hz=float(common["sample_rate_hz"]),
            center_frequency_hz=float(common["center_frequency_hz"]), frame_index=frame_index,
        )
        for index, extractor in enumerate(extractors):
            result = extractor.process(frame.samples, runtime_result.spectrum, runtime_result.detection, frame_index=frame_index)
            traces[index].append(result)
            if frame_index == score_frame:
                scored[index] = result
    return scored, traces


def _band_pairs(catalog: dict[str, Any], trials: int, full: bool) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any]]:
    gates = catalog["success_gates"]
    contexts = [
        _new_band_accumulator(MethodSelection(noise, bandwidth, "center.excess-power-centroid", "carrier.peak-gated", "domain.explainable-rules", analysis, POWER_SNR_METHOD))
        for analysis in ANALYSIS_METHODS for noise in catalog["method_order"]["noise"] for bandwidth in BANDWIDTH_METHODS
    ]
    snr_order = list(catalog["power_benchmark"]["snr_db_order"])
    for scene_index, scene_id in enumerate(CONTINUOUS_BAND_SCENES):
        spec = _scene(catalog, scene_id)
        center, truth_lo, truth_hi = _truth_bins(catalog, spec)
        assert truth_lo is not None and truth_hi is not None
        truths = ((center, truth_lo, truth_hi),)
        for snr_index, snr_db in enumerate(snr_order):
            for trial in range(trials):
                scored, _ = _run_shared_band_sequence(catalog, contexts, scene_id, trial=trial, condition=scene_index * 4 + snr_index, frame_count=4, score_frame=3, snr_db=snr_db)
                for acc, result in zip(contexts, scored):
                    measurements = _band_measurements(result, truths, gates)
                    key = (scene_id, snr_db)
                    _record_band_diagnostic(acc, key, measurements)
                    if snr_db == 12.0:
                        _record_band_measurements(acc, measurements, "continuous")

    burst = _scene(catalog, "burst-qpsk")
    center, truth_lo, truth_hi = _truth_bins(catalog, burst)
    assert truth_lo is not None and truth_hi is not None
    burst_truth = ((center, truth_lo, truth_hi),)
    for snr_index, snr_db in enumerate(snr_order):
        for trial in range(trials):
            scored, traces = _run_shared_band_sequence(catalog, contexts, "burst-qpsk", trial=trial, condition=28 + snr_index, frame_count=6, score_frame=4, snr_db=snr_db)
            for acc, result, trace in zip(contexts, scored, traces):
                measurements = _band_measurements(result, burst_truth, gates)
                key = ("burst-qpsk", snr_db)
                _record_band_diagnostic(acc, key, measurements)
                acc["burst_passive_valid"] += sum(item.bandwidth.bandwidth_state == "valid" for index in (0, 1, 5) for item in trace[index].events)
                if snr_db == 12.0:
                    _record_band_measurements(acc, measurements, "burst")

    close_truth = _close_truth(catalog)
    midpoint = 0.5 * (close_truth[0][0] + close_truth[1][0])
    for snr_index, snr_db in enumerate(snr_order):
        for trial in range(trials):
            scored, _ = _run_shared_band_sequence(catalog, contexts, "close-am-qpsk", trial=trial, condition=32 + snr_index, frame_count=4, score_frame=3, snr_db=snr_db)
            for acc, result in zip(contexts, scored):
                matched = _match_estimates(result.events, close_truth)
                measurements = _band_measurements(result, close_truth, gates)
                key = ("close-am-qpsk", snr_db)
                _record_band_diagnostic(acc, key, measurements)
                separate = len([item for item in matched if item is not None]) == 2 and int(matched[0].bandwidth.upper_shifted_bin) < int(matched[1].bandwidth.lower_shifted_bin)  # type: ignore[union-attr]
                cross = any((index == 0 and int(item.bandwidth.upper_shifted_bin) >= midpoint) or (index == 1 and int(item.bandwidth.lower_shifted_bin) <= midpoint) for index, item in enumerate(matched) if item is not None)
                if snr_db == 12.0:
                    _record_band_measurements(acc, measurements, "close")
                    acc["close_frames"] += 1
                    acc["close_separate"] += int(separate)
                    acc["close_cross"] += int(cross)
                    acc["layers"]["close"][-2:] = [float(np.mean((np.mean([item["loss"] for item in measurements]), 0.0 if separate else 1.0, 1.0 if cross else 0.0)))]

    noise_sequences = 128 if full else 1
    for trial in range(noise_sequences):
        scored, traces = _run_shared_band_sequence(catalog, contexts, "noise-only", trial=trial, condition=36, frame_count=32, score_frame=31, snr_db=12.0)
        for acc, trace in zip(contexts, traces):
            false_frames = sum(any(item.bandwidth.bandwidth_state == "valid" for item in result.events) for result in trace)
            unique_events = {item.event_id for result in trace for item in result.events if item.bandwidth.bandwidth_state == "valid"}
            acc["noise_frames"] += 32
            acc["noise_false_frames"] += false_frames
            acc["noise_unique_events"] += len(unique_events)
            acc["noise_false_sequences"] += int(false_frames > 0)
            acc["layers"]["noise"].append(len(unique_events) / 32.0)

    records: list[dict[str, Any]] = []
    for acc in contexts:
        valid_rate = acc["valid_count"] / acc["target_count"]
        region_rate = acc["region_success_count"] / acc["target_count"]
        close_separate_rate = acc["close_separate"] / acc["close_frames"]
        close_cross_rate = acc["close_cross"] / acc["close_frames"]
        noise_rate = acc["noise_unique_events"] / acc["noise_frames"]
        noise_false_frame_rate = acc["noise_false_frames"] / acc["noise_frames"]
        width_q95 = _q95(acc["width_errors"])
        lower_normalized_q95 = _q95(acc["lower_normalized"])
        upper_normalized_q95 = _q95(acc["upper_normalized"])
        eligible = valid_rate >= gates["bandwidth_valid_rate_minimum"] and _finite_gate(width_q95, gates["bandwidth_q95_relative_error_maximum"]) and _finite_gate(lower_normalized_q95, 1.0) and _finite_gate(upper_normalized_q95, 1.0) and region_rate >= gates["region_success_rate_minimum"] and close_separate_rate >= gates["close_pair_separate_rate_minimum"] and close_cross_rate <= gates["close_pair_cross_match_rate_maximum"] and noise_rate <= gates["noise_false_valid_rate_maximum"]
        selection = acc["selection"]
        diagnostic_rows = [
            _band_diagnostic_row(scene, snr, values)
            for (scene, snr), values in sorted(acc["diagnostics"].items(), key=lambda item: (item[0][0], item[0][1]))
        ]
        records.append({
            "analysis_window_method": selection.analysis_window, "noise_method": selection.noise,
            "bandwidth_method": selection.bandwidth, "target_trials": acc["target_count"],
            "valid_results": acc["valid_count"], "invalid_reasons": dict(sorted(acc["invalid_reasons"].items())),
            "valid_rate": _round(valid_rate), "q95_relative_bandwidth_error": width_q95,
            "q95_lower_edge_error_bins": _q95(acc["lower_errors"]), "q95_upper_edge_error_bins": _q95(acc["upper_errors"]),
            "q95_lower_edge_normalized_to_scene_limit": lower_normalized_q95,
            "q95_upper_edge_normalized_to_scene_limit": upper_normalized_q95,
            "mean_coverage": _round(float(np.mean(acc["coverages"]))) if acc["coverages"] else None,
            "mean_iou": _round(float(np.mean(acc["ious"]))) if acc["ious"] else None,
            "mean_overreach": _round(float(np.mean(acc["overreaches"]))) if acc["overreaches"] else None,
            "region_success_rate": _round(region_rate), "close_pair_separate_rate": _round(close_separate_rate),
            "close_pair_cross_match_rate": _round(close_cross_rate), "noise_false_valid_rate": _round(noise_rate),
            "noise_false_frame_rate_diagnostic": _round(noise_false_frame_rate),
            "noise_temporal_frame_count": acc["noise_frames"],
            "noise_unique_false_event_count": acc["noise_unique_events"],
            "noise_false_sequence_count": acc["noise_false_sequences"],
            "noise_false_sequence_rate_diagnostic": _round(acc["noise_false_sequences"] / noise_sequences),
            "burst_passive_frame_valid_outputs_diagnostic": acc["burst_passive_valid"],
            "family_snr_diagnostics": diagnostic_rows,
            "normalized_loss": _round(float(np.mean([np.mean(values) for values in acc["layers"].values()]))),
            "resource_cost": list(_cost(catalog, (selection.analysis_window, selection.noise, selection.bandwidth))),
            "eligible": bool(eligible), "status": "passed" if eligible else "failed", "_paired_layers": acc["layers"],
        })
    selected, decision = _choose(records, catalog, ("analysis_window_method", "noise_method", "bandwidth_method"))
    return [{key: value for key, value in record.items() if key != "_paired_layers"} for record in records], selected, decision


def _frequency_pairs(catalog: dict[str, Any], upstream: dict[str, Any], trials: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any]]:
    gates = catalog["success_gates"]
    records: list[dict[str, Any]] = []
    for center_method in catalog["method_order"]["spectral_center"]:
        for carrier_method in catalog["method_order"]["carrier"]:
            selection = MethodSelection(
                upstream["noise_method"], upstream["bandwidth_method"], center_method, carrier_method,
                "domain.explainable-rules", upstream["analysis_window_method"], POWER_SNR_METHOD,
            )
            center_errors: list[float] = []
            carrier_errors: list[float] = []
            center_invalid = carrier_valid = carrier_expected = false_carrier = no_carrier_expected = 0
            losses: list[float] = []
            for scene_index, scene_id in enumerate(FREQUENCY_SCENES):
                spec = _scene(catalog, scene_id)
                truth_center, truth_lo, truth_hi = _truth_bins(catalog, spec)
                expected_carrier = spec["validity"][1] == "valid"
                for trial in range(trials):
                    _, result = _run_sequence(
                        selection, scene_id, trial=trial, condition=100 + scene_index,
                        frame_count=4, score_frame=3, power_dbfs=-18.0, snr_db=12.0, catalog=catalog,
                    )
                    estimate = _select_scored_estimate(
                        result.events, catalog, truth_center, truth_lo, truth_hi,
                    )
                    if expected_carrier:
                        carrier_expected += 1
                    else:
                        no_carrier_expected += 1
                    if estimate is None or estimate.frequency.spectral_center_state != "valid":
                        center_invalid += 1
                        losses.append(1.0)
                        continue
                    center_hz = estimate.frequency.spectral_center_frequency_hz
                    assert center_hz is not None
                    center_bin = 2048.0 + (center_hz - catalog["common"]["center_frequency_hz"]) / catalog["common"]["bin_spacing_hz"]
                    center_error = abs(center_bin - truth_center)
                    center_errors.append(center_error)
                    carrier = estimate.frequency.observed_carrier_frequency_hz
                    carrier_error = 1.0
                    if expected_carrier and carrier is not None:
                        carrier_valid += 1
                        carrier_bin = 2048.0 + (carrier - catalog["common"]["center_frequency_hz"]) / catalog["common"]["bin_spacing_hz"]
                        error = abs(carrier_bin - truth_center)
                        carrier_errors.append(error)
                        carrier_error = min(error / gates["carrier_q95_error_bins_maximum"], 2.0)
                    elif not expected_carrier:
                        false_carrier += int(carrier is not None)
                        carrier_error = float(carrier is not None)
                    losses.append(float(np.mean((min(center_error / gates["spectral_center_q95_error_bins_maximum"], 2.0), carrier_error))))
            valid_rate = carrier_valid / carrier_expected if carrier_expected else 0.0
            false_rate = false_carrier / no_carrier_expected if no_carrier_expected else 0.0
            center_q95 = _q95(center_errors)
            carrier_q95 = _q95(carrier_errors)
            abstention = 1.0 - false_rate
            eligible = (
                valid_rate >= gates["carrier_valid_rate_minimum"]
                and _finite_gate(carrier_q95, gates["carrier_q95_error_bins_maximum"])
                and _finite_gate(center_q95, gates["spectral_center_q95_error_bins_maximum"])
                and false_rate <= gates["false_carrier_rate_maximum"]
                and abstention >= gates["carrier_abstention_rate_minimum"]
            )
            records.append({
                "spectral_center_method": center_method, "carrier_method": carrier_method,
                "center_expected_trials": len(FREQUENCY_SCENES) * trials, "center_invalid_results": center_invalid,
                "carrier_expected_trials": carrier_expected, "no_carrier_expected_trials": no_carrier_expected,
                "carrier_valid_rate": _round(valid_rate), "carrier_q95_error_bins": carrier_q95,
                "spectral_center_q95_error_bins": center_q95, "false_carrier_rate": _round(false_rate),
                "carrier_abstention_rate": _round(abstention), "normalized_loss": _round(float(np.mean(losses))),
                "resource_cost": list(_cost(catalog, (center_method, carrier_method))),
                "eligible": bool(eligible), "status": "passed" if eligible else "failed", "_paired_losses": losses,
            })
    selected, decision = _choose(records, catalog, ("spectral_center_method", "carrier_method"))
    return [{key: value for key, value in item.items() if key != "_paired_losses"} for item in records], selected, decision


def _selection_from(upstream: dict[str, Any], center: str, carrier: str, domain: str) -> MethodSelection:
    return MethodSelection(
        upstream["noise_method"], upstream["bandwidth_method"], center, carrier, domain,
        upstream["analysis_window_method"], POWER_SNR_METHOD,
    )


def _record_definite_event_ids(result: Any, sequence_event_ids: set[int]) -> int:
    definite_ids = {
        int(item.event_id) for item in result.events if item.signal_domain.value != "Belirsiz"
    }
    sequence_event_ids.update(definite_ids)
    return int(bool(definite_ids))


def _power_metrics(catalog: dict[str, Any], selection: MethodSelection, trials: int) -> tuple[dict[str, Any], bool]:
    contract = catalog["power_benchmark"]
    errors_high_power: list[float] = []
    errors_high_snr: list[float] = []
    zero_power: list[float] = []
    zero_snr: list[float] = []
    invalid = 0
    families: list[dict[str, Any]] = []
    condition_diagnostics: list[dict[str, Any]] = []
    for family_index, scene_id in enumerate(contract["family_order"]):
        scene_spec = _scene(catalog, scene_id)
        truth_center, truth_lo, truth_hi = _truth_bins(catalog, scene_spec)
        family_power: list[float] = []
        family_snr: list[float] = []
        family_invalid = 0
        for power_index, power_dbfs in enumerate(contract["clean_power_dbfs_order"]):
            for snr_index, snr_db in enumerate(contract["snr_db_order"]):
                condition = family_index * 12 + power_index * 4 + snr_index
                condition_power: list[float] = []
                condition_snr: list[float] = []
                condition_invalid = 0
                for trial in range(trials):
                    _, result = _run_sequence(
                        selection, scene_id, trial=trial, condition=condition,
                        frame_count=4, score_frame=3, power_dbfs=power_dbfs, snr_db=snr_db, catalog=catalog,
                    )
                    estimate = _select_scored_estimate(
                        result.events, catalog, truth_center, truth_lo, truth_hi,
                    )
                    if estimate is None or estimate.power.relative_power_state != "valid" or estimate.power.snr_state != "valid":
                        invalid += 1
                        family_invalid += 1
                        condition_invalid += 1
                        continue
                    power_error = abs(float(estimate.power.signal_power_dbfs) - float(power_dbfs))
                    snr_error = abs(float(estimate.power.snr_db) - float(snr_db))
                    family_power.append(power_error)
                    family_snr.append(snr_error)
                    condition_power.append(power_error)
                    condition_snr.append(snr_error)
                    if snr_db >= 6.0:
                        errors_high_power.append(power_error)
                        errors_high_snr.append(snr_error)
                    elif snr_db == 0.0:
                        zero_power.append(power_error)
                        zero_snr.append(snr_error)
                condition_diagnostics.append({
                    "family": scene_id, "clean_power_dbfs": power_dbfs, "snr_db": snr_db,
                    "trials": trials, "invalid_results": condition_invalid,
                    "q95_power_error_db": _q95(condition_power), "q95_snr_error_db": _q95(condition_snr),
                    "binding": snr_db in {0.0, 6.0, 12.0},
                })
        families.append({
            "family": scene_id, "trials": 12 * trials, "invalid_results": family_invalid,
            "q95_power_error_db": _q95(family_power), "q95_snr_error_db": _q95(family_snr), "binding": False,
        })
    q95_power = _q95(errors_high_power)
    q95_snr = _q95(errors_high_snr)
    median_zero_power = _round(float(np.median(zero_power))) if zero_power else None
    median_zero_snr = _round(float(np.median(zero_snr))) if zero_snr else None
    gates = catalog["success_gates"]
    passed = (
        _finite_gate(q95_power, gates["power_q95_error_db_maximum"])
        and _finite_gate(q95_snr, gates["snr_q95_error_db_maximum"])
        and _finite_gate(median_zero_power, gates["zero_snr_power_median_error_db_maximum"])
        and _finite_gate(median_zero_snr, gates["zero_snr_median_error_db_maximum"])
    )
    return {
        "method": POWER_SNR_METHOD, "status": "passed" if passed else "failed",
        "family_order": list(contract["family_order"]), "clean_power_dbfs_order": list(contract["clean_power_dbfs_order"]),
        "snr_db_order": list(contract["snr_db_order"]), "trials_per_condition": trials,
        "condition_index_rule": contract["condition_index_rule"], "invalid_results_diagnostic": invalid,
        "q95_power_error_db_snr_ge_6": q95_power, "q95_snr_error_db_snr_ge_6": q95_snr,
        "median_power_error_db_snr_0": median_zero_power, "median_snr_error_db_snr_0": median_zero_snr,
        "families": families, "family_power_snr_diagnostics": condition_diagnostics,
    }, passed


def _classification_metrics(catalog: dict[str, Any], upstream: MethodSelection, method: str, trials: int) -> tuple[dict[str, Any], bool]:
    gates = catalog["success_gates"]
    family_records: list[dict[str, Any]] = []
    family_snr_diagnostics: list[dict[str, Any]] = []
    total_correct = total_wrong = total_uncertain = total_definite = 0
    zero_wrong = 0
    zero_total = 0
    rejection_good = 0
    rejection_total = 0
    family_pass = True
    selection = MethodSelection(
        upstream.noise, upstream.bandwidth, upstream.spectral_center, upstream.carrier,
        method, upstream.analysis_window, upstream.power_snr,
    )
    for scene_index, scene_id in enumerate(CLASS_SCENES):
        scene_spec = _scene(catalog, scene_id)
        truth_center, truth_lo, truth_hi = _truth_bins(catalog, scene_spec)
        expected = "Analog" if scene_id in {"am-carrier", "nfm"} else "Sayısal" if scene_id in {"ook", "two-fsk", "bpsk", "qpsk"} else "Belirsiz"
        correct = wrong = uncertain = 0
        for snr_index, snr_db in enumerate(catalog["power_benchmark"]["snr_db_order"]):
            condition_correct = condition_wrong = condition_uncertain = 0
            for trial in range(trials):
                _, result = _run_sequence(
                    selection, scene_id, trial=trial, condition=200 + scene_index * 4 + snr_index,
                    frame_count=4, score_frame=3, power_dbfs=-18.0, snr_db=snr_db, catalog=catalog,
                )
                estimate = _select_scored_estimate(
                    result.events, catalog, truth_center, truth_lo, truth_hi,
                )
                decision = "Belirsiz" if estimate is None else estimate.signal_domain.value
                condition_correct += int(decision == expected and expected != "Belirsiz")
                condition_wrong += int(decision not in {expected, "Belirsiz"} if expected != "Belirsiz" else decision != "Belirsiz")
                condition_uncertain += int(decision == "Belirsiz")
                if snr_db >= 6.0:
                    if expected == "Belirsiz":
                        rejection_total += 1
                        rejection_good += int(decision == "Belirsiz")
                        uncertain += int(decision == "Belirsiz")
                    else:
                        total_definite += 1
                        total_correct += int(decision == expected)
                        total_wrong += int(decision not in {expected, "Belirsiz"})
                        total_uncertain += int(decision == "Belirsiz")
                        correct += int(decision == expected)
                        wrong += int(decision not in {expected, "Belirsiz"})
                        uncertain += int(decision == "Belirsiz")
                elif snr_db == 0.0 and expected != "Belirsiz":
                    zero_total += 1
                    zero_wrong += int(decision not in {expected, "Belirsiz"})
                elif snr_db == -6.0:
                    rejection_total += 1
                    rejection_good += int(decision == "Belirsiz")
            family_snr_diagnostics.append({
                "family": scene_id, "snr_db": snr_db, "total": trials,
                "correct_definite": condition_correct, "wrong_definite": condition_wrong,
                "uncertain": condition_uncertain, "binding": snr_db in {-6.0, 0.0, 6.0, 12.0},
            })
        if expected != "Belirsiz":
            high_total = 2 * trials
            family_pass = family_pass and correct / high_total >= gates["classification_correct_definite_family_minimum"] and wrong / high_total <= gates["classification_wrong_definite_family_maximum"]
            family_records.append({
                "family": scene_id, "expected": expected, "snr_ge_6_total": high_total,
                "correct_definite": correct, "wrong_definite": wrong, "uncertain": uncertain,
                "correct_definite_rate": _round(correct / high_total), "wrong_definite_rate": _round(wrong / high_total),
            })
        else:
            family_pass = family_pass and uncertain / (2 * trials) >= gates["uncertain_rejection_rate_minimum"]
            family_records.append({
                "family": scene_id, "expected": expected, "snr_ge_6_total": 2 * trials,
                "correct_definite": 0, "wrong_definite": 2 * trials - uncertain,
                "uncertain": uncertain, "uncertain_rate": _round(uncertain / (2 * trials)),
            })
    correct_rate = total_correct / total_definite if total_definite else 0.0
    wrong_rate = total_wrong / total_definite if total_definite else 0.0
    zero_wrong_rate = zero_wrong / zero_total if zero_total else 0.0
    rejection_rate = rejection_good / rejection_total if rejection_total else 0.0
    noise_sequences = 128 if trials == 128 else 1
    noise_definite = 0
    noise_definite_sequences = 0
    noise_definite_frames = 0
    for trial in range(noise_sequences):
        from reference.pipeline import RuntimePipeline

        runtime = RuntimePipeline(_phase03_profile())
        extractor = ParameterExtractor(selection)
        sequence_definite_event_ids: set[int] = set()
        for frame_index in range(32):
            frame = generate_parameter_scene(
                "noise-only", trial_index=trial, condition_index=299, frame_index=frame_index,
                clean_power_dbfs=-18.0, snr_db=12.0, catalog=catalog,
            )
            common = catalog["common"]
            runtime_result = runtime.process(
                frame.samples,
                sample_rate_hz=float(common["sample_rate_hz"]),
                center_frequency_hz=float(common["center_frequency_hz"]), frame_index=frame_index,
            )
            result = extractor.process(
                frame.samples, runtime_result.spectrum, runtime_result.detection, frame_index=frame_index,
            )
            noise_definite_frames += _record_definite_event_ids(result, sequence_definite_event_ids)
        noise_definite += len(sequence_definite_event_ids)
        noise_definite_sequences += int(bool(sequence_definite_event_ids))
    passed = (
        family_pass
        and correct_rate >= gates["classification_correct_definite_total_minimum"]
        and wrong_rate <= gates["classification_wrong_definite_total_maximum"]
        and zero_wrong_rate <= gates["zero_snr_wrong_definite_maximum"]
        and rejection_rate >= gates["uncertain_rejection_rate_minimum"]
        and noise_definite <= gates["noise_definite_count_maximum"]
    )
    return {
        "method": method, "status": "passed" if passed else "failed", "eligible": bool(passed),
        "correct_definite_rate": _round(correct_rate), "wrong_definite_rate": _round(wrong_rate),
        "uncertain_rate": _round(total_uncertain / total_definite if total_definite else 0.0),
        "zero_snr_wrong_definite_rate": _round(zero_wrong_rate), "uncertain_rejection_rate": _round(rejection_rate),
        "noise_definite_count": noise_definite,
        "noise_sequence_count": noise_sequences,
        "noise_frame_count": noise_sequences * 32,
        "noise_definite_sequence_count": noise_definite_sequences,
        "noise_definite_sequence_rate_diagnostic": _round(noise_definite_sequences / noise_sequences),
        "noise_definite_frame_count_diagnostic": noise_definite_frames,
        "noise_definite_frame_rate_diagnostic": _round(noise_definite_frames / (noise_sequences * 32)),
        "normalized_loss": _round((1.0 - correct_rate) + wrong_rate),
        "families": family_records, "family_snr_diagnostics": family_snr_diagnostics,
        "resource_cost": list(_cost(catalog, (method,))),
        "_paired_losses": [1.0 - correct_rate, wrong_rate, 1.0 - rejection_rate, zero_wrong_rate],
    }, passed


def evaluate_parameter_methods(*, full: bool = True) -> tuple[dict[str, Any], dict[str, str] | None]:
    catalog = load_parameter_catalog()
    trials = 128 if full else 1
    manifest = phase04_implementation_manifest()
    band_records, band_selected, band_decision = _band_pairs(catalog, trials, full)
    frequency_records: list[dict[str, Any]] = []
    frequency_selected: dict[str, Any] | None = None
    frequency_decision: dict[str, Any] = {"status": "skipped", "reason": "upstream-band-failed", "comparisons": []}
    power_payload: dict[str, Any] = {"status": "skipped", "reason": "upstream-frequency-failed"}
    class_records: list[dict[str, Any]] = []
    class_selected: dict[str, Any] | None = None
    class_decision: dict[str, Any] = {"status": "skipped", "reason": "upstream-power-failed", "comparisons": []}
    power_passed = False
    if band_selected is not None:
        frequency_records, frequency_selected, frequency_decision = _frequency_pairs(catalog, band_selected, trials)
    if frequency_selected is not None and band_selected is not None:
        base = _selection_from(
            band_selected, frequency_selected["spectral_center_method"],
            frequency_selected["carrier_method"], "domain.explainable-rules",
        )
        power_payload, power_passed = _power_metrics(catalog, base, trials)
        if power_passed:
            internal: list[dict[str, Any]] = []
            for method in catalog["method_order"]["signal_domain"]:
                record, _ = _classification_metrics(catalog, base, method, trials)
                internal.append(record)
            class_selected, class_decision = _choose(internal, catalog, ("method",))
            class_records = [{key: value for key, value in item.items() if key != "_paired_losses"} for item in internal]
    selected: dict[str, str] | None = None
    if band_selected is not None and frequency_selected is not None and power_passed and class_selected is not None:
        selected = {
            "analysis_window": band_selected["analysis_window_method"],
            "noise": band_selected["noise_method"],
            "bandwidth": band_selected["bandwidth_method"],
            "spectral_center": frequency_selected["spectral_center_method"],
            "carrier": frequency_selected["carrier_method"],
            "power_snr": POWER_SNR_METHOD,
            "signal_domain": class_selected["method"],
        }
    snr_condition_count = len(catalog["power_benchmark"]["snr_db_order"])
    band_candidate_count = len(ANALYSIS_METHODS) * len(catalog["method_order"]["noise"]) * len(BANDWIDTH_METHODS)
    noise_sequence_count = 128 if full else 1
    r1d_unique_frames = (
        len(CONTINUOUS_BAND_SCENES) * snr_condition_count * trials * 4
        + snr_condition_count * trials * 6
        + snr_condition_count * trials * 4
        + noise_sequence_count * 32
    )
    payload = {
        "schema_version": 2,
        "phase": "PHASE-04",
        "comparison_id": COMPARISON_ID,
        "overall": "passed" if selected is not None else "failed",
        "catalog_sha256": manifest["catalog_sha256"],
        "implementation_manifest_sha256": manifest["implementation_manifest_sha256"],
        "phase03_profile_sha256": manifest["phase03_profile_sha256"],
        "selection_contract": catalog["selection_contract"],
        "gate_applicability": _gate_applicability(catalog),
        "sample_counts": {
            "trials_per_condition": trials, "continuous_frames_per_sequence": 4,
            "continuous_binding_frame": 3, "burst_frames_per_sequence": 6, "burst_binding_frame": 4,
            "noise_sequences": noise_sequence_count, "noise_frames_per_sequence": 32,
            "r1d_band_candidate_count": band_candidate_count,
            "r1d_phase03_unique_frames": r1d_unique_frames,
            "r1d_tuple_extractor_evaluations_maximum": r1d_unique_frames * band_candidate_count,
            "streamed_not_bulk_cached": True,
        },
        "noise_bandwidth_pairs": band_records,
        "noise_bandwidth_decision": band_decision,
        "center_carrier_pairs": frequency_records,
        "center_carrier_decision": frequency_decision,
        "power_snr_chain": power_payload,
        "signal_domain_methods": class_records,
        "signal_domain_decision": class_decision,
        "selected_methods": selected,
        "combined_pipeline": {
            "status": "passed" if selected is not None else "failed",
            "no_upstream_backtracking": True, "same_upstream_for_all_classifiers": True,
            "dynamic_timing_used_for_selection": False,
        },
    }
    return payload, selected
