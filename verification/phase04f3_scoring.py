"""Executable pre-method scoring contract for PHASE-04-F3."""

from __future__ import annotations

import math
from typing import Any

from verification.phase04f2_scoring import (
    evaluate_check,
    score_population,
    validate_acceptance as validate_f2_acceptance,
)


REQUIRED_DEVELOPMENT_CHECKS: tuple[tuple[str, str, str, str, float | int], ...] = (
    ("ook-carrier-seed-valid", "carrier_line_frequency", "carrier.ook.seed_min_valid_count_12_db", ">=", 45),
    ("ook-carrier-seed-frame-support", "carrier_line_frequency", "carrier.ook.seed_min_qualifying_frame_count_12_db", ">=", 180),
    ("ook-carrier-seed-full-support", "carrier_line_frequency", "carrier.ook.seed_min_all_frames_qualified_count_12_db", ">=", 42),
    ("carrier-nonapplicable-seed-false-valid", "carrier_line_frequency", "carrier.nonapplicable.seed_max_false_valid_count_12_db", "<=", 1),
    ("carrier-nonapplicable-aggregate-false-valid", "carrier_line_frequency", "carrier.nonapplicable.aggregate_false_valid_count_12_db", "<=", 2),
    ("ook-domain-seed-correct", "signal_domain", "domain.ook.seed_min_correct_count_6_db", ">=", 40),
    ("ook-domain-seed-wrong", "signal_domain", "domain.ook.seed_max_wrong_count_6_db", "<=", 1),
    ("ook-domain-aggregate-wrong", "signal_domain", "domain.ook.aggregate_wrong_count_6_db", "<=", 2),
    ("development-noise-center-false-valid", "emission_center_frequency", "noise.center_false_valid_count", "<=", 0),
    ("development-noise-carrier-false-valid", "carrier_line_frequency", "noise.carrier_false_valid_count", "<=", 0),
    ("development-noise-obw-false-valid", "occupied_bandwidth", "noise.obw_false_valid_count", "<=", 0),
    ("development-noise-power-false-valid", "uncalibrated_channel_power_dbfs", "noise.power_false_valid_count", "<=", 0),
    ("development-noise-snr-false-valid", "snr_estimate_db", "noise.snr_false_valid_count", "<=", 0),
    ("development-noise-domain-false-valid", "signal_domain", "noise.domain_false_valid_count", "<=", 0),
)


def _violation(check: dict[str, Any]) -> float | int:
    threshold = check["threshold"]
    delta: float | int = 1 if isinstance(threshold, int) else max(abs(float(threshold)) * 1.0e-9, 1.0e-12)
    return threshold - delta if check["operator"] == ">=" else threshold + delta


def validate_acceptance(document: dict[str, Any], base_acceptance: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    base = validate_f2_acceptance(base_acceptance)
    if base["status"] != "passed" or base["check_counts"] != {"binding": 40, "oos": 24}:
        problems.append("F2 base acceptance is incomplete")
    reference = document.get("base_acceptance", {})
    if reference.get("path") != "datasets/fixtures/phase04f2/acceptance-gates.json":
        problems.append("F2 base acceptance path differs")
    if reference.get("binding_check_count") != 40 or reference.get("oos_check_count") != 24:
        problems.append("F2 base acceptance counts differ")
    if document.get("authority", {}).get("f2_acceptance_thresholds_relaxed") is not False:
        problems.append("F2 threshold relaxation must be false")

    population = document.get("development_population_contract", {})
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
    if population != expected_population:
        problems.append("development population contract differs")

    expected_checks = [
        {"id": identifier, "owner": owner, "metric": metric, "operator": operator, "threshold": threshold}
        for identifier, owner, metric, operator, threshold in REQUIRED_DEVELOPMENT_CHECKS
    ]
    checks = document.get("development_checks", [])
    if checks != expected_checks:
        problems.append("development checks differ from executable contract")
    else:
        for check in checks:
            threshold = check["threshold"]
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
                problems.append(f"{check['id']}: invalid threshold")
            elif not evaluate_check(threshold, check) or evaluate_check(_violation(check), check):
                problems.append(f"{check['id']}: boundary exercise failed")

    runtime = document.get("runtime_constraints", {})
    if runtime != {
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
        "development_check_count": len(checks),
    }


def score_development(
    base_metrics: dict[str, float | int],
    risk_metrics: dict[str, float | int],
    document: dict[str, Any],
    base_acceptance: dict[str, Any],
) -> dict[str, Any]:
    validation = validate_acceptance(document, base_acceptance)
    if validation["status"] != "passed":
        raise ValueError(f"invalid F3 acceptance contract: {validation['problems']}")
    checks = document["development_checks"]
    expected = {check["metric"] for check in checks}
    if set(risk_metrics) != expected:
        missing = sorted(expected - set(risk_metrics))
        extra = sorted(set(risk_metrics) - expected)
        raise ValueError(f"risk metric coverage mismatch; missing={missing}; extra={extra}")
    base_scoring = score_population(base_metrics, base_acceptance, "binding")
    risk_evaluations = [
        {
            "id": check["id"],
            "owner": check["owner"],
            "metric": check["metric"],
            "actual": risk_metrics[check["metric"]],
            "operator": check["operator"],
            "threshold": check["threshold"],
            "status": "passed" if evaluate_check(risk_metrics[check["metric"]], check) else "failed",
        }
        for check in checks
    ]
    passed = base_scoring["status"] == "passed" and all(item["status"] == "passed" for item in risk_evaluations)
    return {
        "role": "development",
        "status": "passed" if passed else "failed",
        "base_scoring": base_scoring,
        "risk_checks": risk_evaluations,
    }
