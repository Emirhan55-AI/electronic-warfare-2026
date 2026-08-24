"""Development-only evaluation for the locked PHASE-04-F1 field gates."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.spectrum import SpectrumProcessor

from .f1_estimator import F1ParameterEstimator, _fractional_edge
from .operator_assisted import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from .operator_reference import load_json
from .scenes import generate_parameter_scene, load_parameter_catalog


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
DEVELOPMENT_PATH = FIXTURES / "development-scenes.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"


def _q95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def _intent(span: tuple[int, int], event_id: int, revision: int) -> MeasurementIntent:
    analysis = AnalysisSpan(span[0], span[1], "operator_adjusted", revision)
    candidate = MeasurementCandidate(event_id, revision, span[0], span[1])
    context = MeasurementContext(1, 1, 1, event_id, revision, (True, True, True, True), (candidate,))
    return MeasurementIntent(1, 1, 1, event_id, revision, 0, analysis, context)


def _truth(clean_spectra: tuple[Any, ...], margin: int) -> dict[str, float | tuple[int, int]]:
    mean_psd = np.mean(np.stack([item.display.psd_fs2_per_hz for item in clean_spectra]), axis=0)
    positive = np.maximum(mean_psd, 0.0)
    lower_full = _fractional_edge(positive, 0, 0.005)
    upper_full = _fractional_edge(positive, 0, 0.995)
    span = (
        max(56, int(math.floor(lower_full)) - margin),
        min(4039, int(math.ceil(upper_full)) + margin),
    )
    selected = positive[span[0] : span[1] + 1]
    indices = np.arange(span[0], span[1] + 1, dtype=np.float64)
    total = float(np.sum(selected))
    center_bin = float(np.sum(indices * selected) / total)
    lower = _fractional_edge(selected, span[0], 0.005)
    upper = _fractional_edge(selected, span[0], 0.995)
    power_dbfs = 10.0 * math.log10(total * clean_spectra[0].bin_spacing_hz)
    return {"span": span, "center_bin": center_bin, "lower_bin": lower, "upper_bin": upper, "width_bins": upper - lower, "power_dbfs": power_dbfs}


def _new_family_record(family: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_id": family["id"],
        "expected_domain": family["domain"],
        "carrier_line_applicable": family["carrier_line_applicable"],
        "conditions": {},
    }


def evaluate_development() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    gates = load_json(ACCEPTANCE_PATH)["binding"]
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F1ParameterEstimator()
    base_seed = int(development["common"]["base_seed"])
    trial_count = int(development["common"]["trials_per_family"])
    margin = int(development["common"]["operator_span_truth_margin_bins_per_side"])
    bin_spacing = float(development["common"]["sample_rate_hz"]) / int(development["common"]["frame_length"])
    families: list[dict[str, Any]] = []
    aggregates: dict[float, dict[str, list[float] | int]] = {
        snr: {
            "center_errors": [], "carrier_errors": [], "false_carrier": 0, "carrier_nonapplicable": 0,
            "obw_errors": [], "lower_errors": [], "upper_errors": [], "temporal": [], "robustness": [], "clipping": 0,
            "power_errors": [], "snr_errors": [], "domain_correct": 0, "domain_wrong": 0, "domain_abstained": 0,
            "definite_total": 0, "numeric_trials": 0,
        }
        for snr in (-6.0, 0.0, 6.0, 12.0)
    }
    for family_index, family in enumerate(development["families"]):
        family_record = _new_family_record(family)
        frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
        for condition_index, snr_db in enumerate((-6.0, 0.0, 6.0, 12.0)):
            metrics: dict[str, Any] = {
                "trial_count": trial_count, "center_valid": 0, "center_errors": [], "carrier_valid": 0,
                "carrier_errors": [], "false_carrier": 0, "obw_valid": 0, "obw_errors": [], "lower_errors": [],
                "upper_errors": [], "temporal": [], "robustness": [], "clipping": 0, "power_valid": 0,
                "power_errors": [], "snr_valid": 0, "snr_errors": [], "domain_correct": 0, "domain_wrong": 0,
                "domain_abstained": 0,
            }
            aggregate = aggregates[snr_db]
            for trial in range(trial_count):
                frames = tuple(
                    generate_parameter_scene(
                        str(family["scene_id"]), trial_index=trial, condition_index=condition_index,
                        frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=snr_db, catalog=catalog,
                        scene_seed_override=base_seed + family_index * 10_000,
                    )
                    for frame_index in frame_indices
                )
                spectra = tuple(processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0) for frame in frames)
                clean_spectra = tuple(processor.process(frame.clean_samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0) for frame in frames)
                truth = _truth(clean_spectra, margin)
                span = tuple(int(value) for value in truth["span"])
                result = estimator.measure(_intent(span, family_index + 1, trial), tuple(frame.samples for frame in frames), spectra)
                aggregate["numeric_trials"] += 1
                if result.emission_center_frequency.state == "valid":
                    error = abs(float(result.emission_center_frequency.value) - (100_000_000.0 + (float(truth["center_bin"]) - 2048.0) * bin_spacing)) / bin_spacing
                    metrics["center_valid"] += 1; metrics["center_errors"].append(error); aggregate["center_errors"].append(error)
                applicable = bool(family["carrier_line_applicable"])
                if applicable and result.carrier_line_frequency.state == "valid":
                    scene = next(item for item in catalog["scenes"] if item["id"] == family["scene_id"])
                    truth_carrier = 100_000_000.0 + float(scene["signed_center_bin"]) * bin_spacing
                    error = abs(float(result.carrier_line_frequency.value) - truth_carrier) / bin_spacing
                    metrics["carrier_valid"] += 1; metrics["carrier_errors"].append(error); aggregate["carrier_errors"].append(error)
                elif not applicable:
                    aggregate["carrier_nonapplicable"] += 1
                    if result.carrier_line_frequency.state == "valid":
                        metrics["false_carrier"] += 1; aggregate["false_carrier"] += 1
                if result.occupied_bandwidth.reason == "span_edge_clipping":
                    metrics["clipping"] += 1; aggregate["clipping"] += 1
                if result.occupied_bandwidth.state == "valid":
                    estimated_lower = (float(result.lower_band_edge.value) - 100_000_000.0) / bin_spacing + 2048.0
                    estimated_upper = (float(result.upper_band_edge.value) - 100_000_000.0) / bin_spacing + 2048.0
                    width_error = abs((estimated_upper - estimated_lower) - float(truth["width_bins"])) / float(truth["width_bins"])
                    lower_error = abs(estimated_lower - float(truth["lower_bin"]))
                    upper_error = abs(estimated_upper - float(truth["upper_bin"]))
                    metrics["obw_valid"] += 1; metrics["obw_errors"].append(width_error); metrics["lower_errors"].append(lower_error); metrics["upper_errors"].append(upper_error)
                    aggregate["obw_errors"].append(width_error); aggregate["lower_errors"].append(lower_error); aggregate["upper_errors"].append(upper_error)
                    if result.quality.temporal_edge_range_bins is not None:
                        metrics["temporal"].append(result.quality.temporal_edge_range_bins); aggregate["temporal"].append(result.quality.temporal_edge_range_bins)
                    perturb_differences: list[float] = []
                    for perturb in (-4, 4):
                        moved = (span[0] + perturb, span[1] + perturb)
                        perturbed = estimator.measure(_intent(moved, family_index + 1, trial), tuple(frame.samples for frame in frames), spectra)
                        if perturbed.occupied_bandwidth.state == "valid":
                            perturb_differences.append(max(
                                abs(float(perturbed.lower_band_edge.value) - float(result.lower_band_edge.value)),
                                abs(float(perturbed.upper_band_edge.value) - float(result.upper_band_edge.value)),
                            ) / bin_spacing)
                    if len(perturb_differences) == 2:
                        robust = max(perturb_differences); metrics["robustness"].append(robust); aggregate["robustness"].append(robust)
                if result.channel_power_dbfs.state == "valid":
                    error = abs(float(result.channel_power_dbfs.value) - float(truth["power_dbfs"]))
                    metrics["power_valid"] += 1; metrics["power_errors"].append(error); aggregate["power_errors"].append(error)
                if result.snr_estimate_db.state == "valid":
                    error = abs(float(result.snr_estimate_db.value) - snr_db)
                    metrics["snr_valid"] += 1; metrics["snr_errors"].append(error); aggregate["snr_errors"].append(error)
                domain = str(result.signal_domain.value)
                if result.signal_domain.state == "valid":
                    aggregate["definite_total"] += 1
                    if domain == family["domain"]:
                        metrics["domain_correct"] += 1; aggregate["domain_correct"] += 1
                    else:
                        metrics["domain_wrong"] += 1; aggregate["domain_wrong"] += 1
                else:
                    metrics["domain_abstained"] += 1; aggregate["domain_abstained"] += 1
            family_record["conditions"][str(snr_db)] = {
                "trial_count": trial_count,
                "valid_rates": {"center": metrics["center_valid"] / trial_count, "carrier": metrics["carrier_valid"] / trial_count if family["carrier_line_applicable"] else None, "obw": metrics["obw_valid"] / trial_count, "power": metrics["power_valid"] / trial_count, "snr": metrics["snr_valid"] / trial_count},
                "q95": {"center_bins": _q95(metrics["center_errors"]), "carrier_bins": _q95(metrics["carrier_errors"]), "obw_relative": _q95(metrics["obw_errors"]), "lower_edge_bins": _q95(metrics["lower_errors"]), "upper_edge_bins": _q95(metrics["upper_errors"]), "temporal_bins": _q95(metrics["temporal"]), "span_robustness_bins": _q95(metrics["robustness"]), "power_db": _q95(metrics["power_errors"]), "snr_db": _q95(metrics["snr_errors"])},
                "counts": {"false_carrier": metrics["false_carrier"], "clipping": metrics["clipping"], "domain_correct": metrics["domain_correct"], "domain_wrong": metrics["domain_wrong"], "domain_abstained": metrics["domain_abstained"]},
            }
        families.append(family_record)

    main = aggregates[12.0]; six = aggregates[6.0]; zero = aggregates[0.0]; low = aggregates[-6.0]
    applicable_trials = sum(trial_count for family in development["families"] if family["carrier_line_applicable"])
    nonapplicable_trials = sum(trial_count for family in development["families"] if not family["carrier_line_applicable"])
    numeric_trials = len(development["families"]) * trial_count
    nonambiguous_trials = sum(trial_count for family in development["families"] if family["domain"] != "Belirsiz")
    ambiguous_trials = sum(trial_count for family in development["families"] if family["domain"] == "Belirsiz")
    family_main = [item["conditions"]["12.0"] for item in families]
    family_six = [item["conditions"]["6.0"] for item in families]
    decisions = {
        "emission_center_frequency": all(item["valid_rates"]["center"] >= gates["emission_center_frequency"]["family_valid_minimum"] and item["q95"]["center_bins"] <= gates["emission_center_frequency"]["q95_error_bins_maximum"] for item in family_main) and len(main["center_errors"]) / numeric_trials >= gates["emission_center_frequency"]["global_valid_minimum"] and _q95(main["center_errors"]) <= gates["emission_center_frequency"]["q95_error_bins_maximum"],
        "carrier_line_frequency": all(item["valid_rates"]["carrier"] >= gates["carrier_line_frequency"]["family_valid_minimum"] and item["q95"]["carrier_bins"] <= gates["carrier_line_frequency"]["q95_error_bins_maximum"] for item, family in zip(family_main, development["families"]) if family["carrier_line_applicable"]) and len(main["carrier_errors"]) / applicable_trials >= gates["carrier_line_frequency"]["global_valid_minimum"] and main["false_carrier"] / nonapplicable_trials <= gates["carrier_line_frequency"]["false_carrier_rate_maximum"],
        "occupied_bandwidth": all(item["valid_rates"]["obw"] >= gates["occupied_bandwidth"]["family_valid_minimum"] for item in family_main) and len(main["obw_errors"]) / numeric_trials >= gates["occupied_bandwidth"]["global_valid_minimum"] and _q95(main["obw_errors"]) <= gates["occupied_bandwidth"]["relative_q95_maximum"] and _q95(main["lower_errors"]) <= gates["occupied_bandwidth"]["edge_q95_bins_maximum"] and _q95(main["upper_errors"]) <= gates["occupied_bandwidth"]["edge_q95_bins_maximum"] and _q95(main["temporal"]) <= gates["occupied_bandwidth"]["temporal_q95_bins_maximum"] and main["clipping"] <= gates["occupied_bandwidth"]["clipping_count_maximum"],
        "span_robustness": _q95(main["robustness"]) is not None and _q95(main["robustness"]) <= gates["span_robustness"]["edge_difference_q95_bins_maximum"],
        "uncalibrated_channel_power_dbfs": all(item["valid_rates"]["power"] >= gates["uncalibrated_channel_power_dbfs"]["family_valid_minimum"] for item in family_main) and len(main["power_errors"]) / numeric_trials >= gates["uncalibrated_channel_power_dbfs"]["global_valid_minimum"] and _q95(main["power_errors"]) <= gates["uncalibrated_channel_power_dbfs"]["q95_error_db_maximum"] and _median(zero["power_errors"]) <= gates["uncalibrated_channel_power_dbfs"]["zero_snr_median_error_db_maximum"],
        "snr_estimate_db": all(item["valid_rates"]["snr"] >= gates["snr_estimate_db"]["family_valid_minimum"] for item in family_main) and len(main["snr_errors"]) / numeric_trials >= gates["snr_estimate_db"]["global_valid_minimum"] and _q95(main["snr_errors"]) <= gates["snr_estimate_db"]["q95_error_db_maximum"] and _median(zero["snr_errors"]) <= gates["snr_estimate_db"]["zero_snr_median_error_db_maximum"],
    }
    # Ambiguous families are correct only when the estimator abstains.
    ambiguous_main = next(item for item, family in zip(family_main, development["families"]) if family["domain"] == "Belirsiz")
    domain_gate = gates["signal_domain"]
    family_domain_ok = all(
        item["counts"]["domain_correct"] / trial_count >= domain_gate["family_correct_definite_minimum"]
        and item["counts"]["domain_wrong"] / trial_count <= domain_gate["family_wrong_definite_maximum"]
        for condition in (family_main, family_six)
        for item, family in zip(condition, development["families"])
        if family["domain"] != "Belirsiz"
    )
    decisions["signal_domain"] = (
        main["domain_correct"] / nonambiguous_trials >= domain_gate["global_correct_definite_minimum"]
        and main["domain_wrong"] / nonambiguous_trials <= domain_gate["global_wrong_definite_maximum"]
        and six["domain_correct"] / nonambiguous_trials >= domain_gate["global_correct_definite_minimum"]
        and six["domain_wrong"] / nonambiguous_trials <= domain_gate["global_wrong_definite_maximum"]
        and ambiguous_main["counts"]["domain_abstained"] / ambiguous_trials
        >= domain_gate["ambiguous_rejection_minimum"]
        and zero["domain_wrong"] / nonambiguous_trials <= domain_gate["zero_snr_wrong_definite_maximum"]
        and low["domain_abstained"] / numeric_trials >= domain_gate["low_snr_abstention_minimum"]
        and family_domain_ok
    )

    # Negative control uses the same confirmed ownership shape, without runtime truth.
    noise_false = {name: 0 for name in ("center", "carrier", "obw", "power", "snr", "domain")}
    noise_significance: list[float] = []
    for trial in range(int(gates["noise_sequences"])):
        frames = tuple(generate_parameter_scene("noise-only", trial_index=trial, condition_index=0, frame_index=index, catalog=catalog, scene_seed_override=base_seed + 90_000) for index in range(4))
        spectra = tuple(processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0) for frame in frames)
        result = estimator.measure(_intent((1792, 2303), 99, trial), tuple(frame.samples for frame in frames), spectra)
        if result.quality.detection_significance is not None:
            noise_significance.append(result.quality.detection_significance)
        noise_false["center"] += int(result.emission_center_frequency.state == "valid")
        noise_false["carrier"] += int(result.carrier_line_frequency.state == "valid")
        noise_false["obw"] += int(result.occupied_bandwidth.state == "valid")
        noise_false["power"] += int(result.channel_power_dbfs.state == "valid")
        noise_false["snr"] += int(result.snr_estimate_db.state == "valid")
        noise_false["domain"] += int(result.signal_domain.state == "valid")
    numeric_limit = int(gates["noise_numeric_false_valid_count_maximum"])
    if any(noise_false[name] > numeric_limit for name in ("center", "carrier", "obw", "power", "snr")):
        for name in ("emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_channel_power_dbfs", "snr_estimate_db"):
            decisions[name] = False
    if noise_false["domain"] > int(gates["signal_domain"]["noise_definite_count_maximum"]):
        decisions["signal_domain"] = False
    aggregate_summary = {
        str(snr): {
            "center_q95_bins": _q95(record["center_errors"]),
            "carrier_q95_bins": _q95(record["carrier_errors"]),
            "false_carrier_count": record["false_carrier"],
            "carrier_nonapplicable_count": record["carrier_nonapplicable"],
            "obw_relative_q95": _q95(record["obw_errors"]),
            "lower_edge_q95_bins": _q95(record["lower_errors"]),
            "upper_edge_q95_bins": _q95(record["upper_errors"]),
            "temporal_q95_bins": _q95(record["temporal"]),
            "span_robustness_q95_bins": _q95(record["robustness"]),
            "clipping_count": record["clipping"],
            "power_q95_db": _q95(record["power_errors"]),
            "power_median_db": _median(record["power_errors"]),
            "snr_q95_db": _q95(record["snr_errors"]),
            "snr_median_db": _median(record["snr_errors"]),
            "domain_correct_count": record["domain_correct"],
            "domain_wrong_count": record["domain_wrong"],
            "domain_abstained_count": record["domain_abstained"],
            "numeric_trial_count": record["numeric_trials"],
        }
        for snr, record in aggregates.items()
    }
    return {
        "schema_version": 1,
        "artifact_id": "phase04f1-development-results-v1",
        "role": "development-only",
        "status": "passed" if all(decisions.values()) else "failed",
        "field_decisions": {name: "passed" if value else "failed" for name, value in decisions.items()},
        "aggregate": aggregate_summary,
        "families": families,
        "noise_false_valid_counts": noise_false,
        "noise_detection_significance": {"maximum": max(noise_significance), "q95": _q95(noise_significance)},
        "claim_boundary": "Yalnız açık sentetik geliştirme kataloğu sonucudur; binding, OOS, canlı RF veya PHASE-04 kapanışı değildir.",
    }
