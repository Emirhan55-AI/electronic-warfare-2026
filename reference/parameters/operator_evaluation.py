"""Single-run field-scoped binding and OOS evaluation for PHASE-04-E1."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

import numpy as np

from reference.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from reference.pipeline import RuntimePipeline, load_profile
from reference.spectrum import SpectrumProcessor

from .operator_assisted import (
    AnalysisSpan,
    FieldMeasurement,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
    OperatorAssistedParameterResult,
    OperatorMeasurementProcessor,
    suggest_analysis_span,
)
from .operator_reference import build_golden_reference, load_json, ACCEPTANCE_PATH, SCENES_PATH


def _q95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(item) for item in values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _status(ok: bool) -> str:
    return "passed" if ok else "failed"


def _field_record(valid: int, total: int, errors: list[float], threshold: float, minimum_rate: float) -> dict[str, Any]:
    rate = valid / total if total else 0.0
    q95 = _q95(errors)
    passed = rate >= minimum_rate and q95 is not None and q95 <= threshold
    return {"status": _status(passed), "valid_count": valid, "trial_count": total, "valid_rate": rate, "q95_error": q95, "q95_maximum": threshold, "valid_rate_minimum": minimum_rate}


FIELD_RESULT_ATTRS = {
    "emission_center_frequency": "emission_center_frequency",
    "carrier_line_frequency": "carrier_line_frequency",
    "occupied_bandwidth": "occupied_bandwidth",
    "uncalibrated_power_dbfs": "channel_power_dbfs",
    "signal_domain": "signal_domain",
}


def _counter_template() -> dict[str, Any]:
    return {
        "total": 0,
        "intent_valid": 0,
        "operator_span_received": 0,
        "common_quality_passed": 0,
        "field_math_reached": 0,
        "field_valid": 0,
        "field_uncertain": 0,
        "field_insufficient_quality": 0,
        "field_not_observed": 0,
        "field_failed_gate": 0,
        "reason_counts": {},
    }


def _new_stage_counters() -> dict[str, dict[str, Any]]:
    return {name: _counter_template() for name in FIELD_RESULT_ATTRS}


def _record_stage_counters(counters: dict[str, dict[str, Any]], result: OperatorAssistedParameterResult) -> None:
    common_passed = result.quality.state == "valid"
    intent_valid = result.quality.reasons not in {("stale_generation",), ("event_ownership_lost",)}
    for name, attribute in FIELD_RESULT_ATTRS.items():
        record = counters[name]
        field: FieldMeasurement = getattr(result, attribute)
        record["total"] += 1
        record["intent_valid"] += int(intent_valid)
        record["operator_span_received"] += 1
        record["common_quality_passed"] += int(common_passed)
        record["field_math_reached"] += int(common_passed)
        state_key = f"field_{field.state}"
        if state_key in record:
            record[state_key] += 1
        if field.state != "valid":
            record["field_failed_gate"] += 1
            reason = field.reason or "unspecified"
            record["reason_counts"][reason] = record["reason_counts"].get(reason, 0) + 1


def _forced_intent(span: AnalysisSpan, event_id: int, event_revision: int, start_frame: int = 0) -> MeasurementIntent:
    candidate = MeasurementCandidate(event_id, event_revision, span.lower_shifted_bin, span.upper_shifted_bin)
    context = MeasurementContext(1, 1, 1, event_id, event_revision, (True, True, True, True), (candidate,))
    return MeasurementIntent(1, 1, 1, event_id, event_revision, start_frame, span, context)


def _event_context(event: Any, events: tuple[Any, ...], observations: tuple[bool, bool, bool, bool]) -> MeasurementContext:
    candidates = tuple(
        MeasurementCandidate(
            int(item.event_id),
            int(item.seen_count),
            int(item.region.start_bin),
            int(item.region.end_bin),
            item.state == "confirmed",
        )
        for item in events
    )
    return MeasurementContext(1, 1, 1, int(event.event_id), int(event.seen_count), observations, candidates)


def evaluate(role: str) -> dict[str, Any]:
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    scenes = load_json(SCENES_PATH)
    gates = load_json(ACCEPTANCE_PATH)[role]
    golden = build_golden_reference()
    truth_by_family = {item["family_id"]: item for item in golden["families"]}
    parameter_catalog = load_parameter_catalog()
    trial_count = int(gates["trials_per_family"])
    seed_base = int(scenes["common"]["binding_seed" if role == "binding" else "oos_seed"])
    processor = SpectrumProcessor()
    measurement = OperatorMeasurementProcessor()
    family_records: list[dict[str, Any]] = []
    aggregate: dict[str, dict[str, Any]] = {
        name: {"valid": 0, "total": 0, "errors": []}
        for name in ("emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain")
    }
    false_carrier = 0
    carrier_nonapplicable = 0
    automatic_span_success = 0
    automatic_span_total = 0
    lower_edge_errors: list[float] = []
    upper_edge_errors: list[float] = []
    robustness_errors: list[float] = []
    temporal_edge_ranges: list[float] = []
    channel_power_errors: list[float] = []
    peak_power_errors: list[float] = []
    clipping_count = 0
    state_counts: dict[str, int] = {}
    stage_counters = _new_stage_counters()
    ambiguous_total = 0
    ambiguous_rejected = 0
    for family_index, family in enumerate(scenes["families"]):
        family_id = str(family["id"])
        truth = truth_by_family[family_id]
        counts = {name: 0 for name in aggregate}
        errors = {name: [] for name in aggregate}
        family_lower_edges: list[float] = []
        family_upper_edges: list[float] = []
        family_robustness: list[float] = []
        family_temporal_ranges: list[float] = []
        family_channel_power_errors: list[float] = []
        family_peak_power_errors: list[float] = []
        family_domain_correct = 0
        family_domain_wrong = 0
        family_auto_success = 0
        family_stage_counters = _new_stage_counters()
        applicable_carrier = bool(family["carrier_line_applicable"])
        active_frames = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
        for trial in range(trial_count):
            samples = []
            spectra = []
            detection_pipeline = RuntimePipeline(load_profile()).detection
            last_detection = None
            for frame_index in active_frames:
                frame = generate_parameter_scene(
                    str(family["scene_id"]), trial_index=trial, condition_index=0, frame_index=frame_index,
                    clean_power_dbfs=-18.0, snr_db=12.0, catalog=parameter_catalog,
                    scene_seed_override=seed_base + family_index * 10_000,
                )
                samples.append(frame.samples)
                spectrum = processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
                spectra.append(spectrum)
                last_detection = detection_pipeline.process(spectrum, frame_index=len(spectra) - 1)
            automatic_span_total += 1
            truth_lower = float(truth["obw99"]["lower_shifted_native_bin"])
            truth_upper = float(truth["obw99"]["upper_shifted_native_bin"])
            suggestions = [] if last_detection is None else [
                suggest_analysis_span(event, last_detection.active_events)
                for event in last_detection.active_events
                if event.state == "confirmed" and event.observed_this_frame
            ]
            if any(item is not None and item.lower_shifted_bin <= truth_lower and item.upper_shifted_bin >= truth_upper for item in suggestions):
                automatic_span_success += 1
                family_auto_success += 1
            span = AnalysisSpan(int(truth["operator_span"][0]), int(truth["operator_span"][1]), "operator_adjusted")
            intent = _forced_intent(span, family_index + 1, trial)
            result = measurement.measure(intent, tuple(samples), tuple(spectra))
            _record_stage_counters(stage_counters, result)
            _record_stage_counters(family_stage_counters, result)
            state_counts[result.quality.state] = state_counts.get(result.quality.state, 0) + 1
            if result.occupied_bandwidth.reason == "span_edge_clipping":
                clipping_count += 1
            aggregate["emission_center_frequency"]["total"] += 1
            if result.emission_center_frequency.state == "valid":
                counts["emission_center_frequency"] += 1
                aggregate["emission_center_frequency"]["valid"] += 1
                error = abs(float(result.emission_center_frequency.value) - float(truth["emission_center_frequency_hz"])) / (8_000_000.0 / 4096.0)
                errors["emission_center_frequency"].append(error)
                aggregate["emission_center_frequency"]["errors"].append(error)
            if applicable_carrier:
                aggregate["carrier_line_frequency"]["total"] += 1
                if result.carrier_line_frequency.state == "valid":
                    counts["carrier_line_frequency"] += 1
                    aggregate["carrier_line_frequency"]["valid"] += 1
                    error = abs(float(result.carrier_line_frequency.value) - float(truth["carrier_line_frequency_hz"])) / (8_000_000.0 / 4096.0)
                    errors["carrier_line_frequency"].append(error)
                    aggregate["carrier_line_frequency"]["errors"].append(error)
            else:
                carrier_nonapplicable += 1
                if result.carrier_line_frequency.state == "valid":
                    false_carrier += 1
            aggregate["occupied_bandwidth"]["total"] += 1
            if result.occupied_bandwidth.state == "valid":
                counts["occupied_bandwidth"] += 1
                aggregate["occupied_bandwidth"]["valid"] += 1
                truth_width = float(truth["obw99"]["occupied_bandwidth_hz"])
                error = abs(float(result.occupied_bandwidth.value) - truth_width) / truth_width
                errors["occupied_bandwidth"].append(error)
                aggregate["occupied_bandwidth"]["errors"].append(error)
                lower_error = abs(float(result.lower_band_edge.value) - float(truth["obw99"]["lower_frequency_hz"])) / (8_000_000.0 / 4096.0)
                upper_error = abs(float(result.upper_band_edge.value) - float(truth["obw99"]["upper_frequency_hz"])) / (8_000_000.0 / 4096.0)
                family_lower_edges.append(lower_error)
                family_upper_edges.append(upper_error)
                lower_edge_errors.append(lower_error)
                upper_edge_errors.append(upper_error)
                perturb_results = []
                for perturb in (-4, 4):
                    perturbed_lower = int(truth["operator_span"][0]) + perturb
                    perturbed_upper = int(truth["operator_span"][1]) + perturb
                    perturbed = measurement.measure(
                        _forced_intent(AnalysisSpan(perturbed_lower, perturbed_upper, "operator_adjusted"), family_index + 1, trial),
                        tuple(samples), tuple(spectra),
                    )
                    if perturbed.occupied_bandwidth.state == "valid":
                        perturb_results.append(max(
                            abs(float(perturbed.lower_band_edge.value) - float(result.lower_band_edge.value)),
                            abs(float(perturbed.upper_band_edge.value) - float(result.upper_band_edge.value)),
                        ) / (8_000_000.0 / 4096.0))
                if len(perturb_results) == 2:
                    robust_error = max(perturb_results)
                    family_robustness.append(robust_error)
                    robustness_errors.append(robust_error)
                if result.quality.temporal_edge_range_bins is not None:
                    family_temporal_ranges.append(result.quality.temporal_edge_range_bins)
                    temporal_edge_ranges.append(result.quality.temporal_edge_range_bins)
            aggregate["uncalibrated_power_dbfs"]["total"] += 1
            if result.channel_power_dbfs.state == "valid" and result.peak_power_dbfs_per_bin.state == "valid":
                counts["uncalibrated_power_dbfs"] += 1
                aggregate["uncalibrated_power_dbfs"]["valid"] += 1
                channel_error = abs(float(result.channel_power_dbfs.value) - float(truth["clean_channel_power_dbfs"]))
                peak_error = abs(float(result.peak_power_dbfs_per_bin.value) - float(truth["clean_peak_power_dbfs_per_bin"]))
                joint_error = max(channel_error, peak_error)
                errors["uncalibrated_power_dbfs"].append(joint_error)
                aggregate["uncalibrated_power_dbfs"]["errors"].append(joint_error)
                family_channel_power_errors.append(channel_error)
                family_peak_power_errors.append(peak_error)
                channel_power_errors.append(channel_error)
                peak_power_errors.append(peak_error)
            if truth["expected_domain"] == "Belirsiz":
                ambiguous_total += 1
                if result.signal_domain.state != "valid":
                    ambiguous_rejected += 1
            else:
                aggregate["signal_domain"]["total"] += 1
                if result.signal_domain.state == "valid":
                    counts["signal_domain"] += 1
                    aggregate["signal_domain"]["valid"] += 1
                    error = 0.0 if result.signal_domain.value == truth["expected_domain"] else 1.0
                    if error == 0.0:
                        family_domain_correct += 1
                    else:
                        family_domain_wrong += 1
                    errors["signal_domain"].append(error)
                    aggregate["signal_domain"]["errors"].append(error)
        family_records.append({
            "family_id": family_id,
            "trial_count": trial_count,
            "valid_counts": counts,
            "q95_errors": {name: _q95(values) for name, values in errors.items()},
            "lower_edge_q95_bins": _q95(family_lower_edges),
            "upper_edge_q95_bins": _q95(family_upper_edges),
            "span_robustness_q95_bins": _q95(family_robustness),
            "temporal_edge_q95_bins": _q95(family_temporal_ranges),
            "channel_power_q95_db": _q95(family_channel_power_errors),
            "peak_power_q95_db": _q95(family_peak_power_errors),
            "domain_correct_count": family_domain_correct,
            "domain_wrong_count": family_domain_wrong,
            "automatic_span_success_count": family_auto_success,
            "stage_counters": family_stage_counters,
        })
    close_success = 0
    close_cross_match = 0
    close_trials = trial_count
    for trial in range(close_trials):
        pipeline = RuntimePipeline(load_profile()).detection
        detection = None
        for frame_index in range(4):
            frame = generate_parameter_scene(
                "close-am-qpsk", trial_index=trial, frame_index=frame_index,
                catalog=parameter_catalog, scene_seed_override=seed_base + 800_000,
            )
            spectrum = processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            detection = pipeline.process(spectrum, frame_index=frame_index)
        assert detection is not None
        suggestions = [
            span for event in detection.active_events
            if event.state == "confirmed" and event.observed_this_frame
            for span in [suggest_analysis_span(event, detection.active_events)] if span is not None
        ]
        centers = (1848.0, 1968.0)
        matched = []
        for center in centers:
            options = [span for span in suggestions if span.lower_shifted_bin <= center <= span.upper_shifted_bin]
            matched.append(options[0] if options else None)
        if all(item is not None for item in matched) and matched[0] != matched[1]:
            close_success += 1
        if any(span.lower_shifted_bin <= centers[0] and span.upper_shifted_bin >= centers[1] for span in suggestions):
            close_cross_match += 1
    # Real temporal noise exposure. A numeric field is counted only after a confirmed event
    # supplies an automatically bounded span and four observed frames are available.
    noise_sequences = int(gates.get("noise_sequences", 0))
    noise_frames_per_sequence = int(gates.get("noise_frames_per_sequence", 0))
    noise_false_valid = 0
    noise_domain_definite = 0
    for sequence in range(noise_sequences):
        detection_pipeline = RuntimePipeline(load_profile()).detection
        recent_samples: list[np.ndarray] = []
        recent_spectra: list[Any] = []
        observation_history: dict[int, list[bool]] = {}
        for frame_index in range(noise_frames_per_sequence):
            frame = generate_parameter_scene(
                "noise-only", trial_index=sequence, condition_index=0, frame_index=frame_index,
                catalog=parameter_catalog, scene_seed_override=seed_base + 900_000,
            )
            spectrum = processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            detection = detection_pipeline.process(spectrum, frame_index=frame_index)
            recent_samples.append(frame.samples)
            recent_spectra.append(spectrum)
            recent_samples = recent_samples[-4:]
            recent_spectra = recent_spectra[-4:]
            active_ids = {int(item.event_id) for item in detection.active_events}
            for event_id in set(observation_history) | active_ids:
                event = next((item for item in detection.active_events if int(item.event_id) == event_id), None)
                observation_history.setdefault(event_id, []).append(bool(event is not None and event.observed_this_frame))
                observation_history[event_id] = observation_history[event_id][-4:]
            if len(recent_samples) < 4:
                continue
            for event in detection.active_events:
                span = suggest_analysis_span(event, detection.active_events)
                if span is None:
                    continue
                observations = tuple(observation_history.get(int(event.event_id), ()))
                if len(observations) != 4 or not all(observations):
                    continue
                context = _event_context(event, detection.active_events, observations)  # type: ignore[arg-type]
                intent = MeasurementIntent(1, 1, 1, event.event_id, event.seen_count, frame_index - 3, span, context)
                result = measurement.measure(intent, tuple(recent_samples), tuple(recent_spectra))
                if any(field.state == "valid" for field in (result.carrier_line_frequency, result.occupied_bandwidth, result.channel_power_dbfs)):
                    noise_false_valid += 1
                if result.signal_domain.state == "valid":
                    noise_domain_definite += 1
    snr_diagnostics: list[dict[str, Any]] = []
    for diagnostic_snr in (6.0, 0.0, -6.0):
        channel_errors: list[float] = []
        peak_errors: list[float] = []
        power_valid = 0
        power_trials = 0
        domain_correct = 0
        domain_wrong = 0
        domain_definite = 0
        expected_domain_trials = 0
        diagnostic_families: list[dict[str, Any]] = []
        for family_index, family in enumerate(scenes["families"]):
            truth = truth_by_family[str(family["id"])]
            family_power_valid = 0
            family_channel_errors: list[float] = []
            family_peak_errors: list[float] = []
            family_domain_total = 0
            family_domain_correct = 0
            family_domain_wrong = 0
            family_domain_definite = 0
            active_frames = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
            for trial in range(trial_count):
                frame_samples = []
                frame_spectra = []
                for frame_index in active_frames:
                    frame = generate_parameter_scene(
                        str(family["scene_id"]), trial_index=trial, frame_index=frame_index,
                        clean_power_dbfs=-18.0, snr_db=diagnostic_snr, catalog=parameter_catalog,
                        scene_seed_override=seed_base + family_index * 10_000,
                    )
                    frame_samples.append(frame.samples)
                    frame_spectra.append(processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0))
                span = AnalysisSpan(int(truth["operator_span"][0]), int(truth["operator_span"][1]), "operator_adjusted")
                result = measurement.measure(_forced_intent(span, family_index + 1, trial), tuple(frame_samples), tuple(frame_spectra))
                power_trials += 1
                if result.channel_power_dbfs.state == "valid" and result.peak_power_dbfs_per_bin.state == "valid":
                    power_valid += 1
                    family_power_valid += 1
                    channel_error = abs(float(result.channel_power_dbfs.value) - float(truth["clean_channel_power_dbfs"]))
                    peak_error = abs(float(result.peak_power_dbfs_per_bin.value) - float(truth["clean_peak_power_dbfs_per_bin"]))
                    channel_errors.append(channel_error)
                    peak_errors.append(peak_error)
                    family_channel_errors.append(channel_error)
                    family_peak_errors.append(peak_error)
                if truth["expected_domain"] != "Belirsiz":
                    expected_domain_trials += 1
                    family_domain_total += 1
                    if result.signal_domain.state == "valid":
                        domain_definite += 1
                        family_domain_definite += 1
                        if result.signal_domain.value == truth["expected_domain"]:
                            domain_correct += 1
                            family_domain_correct += 1
                        else:
                            domain_wrong += 1
                            family_domain_wrong += 1
            diagnostic_families.append({
                "family_id": str(family["id"]),
                "power_trial_count": trial_count,
                "power_valid_count": family_power_valid,
                "channel_power_q95_db": _q95(family_channel_errors),
                "peak_power_q95_db": _q95(family_peak_errors),
                "domain_trial_count": family_domain_total,
                "domain_definite_count": family_domain_definite,
                "domain_correct_count": family_domain_correct,
                "domain_wrong_count": family_domain_wrong,
            })
        snr_diagnostics.append({
            "snr_db": diagnostic_snr,
            "power_trial_count": power_trials,
            "power_valid_count": power_valid,
            "channel_power_q95_db": _q95(channel_errors),
            "peak_power_q95_db": _q95(peak_errors),
            "channel_power_median_db": float(np.median(channel_errors)) if channel_errors else None,
            "peak_power_median_db": float(np.median(peak_errors)) if peak_errors else None,
            "domain_trial_count": expected_domain_trials,
            "domain_definite_count": domain_definite,
            "domain_correct_count": domain_correct,
            "domain_wrong_count": domain_wrong,
            "domain_wrong_rate": domain_wrong / expected_domain_trials,
            "domain_abstention_rate": 1.0 - domain_definite / expected_domain_trials,
            "family_results": diagnostic_families,
        })
    decisions: dict[str, dict[str, Any]] = {}
    family_definitions = {str(item["id"]): item for item in scenes["families"]}
    six = next(item for item in snr_diagnostics if item["snr_db"] == 6.0)
    zero = next(item for item in snr_diagnostics if item["snr_db"] == 0.0)
    low = next(item for item in snr_diagnostics if item["snr_db"] == -6.0)
    if role == "binding":
        center_gate = gates["emission_center_frequency"]
        center = _field_record(aggregate["emission_center_frequency"]["valid"], aggregate["emission_center_frequency"]["total"], aggregate["emission_center_frequency"]["errors"], center_gate["q95_error_bins_maximum"], center_gate["global_valid_minimum"])
        center["status"] = _status(center["status"] == "passed" and all(item["valid_counts"]["emission_center_frequency"] / item["trial_count"] >= center_gate["family_valid_minimum"] for item in family_records))
        decisions["emission_center_frequency"] = center

        carrier_gate = gates["carrier_line_frequency"]
        carrier = _field_record(aggregate["carrier_line_frequency"]["valid"], aggregate["carrier_line_frequency"]["total"], aggregate["carrier_line_frequency"]["errors"], carrier_gate["q95_error_bins_maximum"], carrier_gate["global_valid_minimum"])
        carrier.update({"false_carrier_count": false_carrier, "false_carrier_rate": false_carrier / max(carrier_nonapplicable, 1), "abstention_rate": (carrier_nonapplicable - false_carrier) / max(carrier_nonapplicable, 1)})
        carrier["status"] = _status(carrier["status"] == "passed" and carrier["false_carrier_rate"] <= carrier_gate["false_carrier_rate_maximum"] and carrier["abstention_rate"] >= carrier_gate["abstention_rate_minimum"] and all(item["valid_counts"]["carrier_line_frequency"] / item["trial_count"] >= carrier_gate["family_valid_minimum"] for item in family_records if family_definitions[item["family_id"]]["carrier_line_applicable"]))
        decisions["carrier_line_frequency"] = carrier

        obw_gate = gates["occupied_bandwidth"]
        obw = _field_record(aggregate["occupied_bandwidth"]["valid"], aggregate["occupied_bandwidth"]["total"], aggregate["occupied_bandwidth"]["errors"], obw_gate["relative_q95_maximum"], obw_gate["global_valid_minimum"])
        obw.update({"lower_edge_q95_bins": _q95(lower_edge_errors), "upper_edge_q95_bins": _q95(upper_edge_errors), "span_robustness_q95_bins": _q95(robustness_errors), "temporal_edge_q95_bins": _q95(temporal_edge_ranges), "clipping_count": clipping_count})
        obw["status"] = _status(obw["status"] == "passed" and obw["lower_edge_q95_bins"] is not None and obw["lower_edge_q95_bins"] <= obw_gate["edge_q95_bins_maximum"] and obw["upper_edge_q95_bins"] is not None and obw["upper_edge_q95_bins"] <= obw_gate["edge_q95_bins_maximum"] and obw["span_robustness_q95_bins"] is not None and obw["span_robustness_q95_bins"] <= gates["span_robustness"]["edge_difference_q95_bins_maximum"] and obw["temporal_edge_q95_bins"] is not None and obw["temporal_edge_q95_bins"] <= obw_gate["temporal_q95_bins_maximum"] and clipping_count <= obw_gate["clipping_count_maximum"] and all(item["valid_counts"]["occupied_bandwidth"] / item["trial_count"] >= obw_gate["family_valid_minimum"] for item in family_records))
        decisions["occupied_bandwidth"] = obw

        power_gate = gates["uncalibrated_power_dbfs"]
        power = _field_record(aggregate["uncalibrated_power_dbfs"]["valid"], aggregate["uncalibrated_power_dbfs"]["total"], aggregate["uncalibrated_power_dbfs"]["errors"], power_gate["q95_error_db_maximum"], power_gate["global_valid_minimum"])
        power.update({"channel_power_q95_db": _q95(channel_power_errors), "peak_power_q95_db": _q95(peak_power_errors), "six_db": six, "zero_db": zero})
        six_family_ok = all(item["power_valid_count"] / item["power_trial_count"] >= power_gate["family_valid_minimum"] for item in six["family_results"])
        power["status"] = _status(power["status"] == "passed" and all(item["valid_counts"]["uncalibrated_power_dbfs"] / item["trial_count"] >= power_gate["family_valid_minimum"] for item in family_records) and power["channel_power_q95_db"] is not None and power["channel_power_q95_db"] <= power_gate["q95_error_db_maximum"] and power["peak_power_q95_db"] is not None and power["peak_power_q95_db"] <= power_gate["q95_error_db_maximum"] and six["power_valid_count"] / six["power_trial_count"] >= power_gate["global_valid_minimum"] and six_family_ok and six["channel_power_q95_db"] is not None and six["channel_power_q95_db"] <= power_gate["q95_error_db_maximum"] and six["peak_power_q95_db"] is not None and six["peak_power_q95_db"] <= power_gate["q95_error_db_maximum"] and zero["channel_power_median_db"] is not None and zero["channel_power_median_db"] <= power_gate["zero_snr_median_error_db_maximum"] and zero["peak_power_median_db"] is not None and zero["peak_power_median_db"] <= power_gate["zero_snr_median_error_db_maximum"])
        decisions["uncalibrated_power_dbfs"] = power

        domain_gate = gates["signal_domain"]
        domain_errors = aggregate["signal_domain"]["errors"]
        total = aggregate["signal_domain"]["total"]
        correct_rate = sum(value == 0.0 for value in domain_errors) / total
        wrong_rate = sum(value == 1.0 for value in domain_errors) / total
        ambiguous_rate = ambiguous_rejected / max(ambiguous_total, 1)
        family_main_ok = all(item["domain_correct_count"] / item["trial_count"] >= domain_gate["family_correct_definite_minimum"] and item["domain_wrong_count"] / item["trial_count"] <= domain_gate["family_wrong_definite_maximum"] for item in family_records if family_definitions[item["family_id"]]["domain"] != "Belirsiz")
        six_family_ok = all(item["domain_correct_count"] / item["domain_trial_count"] >= domain_gate["family_correct_definite_minimum"] and item["domain_wrong_count"] / item["domain_trial_count"] <= domain_gate["family_wrong_definite_maximum"] for item in six["family_results"] if item["domain_trial_count"])
        domain = {"trial_count": total, "valid_count": aggregate["signal_domain"]["valid"], "correct_definite_rate": correct_rate, "wrong_definite_rate": wrong_rate, "ambiguous_rejection_rate": ambiguous_rate, "six_db": six, "zero_db": zero, "minus_six_db": low}
        domain["status"] = _status(correct_rate >= domain_gate["global_correct_definite_minimum"] and wrong_rate <= domain_gate["global_wrong_definite_maximum"] and family_main_ok and ambiguous_rate >= domain_gate["ambiguous_rejection_minimum"] and six["domain_correct_count"] / six["domain_trial_count"] >= domain_gate["global_correct_definite_minimum"] and six["domain_wrong_rate"] <= domain_gate["global_wrong_definite_maximum"] and six_family_ok and zero["domain_wrong_rate"] <= domain_gate["zero_snr_wrong_definite_maximum"] and low["domain_abstention_rate"] >= domain_gate["low_snr_abstention_minimum"])
        decisions["signal_domain"] = domain

        auto_gate = gates["automatic_span"]
        auto = {"success_count": automatic_span_success, "trial_count": automatic_span_total, "success_rate": automatic_span_success / automatic_span_total, "close_success_count": close_success, "close_trial_count": close_trials, "close_separation_rate": close_success / close_trials, "cross_match_count": close_cross_match}
        auto["status"] = _status(auto["success_rate"] >= auto_gate["isolated_success_minimum"] and auto["close_separation_rate"] >= auto_gate["close_separation_minimum"] and close_cross_match / close_trials <= auto_gate["cross_match_maximum"])
        decisions["automatic_span"] = auto
    else:
        center_gate = gates["emission_center_frequency"]
        center_q95 = _q95(aggregate["emission_center_frequency"]["errors"])
        decisions["emission_center_frequency"] = {"status": _status(all(item["valid_counts"]["emission_center_frequency"] >= center_gate["family_valid_count_minimum"] for item in family_records) and center_q95 is not None and center_q95 <= center_gate["q95_error_bins_maximum"]), "valid_count": aggregate["emission_center_frequency"]["valid"], "trial_count": aggregate["emission_center_frequency"]["total"], "q95_error": center_q95}
        carrier_gate = gates["carrier_line_frequency"]
        carrier_q95 = _q95(aggregate["carrier_line_frequency"]["errors"])
        decisions["carrier_line_frequency"] = {"status": _status(all(item["valid_counts"]["carrier_line_frequency"] >= carrier_gate["family_valid_count_minimum"] for item in family_records if family_definitions[item["family_id"]]["carrier_line_applicable"]) and carrier_q95 is not None and carrier_q95 <= carrier_gate["q95_error_bins_maximum"] and false_carrier <= carrier_gate["false_carrier_count_maximum"]), "valid_count": aggregate["carrier_line_frequency"]["valid"], "trial_count": aggregate["carrier_line_frequency"]["total"], "q95_error": carrier_q95, "false_carrier_count": false_carrier}
        obw_gate = gates["occupied_bandwidth"]
        obw_q95 = _q95(aggregate["occupied_bandwidth"]["errors"])
        decisions["occupied_bandwidth"] = {"status": _status(all(item["valid_counts"]["occupied_bandwidth"] >= obw_gate["family_valid_count_minimum"] for item in family_records) and obw_q95 is not None and obw_q95 <= obw_gate["relative_q95_maximum"] and _q95(lower_edge_errors) is not None and _q95(lower_edge_errors) <= obw_gate["edge_q95_bins_maximum"] and _q95(upper_edge_errors) is not None and _q95(upper_edge_errors) <= obw_gate["edge_q95_bins_maximum"] and _q95(robustness_errors) is not None and _q95(robustness_errors) <= gates["span_robustness"]["edge_difference_q95_bins_maximum"] and clipping_count <= obw_gate["clipping_count_maximum"]), "valid_count": aggregate["occupied_bandwidth"]["valid"], "trial_count": aggregate["occupied_bandwidth"]["total"], "q95_error": obw_q95, "lower_edge_q95_bins": _q95(lower_edge_errors), "upper_edge_q95_bins": _q95(upper_edge_errors), "span_robustness_q95_bins": _q95(robustness_errors), "clipping_count": clipping_count}
        power_gate = gates["uncalibrated_power_dbfs"]
        decisions["uncalibrated_power_dbfs"] = {"status": _status(all(item["valid_counts"]["uncalibrated_power_dbfs"] >= power_gate["family_valid_count_minimum"] for item in family_records) and _q95(channel_power_errors) is not None and _q95(channel_power_errors) <= power_gate["q95_error_db_maximum"] and _q95(peak_power_errors) is not None and _q95(peak_power_errors) <= power_gate["q95_error_db_maximum"]), "valid_count": aggregate["uncalibrated_power_dbfs"]["valid"], "trial_count": aggregate["uncalibrated_power_dbfs"]["total"], "channel_power_q95_db": _q95(channel_power_errors), "peak_power_q95_db": _q95(peak_power_errors)}
        domain_gate = gates["signal_domain"]
        domain_family_ok = all(item["domain_correct_count"] >= domain_gate["family_correct_count_minimum"] and item["domain_wrong_count"] <= domain_gate["wrong_count_maximum"] for item in family_records if family_definitions[item["family_id"]]["domain"] != "Belirsiz")
        decisions["signal_domain"] = {"status": _status(domain_family_ok), "valid_count": aggregate["signal_domain"]["valid"], "trial_count": aggregate["signal_domain"]["total"]}
        required = int(gates["automatic_span"]["family_success_count_minimum"])
        decisions["automatic_span"] = {"status": _status(all(item["automatic_span_success_count"] >= required for item in family_records) and close_cross_match <= gates["automatic_span"]["cross_match_count_maximum"]), "success_count": automatic_span_success, "trial_count": automatic_span_total, "success_rate": automatic_span_success / automatic_span_total, "close_success_count": close_success, "close_trial_count": close_trials, "cross_match_count": close_cross_match}
    forced_noise = evaluate_forced_measurement_noise(role)
    noise_limit = int(gates["noise_numeric_false_valid_count_maximum"])
    if noise_false_valid > noise_limit:
        for name in ("carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs"):
            decisions[name]["status"] = "failed"
    if noise_domain_definite > int(gates["signal_domain"]["noise_definite_count_maximum"]):
        decisions["signal_domain"]["status"] = "failed"
    for name in ("emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs"):
        if forced_noise["field_valid_counts"][name] > noise_limit:
            decisions[name]["status"] = "failed"
    if forced_noise["field_valid_counts"]["signal_domain"] > int(gates["signal_domain"]["noise_definite_count_maximum"]):
        decisions["signal_domain"]["status"] = "failed"
    validated_fields = [name for name, decision in decisions.items() if decision["status"] == "passed"]
    return {
        "schema_version": 2,
        "artifact_id": f"phase04e1-{role}-results-v1",
        "protocol_revision": "independent-fields-v2",
        "role": role,
        "status": "passed" if validated_fields else "failed",
        "validated_fields": validated_fields,
        "family_results": family_records,
        "field_decisions": decisions,
        "diagnostics": {"false_carrier_count": false_carrier, "carrier_nonapplicable_trials": carrier_nonapplicable, "quality_state_counts": state_counts, "stage_counters": stage_counters, "clipping_count": clipping_count, "noise_sequences": noise_sequences, "noise_frames_per_sequence": noise_frames_per_sequence, "noise_total_frames": noise_sequences * noise_frames_per_sequence, "noise_numeric_false_valid_count": noise_false_valid, "noise_domain_definite_count": noise_domain_definite, "forced_measurement_noise": forced_noise, "snr_conditions": snr_diagnostics},
    }


def evaluate_forced_measurement_noise(role: str) -> dict[str, Any]:
    """Run the forced negative control with the same ownership contract as signal trials."""
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    scenes = load_json(SCENES_PATH)
    gates = load_json(ACCEPTANCE_PATH)[role]
    catalog = load_parameter_catalog()
    seed_base = int(scenes["common"]["binding_seed" if role == "binding" else "oos_seed"])
    trial_count = int(gates["noise_sequences"])
    processor = SpectrumProcessor()
    measurement = OperatorMeasurementProcessor()
    counters = _new_stage_counters()
    valid_counts = {name: 0 for name in FIELD_RESULT_ATTRS}
    span = AnalysisSpan(1792, 2303, "operator_adjusted")
    for trial in range(trial_count):
        samples: list[np.ndarray] = []
        spectra: list[Any] = []
        for frame_index in range(4):
            frame = generate_parameter_scene(
                "noise-only", trial_index=trial, condition_index=0, frame_index=frame_index,
                catalog=catalog, scene_seed_override=seed_base,
            )
            samples.append(frame.samples)
            spectra.append(processor.process(
                frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0,
            ))
        result = measurement.measure(_forced_intent(span, 1, trial), tuple(samples), tuple(spectra))
        _record_stage_counters(counters, result)
        for name, attribute in FIELD_RESULT_ATTRS.items():
            if getattr(result, attribute).state == "valid":
                valid_counts[name] += 1
    return {
        "contract": "confirmed-style-intent-same-ownership-v1",
        "trial_count": trial_count,
        "frames_per_trial": 4,
        "field_valid_counts": valid_counts,
        "stage_counters": counters,
    }


def complete_existing_v2_result(document: dict[str, Any]) -> dict[str, Any]:
    """Complete derived protocol evidence without rerunning the signal population."""
    role = str(document["role"])
    completed = dict(document)
    completed["schema_version"] = 2
    completed["protocol_revision"] = "independent-fields-v2"
    diagnostics = dict(completed["diagnostics"])
    clipping_count = int(
        diagnostics["stage_counters"]["occupied_bandwidth"]["reason_counts"].get("span_edge_clipping", 0)
    )
    diagnostics["clipping_count"] = clipping_count
    forced_noise = evaluate_forced_measurement_noise(role)
    diagnostics["forced_measurement_noise"] = forced_noise
    completed["diagnostics"] = diagnostics
    decisions = {name: dict(value) for name, value in completed["field_decisions"].items()}
    decisions["occupied_bandwidth"]["clipping_count"] = clipping_count
    gates = load_json(ACCEPTANCE_PATH)[role]
    if clipping_count > int(gates["occupied_bandwidth"]["clipping_count_maximum"]):
        decisions["occupied_bandwidth"]["status"] = "failed"
    numeric_limit = int(gates["noise_numeric_false_valid_count_maximum"])
    for name in ("emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs"):
        if forced_noise["field_valid_counts"][name] > numeric_limit:
            decisions[name]["status"] = "failed"
    if forced_noise["field_valid_counts"]["signal_domain"] > int(gates["signal_domain"]["noise_definite_count_maximum"]):
        decisions["signal_domain"]["status"] = "failed"
    completed["field_decisions"] = decisions
    completed["validated_fields"] = [name for name, value in decisions.items() if value["status"] == "passed"]
    completed["status"] = "passed" if completed["validated_fields"] else "failed"
    return completed


def compare(binding: dict[str, Any], oos: dict[str, Any]) -> dict[str, Any]:
    fields = ["automatic_span", "emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain"]
    decisions = []
    validated = []
    automatic_span = (
        binding["field_decisions"]["automatic_span"]["status"] == "passed"
        and oos["field_decisions"]["automatic_span"]["status"] == "passed"
    )
    for name in fields:
        field_passed = binding["field_decisions"][name]["status"] == "passed" and oos["field_decisions"][name]["status"] == "passed"
        passed = field_passed
        capability = name if name == "automatic_span" else f"manual_{name}"
        decisions.append({"capability": capability, "field": name, "binding": binding["field_decisions"][name]["status"], "oos": oos["field_decisions"][name]["status"], "status": _status(passed)})
        if passed and name != "automatic_span":
            validated.append(name)
    return {"schema_version": 2, "comparison_id": "phase04e1-operator-assisted-parameters", "protocol_revision": "independent-fields-v2", "status": "passed" if validated else "failed", "automatic_span_validated": automatic_span, "validated_fields": validated, "field_decisions": decisions}
