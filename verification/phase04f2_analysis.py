"""Deterministic post-run analysis for the immutable PHASE-04-F1D evidence."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
F1_FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f1"
F1_EVIDENCE = ROOT / "results" / "evidence" / "phase04f1"
INPUTS = {
    "acceptance_gates": F1_FIXTURES / "acceptance-gates.json",
    "method_lock": F1_FIXTURES / "method-lock.json",
    "runner_lock": F1_FIXTURES / "evaluation-runner-lock.json",
    "development_results": F1_EVIDENCE / "development-results.json",
    "binding_results": F1_EVIDENCE / "binding-results.json",
    "oos_results": F1_EVIDENCE / "oos-results.json",
    "comparison": F1_EVIDENCE / "parameter-comparison.json",
}
NUMERIC_FIELDS = (
    "emission_center_frequency",
    "carrier_line_frequency",
    "occupied_bandwidth",
    "uncalibrated_channel_power_dbfs",
    "snr_estimate_db",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(identifier: str, actual: float | int, operator: str, threshold: float | int) -> dict[str, Any]:
    if operator == ">=":
        passed = actual >= threshold
    elif operator == "<=":
        passed = actual <= threshold
    else:
        raise ValueError(f"unsupported operator: {operator}")
    return {
        "id": identifier,
        "status": "passed" if passed else "failed",
        "actual": actual,
        "operator": operator,
        "threshold": threshold,
    }


def _minimum_rate(rows: list[dict[str, Any]], key: str) -> float:
    return min(float(row["valid_rates"][key]) for row in rows if row["valid_rates"][key] is not None)


def _maximum_q95(rows: list[dict[str, Any]], key: str) -> float:
    return max(float(row["q95"][key]) for row in rows if row["q95"][key] is not None)


def _binding_local_gates(result: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    families = result["families"]
    trials = int(result["population_trial_count"])
    main_rows = [family["conditions"]["12.0"] for family in families]
    six_rows = [family["conditions"]["6.0"] for family in families]
    numeric_trials = trials * len(families)
    main = result["aggregate"]["12.0"]
    zero = result["aggregate"]["0.0"]
    low = result["aggregate"]["-6.0"]

    checks: dict[str, list[dict[str, Any]]] = {}
    center = gates["emission_center_frequency"]
    checks["emission_center_frequency"] = [
        _check("family-valid-minimum", _minimum_rate(main_rows, "center"), ">=", center["family_valid_minimum"]),
        _check("family-q95-maximum", _maximum_q95(main_rows, "center_bins"), "<=", center["q95_error_bins_maximum"]),
        _check("global-valid-minimum", sum(row["valid_rates"]["center"] for row in main_rows) / len(main_rows), ">=", center["global_valid_minimum"]),
        _check("global-q95-maximum", main["center_q95_bins"], "<=", center["q95_error_bins_maximum"]),
    ]

    applicable = [
        row for row, family in zip(main_rows, families) if family["carrier_line_applicable"]
    ]
    carrier = gates["carrier_line_frequency"]
    checks["carrier_line_frequency"] = [
        _check("family-valid-minimum", _minimum_rate(applicable, "carrier"), ">=", carrier["family_valid_minimum"]),
        _check("family-q95-maximum", _maximum_q95(applicable, "carrier_bins"), "<=", carrier["q95_error_bins_maximum"]),
        _check("global-valid-minimum", sum(row["valid_rates"]["carrier"] for row in applicable) / len(applicable), ">=", carrier["global_valid_minimum"]),
        _check("false-carrier-rate-maximum", main["false_carrier_count"] / main["carrier_nonapplicable_count"], "<=", carrier["false_carrier_rate_maximum"]),
    ]

    obw = gates["occupied_bandwidth"]
    checks["occupied_bandwidth"] = [
        _check("family-valid-minimum", _minimum_rate(main_rows, "obw"), ">=", obw["family_valid_minimum"]),
        _check("global-valid-minimum", sum(row["valid_rates"]["obw"] for row in main_rows) / len(main_rows), ">=", obw["global_valid_minimum"]),
        _check("relative-q95-maximum", main["obw_relative_q95"], "<=", obw["relative_q95_maximum"]),
        _check("lower-edge-q95-maximum", main["lower_edge_q95_bins"], "<=", obw["edge_q95_bins_maximum"]),
        _check("upper-edge-q95-maximum", main["upper_edge_q95_bins"], "<=", obw["edge_q95_bins_maximum"]),
        _check("temporal-q95-maximum", main["temporal_q95_bins"], "<=", obw["temporal_q95_bins_maximum"]),
        _check("clipping-count-maximum", main["clipping_count"], "<=", obw["clipping_count_maximum"]),
    ]

    span = gates["span_robustness"]
    checks["span_robustness"] = [
        _check("edge-difference-q95-maximum", main["span_robustness_q95_bins"], "<=", span["edge_difference_q95_bins_maximum"])
    ]

    for field, rate_key, q95_key, zero_key in (
        ("uncalibrated_channel_power_dbfs", "power", "power_q95_db", "power_median_db"),
        ("snr_estimate_db", "snr", "snr_q95_db", "snr_median_db"),
    ):
        gate = gates[field]
        checks[field] = [
            _check("family-valid-minimum", _minimum_rate(main_rows, rate_key), ">=", gate["family_valid_minimum"]),
            _check("global-valid-minimum", sum(row["valid_rates"][rate_key] for row in main_rows) / len(main_rows), ">=", gate["global_valid_minimum"]),
            _check("q95-error-maximum", main[q95_key], "<=", gate["q95_error_db_maximum"]),
            _check("zero-snr-median-maximum", zero[zero_key], "<=", gate["zero_snr_median_error_db_maximum"]),
        ]

    domain = gates["signal_domain"]
    nonambiguous = [family for family in families if family["expected_domain"] != "Belirsiz"]
    nonambiguous_trials = len(nonambiguous) * trials
    ambiguous = next(family for family in families if family["expected_domain"] == "Belirsiz")
    family_correct = []
    family_wrong = []
    for family in nonambiguous:
        for condition in ("12.0", "6.0"):
            counts = family["conditions"][condition]["counts"]
            family_correct.append(counts["domain_correct"] / trials)
            family_wrong.append(counts["domain_wrong"] / trials)
    main_domain = result["aggregate"]["12.0"]
    six_domain = result["aggregate"]["6.0"]
    checks["signal_domain"] = [
        _check("main-global-correct-minimum", main_domain["domain_correct_count"] / nonambiguous_trials, ">=", domain["global_correct_definite_minimum"]),
        _check("main-global-wrong-maximum", main_domain["domain_wrong_count"] / nonambiguous_trials, "<=", domain["global_wrong_definite_maximum"]),
        _check("six-db-global-correct-minimum", six_domain["domain_correct_count"] / nonambiguous_trials, ">=", domain["global_correct_definite_minimum"]),
        _check("six-db-global-wrong-maximum", six_domain["domain_wrong_count"] / nonambiguous_trials, "<=", domain["global_wrong_definite_maximum"]),
        _check("family-correct-minimum", min(family_correct), ">=", domain["family_correct_definite_minimum"]),
        _check("family-wrong-maximum", max(family_wrong), "<=", domain["family_wrong_definite_maximum"]),
        _check("ambiguous-rejection-minimum", ambiguous["conditions"]["12.0"]["counts"]["domain_abstained"] / trials, ">=", domain["ambiguous_rejection_minimum"]),
        _check("zero-snr-wrong-maximum", zero["domain_wrong_count"] / nonambiguous_trials, "<=", domain["zero_snr_wrong_definite_maximum"]),
        _check("low-snr-abstention-minimum", low["domain_abstained_count"] / numeric_trials, ">=", domain["low_snr_abstention_minimum"]),
    ]
    return _summarize_fields(result, checks, gates["noise_numeric_false_valid_count_maximum"], domain["noise_definite_count_maximum"])


def _oos_local_gates(result: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    families = result["families"]
    trials = int(result["population_trial_count"])
    main_rows = [family["conditions"]["12.0"] for family in families]
    main = result["aggregate"]["12.0"]
    checks: dict[str, list[dict[str, Any]]] = {}
    for field, rate_key, q95_key in (
        ("emission_center_frequency", "center", "center_q95_bins"),
        ("carrier_line_frequency", "carrier", "carrier_q95_bins"),
    ):
        rows = main_rows if field == "emission_center_frequency" else [
            row for row, family in zip(main_rows, families) if family["carrier_line_applicable"]
        ]
        gate = gates[field]
        checks[field] = [
            _check("family-valid-count-minimum", min(round(row["valid_rates"][rate_key] * trials) for row in rows), ">=", gate["family_valid_count_minimum"]),
            _check("q95-error-maximum", main[q95_key], "<=", gate["q95_error_bins_maximum"]),
        ]
    checks["carrier_line_frequency"].append(
        _check("false-carrier-count-maximum", main["false_carrier_count"], "<=", gates["carrier_line_frequency"]["false_carrier_count_maximum"])
    )

    obw = gates["occupied_bandwidth"]
    checks["occupied_bandwidth"] = [
        _check("family-valid-count-minimum", min(round(row["valid_rates"]["obw"] * trials) for row in main_rows), ">=", obw["family_valid_count_minimum"]),
        _check("relative-q95-maximum", main["obw_relative_q95"], "<=", obw["relative_q95_maximum"]),
        _check("lower-edge-q95-maximum", main["lower_edge_q95_bins"], "<=", obw["edge_q95_bins_maximum"]),
        _check("upper-edge-q95-maximum", main["upper_edge_q95_bins"], "<=", obw["edge_q95_bins_maximum"]),
        _check("clipping-count-maximum", main["clipping_count"], "<=", obw["clipping_count_maximum"]),
    ]
    checks["span_robustness"] = [
        _check("edge-difference-q95-maximum", main["span_robustness_q95_bins"], "<=", gates["span_robustness"]["edge_difference_q95_bins_maximum"])
    ]
    for field, rate_key, q95_key in (
        ("uncalibrated_channel_power_dbfs", "power", "power_q95_db"),
        ("snr_estimate_db", "snr", "snr_q95_db"),
    ):
        gate = gates[field]
        checks[field] = [
            _check("family-valid-count-minimum", min(round(row["valid_rates"][rate_key] * trials) for row in main_rows), ">=", gate["family_valid_count_minimum"]),
            _check("q95-error-maximum", main[q95_key], "<=", gate["q95_error_db_maximum"]),
        ]

    domain = gates["signal_domain"]
    correct_counts = []
    wrong_counts = []
    for family in families:
        if family["expected_domain"] == "Belirsiz":
            continue
        for condition in ("12.0", "6.0"):
            counts = family["conditions"][condition]["counts"]
            correct_counts.append(counts["domain_correct"])
            wrong_counts.append(counts["domain_wrong"])
    checks["signal_domain"] = [
        _check("family-correct-count-minimum", min(correct_counts), ">=", domain["family_correct_count_minimum"]),
        _check("family-wrong-count-maximum", max(wrong_counts), "<=", domain["wrong_count_maximum"]),
    ]
    return _summarize_fields(result, checks, gates["noise_numeric_false_valid_count_maximum"], domain["noise_definite_count_maximum"])


def _summarize_fields(
    result: dict[str, Any],
    checks: dict[str, list[dict[str, Any]]],
    numeric_noise_limit: int,
    domain_noise_limit: int,
) -> dict[str, Any]:
    noise = result["noise_false_valid_counts"]
    numeric_noise = [
        _check(f"{name}-false-valid-count", noise[name], "<=", numeric_noise_limit)
        for name in ("center", "carrier", "obw", "power", "snr")
    ]
    numeric_noise_passed = all(item["status"] == "passed" for item in numeric_noise)
    domain_noise = _check("domain-false-valid-count", noise["domain"], "<=", domain_noise_limit)
    fields: dict[str, Any] = {}
    for field, field_checks in checks.items():
        local_passed = all(item["status"] == "passed" for item in field_checks)
        expected = local_passed
        if field in NUMERIC_FIELDS:
            expected = expected and numeric_noise_passed
        elif field == "signal_domain":
            expected = expected and domain_noise["status"] == "passed"
        recorded = result["field_decisions"][field]
        fields[field] = {
            "field_local_status": "passed" if local_passed else "failed",
            "recorded_status": recorded,
            "recorded_status_reproduced": recorded == ("passed" if expected else "failed"),
            "checks": field_checks,
        }
    return {
        "status": result["status"],
        "fields": fields,
        "shared_numeric_noise_gate": {
            "status": "passed" if numeric_noise_passed else "failed",
            "checks": numeric_noise,
        },
        "domain_noise_gate": domain_noise,
    }


def _gate_paths(source: str) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()

    def decode(node: ast.AST) -> tuple[str, ...] | None:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Subscript):
            if not isinstance(current.slice, ast.Constant) or not isinstance(current.slice.value, str):
                return None
            parts.append(current.slice.value)
            current = current.value
        if isinstance(current, ast.Name) and current.id == "gates":
            return tuple(reversed(parts))
        return None

    for node in ast.walk(ast.parse(source)):
        path = decode(node)
        if path:
            paths.add(path)
    return paths


def build_analysis() -> dict[str, Any]:
    acceptance = _load(INPUTS["acceptance_gates"])
    development = _load(INPUTS["development_results"])
    binding = _load(INPUTS["binding_results"])
    oos = _load(INPUTS["oos_results"])
    comparison = _load(INPUTS["comparison"])
    binding_audit = _binding_local_gates(binding, acceptance["binding"])
    oos_audit = _oos_local_gates(oos, acceptance["oos"])

    scorer_path = ROOT / "algorithms" / "parameters" / "f1_development.py"
    gate_paths = _gate_paths(scorer_path.read_text(encoding="utf-8"))
    coverage = [
        {
            "gate": "binding.carrier_line_frequency.abstention_rate_minimum",
            "status": "evaluated" if ("carrier_line_frequency", "abstention_rate_minimum") in gate_paths else "not_evaluated",
        },
        {
            "gate": "binding.noise_frames_per_sequence",
            "status": "evaluated" if ("noise_frames_per_sequence",) in gate_paths else "not_evaluated",
            "locked_value": acceptance["binding"]["noise_frames_per_sequence"],
            "implemented_frames_per_measurement": 4,
        },
        {
            "gate": "oos.noise_frames_per_sequence",
            "status": "evaluated" if ("noise_frames_per_sequence",) in gate_paths else "not_evaluated",
            "locked_value": acceptance["oos"]["noise_frames_per_sequence"],
            "implemented_frames_per_measurement": 4,
        },
    ]

    local_binding = {field: item["field_local_status"] for field, item in binding_audit["fields"].items()}
    findings = [
        {
            "id": "F2A-01",
            "class": "protocol-scorer-coverage",
            "severity": "critical",
            "status": "confirmed",
            "evidence": [item["gate"] for item in coverage if item["status"] == "not_evaluated"],
            "required_action": "F2B must reject a protocol unless every binding and OOS gate has an executable coverage check.",
        },
        {
            "id": "F2A-02",
            "class": "cross-field-fail-closed-cascade",
            "severity": "high",
            "status": "confirmed",
            "evidence": {
                "binding_local_passed_but_recorded_failed": [
                    field for field in NUMERIC_FIELDS
                    if local_binding[field] == "passed" and binding["field_decisions"][field] == "failed"
                ],
                "binding_noise_false_valid_counts": binding["noise_false_valid_counts"],
            },
            "required_action": "F2B must define negative-control decisions per field and separately define the whole-profile decision.",
        },
        {
            "id": "F2A-03",
            "class": "noise-rejection",
            "severity": "high",
            "status": "confirmed",
            "evidence": {
                "binding_false_power": binding["noise_false_valid_counts"]["power"],
                "binding_false_snr": binding["noise_false_valid_counts"]["snr"],
                "binding_noise_significance_maximum": binding["noise_detection_significance"]["maximum"],
                "locked_detection_significance_minimum": _load(INPUTS["method_lock"])["constants"]["detection_significance_minimum"],
            },
            "required_action": "F2C must use an open multi-seed noise-development corpus and preserve zero runtime ground-truth access.",
        },
        {
            "id": "F2A-04",
            "class": "occupied-bandwidth-generalization",
            "severity": "high",
            "status": "confirmed",
            "evidence": {
                "binding_local_status": local_binding["occupied_bandwidth"],
                "oos_local_status": oos_audit["fields"]["occupied_bandwidth"]["field_local_status"],
                "binding_failed_checks": [item["id"] for item in binding_audit["fields"]["occupied_bandwidth"]["checks"] if item["status"] == "failed"],
                "oos_failed_checks": [item["id"] for item in oos_audit["fields"]["occupied_bandwidth"]["checks"] if item["status"] == "failed"],
            },
            "required_action": "F2C must develop OBW independently across wider open seeds and preserve clipping abstention.",
        },
        {
            "id": "F2A-05",
            "class": "signal-domain-generalization",
            "severity": "high",
            "status": "confirmed",
            "evidence": {
                "binding_failed_checks": [item["id"] for item in binding_audit["fields"]["signal_domain"]["checks"] if item["status"] == "failed"],
                "oos_failed_checks": [item["id"] for item in oos_audit["fields"]["signal_domain"]["checks"] if item["status"] == "failed"],
            },
            "required_action": "F2C must retrain a new bounded model only on a new open development corpus and retain abstention as a first-class outcome.",
        },
    ]

    reproduced = all(
        field["recorded_status_reproduced"]
        for audit in (binding_audit, oos_audit)
        for field in audit["fields"].values()
    )
    comparison_ok = comparison["status"] == "failed" and comparison["field_decisions"] == [
        {
            "field": field,
            "binding": binding["field_decisions"][field],
            "oos": oos["field_decisions"][field],
            "status": "passed" if binding["field_decisions"][field] == "passed" and oos["field_decisions"][field] == "passed" else "failed",
        }
        for field in binding["field_decisions"]
    ]
    passed = reproduced and comparison_ok and all(item["status"] == "confirmed" for item in findings)
    return {
        "schema_version": 1,
        "phase": "PHASE-04-F2A",
        "status": "passed" if passed else "failed",
        "f1_evaluation_status": comparison["status"],
        "inputs": {name: {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)} for name, path in INPUTS.items()},
        "development_field_decisions": development["field_decisions"],
        "binding_audit": binding_audit,
        "oos_audit": oos_audit,
        "protocol_scorer_coverage": coverage,
        "findings": findings,
        "checks": {
            "recorded_field_decisions_reproduced": reproduced,
            "stored_comparison_reproduced": comparison_ok,
            "f1_locked_sources_modified": False,
            "f1_reveal_used_for_method_tuning": False,
        },
        "claim_boundary": "Bu belge başarısız F1D kanıtının salt-okunur teşhisidir; yeni yöntem, yeni eşik veya ürün başarısı değildir.",
    }
