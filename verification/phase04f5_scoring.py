"""Executable pre-method scoring contract for PHASE-04-F5."""

from __future__ import annotations

import math
from typing import Any

from verification.phase04f2_scoring import evaluate_check
from verification.phase04f4_scoring import validate_acceptance as validate_f4


REQUIRED_ADDITIONAL_CHECKS: tuple[tuple[str, str, str, str, float | int], ...] = (
    ("obw-family-valid", "occupied_bandwidth", "obw.family_min_valid_count_12_db", ">=", 379),
    ("obw-seed-valid", "occupied_bandwidth", "obw.seed_min_valid_count_12_db", ">=", 47),
    ("obw-family-wilson-lower", "occupied_bandwidth", "obw.family_min_wilson_lower_95_12_db", ">=", 0.96875),
    ("obw-family-relative-q95", "occupied_bandwidth", "obw.family_max_relative_q95_12_db", "<=", 0.2),
    ("obw-family-lower-edge-q95", "occupied_bandwidth", "obw.family_max_lower_edge_q95_bins_12_db", "<=", 2.0),
    ("obw-family-upper-edge-q95", "occupied_bandwidth", "obw.family_max_upper_edge_q95_bins_12_db", "<=", 2.0),
    ("obw-family-temporal-rejection", "occupied_bandwidth", "obw.family_max_temporal_rejection_count_12_db", "<=", 5),
)
REQUIRED_DIAGNOSTICS = (
    "obw.seed_counts_12_db",
    "obw.rejection_reason_counts_12_db",
    "obw.temporal_range_quantiles_12_db",
    "obw.recovery_attempt_counts_12_db",
    "obw.recovery_outcome_counts_12_db",
    "obw.invalid_trial_diagnostics_12_db",
)


def _expected_checks() -> list[dict[str, Any]]:
    return [
        {"id": identifier, "owner": owner, "metric": metric, "operator": operator, "threshold": threshold}
        for identifier, owner, metric, operator, threshold in REQUIRED_ADDITIONAL_CHECKS
    ]


def _violation(check: dict[str, Any]) -> float | int:
    threshold = check["threshold"]
    delta: float | int = 1 if isinstance(threshold, int) else max(abs(float(threshold)) * 1.0e-9, 1.0e-12)
    return threshold - delta if check["operator"] == ">=" else threshold + delta


def validate_acceptance(
    document: dict[str, Any],
    f4_acceptance: dict[str, Any],
    f3_acceptance: dict[str, Any],
    base_acceptance: dict[str, Any],
) -> dict[str, Any]:
    problems: list[str] = []
    inherited = validate_f4(f4_acceptance, f3_acceptance, base_acceptance)
    if inherited["status"] != "passed" or inherited["combined_development_check_count"] != 18:
        problems.append("F4 inherited acceptance is incomplete")
    expected_paths = {
        "base_acceptance": "datasets/fixtures/phase04f2/acceptance-gates.json",
        "f3_development_acceptance": "datasets/fixtures/phase04f3/acceptance-gates.json",
        "f4_development_acceptance": "datasets/fixtures/phase04f4/acceptance-gates.json",
        "f5a_analysis": "results/evidence/phase04f5/f5a-analysis.json",
    }
    for key, path in expected_paths.items():
        if document.get(key, {}).get("path") != path:
            problems.append(f"{key} path differs")
    authority = document.get("authority", {})
    for key in (
        "f2_acceptance_thresholds_relaxed",
        "f3_development_thresholds_relaxed",
        "f4_development_thresholds_relaxed",
    ):
        if authority.get(key) is not False:
            problems.append(f"{key} must be false")
    if document.get("development_population_contract") != {
        "seed_count": 8,
        "trials_per_seed_per_family": 48,
        "total_trials_per_family": 384,
        "negative_control_measurements_per_seed": 64,
        "total_negative_control_measurements": 512,
        "frames_per_measurement": 4,
        "snr_db": [-6.0, 0.0, 6.0, 12.0],
        "base_gate_role": "binding",
    }:
        problems.append("development population contract differs")
    checks = document.get("additional_development_checks", [])
    if checks != _expected_checks():
        problems.append("additional development checks differ")
    else:
        for check in checks:
            threshold = check["threshold"]
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
                problems.append(f"{check['id']}: invalid threshold")
            elif not evaluate_check(threshold, check) or evaluate_check(_violation(check), check):
                problems.append(f"{check['id']}: boundary exercise failed")
    if document.get("required_development_diagnostics") != list(REQUIRED_DIAGNOSTICS):
        problems.append("required diagnostics differ")
    if document.get("runtime_constraints") != {
        "runtime_ground_truth_allowed": False,
        "frames_per_measurement": 4,
        "worker_count": 1,
        "maximum_pending_intent_count": 1,
        "maximum_persistent_payload_bytes": 65536,
    }:
        problems.append("runtime constraints differ")
    return {
        "status": "passed" if not problems else "failed",
        "problems": problems,
        "base_check_counts": inherited["base_check_counts"],
        "f3_development_check_count": inherited["inherited_development_check_count"],
        "f4_additional_development_check_count": inherited["additional_development_check_count"],
        "inherited_combined_development_check_count": inherited["combined_development_check_count"],
        "f5_additional_development_check_count": len(checks),
        "combined_development_check_count": inherited["combined_development_check_count"] + len(checks),
        "required_diagnostic_count": len(document.get("required_development_diagnostics", [])),
    }


def score_additional(metrics: dict[str, float | int], document: dict[str, Any]) -> dict[str, Any]:
    checks = document["additional_development_checks"]
    if set(metrics) != {item["metric"] for item in checks}:
        raise ValueError("F5 additional risk metric coverage mismatch")
    evaluations = [
        {
            "id": check["id"],
            "owner": check["owner"],
            "metric": check["metric"],
            "actual": metrics[check["metric"]],
            "operator": check["operator"],
            "threshold": check["threshold"],
            "status": "passed" if evaluate_check(metrics[check["metric"]], check) else "failed",
        }
        for check in checks
    ]
    return {
        "status": "passed" if all(item["status"] == "passed" for item in evaluations) else "failed",
        "checks": evaluations,
    }
