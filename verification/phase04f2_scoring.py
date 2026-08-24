"""Algorithm-neutral executable scoring contract for PHASE-04-F2."""

from __future__ import annotations

import math
from typing import Any


VALID_OPERATORS = {">=", "<="}
POPULATION_KEYS = {"trials_per_family", "noise_measurements", "frames_per_measurement", "snr_db"}


def evaluate_check(actual: float | int, check: dict[str, Any]) -> bool:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(float(actual)):
        return False
    threshold = check["threshold"]
    if check["operator"] == ">=":
        return actual >= threshold
    if check["operator"] == "<=":
        return actual <= threshold
    raise ValueError(f"unsupported operator: {check['operator']}")


def _violation(check: dict[str, Any]) -> float | int:
    threshold = check["threshold"]
    delta: float | int = 1 if isinstance(threshold, int) else max(abs(float(threshold)) * 1.0e-9, 1.0e-12)
    return threshold - delta if check["operator"] == ">=" else threshold + delta


def validate_acceptance(document: dict[str, Any]) -> dict[str, Any]:
    fields = tuple(document["required_parameter_fields"])
    support = tuple(document["required_support_gates"])
    owners = set(fields + support)
    problems: list[str] = []
    coverage: dict[str, list[str]] = {}
    for role in ("binding", "oos"):
        population = document.get("population_contract", {}).get(role, {})
        if set(population) != POPULATION_KEYS:
            problems.append(f"{role}: population keys differ")
        if population.get("frames_per_measurement") != 4:
            problems.append(f"{role}: frames_per_measurement must be 4")
        checks = document.get("checks", {}).get(role, ())
        identifiers: set[str] = set()
        metrics: set[str] = set()
        role_owners: set[str] = set()
        for check in checks:
            identifier = check.get("id")
            metric = check.get("metric")
            owner = check.get("owner")
            operator = check.get("operator")
            threshold = check.get("threshold")
            if not isinstance(identifier, str) or identifier in identifiers:
                problems.append(f"{role}: duplicate or invalid check id")
                continue
            identifiers.add(identifier)
            if not isinstance(metric, str) or metric in metrics:
                problems.append(f"{role}.{identifier}: duplicate or invalid metric")
            else:
                metrics.add(metric)
            if owner not in owners:
                problems.append(f"{role}.{identifier}: unknown owner")
            else:
                role_owners.add(owner)
            if operator not in VALID_OPERATORS:
                problems.append(f"{role}.{identifier}: invalid operator")
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
                problems.append(f"{role}.{identifier}: invalid threshold")
                continue
            if not evaluate_check(threshold, check) or evaluate_check(_violation(check), check):
                problems.append(f"{role}.{identifier}: boundary exercise failed")
        if role_owners != owners:
            problems.append(f"{role}: owner coverage differs")
        noise_owners = {
            check["owner"]
            for check in checks
            if isinstance(check.get("metric"), str) and check["metric"].startswith("noise.")
        }
        if noise_owners != set(fields):
            problems.append(f"{role}: per-field noise coverage differs")
        if not any(check.get("metric") == "carrier.low_snr_abstention_rate" for check in checks) and role == "binding":
            problems.append("binding: carrier abstention gate missing")
        if not any(check.get("metric") == "carrier.family_min_low_snr_abstention_count" for check in checks) and role == "oos":
            problems.append("oos: carrier abstention gate missing")
        coverage[role] = sorted(metrics)
    return {
        "status": "passed" if not problems else "failed",
        "problems": problems,
        "coverage": coverage,
        "check_counts": {role: len(document["checks"][role]) for role in ("binding", "oos")},
    }


def score_population(metrics: dict[str, float | int], document: dict[str, Any], role: str) -> dict[str, Any]:
    if role not in {"binding", "oos"}:
        raise ValueError("role must be binding or oos")
    checks = document["checks"][role]
    expected = {check["metric"] for check in checks}
    if set(metrics) != expected:
        missing = sorted(expected - set(metrics))
        extra = sorted(set(metrics) - expected)
        raise ValueError(f"metric coverage mismatch; missing={missing}; extra={extra}")
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
    owners = tuple(document["required_parameter_fields"] + document["required_support_gates"])
    decisions = {
        owner: "passed"
        if all(item["status"] == "passed" for item in evaluations if item["owner"] == owner)
        else "failed"
        for owner in owners
    }
    passed = all(value == "passed" for value in decisions.values())
    return {
        "role": role,
        "status": "passed" if passed else "failed",
        "field_decisions": decisions,
        "checks": evaluations,
    }
