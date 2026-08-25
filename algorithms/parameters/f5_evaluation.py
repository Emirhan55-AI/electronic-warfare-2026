"""Locked-population orchestration for PHASE-04-F5 binding and OOS runs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from verification.phase04f2_scoring import score_population

from . import f2_development, f4_evaluation
from .f5_estimator import F5ParameterEstimator
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f5"
DEVELOPMENT_PATH = FIXTURES / "development-catalog.json"
BASE_ACCEPTANCE_PATH = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"


def _population_catalog(role: str, seed: int, acceptance: dict[str, Any]) -> dict[str, Any]:
    catalog = deepcopy(load_json(DEVELOPMENT_PATH))
    population = acceptance["population_contract"][role]
    trials = int(population["trials_per_family"])
    noise = int(population["noise_measurements"])
    catalog["role"] = role
    catalog["catalog_id"] = f"phase04f5-{role}-population-v1"
    catalog["common"].update({
        "development_seeds": [int(seed)],
        "trials_per_seed_per_family": trials,
        "total_trials_per_family": trials,
        "negative_control_measurements_per_seed": noise,
        "total_negative_control_measurements": noise,
    })
    catalog["claim_boundary"] = "Kilitli değerlendirme popülasyonudur; çalışma zamanı ground-truth girdisi değildir."
    return catalog


def _oos_metrics(result: dict[str, Any], acceptance: dict[str, Any]) -> dict[str, float | int]:
    original_path = f4_evaluation.DEVELOPMENT_PATH
    f4_evaluation.DEVELOPMENT_PATH = DEVELOPMENT_PATH
    try:
        return f4_evaluation._oos_metrics(result, acceptance)
    finally:
        f4_evaluation.DEVELOPMENT_PATH = original_path


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
    f2_development.F2ParameterEstimator = F5ParameterEstimator
    try:
        result = f2_development.evaluate_development()
    finally:
        f2_development.load_json = original_loader
        f2_development.F2ParameterEstimator = original_estimator

    metrics = result["metrics"] if role == "binding" else _oos_metrics(result, acceptance)
    scoring = score_population(metrics, acceptance, role)
    result.update({
        "artifact_id": f"phase04f5-{role}-results-v1",
        "role": role,
        "status": scoring["status"],
        "population": {
            "trials_per_family": acceptance["population_contract"][role]["trials_per_family"],
            "noise_measurements": acceptance["population_contract"][role]["noise_measurements"],
            "frames_per_measurement": acceptance["population_contract"][role]["frames_per_measurement"],
        },
        "method_ids": F5ParameterEstimator.METHOD_IDS,
        "metrics": metrics,
        "scoring": scoring,
        "claim_boundary": "Tek seferlik kilitli değerlendirme sonucudur; canlı RF, FPGA veya ürün entegrasyonu değildir.",
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
        "comparison_id": "phase04f5-locked-binding-oos-v1",
        "status": "passed" if all(item["status"] == "passed" for item in decisions) else "failed",
        "field_decisions": decisions,
        "claim_boundary": "Binding ve OOS birlikte geçmeden hiçbir alan ürün profiline alınmaz.",
    }
