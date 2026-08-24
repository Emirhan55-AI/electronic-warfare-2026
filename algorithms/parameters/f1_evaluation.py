"""Locked-population orchestration for PHASE-04-F1 binding and OOS runs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from . import f1_development
from .operator_reference import load_json


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
DEVELOPMENT_PATH = FIXTURES / "development-scenes.json"
ACCEPTANCE_PATH = FIXTURES / "acceptance-gates.json"


def _oos_adapter_gates(oos: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """Express locked OOS counts through the locked development scorer interface."""
    trials = int(oos["trials_per_family"])
    adapted = deepcopy(binding)
    adapted["trials_per_family"] = trials
    adapted["noise_sequences"] = int(oos["noise_sequences"])
    adapted["noise_frames_per_sequence"] = int(oos["noise_frames_per_sequence"])

    for field in ("emission_center_frequency", "carrier_line_frequency"):
        minimum = float(oos[field]["family_valid_count_minimum"]) / trials
        adapted[field]["family_valid_minimum"] = minimum
        adapted[field]["global_valid_minimum"] = minimum
        adapted[field]["q95_error_bins_maximum"] = float(oos[field]["q95_error_bins_maximum"])
    adapted["carrier_line_frequency"]["false_carrier_rate_maximum"] = (
        float(oos["carrier_line_frequency"]["false_carrier_count_maximum"]) / trials
    )
    adapted["carrier_line_frequency"]["abstention_rate_minimum"] = 0.0

    obw_minimum = float(oos["occupied_bandwidth"]["family_valid_count_minimum"]) / trials
    adapted["occupied_bandwidth"].update({
        "family_valid_minimum": obw_minimum,
        "global_valid_minimum": obw_minimum,
        "relative_q95_maximum": float(oos["occupied_bandwidth"]["relative_q95_maximum"]),
        "edge_q95_bins_maximum": float(oos["occupied_bandwidth"]["edge_q95_bins_maximum"]),
        "clipping_count_maximum": int(oos["occupied_bandwidth"]["clipping_count_maximum"]),
        "temporal_q95_bins_maximum": 1.0e9,
    })
    adapted["span_robustness"]["edge_difference_q95_bins_maximum"] = float(
        oos["span_robustness"]["edge_difference_q95_bins_maximum"]
    )

    for field, error_key in (
        ("uncalibrated_channel_power_dbfs", "q95_error_db_maximum"),
        ("snr_estimate_db", "q95_error_db_maximum"),
    ):
        minimum = float(oos[field]["family_valid_count_minimum"]) / trials
        adapted[field]["family_valid_minimum"] = minimum
        adapted[field]["global_valid_minimum"] = minimum
        adapted[field][error_key] = float(oos[field][error_key])
        adapted[field]["zero_snr_median_error_db_maximum"] = 1.0e9

    domain = adapted["signal_domain"]
    domain["family_correct_definite_minimum"] = float(
        oos["signal_domain"]["family_correct_count_minimum"]
    ) / trials
    domain["global_correct_definite_minimum"] = domain["family_correct_definite_minimum"]
    domain["family_wrong_definite_maximum"] = float(oos["signal_domain"]["wrong_count_maximum"]) / trials
    domain["global_wrong_definite_maximum"] = domain["family_wrong_definite_maximum"]
    domain["ambiguous_rejection_minimum"] = 0.0
    domain["zero_snr_wrong_definite_maximum"] = 1.0
    domain["low_snr_abstention_minimum"] = 0.0
    domain["noise_definite_count_maximum"] = int(oos["signal_domain"]["noise_definite_count_maximum"])
    adapted["noise_numeric_false_valid_count_maximum"] = int(oos["noise_numeric_false_valid_count_maximum"])
    return adapted


def _population_catalog(role: str, seed: int, trials: int) -> dict[str, Any]:
    catalog = deepcopy(load_json(DEVELOPMENT_PATH))
    catalog["role"] = role
    catalog["catalog_id"] = f"phase04f1-{role}-population-v1"
    catalog["common"]["base_seed"] = int(seed)
    catalog["common"]["trials_per_family"] = int(trials)
    catalog["claim_boundary"] = "Kilitli değerlendirme popülasyonudur; runtime ground truth girdisi değildir."
    return catalog


def evaluate_population(role: str, seed: int) -> dict[str, Any]:
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    acceptance = load_json(ACCEPTANCE_PATH)
    original_gates = acceptance[role]
    scorer_gates = (
        original_gates
        if role == "binding"
        else _oos_adapter_gates(original_gates, acceptance["binding"])
    )
    population = _population_catalog(role, seed, int(original_gates["trials_per_family"]))
    scorer_acceptance = {"binding": scorer_gates}

    original_loader = f1_development.load_json

    def locked_loader(path: Path) -> dict[str, Any]:
        if path == f1_development.DEVELOPMENT_PATH:
            return population
        if path == f1_development.ACCEPTANCE_PATH:
            return scorer_acceptance
        return original_loader(path)

    f1_development.load_json = locked_loader
    try:
        result = f1_development.evaluate_development()
    finally:
        f1_development.load_json = original_loader

    result["artifact_id"] = f"phase04f1-{role}-results-v1"
    result["role"] = role
    result["population_trial_count"] = int(original_gates["trials_per_family"])
    result["gate_semantics"] = "locked-binding-rates" if role == "binding" else "locked-oos-counts-adapted-to-identical-scorer"
    result["claim_boundary"] = "Tek seferlik kilitli değerlendirme sonucudur; canlı RF veya ürün entegrasyonu değildir."
    return result


def compare_results(binding: dict[str, Any], oos: dict[str, Any]) -> dict[str, Any]:
    fields = tuple(binding["field_decisions"])
    decisions = [
        {
            "field": field,
            "binding": binding["field_decisions"][field],
            "oos": oos["field_decisions"][field],
            "status": "passed"
            if binding["field_decisions"][field] == "passed" and oos["field_decisions"][field] == "passed"
            else "failed",
        }
        for field in fields
    ]
    passed = all(item["status"] == "passed" for item in decisions)
    return {
        "schema_version": 1,
        "comparison_id": "phase04f1-locked-binding-oos-v1",
        "status": "passed" if passed else "failed",
        "field_decisions": decisions,
        "claim_boundary": "Binding ve OOS birlikte geçmeden hiçbir alan ürün profiline alınmaz.",
    }
