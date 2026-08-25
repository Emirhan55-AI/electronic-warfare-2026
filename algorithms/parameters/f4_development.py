"""Open-catalog development evaluation for the PHASE-04-F4 v5 estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from algorithms.spectrum import SpectrumProcessor
from verification.phase04f4_scoring import score_development

from . import f2_development
from .f1_development import _intent, _truth
from .f2_domain import prototype_scores
from .f4_domain import DEFAULT_MODEL_PATH, extract_domain_vector_v5, minimum_margin_for_family
from .f4_estimator import F4ParameterEstimator
from .operator_reference import load_json
from .scenes import generate_parameter_scene, load_parameter_catalog


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f4"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
INHERITED_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "acceptance-gates.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
CARRIER_RESULT_PATH = ROOT / "results" / "evidence" / "phase04f4" / "carrier-analysis-v5.json"


def _base_evaluation() -> dict[str, Any]:
    original_development_path = f2_development.DEVELOPMENT_PATH
    original_acceptance_path = f2_development.ACCEPTANCE_PATH
    original_estimator = f2_development.F2ParameterEstimator
    f2_development.DEVELOPMENT_PATH = DEVELOPMENT_PATH
    f2_development.ACCEPTANCE_PATH = BASE_ACCEPTANCE_PATH
    f2_development.F2ParameterEstimator = F4ParameterEstimator
    try:
        return f2_development.evaluate_development()
    finally:
        f2_development.DEVELOPMENT_PATH = original_development_path
        f2_development.ACCEPTANCE_PATH = original_acceptance_path
        f2_development.F2ParameterEstimator = original_estimator


def _q(values: list[float]) -> dict[str, float]:
    labels = ("q0", "q10", "q25", "q50", "q75", "q90", "q100")
    result = np.quantile(np.asarray(values, dtype=np.float64), (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0))
    return {label: float(value) for label, value in zip(labels, result, strict=True)}


def _domain_seed_diagnostics() -> dict[str, Any]:
    development = load_json(DEVELOPMENT_PATH)
    model = load_json(DEFAULT_MODEL_PATH)
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F4ParameterEstimator()
    common = development["common"]
    counts = {
        family_id: [
            {"seed_index": index, "correct": 0, "wrong": 0, "abstained": 0}
            for index in range(len(common["development_seeds"]))
        ]
        for family_id in ("ook", "nfm")
    }
    nfm_distances: list[float] = []
    nfm_margins: list[float] = []
    reasons = {"distance_only": 0, "margin_only": 0, "both": 0, "nearest_uncertain": 0}
    for family_index, family in enumerate(development["families"]):
        family_id = str(family["id"])
        if family_id not in counts:
            continue
        expected = str(family["domain"])
        frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
        for seed_index, seed in enumerate(common["development_seeds"]):
            for trial in range(int(common["trials_per_seed_per_family"])):
                frames = tuple(
                    generate_parameter_scene(
                        str(family["scene_id"]), trial_index=trial, condition_index=2,
                        frame_index=frame_index, clean_power_dbfs=-18.0, snr_db=6.0,
                        catalog=catalog, scene_seed_override=int(seed) + family_index * 10_000,
                    )
                    for frame_index in frame_indices
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
                intent = _intent(tuple(int(value) for value in truth["span"]), family_index + 1, trial)
                samples = tuple(frame.samples for frame in frames)
                result = estimator.measure(intent, samples, spectra)
                record = counts[family_id][seed_index]
                if result.signal_domain.state != "valid":
                    record["abstained"] += 1
                elif result.signal_domain.value == expected:
                    record["correct"] += 1
                else:
                    record["wrong"] += 1

                if family_id == "nfm":
                    vector = extract_domain_vector_v5(
                        samples, intent.span.lower_shifted_bin, intent.span.upper_shifted_bin,
                    )
                    distance, margin, nearest = prototype_scores(vector, model)
                    nfm_distances.append(distance)
                    nfm_margins.append(margin)
                    if result.signal_domain.state != "valid":
                        distance_failed = distance > float(model["thresholds"]["maximum_distance"])
                        margin_failed = margin < minimum_margin_for_family(model, str(nearest["family_id"]))
                        if nearest["domain"] == "Belirsiz":
                            reasons["nearest_uncertain"] += 1
                        elif distance_failed and margin_failed:
                            reasons["both"] += 1
                        elif distance_failed:
                            reasons["distance_only"] += 1
                        else:
                            reasons["margin_only"] += 1
    return {
        "ook_6_db": counts["ook"],
        "nfm_6_db": counts["nfm"],
        "nfm_rejection_reason_counts_6_db": reasons,
        "nfm_distance_margin_quantiles_6_db": {
            "distance": _q(nfm_distances),
            "margin": _q(nfm_margins),
        },
    }


def evaluate_development() -> dict[str, Any]:
    acceptance = load_json(ACCEPTANCE_PATH)
    inherited_acceptance = load_json(INHERITED_ACCEPTANCE_PATH)
    base_acceptance = load_json(BASE_ACCEPTANCE_PATH)
    carrier = load_json(CARRIER_RESULT_PATH)
    base = _base_evaluation()
    domain = _domain_seed_diagnostics()
    carrier_seed = carrier["per_seed"]
    ook = domain["ook_6_db"]
    nfm = domain["nfm_6_db"]
    inherited_metrics: dict[str, float | int] = {
        "carrier.ook.seed_min_valid_count_12_db": min(item["ook_valid_count"] for item in carrier_seed),
        "carrier.ook.seed_min_qualifying_frame_count_12_db": min(item["ook_qualifying_frame_count"] for item in carrier_seed),
        "carrier.ook.seed_min_all_frames_qualified_count_12_db": min(item["ook_all_frames_qualified_count"] for item in carrier_seed),
        "carrier.nonapplicable.seed_max_false_valid_count_12_db": max(item["nonapplicable_false_valid_count"] for item in carrier_seed),
        "carrier.nonapplicable.aggregate_false_valid_count_12_db": sum(item["nonapplicable_false_valid_count"] for item in carrier_seed),
        "domain.ook.seed_min_correct_count_6_db": min(item["correct"] for item in ook),
        "domain.ook.seed_max_wrong_count_6_db": max(item["wrong"] for item in ook),
        "domain.ook.aggregate_wrong_count_6_db": sum(item["wrong"] for item in ook),
        "noise.center_false_valid_count": base["metrics"]["noise.center_false_valid_count"],
        "noise.carrier_false_valid_count": base["metrics"]["noise.carrier_false_valid_count"],
        "noise.obw_false_valid_count": base["metrics"]["noise.obw_false_valid_count"],
        "noise.power_false_valid_count": base["metrics"]["noise.power_false_valid_count"],
        "noise.snr_false_valid_count": base["metrics"]["noise.snr_false_valid_count"],
        "noise.domain_false_valid_count": base["metrics"]["noise.domain_false_valid_count"],
    }
    additional_metrics: dict[str, float | int] = {
        "domain.nfm.seed_min_correct_count_6_db": min(item["correct"] for item in nfm),
        "domain.nfm.seed_max_wrong_count_6_db": max(item["wrong"] for item in nfm),
        "domain.nfm.seed_max_abstained_count_6_db": max(item["abstained"] for item in nfm),
        "domain.nfm.aggregate_wrong_count_6_db": sum(item["wrong"] for item in nfm),
    }
    scoring = score_development(
        base["metrics"], inherited_metrics, additional_metrics,
        acceptance, inherited_acceptance, base_acceptance,
    )
    common = load_json(DEVELOPMENT_PATH)["common"]
    base.update({
        "artifact_id": "phase04f4-open-development-results-v5",
        "role": "development-only",
        "status": scoring["status"],
        "population": {
            "seed_count": len(common["development_seeds"]),
            "trials_per_seed_per_family": common["trials_per_seed_per_family"],
            "total_trials_per_family": common["total_trials_per_family"],
            "noise_measurements": common["total_negative_control_measurements"],
            "frames_per_measurement": common["frames_per_measurement"],
        },
        "method_ids": F4ParameterEstimator.METHOD_IDS,
        "scoring": scoring,
        "inherited_risk_metrics": inherited_metrics,
        "additional_risk_metrics": additional_metrics,
        "diagnostics": {
            "domain.nfm.seed_counts_6_db": nfm,
            "domain.nfm.rejection_reason_counts_6_db": domain["nfm_rejection_reason_counts_6_db"],
            "domain.nfm.distance_margin_quantiles_6_db": domain["nfm_distance_margin_quantiles_6_db"],
            "domain.ook.seed_counts_6_db": ook,
            "carrier.seed_counts_12_db": carrier_seed,
        },
        "claim_boundary": "Yalnız sekiz açık F4 geliştirme seed'inin sonucudur; binding, OOS, canlı RF veya ürün kabulü değildir.",
    })
    return base
