"""Executable pre-method scoring contract for PHASE-04-F4."""

from __future__ import annotations

import math
from typing import Any

from verification.phase04f2_scoring import evaluate_check, score_population, validate_acceptance as validate_f2
from verification.phase04f3_scoring import REQUIRED_DEVELOPMENT_CHECKS, validate_acceptance as validate_f3


REQUIRED_ADDITIONAL_CHECKS: tuple[tuple[str, str, str, str, float | int], ...] = (
    ("nfm-domain-seed-correct", "signal_domain", "domain.nfm.seed_min_correct_count_6_db", ">=", 40),
    ("nfm-domain-seed-wrong", "signal_domain", "domain.nfm.seed_max_wrong_count_6_db", "<=", 1),
    ("nfm-domain-seed-abstained", "signal_domain", "domain.nfm.seed_max_abstained_count_6_db", "<=", 8),
    ("nfm-domain-aggregate-wrong", "signal_domain", "domain.nfm.aggregate_wrong_count_6_db", "<=", 2),
)
REQUIRED_DIAGNOSTICS = (
    "domain.nfm.seed_counts_6_db",
    "domain.nfm.rejection_reason_counts_6_db",
    "domain.nfm.distance_margin_quantiles_6_db",
)


def _violation(check: dict[str, Any]) -> float | int:
    threshold = check["threshold"]
    delta: float | int = 1 if isinstance(threshold, int) else max(abs(float(threshold)) * 1.0e-9, 1.0e-12)
    return threshold - delta if check["operator"] == ">=" else threshold + delta


def _expected_checks(specification: tuple[tuple[str, str, str, str, float | int], ...]) -> list[dict[str, Any]]:
    return [
        {"id": identifier, "owner": owner, "metric": metric, "operator": operator, "threshold": threshold}
        for identifier, owner, metric, operator, threshold in specification
    ]


def validate_acceptance(
    document: dict[str, Any],
    f3_acceptance: dict[str, Any],
    base_acceptance: dict[str, Any],
) -> dict[str, Any]:
    problems: list[str] = []
    base = validate_f2(base_acceptance)
    inherited = validate_f3(f3_acceptance, base_acceptance)
    if base["status"] != "passed" or base["check_counts"] != {"binding": 40, "oos": 24}:
        problems.append("F2 base acceptance is incomplete")
    if inherited["status"] != "passed" or inherited["development_check_count"] != 14:
        problems.append("F3 inherited acceptance is incomplete")
    if document.get("base_acceptance", {}).get("path") != "datasets/fixtures/phase04f2/acceptance-gates.json":
        problems.append("F2 base acceptance path differs")
    if document.get("inherited_development_acceptance", {}).get("path") != "datasets/fixtures/phase04f3/acceptance-gates.json":
        problems.append("F3 inherited acceptance path differs")
    authority = document.get("authority", {})
    if authority.get("f2_acceptance_thresholds_relaxed") is not False:
        problems.append("F2 threshold relaxation must be false")
    if authority.get("f3_development_thresholds_relaxed") is not False:
        problems.append("F3 threshold relaxation must be false")

    expected_population = {
        "seed_count": 8,
        "trials_per_seed_per_family": 48,
        "total_trials_per_family": 384,
        "negative_control_measurements_per_seed": 64,
        "total_negative_control_measurements": 512,
        "frames_per_measurement": 4,
        "snr_db": [-6.0, 0.0, 6.0, 12.0],
        "base_gate_role": "binding",
    }
    if document.get("development_population_contract") != expected_population:
        problems.append("development population contract differs")
    checks = document.get("additional_development_checks", [])
    if checks != _expected_checks(REQUIRED_ADDITIONAL_CHECKS):
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
        "base_check_counts": base["check_counts"],
        "inherited_development_check_count": inherited["development_check_count"],
        "additional_development_check_count": len(checks),
        "combined_development_check_count": inherited["development_check_count"] + len(checks),
        "required_diagnostic_count": len(document.get("required_development_diagnostics", [])),
    }


def score_development(
    base_metrics: dict[str, float | int],
    inherited_metrics: dict[str, float | int],
    additional_metrics: dict[str, float | int],
    document: dict[str, Any],
    f3_acceptance: dict[str, Any],
    base_acceptance: dict[str, Any],
) -> dict[str, Any]:
    validation = validate_acceptance(document, f3_acceptance, base_acceptance)
    if validation["status"] != "passed":
        raise ValueError(f"invalid F4 acceptance contract: {validation['problems']}")
    inherited_checks = f3_acceptance["development_checks"]
    additional_checks = document["additional_development_checks"]
    if set(inherited_metrics) != {check["metric"] for check in inherited_checks}:
        raise ValueError("inherited risk metric coverage mismatch")
    if set(additional_metrics) != {check["metric"] for check in additional_checks}:
        raise ValueError("additional risk metric coverage mismatch")
    base_scoring = score_population(base_metrics, base_acceptance, "binding")

    def evaluations(checks: list[dict[str, Any]], metrics: dict[str, float | int]) -> list[dict[str, Any]]:
        return [
            {
                "id": check["id"], "owner": check["owner"], "metric": check["metric"],
                "actual": metrics[check["metric"]], "operator": check["operator"],
                "threshold": check["threshold"],
                "status": "passed" if evaluate_check(metrics[check["metric"]], check) else "failed",
            }
            for check in checks
        ]

    inherited_evaluations = evaluations(inherited_checks, inherited_metrics)
    additional_evaluations = evaluations(additional_checks, additional_metrics)
    passed = (
        base_scoring["status"] == "passed"
        and all(item["status"] == "passed" for item in inherited_evaluations + additional_evaluations)
    )
    return {
        "role": "development",
        "status": "passed" if passed else "failed",
        "base_scoring": base_scoring,
        "inherited_risk_checks": inherited_evaluations,
        "additional_risk_checks": additional_evaluations,
    }
