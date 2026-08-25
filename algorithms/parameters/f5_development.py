"""Open-catalog development evaluation for the PHASE-04-F5 v6 estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from verification.phase04f4_scoring import score_development as score_f4_development
from verification.phase04f5_scoring import score_additional, validate_acceptance

from . import f4_development
from .f5_estimator import F5ParameterEstimator
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"
F4_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f4" / "acceptance-gates.json"
F3_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f3" / "acceptance-gates.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
CARRIER_RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "carrier-analysis-v6.json"
OBW_RESULT_PATH = ROOT / "results" / "evidence" / "phase04f5" / "obw-temporal-candidates-v6.json"


def _with_f5_catalog(function):
    original_path = f4_development.DEVELOPMENT_PATH
    original_estimator = f4_development.F4ParameterEstimator
    f4_development.DEVELOPMENT_PATH = DEVELOPMENT_PATH
    f4_development.F4ParameterEstimator = F5ParameterEstimator
    try:
        return function()
    finally:
        f4_development.DEVELOPMENT_PATH = original_path
        f4_development.F4ParameterEstimator = original_estimator


def _base_evaluation() -> dict[str, Any]:
    return _with_f5_catalog(f4_development._base_evaluation)


def _domain_seed_diagnostics() -> dict[str, Any]:
    return _with_f5_catalog(f4_development._domain_seed_diagnostics)


def _obw_evidence() -> tuple[dict[str, float | int], dict[str, Any], dict[str, Any]]:
    document = load_json(OBW_RESULT_PATH)
    selected = document.get("selected")
    if document.get("status") != "passed" or not isinstance(selected, dict):
        raise ValueError("F5 selected OBW development evidence is not passed")
    candidate = next(
        (
            item for item in document["candidates"]
            if item["tail_fraction"] == selected["tail_fraction"]
            and item["edge_expansion_bins"] == selected["edge_expansion_bins"]
            and item["temporal_range_maximum_bins"] == selected["temporal_range_maximum_bins"]
        ),
        None,
    )
    if candidate is None or candidate.get("status") != "passed":
        raise ValueError("F5 selected OBW candidate is missing")
    return candidate["metrics"], document["selected_diagnostics"], selected


def evaluate_development() -> dict[str, Any]:
    acceptance = load_json(ACCEPTANCE_PATH)
    f4_acceptance = load_json(F4_ACCEPTANCE_PATH)
    f3_acceptance = load_json(F3_ACCEPTANCE_PATH)
    base_acceptance = load_json(BASE_ACCEPTANCE_PATH)
    carrier = load_json(CARRIER_RESULT_PATH)
    base = _base_evaluation()
    domain = _domain_seed_diagnostics()
    obw_metrics, obw_diagnostics, selected = _obw_evidence()

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
    f4_metrics: dict[str, float | int] = {
        "domain.nfm.seed_min_correct_count_6_db": min(item["correct"] for item in nfm),
        "domain.nfm.seed_max_wrong_count_6_db": max(item["wrong"] for item in nfm),
        "domain.nfm.seed_max_abstained_count_6_db": max(item["abstained"] for item in nfm),
        "domain.nfm.aggregate_wrong_count_6_db": sum(item["wrong"] for item in nfm),
    }
    protocol = validate_acceptance(acceptance, f4_acceptance, f3_acceptance, base_acceptance)
    if protocol["status"] != "passed":
        raise ValueError(f"invalid F5 acceptance contract: {protocol['problems']}")
    inherited_scoring = score_f4_development(
        base["metrics"], inherited_metrics, f4_metrics,
        f4_acceptance, f3_acceptance, base_acceptance,
    )
    f5_scoring = score_additional(obw_metrics, acceptance)
    passed = inherited_scoring["status"] == "passed" and f5_scoring["status"] == "passed"
    common = load_json(DEVELOPMENT_PATH)["common"]
    base.update({
        "artifact_id": "phase04f5-open-development-results-v6",
        "role": "development-only",
        "status": "passed" if passed else "failed",
        "population": {
            "seed_count": len(common["development_seeds"]),
            "trials_per_seed_per_family": common["trials_per_seed_per_family"],
            "total_trials_per_family": common["total_trials_per_family"],
            "noise_measurements": common["total_negative_control_measurements"],
            "frames_per_measurement": common["frames_per_measurement"],
        },
        "method_ids": F5ParameterEstimator.METHOD_IDS,
        "scoring": {
            "role": "development",
            "status": "passed" if passed else "failed",
            "base_scoring": inherited_scoring["base_scoring"],
            "f3_inherited_risk_checks": inherited_scoring["inherited_risk_checks"],
            "f4_additional_risk_checks": inherited_scoring["additional_risk_checks"],
            "f5_additional_risk_checks": f5_scoring["checks"],
            "protocol_contract": protocol,
        },
        "inherited_risk_metrics": inherited_metrics,
        "f4_additional_risk_metrics": f4_metrics,
        "f5_additional_risk_metrics": obw_metrics,
        "selected_obw_calibration": selected,
        "diagnostics": {
            "domain.nfm.seed_counts_6_db": nfm,
            "domain.nfm.rejection_reason_counts_6_db": domain["nfm_rejection_reason_counts_6_db"],
            "domain.nfm.distance_margin_quantiles_6_db": domain["nfm_distance_margin_quantiles_6_db"],
            "domain.ook.seed_counts_6_db": ook,
            "carrier.seed_counts_12_db": carrier_seed,
            **obw_diagnostics,
        },
        "claim_boundary": "Yalnız sekiz açık F5 geliştirme seed'inin sonucudur; binding, OOS, canlı RF, FPGA veya ürün kabulü değildir.",
    })
    return base
