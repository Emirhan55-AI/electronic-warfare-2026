"""Open-catalog development evaluation for the PHASE-04-F3 v4 estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from algorithms.spectrum import SpectrumProcessor
from verification.phase04f3_scoring import score_development

from . import f2_development
from .f1_development import _intent, _truth
from .f3_estimator import F3ParameterEstimator
from .operator_reference import load_json
from .scenes import generate_parameter_scene, load_parameter_catalog


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
CARRIER_RESULT_PATH = ROOT / "results" / "evidence" / "phase04f3" / "carrier-analysis-v4.json"


def _base_evaluation() -> dict[str, Any]:
    original_development_path = f2_development.DEVELOPMENT_PATH
    original_acceptance_path = f2_development.ACCEPTANCE_PATH
    original_estimator = f2_development.F2ParameterEstimator
    f2_development.DEVELOPMENT_PATH = DEVELOPMENT_PATH
    f2_development.ACCEPTANCE_PATH = BASE_ACCEPTANCE_PATH
    f2_development.F2ParameterEstimator = F3ParameterEstimator
    try:
        return f2_development.evaluate_development()
    finally:
        f2_development.DEVELOPMENT_PATH = original_development_path
        f2_development.ACCEPTANCE_PATH = original_acceptance_path
        f2_development.F2ParameterEstimator = original_estimator


def _domain_seed_diagnostics() -> list[dict[str, int]]:
    development = load_json(DEVELOPMENT_PATH)
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F3ParameterEstimator()
    common = development["common"]
    family_index, family = next(
        (index, item) for index, item in enumerate(development["families"])
        if item["id"] == "ook"
    )
    frame_indices = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
    diagnostics: list[dict[str, int]] = []
    for seed_index, seed in enumerate(common["development_seeds"]):
        counts = {"seed_index": seed_index, "correct": 0, "wrong": 0, "abstained": 0}
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
                    frame.samples,
                    sample_rate_hz=float(common["sample_rate_hz"]),
                    center_frequency_hz=float(common["center_frequency_hz"]),
                )
                for frame in frames
            )
            clean = tuple(
                processor.process(
                    frame.clean_samples,
                    sample_rate_hz=float(common["sample_rate_hz"]),
                    center_frequency_hz=float(common["center_frequency_hz"]),
                )
                for frame in frames
            )
            truth = _truth(clean, int(common["operator_span_truth_margin_bins_per_side"]))
            result = estimator.measure(
                _intent(tuple(int(value) for value in truth["span"]), family_index + 1, trial),
                tuple(frame.samples for frame in frames),
                spectra,
            )
            if result.signal_domain.state != "valid":
                counts["abstained"] += 1
            elif result.signal_domain.value == "Sayısal":
                counts["correct"] += 1
            else:
                counts["wrong"] += 1
        diagnostics.append(counts)
    return diagnostics


def evaluate_development() -> dict[str, Any]:
    acceptance = load_json(ACCEPTANCE_PATH)
    base_acceptance = load_json(BASE_ACCEPTANCE_PATH)
    carrier = load_json(CARRIER_RESULT_PATH)
    base = _base_evaluation()
    domain = _domain_seed_diagnostics()
    carrier_seed = carrier["per_seed"]
    risk_metrics: dict[str, float | int] = {
        "carrier.ook.seed_min_valid_count_12_db": min(item["ook_valid_count"] for item in carrier_seed),
        "carrier.ook.seed_min_qualifying_frame_count_12_db": min(item["ook_qualifying_frame_count"] for item in carrier_seed),
        "carrier.ook.seed_min_all_frames_qualified_count_12_db": min(item["ook_all_frames_qualified_count"] for item in carrier_seed),
        "carrier.nonapplicable.seed_max_false_valid_count_12_db": max(item["nonapplicable_false_valid_count"] for item in carrier_seed),
        "carrier.nonapplicable.aggregate_false_valid_count_12_db": sum(item["nonapplicable_false_valid_count"] for item in carrier_seed),
        "domain.ook.seed_min_correct_count_6_db": min(item["correct"] for item in domain),
        "domain.ook.seed_max_wrong_count_6_db": max(item["wrong"] for item in domain),
        "domain.ook.aggregate_wrong_count_6_db": sum(item["wrong"] for item in domain),
        "noise.center_false_valid_count": base["metrics"]["noise.center_false_valid_count"],
        "noise.carrier_false_valid_count": base["metrics"]["noise.carrier_false_valid_count"],
        "noise.obw_false_valid_count": base["metrics"]["noise.obw_false_valid_count"],
        "noise.power_false_valid_count": base["metrics"]["noise.power_false_valid_count"],
        "noise.snr_false_valid_count": base["metrics"]["noise.snr_false_valid_count"],
        "noise.domain_false_valid_count": base["metrics"]["noise.domain_false_valid_count"],
    }
    scoring = score_development(
        base["metrics"], risk_metrics, acceptance, base_acceptance,
    )
    common = load_json(DEVELOPMENT_PATH)["common"]
    base.update({
        "artifact_id": "phase04f3-open-development-results-v4",
        "role": "development-only",
        "status": scoring["status"],
        "population": {
            "seed_count": len(common["development_seeds"]),
            "trials_per_seed_per_family": common["trials_per_seed_per_family"],
            "total_trials_per_family": common["total_trials_per_family"],
            "noise_measurements": common["total_negative_control_measurements"],
            "frames_per_measurement": common["frames_per_measurement"],
        },
        "method_ids": F3ParameterEstimator.METHOD_IDS,
        "scoring": scoring,
        "risk_metrics": risk_metrics,
        "seed_diagnostics": {
            "carrier_12_db": carrier_seed,
            "ook_domain_6_db": domain,
        },
        "claim_boundary": "Yalnız sekiz açık F3 geliştirme seed'inin sonucudur; binding, OOS, canlı RF veya ürün kabulü değildir.",
    })
    return base
