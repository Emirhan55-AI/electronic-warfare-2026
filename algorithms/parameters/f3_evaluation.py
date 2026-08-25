"""Locked-population orchestration for PHASE-04-F3 binding and OOS runs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from verification.phase04f2_scoring import score_population

from . import f2_development
from .f3_estimator import F3ParameterEstimator
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"


def _population_catalog(role: str, seed: int, acceptance: dict[str, Any]) -> dict[str, Any]:
    catalog = deepcopy(load_json(DEVELOPMENT_PATH))
    population = acceptance["population_contract"][role]
    trials = int(population["trials_per_family"])
    noise = int(population["noise_measurements"])
    catalog["role"] = role
    catalog["catalog_id"] = f"phase04f3-{role}-population-v1"
    catalog["common"].update({
        "development_seeds": [int(seed)],
        "trials_per_seed_per_family": trials,
        "total_trials_per_family": trials,
        "negative_control_measurements_per_seed": noise,
        "total_negative_control_measurements": noise,
    })
    catalog["claim_boundary"] = "Kilitli değerlendirme popülasyonudur; runtime ground-truth girdisi değildir."
    return catalog


def _oos_metrics(result: dict[str, Any], acceptance: dict[str, Any]) -> dict[str, float | int]:
    metrics = result["metrics"]
    families = result["families"]
    catalog = load_json(DEVELOPMENT_PATH)
    trials = int(acceptance["population_contract"]["oos"]["trials_per_family"])
    applicable = [str(item["id"]) for item in catalog["families"] if item["carrier_line_applicable"]]
    nonapplicable_count = sum(not item["carrier_line_applicable"] for item in catalog["families"]) * trials
    nonambiguous = [str(item["id"]) for item in catalog["families"] if item["domain"] != "Belirsiz"]
    main = "12.0"
    low = "-6.0"
    domain_conditions = ("6.0", "12.0")
    return {
        "center.family_min_valid_count": min(item[main]["center_valid_count"] for item in families.values()),
        "center.global_q95_error_bins": metrics["center.global_q95_error_bins"],
        "noise.center_false_valid_count": metrics["noise.center_false_valid_count"],
        "carrier.family_min_valid_count": min(families[name][main]["carrier_valid_count"] for name in applicable),
        "carrier.global_q95_error_bins": metrics["carrier.family_max_q95_error_bins"],
        "carrier.false_carrier_count": round(metrics["carrier.false_carrier_rate"] * nonapplicable_count),
        "carrier.family_min_low_snr_abstention_count": min(
            families[name][low]["trial_count"] - families[name][low]["carrier_valid_count"]
            for name in applicable
        ),
        "noise.carrier_false_valid_count": metrics["noise.carrier_false_valid_count"],
        "obw.family_min_valid_count": min(item[main]["obw_valid_count"] for item in families.values()),
        "obw.global_relative_q95": metrics["obw.global_relative_q95"],
        "obw.global_lower_edge_q95_bins": metrics["obw.global_lower_edge_q95_bins"],
        "obw.global_upper_edge_q95_bins": metrics["obw.global_upper_edge_q95_bins"],
        "obw.clipping_count": metrics["obw.clipping_count"],
        "noise.obw_false_valid_count": metrics["noise.obw_false_valid_count"],
        "span.edge_difference_q95_bins": metrics["span.edge_difference_q95_bins"],
        "power.family_min_valid_count": min(item[main]["power_valid_count"] for item in families.values()),
        "power.global_q95_error_db": metrics["power.global_q95_error_db"],
        "noise.power_false_valid_count": metrics["noise.power_false_valid_count"],
        "snr.family_min_valid_count": min(item[main]["snr_valid_count"] for item in families.values()),
        "snr.global_q95_error_db": metrics["snr.global_q95_error_db"],
        "noise.snr_false_valid_count": metrics["noise.snr_false_valid_count"],
        "domain.family_min_correct_count": min(
            families[name][condition]["domain_correct_count"]
            for name in nonambiguous for condition in domain_conditions
        ),
        "domain.family_max_wrong_count": max(
            families[name][condition]["domain_wrong_count"]
            for name in nonambiguous for condition in domain_conditions
        ),
        "noise.domain_false_valid_count": metrics["noise.domain_false_valid_count"],
    }


def evaluate_population(role: str, seed: int) -> dict[str, Any]:
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    acceptance = load_json(BASE_ACCEPTANCE_PATH)
    population = _population_catalog(role, seed, acceptance)
    original_loader = f2_development.load_json
    original_estimator = f2_development.F2ParameterEstimator

    def locked_loader(path: Path) -> dict[str, Any]:
        if path == f2_development.DEVELOPMENT_PATH:
            return population
        return original_loader(path)

    f2_development.load_json = locked_loader
    f2_development.F2ParameterEstimator = F3ParameterEstimator
    try:
        result = f2_development.evaluate_development()
    finally:
        f2_development.load_json = original_loader
        f2_development.F2ParameterEstimator = original_estimator

    metrics = result["metrics"] if role == "binding" else _oos_metrics(result, acceptance)
    scoring = score_population(metrics, acceptance, role)
    result.update({
        "artifact_id": f"phase04f3-{role}-results-v1",
        "role": role,
        "status": scoring["status"],
        "population": {
            "trials_per_family": acceptance["population_contract"][role]["trials_per_family"],
            "noise_measurements": acceptance["population_contract"][role]["noise_measurements"],
            "frames_per_measurement": acceptance["population_contract"][role]["frames_per_measurement"],
        },
        "method_ids": F3ParameterEstimator.METHOD_IDS,
        "metrics": metrics,
        "scoring": scoring,
        "claim_boundary": "Tek seferlik kilitli değerlendirme sonucudur; canlı RF veya ürün entegrasyonu değildir.",
    })
    return result


def compare_results(binding: dict[str, Any], oos: dict[str, Any]) -> dict[str, Any]:
    fields = tuple(binding["scoring"]["field_decisions"])
    decisions = [
        {
            "field": field,
            "binding": binding["scoring"]["field_decisions"][field],
            "oos": oos["scoring"]["field_decisions"][field],
            "status": "passed"
            if binding["scoring"]["field_decisions"][field] == "passed"
            and oos["scoring"]["field_decisions"][field] == "passed"
            else "failed",
        }
        for field in fields
    ]
    return {
        "schema_version": 1,
        "comparison_id": "phase04f3-locked-binding-oos-v1",
        "status": "passed" if all(item["status"] == "passed" for item in decisions) else "failed",
        "field_decisions": decisions,
        "claim_boundary": "Binding ve OOS birlikte geçmeden hiçbir alan ürün profiline alınmaz.",
    }
