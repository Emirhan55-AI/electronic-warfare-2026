"""Read-only root-cause analysis for the PHASE-04-F3D NFM abstention failure."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algorithms.parameters.f3_evaluation import compare_results
from verification.phase04f2_scoring import score_population


ROOT = Path(__file__).resolve().parents[1]
F2_ACCEPTANCE = ROOT / "datasets" / "fixtures" / "phase04f2" / "acceptance-gates.json"
F3_FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f3"
F3_EVIDENCE = ROOT / "results" / "evidence" / "phase04f3"
PROTECTED_INPUTS = (
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f3/acceptance-gates.json",
    "datasets/fixtures/phase04f3/domain-model-v4.json",
    "datasets/fixtures/phase04f3/method-lock-v4.json",
    "datasets/fixtures/phase04f3/evaluation-runner-lock-v4.json",
    "datasets/fixtures/phase04f3/evaluation-seeds.json",
    "results/evidence/phase04f3/development-results-v4.json",
    "results/evidence/phase04f3/binding-results-v4.json",
    "results/evidence/phase04f3/oos-results-v4.json",
    "results/evidence/phase04f3/parameter-comparison-v4.json",
    "results/evidence/phase04f3/f3d-verification.json",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    half = z * math.sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)) / denominator
    return center - half, center + half


def _domain_counts(document: dict[str, Any], family: str, snr_db: str) -> dict[str, int]:
    row = document["families"][family][snr_db]
    return {
        "correct": int(row["domain_correct_count"]),
        "wrong": int(row["domain_wrong_count"]),
        "abstained": int(row["domain_abstained_count"]),
        "trials": int(row["trial_count"]),
    }


def build_analysis() -> dict[str, Any]:
    acceptance = _load(F2_ACCEPTANCE)
    model = _load(F3_FIXTURES / "domain-model-v4.json")
    development = _load(F3_EVIDENCE / "development-results-v4.json")
    binding = _load(F3_EVIDENCE / "binding-results-v4.json")
    oos = _load(F3_EVIDENCE / "oos-results-v4.json")
    comparison = _load(F3_EVIDENCE / "parameter-comparison-v4.json")
    verification = _load(F3_EVIDENCE / "f3d-verification.json")

    rescored_binding = score_population(binding["metrics"], acceptance, "binding")
    rescored_oos = score_population(oos["metrics"], acceptance, "oos")
    decisions_reproduced = (
        rescored_binding == binding["scoring"]
        and rescored_oos == oos["scoring"]
        and compare_results(binding, oos) == comparison
        and verification.get("status") == "passed"
        and verification.get("evaluation_status") == "failed"
    )

    development_nfm = _domain_counts(development, "nfm", "6.0")
    binding_nfm = _domain_counts(binding, "nfm", "6.0")
    oos_nfm = _domain_counts(oos, "nfm", "6.0")
    oos_nfm_12 = _domain_counts(oos, "nfm", "12.0")
    oos_ook = _domain_counts(oos, "ook", "6.0")
    loso_rate = float(model["cross_seed_diagnostics"]["family_condition"]["nfm:6.0"]["correct_rate"])
    loso_trials = int(model["development_split"]["seed_count"]) * int(
        model["development_split"]["trials_per_seed_per_family"]
    )
    loso_correct = round(loso_rate * loso_trials)
    oos_gate = next(
        item for item in acceptance["checks"]["oos"]
        if item["metric"] == "domain.family_min_correct_count"
    )
    protected = {path: _sha256(ROOT / path) for path in PROTECTED_INPUTS}

    return {
        "schema_version": 1,
        "artifact_id": "phase04f4a-nfm-abstention-analysis-v1",
        "phase": "PHASE-04-F4A",
        "status": "passed" if decisions_reproduced else "failed",
        "f3d_evaluation_status": comparison["status"],
        "recorded_decisions_reproduced": decisions_reproduced,
        "nfm_6_db": {
            "open_development": {
                **development_nfm,
                "correct_rate": development_nfm["correct"] / development_nfm["trials"],
            },
            "leave_one_seed_out": {
                "correct": loso_correct,
                "trials": loso_trials,
                "correct_rate": loso_rate,
            },
            "binding": {
                **binding_nfm,
                "correct_rate": binding_nfm["correct"] / binding_nfm["trials"],
            },
            "oos": {
                **oos_nfm,
                "correct_rate": oos_nfm["correct"] / oos_nfm["trials"],
                "correct_rate_wilson_95": list(_wilson_interval(oos_nfm["correct"], oos_nfm["trials"])),
                "required_correct": int(oos_gate["threshold"]),
                "correct_deficit": int(oos_gate["threshold"]) - oos_nfm["correct"],
            },
            "oos_12_db_control": oos_nfm_12,
        },
        "ook_6_db_oos_control": oos_ook,
        "root_causes": [
            {
                "id": "F4A-01",
                "class": "nfm-low-snr-seed-generalization",
                "status": "confirmed",
                "evidence": {
                    "leave_one_seed_out_correct_rate": loso_rate,
                    "binding_correct_rate": binding_nfm["correct"] / binding_nfm["trials"],
                    "oos_correct_rate": oos_nfm["correct"] / oos_nfm["trials"],
                    "oos_required_rate": int(oos_gate["threshold"]) / oos_nfm["trials"],
                    "oos_correct_deficit": int(oos_gate["threshold"]) - oos_nfm["correct"],
                },
                "required_action": "Yeni açık veri ayrımı NFM 6 dB kararını aggregate oran yerine seed-bazlı doğru ve abstention sınırlarıyla doğrulamalıdır.",
            },
            {
                "id": "F4A-02",
                "class": "abstention-not-wrong-decision",
                "status": "confirmed",
                "evidence": {
                    "binding_wrong": binding_nfm["wrong"],
                    "binding_abstained": binding_nfm["abstained"],
                    "oos_wrong": oos_nfm["wrong"],
                    "oos_abstained": oos_nfm["abstained"],
                    "oos_12_db_correct": oos_nfm_12["correct"],
                },
                "required_action": "Yanlış kesin karar güvenliği korunurken düşük SNR NFM kabul kapsamı yeni açık seed'lerde genişletilmelidir.",
            },
            {
                "id": "F4A-03",
                "class": "missing-nfm-seed-risk-gate",
                "status": "confirmed",
                "evidence": {
                    "f3_additional_gate_family": "ook",
                    "nfm_seed_specific_gate_present": False,
                    "f3d_oos_failed_metric": "domain.family_min_correct_count",
                },
                "required_action": "F4B, korunan F2 kapılarını gevşetmeden NFM 6 dB için seed-bazlı geliştirme güvenlik payı eklemelidir.",
            },
            {
                "id": "F4A-04",
                "class": "distance-versus-margin-subcause",
                "status": "not-identifiable-from-stored-evidence",
                "evidence": {
                    "stored_trial_level_distance_margin": False,
                    "f3d_rerun_allowed": False,
                },
                "required_action": "Alt neden yalnız yeni açık F4 geliştirme popülasyonunda trial-level mesafe/marj sayımıyla ayrılmalıdır.",
            },
        ],
        "protected_inputs": protected,
        "next_phase_requirements": [
            "F4B başlamadan F1/F2/F3 seed'lerinden bağımsız yeni açık geliştirme seed'leri ayrılmalıdır.",
            "Yeni binding/OOS seed ve salt commitment'ları yöntem geliştirmeden önce oluşturulmalıdır.",
            "F2'nin 40 binding ve 24 OOS kapısı gevşetilmemelidir.",
            "NFM 6 dB için seed-bazlı doğru, yanlış ve abstention geliştirme kapıları yöntemden önce kilitlenmelidir.",
            "F4B ayrı kullanıcı onayı olmadan başlatılmamalıdır.",
        ],
        "claim_boundary": "Salt-okunur F3D kök neden analizidir; F3D popülasyonunu yeniden çalıştırmaz, yeni yöntem veya ürün kararı değildir.",
    }
