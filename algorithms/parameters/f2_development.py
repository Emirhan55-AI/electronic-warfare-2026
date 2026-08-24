"""Open-catalog development evaluation for the PHASE-04-F2 v3 estimator."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from algorithms.spectrum import SpectrumProcessor
from verification.phase04f2_scoring import score_population

from .f1_development import _intent, _median, _q95, _truth
from .f2_estimator import F2ParameterEstimator
from .operator_reference import load_json
from .scenes import generate_parameter_scene, load_parameter_catalog


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f2"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"


def _bucket() -> dict[str, Any]:
    return {
        "trials": 0,
        "center_errors": [], "carrier_errors": [], "false_carrier": 0, "carrier_abstained": 0,
        "obw_errors": [], "lower_errors": [], "upper_errors": [], "temporal": [], "robustness": [], "clipping": 0,
        "power_errors": [], "snr_errors": [],
        "domain_correct": 0, "domain_wrong": 0, "domain_abstained": 0,
    }


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _finite_max(values: list[float | None]) -> float:
    return max(_required(value) for value in values)


def _required(value: float | None) -> float:
    """Represent a missing required error metric as a finite, scoring-safe violation."""
    return float(value) if value is not None else 1.0e300


def evaluate_development() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    acceptance = load_json(ACCEPTANCE_PATH)
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F2ParameterEstimator()
    common = development["common"]
    trial_count = int(common["trials_per_seed_per_family"])
    seed_count = len(common["development_seeds"])
    family_trials = trial_count * seed_count
    margin = int(common["operator_span_truth_margin_bins_per_side"])
    bin_spacing = float(common["sample_rate_hz"]) / int(common["frame_length"])
    conditions = tuple(float(value) for value in common["snr_db"])
    family_buckets = {
        str(family["id"]): {snr_db: _bucket() for snr_db in conditions}
        for family in development["families"]
    }
    aggregates = {snr_db: _bucket() for snr_db in conditions}

    for seed_index, seed in enumerate(common["development_seeds"]):
        for family_index, family in enumerate(development["families"]):
            family_id = str(family["id"])
            frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
            scene_seed = int(seed) + family_index * 10_000
            for condition_index, snr_db in enumerate(conditions):
                family_bucket = family_buckets[family_id][snr_db]
                aggregate = aggregates[snr_db]
                for trial in range(trial_count):
                    frames = tuple(
                        generate_parameter_scene(
                            str(family["scene_id"]),
                            trial_index=trial,
                            condition_index=condition_index,
                            frame_index=frame_index,
                            clean_power_dbfs=-18.0,
                            snr_db=snr_db,
                            catalog=catalog,
                            scene_seed_override=scene_seed,
                        )
                        for frame_index in frame_indices
                    )
                    samples = tuple(frame.samples for frame in frames)
                    spectra = tuple(
                        processor.process(
                            frame.samples,
                            sample_rate_hz=float(common["sample_rate_hz"]),
                            center_frequency_hz=float(common["center_frequency_hz"]),
                        )
                        for frame in frames
                    )
                    clean_spectra = tuple(
                        processor.process(
                            frame.clean_samples,
                            sample_rate_hz=float(common["sample_rate_hz"]),
                            center_frequency_hz=float(common["center_frequency_hz"]),
                        )
                        for frame in frames
                    )
                    truth = _truth(clean_spectra, margin)
                    span = tuple(int(value) for value in truth["span"])
                    event_id = seed_index * 100 + family_index + 1
                    revision = condition_index * trial_count + trial
                    result = estimator.measure(_intent(span, event_id, revision), samples, spectra)
                    for bucket in (family_bucket, aggregate):
                        bucket["trials"] += 1

                    if result.emission_center_frequency.state == "valid":
                        truth_hz = float(common["center_frequency_hz"]) + (float(truth["center_bin"]) - 2048.0) * bin_spacing
                        error = abs(float(result.emission_center_frequency.value) - truth_hz) / bin_spacing
                        family_bucket["center_errors"].append(error); aggregate["center_errors"].append(error)

                    applicable = bool(family["carrier_line_applicable"])
                    if applicable and result.carrier_line_frequency.state == "valid":
                        scene = next(item for item in catalog["scenes"] if item["id"] == family["scene_id"])
                        truth_hz = float(common["center_frequency_hz"]) + float(scene["signed_center_bin"]) * bin_spacing
                        error = abs(float(result.carrier_line_frequency.value) - truth_hz) / bin_spacing
                        family_bucket["carrier_errors"].append(error); aggregate["carrier_errors"].append(error)
                    elif applicable:
                        family_bucket["carrier_abstained"] += 1; aggregate["carrier_abstained"] += 1
                    elif result.carrier_line_frequency.state == "valid":
                        family_bucket["false_carrier"] += 1; aggregate["false_carrier"] += 1

                    if result.occupied_bandwidth.reason == "span_edge_clipping":
                        family_bucket["clipping"] += 1; aggregate["clipping"] += 1
                    if result.occupied_bandwidth.state == "valid":
                        lower_bin = (float(result.lower_band_edge.value) - float(common["center_frequency_hz"])) / bin_spacing + 2048.0
                        upper_bin = (float(result.upper_band_edge.value) - float(common["center_frequency_hz"])) / bin_spacing + 2048.0
                        width_error = abs((upper_bin - lower_bin) - float(truth["width_bins"])) / float(truth["width_bins"])
                        lower_error = abs(lower_bin - float(truth["lower_bin"]))
                        upper_error = abs(upper_bin - float(truth["upper_bin"]))
                        for bucket in (family_bucket, aggregate):
                            bucket["obw_errors"].append(width_error)
                            bucket["lower_errors"].append(lower_error)
                            bucket["upper_errors"].append(upper_error)
                            if result.quality.temporal_edge_range_bins is not None:
                                bucket["temporal"].append(result.quality.temporal_edge_range_bins)
                        if snr_db == 12.0:
                            differences: list[float] = []
                            for perturb in common["span_perturbation_bins"]:
                                if int(perturb) == 0:
                                    continue
                                moved = (span[0] + int(perturb), span[1] + int(perturb))
                                perturbed = estimator.measure(_intent(moved, event_id, revision), samples, spectra)
                                if perturbed.occupied_bandwidth.state == "valid":
                                    differences.append(max(
                                        abs(float(perturbed.lower_band_edge.value) - float(result.lower_band_edge.value)),
                                        abs(float(perturbed.upper_band_edge.value) - float(result.upper_band_edge.value)),
                                    ) / bin_spacing)
                            if len(differences) == 2:
                                robust = max(differences)
                                family_bucket["robustness"].append(robust); aggregate["robustness"].append(robust)

                    if result.channel_power_dbfs.state == "valid":
                        error = abs(float(result.channel_power_dbfs.value) - float(truth["power_dbfs"]))
                        family_bucket["power_errors"].append(error); aggregate["power_errors"].append(error)
                    if result.snr_estimate_db.state == "valid":
                        error = abs(float(result.snr_estimate_db.value) - snr_db)
                        family_bucket["snr_errors"].append(error); aggregate["snr_errors"].append(error)

                    if result.signal_domain.state == "valid":
                        if str(result.signal_domain.value) == str(family["domain"]):
                            family_bucket["domain_correct"] += 1; aggregate["domain_correct"] += 1
                        else:
                            family_bucket["domain_wrong"] += 1; aggregate["domain_wrong"] += 1
                    else:
                        family_bucket["domain_abstained"] += 1; aggregate["domain_abstained"] += 1

    main = aggregates[12.0]
    six = aggregates[6.0]
    zero = aggregates[0.0]
    low = aggregates[-6.0]
    families = development["families"]
    applicable = [family for family in families if family["carrier_line_applicable"]]
    nonapplicable = [family for family in families if not family["carrier_line_applicable"]]
    nonambiguous = [family for family in families if family["domain"] != "Belirsiz"]
    ambiguous = [family for family in families if family["domain"] == "Belirsiz"]
    all_main = [family_buckets[str(family["id"])][12.0] for family in families]
    applicable_main = [family_buckets[str(family["id"])][12.0] for family in applicable]
    nonambiguous_six_main = [
        family_buckets[str(family["id"])][snr_db]
        for snr_db in (6.0, 12.0)
        for family in nonambiguous
    ]
    numeric_total = len(families) * family_trials
    applicable_total = len(applicable) * family_trials
    nonapplicable_total = len(nonapplicable) * family_trials
    nonambiguous_total = len(nonambiguous) * family_trials
    ambiguous_total = len(ambiguous) * family_trials

    noise_false = {name: 0 for name in ("center", "carrier", "obw", "power", "snr", "domain")}
    noise_significance: list[float] = []
    for seed_index, seed in enumerate(common["development_seeds"]):
        for trial in range(int(common["negative_control_measurements_per_seed"])):
            frames = tuple(
                generate_parameter_scene(
                    str(development["negative_scene"]["scene_id"]),
                    trial_index=trial,
                    condition_index=0,
                    frame_index=frame_index,
                    catalog=catalog,
                    scene_seed_override=int(seed) + 90_000,
                )
                for frame_index in range(4)
            )
            spectra = tuple(
                processor.process(
                    frame.samples,
                    sample_rate_hz=float(common["sample_rate_hz"]),
                    center_frequency_hz=float(common["center_frequency_hz"]),
                )
                for frame in frames
            )
            result = estimator.measure(
                _intent((1792, 2303), 9_000 + seed_index, trial),
                tuple(frame.samples for frame in frames),
                spectra,
            )
            if result.quality.detection_significance is not None:
                noise_significance.append(float(result.quality.detection_significance))
            noise_false["center"] += int(result.emission_center_frequency.state == "valid")
            noise_false["carrier"] += int(result.carrier_line_frequency.state == "valid")
            noise_false["obw"] += int(result.occupied_bandwidth.state == "valid")
            noise_false["power"] += int(result.channel_power_dbfs.state == "valid")
            noise_false["snr"] += int(result.snr_estimate_db.state == "valid")
            noise_false["domain"] += int(result.signal_domain.state == "valid")

    metrics: dict[str, float | int] = {
        "center.family_min_valid_rate": min(_rate(len(item["center_errors"]), family_trials) for item in all_main),
        "center.family_max_q95_error_bins": _finite_max([_q95(item["center_errors"]) for item in all_main]),
        "center.global_valid_rate": _rate(len(main["center_errors"]), numeric_total),
        "center.global_q95_error_bins": _required(_q95(main["center_errors"])),
        "noise.center_false_valid_count": noise_false["center"],
        "carrier.family_min_valid_rate": min(_rate(len(item["carrier_errors"]), family_trials) for item in applicable_main),
        "carrier.family_max_q95_error_bins": _finite_max([_q95(item["carrier_errors"]) for item in applicable_main]),
        "carrier.global_valid_rate": _rate(len(main["carrier_errors"]), applicable_total),
        "carrier.false_carrier_rate": _rate(main["false_carrier"], nonapplicable_total),
        "carrier.low_snr_abstention_rate": _rate(low["carrier_abstained"], applicable_total),
        "noise.carrier_false_valid_count": noise_false["carrier"],
        "obw.family_min_valid_rate": min(_rate(len(item["obw_errors"]), family_trials) for item in all_main),
        "obw.global_valid_rate": _rate(len(main["obw_errors"]), numeric_total),
        "obw.global_relative_q95": _required(_q95(main["obw_errors"])),
        "obw.global_lower_edge_q95_bins": _required(_q95(main["lower_errors"])),
        "obw.global_upper_edge_q95_bins": _required(_q95(main["upper_errors"])),
        "obw.global_temporal_q95_bins": _required(_q95(main["temporal"])),
        "obw.clipping_count": main["clipping"],
        "noise.obw_false_valid_count": noise_false["obw"],
        "span.edge_difference_q95_bins": _required(_q95(main["robustness"])),
        "power.family_min_valid_rate": min(_rate(len(item["power_errors"]), family_trials) for item in all_main),
        "power.global_valid_rate": _rate(len(main["power_errors"]), numeric_total),
        "power.global_q95_error_db": _required(_q95(main["power_errors"])),
        "power.zero_snr_median_error_db": _required(_median(zero["power_errors"])),
        "noise.power_false_valid_count": noise_false["power"],
        "snr.family_min_valid_rate": min(_rate(len(item["snr_errors"]), family_trials) for item in all_main),
        "snr.global_valid_rate": _rate(len(main["snr_errors"]), numeric_total),
        "snr.global_q95_error_db": _required(_q95(main["snr_errors"])),
        "snr.zero_snr_median_error_db": _required(_median(zero["snr_errors"])),
        "noise.snr_false_valid_count": noise_false["snr"],
        "domain.main_global_correct_rate": _rate(sum(family_buckets[str(family["id"])][12.0]["domain_correct"] for family in nonambiguous), nonambiguous_total),
        "domain.main_global_wrong_rate": _rate(sum(family_buckets[str(family["id"])][12.0]["domain_wrong"] for family in nonambiguous), nonambiguous_total),
        "domain.six_db_global_correct_rate": _rate(sum(family_buckets[str(family["id"])][6.0]["domain_correct"] for family in nonambiguous), nonambiguous_total),
        "domain.six_db_global_wrong_rate": _rate(sum(family_buckets[str(family["id"])][6.0]["domain_wrong"] for family in nonambiguous), nonambiguous_total),
        "domain.family_min_correct_rate": min(_rate(item["domain_correct"], family_trials) for item in nonambiguous_six_main),
        "domain.family_max_wrong_rate": max(_rate(item["domain_wrong"], family_trials) for item in nonambiguous_six_main),
        "domain.ambiguous_rejection_rate": _rate(sum(family_buckets[str(family["id"])][12.0]["domain_abstained"] for family in ambiguous), ambiguous_total),
        "domain.zero_snr_wrong_rate": _rate(sum(family_buckets[str(family["id"])][0.0]["domain_wrong"] for family in nonambiguous), nonambiguous_total),
        "domain.low_snr_abstention_rate": _rate(low["domain_abstained"], numeric_total),
        "noise.domain_false_valid_count": noise_false["domain"],
    }
    scoring = score_population(metrics, acceptance, "binding")
    family_summary = {
        family_id: {
            str(snr_db): {
                "trial_count": bucket["trials"],
                "center_valid_count": len(bucket["center_errors"]),
                "carrier_valid_count": len(bucket["carrier_errors"]),
                "obw_valid_count": len(bucket["obw_errors"]),
                "power_valid_count": len(bucket["power_errors"]),
                "snr_valid_count": len(bucket["snr_errors"]),
                "domain_correct_count": bucket["domain_correct"],
                "domain_wrong_count": bucket["domain_wrong"],
                "domain_abstained_count": bucket["domain_abstained"],
            }
            for snr_db, bucket in conditions_by_snr.items()
        }
        for family_id, conditions_by_snr in family_buckets.items()
    }
    return {
        "schema_version": 1,
        "artifact_id": "phase04f2-open-development-results-v3",
        "role": "development-only",
        "status": scoring["status"],
        "population": {
            "seed_count": seed_count,
            "trials_per_seed_per_family": trial_count,
            "total_trials_per_family": family_trials,
            "noise_measurements": int(common["total_negative_control_measurements"]),
            "frames_per_measurement": int(common["frames_per_measurement"]),
        },
        "method_ids": estimator.METHOD_IDS,
        "metrics": metrics,
        "scoring": scoring,
        "noise_detection_significance": {
            "maximum": max(noise_significance),
            "q95": _q95(noise_significance),
        },
        "families": family_summary,
        "claim_boundary": "Yalnız altı açık F2 geliştirme seed'inin sonucudur; binding, OOS, canlı RF veya ürün kabulü değildir.",
    }
