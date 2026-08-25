"""Read-only root-cause analysis for the PHASE-04-F4D OBW validity failure."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algorithms.parameters.f4_evaluation import compare_results
from verification.phase04f2_scoring import score_population


ROOT = Path(__file__).resolve().parents[1]
F2_ACCEPTANCE = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
F3_ACCEPTANCE = ROOT / "datasets" / "fixtures" / "phase04f3" / "acceptance-gates.json"
F4_ACCEPTANCE = ROOT / "datasets" / "fixtures" / "phase04f4" / "acceptance-gates.json"
F4_EVIDENCE = ROOT / "results" / "evidence" / "phase04f4"
PROTECTED_INPUTS = (
    "algorithms/parameters/f1_estimator.py",
    "algorithms/parameters/f2_estimator.py",
    "algorithms/parameters/f4_estimator.py",
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f3/acceptance-gates.json",
    "datasets/fixtures/phase04f4/acceptance-gates.json",
    "datasets/fixtures/phase04f4/method-lock-v5.json",
    "datasets/fixtures/phase04f4/evaluation-runner-lock-v5.json",
    "datasets/fixtures/phase04f4/evaluation-seeds.json",
    "results/evidence/phase04f2/oos-results-v3.json",
    "results/evidence/phase04f3/oos-results-v4.json",
    "results/evidence/phase04f4/development-results-v5.json",
    "results/evidence/phase04f4/binding-results-v5.json",
    "results/evidence/phase04f4/oos-results-v5.json",
    "results/evidence/phase04f4/parameter-comparison-v5.json",
    "results/evidence/phase04f4/f4d-verification.json",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _obw_counts(document: dict[str, Any]) -> dict[str, dict[str, int | float]]:
    return {
        family: {
            "valid": int(conditions["12.0"]["obw_valid_count"]),
            "trials": int(conditions["12.0"]["trial_count"]),
            "valid_rate": int(conditions["12.0"]["obw_valid_count"])
            / int(conditions["12.0"]["trial_count"]),
        }
        for family, conditions in document["families"].items()
    }


def _check(document: dict[str, Any], role: str, metric: str) -> dict[str, Any]:
    return next(item for item in document["checks"][role] if item["metric"] == metric)


def build_analysis() -> dict[str, Any]:
    base_acceptance = _load(F2_ACCEPTANCE)
    inherited_acceptance = _load(F3_ACCEPTANCE)
    f4_acceptance = _load(F4_ACCEPTANCE)
    development = _load(F4_EVIDENCE / "development-results-v5.json")
    binding = _load(F4_EVIDENCE / "binding-results-v5.json")
    oos = _load(F4_EVIDENCE / "oos-results-v5.json")
    comparison = _load(F4_EVIDENCE / "parameter-comparison-v5.json")
    verification = _load(F4_EVIDENCE / "f4d-verification.json")

    rescored_binding = score_population(binding["metrics"], base_acceptance, "binding")
    rescored_oos = score_population(oos["metrics"], base_acceptance, "oos")
    decisions_reproduced = (
        rescored_binding == binding["scoring"]
        and rescored_oos == oos["scoring"]
        and compare_results(binding, oos) == comparison
        and verification.get("status") == "passed"
        and verification.get("evaluation_status") == "failed"
    )

    development_counts = _obw_counts(development)
    binding_counts = _obw_counts(binding)
    oos_counts = _obw_counts(oos)
    development_family_gate = _check(base_acceptance, "binding", "obw.family_min_valid_rate")
    development_global_gate = _check(base_acceptance, "binding", "obw.global_valid_rate")
    oos_family_gate = _check(base_acceptance, "oos", "obw.family_min_valid_count")
    oos_trials = int(oos["population"]["trials_per_family"])
    development_trials = next(iter(development_counts.values()))["trials"]
    oos_required_rate = int(oos_family_gate["threshold"]) / oos_trials
    development_oos_equivalent_count = math.ceil(oos_required_rate * int(development_trials))
    weak_development_families = {
        family: {
            **counts,
            "oos_rate_equivalent_required": development_oos_equivalent_count,
            "margin_to_oos_rate_equivalent": int(counts["valid"]) - development_oos_equivalent_count,
        }
        for family, counts in development_counts.items()
        if int(counts["valid"]) < development_oos_equivalent_count
    }
    additional_obw_seed_gate = any(
        item.get("owner") == "occupied_bandwidth"
        and not str(item.get("metric", "")).startswith("noise.")
        for item in inherited_acceptance["development_checks"]
        + f4_acceptance["additional_development_checks"]
    )
    all_family_numeric_valid = all(
        int(conditions["12.0"][field]) == int(conditions["12.0"]["trial_count"])
        for conditions in oos["families"].values()
        for field in ("center_valid_count", "power_valid_count", "snr_valid_count")
    )
    temporal_instability_isolated = (
        all_family_numeric_valid
        and int(oos["metrics"]["obw.clipping_count"]) == 0
        and any(int(item["valid"]) < int(item["trials"]) for item in oos_counts.values())
    )
    historical_controls: dict[str, Any] = {}
    for phase, version in (("phase04f2", "v3"), ("phase04f3", "v4"), ("phase04f4", "v5")):
        document = _load(ROOT / "results" / "evidence" / phase / f"oos-results-{version}.json")
        historical_controls[version] = {
            "method_id": document["method_ids"]["occupied_bandwidth"],
            "field_decision": document["scoring"]["field_decisions"]["occupied_bandwidth"],
            "family_min_valid_count": min(
                int(conditions["12.0"]["obw_valid_count"])
                for conditions in document["families"].values()
            ),
        }

    protected = {path: _sha256(ROOT / path) for path in PROTECTED_INPUTS}
    return {
        "schema_version": 1,
        "artifact_id": "phase04f5a-obw-validity-analysis-v1",
        "phase": "PHASE-04-F5A",
        "status": "passed" if decisions_reproduced and temporal_instability_isolated else "failed",
        "f4d_evaluation_status": comparison["status"],
        "recorded_decisions_reproduced": decisions_reproduced,
        "obw_method": {
            "method_id": oos["method_ids"]["occupied_bandwidth"],
            "unchanged_across_v3_v4_v5": len(
                {item["method_id"] for item in historical_controls.values()}
            ) == 1,
            "base_temporal_limit_bins": 2.0,
            "recovery_temporal_limit_bins": 3.0,
        },
        "acceptance_gap": {
            "development_family_minimum_rate": float(development_family_gate["threshold"]),
            "development_global_minimum_rate": float(development_global_gate["threshold"]),
            "oos_family_minimum_count": int(oos_family_gate["threshold"]),
            "oos_trials_per_family": oos_trials,
            "oos_family_minimum_rate": oos_required_rate,
            "development_trials_per_family": int(development_trials),
            "oos_rate_equivalent_development_count": development_oos_equivalent_count,
            "additional_seed_level_obw_validity_gate_present": additional_obw_seed_gate,
        },
        "populations": {
            "development": development_counts,
            "binding": binding_counts,
            "oos": oos_counts,
            "development_below_oos_rate_equivalent": weak_development_families,
        },
        "failure_isolation": {
            "all_oos_center_power_snr_valid_per_family": all_family_numeric_valid,
            "oos_clipping_count": int(oos["metrics"]["obw.clipping_count"]),
            "remaining_failure_class": "obw_temporal_instability"
            if temporal_instability_isolated else "not_isolated",
            "exact_trial_level_temporal_ranges_stored": False,
            "f4d_rerun_allowed": False,
        },
        "historical_oos_controls": historical_controls,
        "root_causes": [
            {
                "id": "F5A-01",
                "class": "obw-seed-generalization-margin",
                "status": "confirmed",
                "evidence": {
                    "v3_oos_minimum": historical_controls["v3"]["family_min_valid_count"],
                    "v4_oos_minimum": historical_controls["v4"]["family_min_valid_count"],
                    "v5_oos_minimum": historical_controls["v5"]["family_min_valid_count"],
                    "required": int(oos_family_gate["threshold"]),
                },
                "required_action": "Yeni açık veri ayrımında OBW geçerliliği aggregate oran yerine seed ve aile bazlı güvenlik payıyla doğrulanmalıdır.",
            },
            {
                "id": "F5A-02",
                "class": "development-oos-acceptance-mismatch",
                "status": "confirmed",
                "evidence": {
                    "development_family_minimum_rate": float(development_family_gate["threshold"]),
                    "oos_family_minimum_rate": oos_required_rate,
                    "additional_seed_level_obw_gate_present": additional_obw_seed_gate,
                    "weak_development_families": sorted(weak_development_families),
                },
                "required_action": "F5B, mevcut değerlendirme eşiklerini gevşetmeden OOS oranından daha güçlü OBW geliştirme kapılarını yöntemden önce kilitlemelidir.",
            },
            {
                "id": "F5A-03",
                "class": "temporal-instability-not-clipping",
                "status": "confirmed" if temporal_instability_isolated else "not-confirmed",
                "evidence": {
                    "all_center_power_snr_valid": all_family_numeric_valid,
                    "clipping_count": int(oos["metrics"]["obw.clipping_count"]),
                    "invalid_family_counts": {
                        family: int(item["trials"]) - int(item["valid"])
                        for family, item in oos_counts.items()
                        if int(item["valid"]) < int(item["trials"])
                    },
                },
                "required_action": "Yeni açık popülasyonda temporal range, recovery denemesi ve ret nedeni trial bazında kaydedilmelidir.",
            },
            {
                "id": "F5A-04",
                "class": "exact-recovery-guard-subcause",
                "status": "not-identifiable-from-stored-evidence",
                "evidence": {
                    "trial_level_diagnostics_stored": False,
                    "f4d_rerun_allowed": False,
                },
                "required_action": "Alt neden yalnız yeni açık F5 geliştirme verisinde ayrılmalı; açılmış F4 popülasyonları tuning veya yeniden koşu için kullanılmamalıdır.",
            },
        ],
        "protected_inputs": protected,
        "next_phase_requirements": [
            "F5B öncesinde F1-F4 popülasyonlarından bağımsız yeni açık geliştirme seed'leri ayrılmalıdır.",
            "Yeni binding/OOS seed ve salt commitment'ları yöntem geliştirmeden önce oluşturulmalıdır.",
            "F2'nin 40 binding ve 24 OOS kapısı gevşetilmemelidir.",
            "OBW geçerliliği için aile ve seed bazlı geliştirme güvenlik payı kilitlenmelidir.",
            "Temporal range, recovery sonucu ve ret nedeni yeni açık geliştirme kanıtında zorunlu tanı olmalıdır.",
            "F5B ayrı kullanıcı onayı olmadan başlatılmamalıdır.",
        ],
        "claim_boundary": "Salt-okunur F4D kök neden analizidir; F4D popülasyonunu yeniden çalıştırmaz, yeni yöntem, FPGA entegrasyonu veya ürün kararı değildir.",
    }
