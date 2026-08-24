"""Read-only PHASE-04-F3A analysis of the preserved F2D failure."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f2_evaluation import compare_results
from algorithms.parameters.f2_estimator import F2ParameterEstimator
from algorithms.parameters.operator_reference import load_json
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor
from verification.phase04f2_scoring import score_population


ROOT = Path(__file__).resolve().parents[1]
F2_FIXTURES = ROOT / "datasets" / "fixtures" / "phase04f2"
F2_EVIDENCE = ROOT / "results" / "evidence" / "phase04f2"
PROTECTED_INPUTS = (
    "algorithms/parameters/f2_development.py",
    "algorithms/parameters/f2_domain.py",
    "algorithms/parameters/f2_estimator.py",
    "algorithms/parameters/f2_evaluation.py",
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f2/development-catalog.json",
    "datasets/fixtures/phase04f2/domain-model-v3.json",
    "datasets/fixtures/phase04f2/method-lock-v3.json",
    "datasets/fixtures/phase04f2/evaluation-runner-lock-v3.json",
    "datasets/fixtures/phase04f2/evaluation-seeds.json",
    "results/evidence/phase04f2/development-results-v3.json",
    "results/evidence/phase04f2/binding-results-v3.json",
    "results/evidence/phase04f2/oos-results-v3.json",
    "results/evidence/phase04f2/parameter-comparison-v3.json",
    "results/evidence/phase04f2/f2d-verification.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wilson_upper(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    rate = successes / trials
    denominator = 1.0 + z**2 / trials
    center = rate + z**2 / (2.0 * trials)
    radius = z * math.sqrt(rate * (1.0 - rate) / trials + z**2 / (4.0 * trials**2))
    return (center + radius) / denominator


def _measure(
    scene_id: str,
    *,
    seed: int,
    family_index: int,
    trial: int,
    condition_index: int,
    snr_db: float,
    frame_indices: tuple[int, ...],
    catalog: dict[str, Any],
    processor: SpectrumProcessor,
    estimator: F2ParameterEstimator,
    margin: int,
) -> Any:
    frames = tuple(
        generate_parameter_scene(
            scene_id,
            trial_index=trial,
            condition_index=condition_index,
            frame_index=frame_index,
            clean_power_dbfs=-18.0,
            snr_db=snr_db,
            catalog=catalog,
            scene_seed_override=seed + family_index * 10_000,
        )
        for frame_index in frame_indices
    )
    spectra = tuple(
        processor.process(frame.samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
        for frame in frames
    )
    clean = tuple(
        processor.process(frame.clean_samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
        for frame in frames
    )
    truth = _truth(clean, margin)
    return estimator.measure(
        _intent(truth["span"], family_index + 1, trial),
        tuple(frame.samples for frame in frames),
        spectra,
    )


def build_open_seed_diagnostics() -> dict[str, Any]:
    development = load_json(F2_FIXTURES / "development-catalog.json")
    stored = load_json(F2_EVIDENCE / "development-results-v3.json")
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    estimator = F2ParameterEstimator()
    common = development["common"]
    trials = int(common["trials_per_seed_per_family"])
    margin = int(common["operator_span_truth_margin_bins_per_side"])
    applicable = [
        (index, family)
        for index, family in enumerate(development["families"])
        if family["carrier_line_applicable"]
    ]
    ook_index, ook = next(
        (index, family) for index, family in enumerate(development["families"])
        if family["id"] == "ook"
    )
    per_seed: list[dict[str, Any]] = []
    carrier_aggregate = {str(family["id"]): 0 for _, family in applicable}
    domain_aggregate = {"correct": 0, "wrong": 0, "abstained": 0}
    for seed_index, raw_seed in enumerate(common["development_seeds"]):
        seed = int(raw_seed)
        carrier_counts: dict[str, int] = {}
        for family_index, family in applicable:
            frames = tuple(int(value) for value in family.get("active_frames", [0, 1, 2, 3]))[:4]
            valid = 0
            for trial in range(trials):
                result = _measure(
                    str(family["scene_id"]), seed=seed, family_index=family_index, trial=trial,
                    condition_index=3, snr_db=12.0, frame_indices=frames, catalog=catalog,
                    processor=processor, estimator=estimator, margin=margin,
                )
                valid += int(result.carrier_line_frequency.state == "valid")
            family_id = str(family["id"])
            carrier_counts[family_id] = valid
            carrier_aggregate[family_id] += valid
        domain = {"correct": 0, "wrong": 0, "abstained": 0}
        frames = tuple(int(value) for value in ook.get("active_frames", [0, 1, 2, 3]))[:4]
        for trial in range(trials):
            result = _measure(
                str(ook["scene_id"]), seed=seed, family_index=ook_index, trial=trial,
                condition_index=2, snr_db=6.0, frame_indices=frames, catalog=catalog,
                processor=processor, estimator=estimator, margin=margin,
            )
            if result.signal_domain.state != "valid":
                domain["abstained"] += 1
            elif result.signal_domain.value == "Sayısal":
                domain["correct"] += 1
            else:
                domain["wrong"] += 1
        for key in domain_aggregate:
            domain_aggregate[key] += domain[key]
        per_seed.append({
            "seed_index": seed_index,
            "trial_count": trials,
            "carrier_valid_counts_12_db": carrier_counts,
            "ook_domain_counts_6_db": domain,
        })
    expected_carrier = {
        family_id: stored["families"][family_id]["12.0"]["carrier_valid_count"]
        for family_id in carrier_aggregate
    }
    expected_domain = {
        "correct": stored["families"]["ook"]["6.0"]["domain_correct_count"],
        "wrong": stored["families"]["ook"]["6.0"]["domain_wrong_count"],
        "abstained": stored["families"]["ook"]["6.0"]["domain_abstained_count"],
    }
    return {
        "per_seed": per_seed,
        "aggregate": {
            "carrier_valid_counts_12_db": carrier_aggregate,
            "ook_domain_counts_6_db": domain_aggregate,
        },
        "stored_development_counts_reproduced": carrier_aggregate == expected_carrier and domain_aggregate == expected_domain,
    }


def build_analysis() -> dict[str, Any]:
    acceptance = load_json(F2_FIXTURES / "acceptance-gates.json")
    development = load_json(F2_EVIDENCE / "development-results-v3.json")
    binding = load_json(F2_EVIDENCE / "binding-results-v3.json")
    oos = load_json(F2_EVIDENCE / "oos-results-v3.json")
    comparison = load_json(F2_EVIDENCE / "parameter-comparison-v3.json")
    public = build_open_seed_diagnostics()
    rescored_binding = score_population(binding["metrics"], acceptance, "binding")
    rescored_oos = score_population(oos["metrics"], acceptance, "oos")
    decisions_reproduced = (
        binding["scoring"] == rescored_binding
        and oos["scoring"] == rescored_oos
        and comparison == compare_results(binding, oos)
    )
    populations = {
        "development": development["families"]["ook"],
        "binding": binding["families"]["ook"],
        "oos": oos["families"]["ook"],
    }
    carrier = {
        role: {
            "valid_count": record["12.0"]["carrier_valid_count"],
            "trial_count": record["12.0"]["trial_count"],
            "valid_rate": record["12.0"]["carrier_valid_count"] / record["12.0"]["trial_count"],
        }
        for role, record in populations.items()
    }
    domain = {
        role: {
            "correct_count": record["6.0"]["domain_correct_count"],
            "wrong_count": record["6.0"]["domain_wrong_count"],
            "abstained_count": record["6.0"]["domain_abstained_count"],
            "trial_count": record["6.0"]["trial_count"],
            "wrong_rate": record["6.0"]["domain_wrong_count"] / record["6.0"]["trial_count"],
        }
        for role, record in populations.items()
    }
    development_wrong_upper = _wilson_upper(domain["development"]["wrong_count"], domain["development"]["trial_count"])
    oos_wrong_rate_limit = 2 / 64
    root_causes = [
        {
            "id": "F3A-01",
            "class": "ook-carrier-seed-generalization",
            "status": "confirmed",
            "evidence": {
                "development": carrier["development"],
                "binding": carrier["binding"],
                "oos": carrier["oos"],
                "oos_required_valid_count": 56,
                "oos_deficit": 56 - carrier["oos"]["valid_count"],
                "public_seed_valid_counts": [
                    item["carrier_valid_counts_12_db"]["ook"] for item in public["per_seed"]
                ],
            },
            "required_action": "Yeni geliştirme bölümü OOK taşıyıcı kararını aggregate oran yerine seed-bazlı alt sınır ve temporal kanıt dağılımıyla doğrulamalıdır.",
        },
        {
            "id": "F3A-02",
            "class": "domain-wrong-decision-safety-margin",
            "status": "confirmed",
            "evidence": {
                "development": domain["development"],
                "binding": domain["binding"],
                "oos": domain["oos"],
                "oos_wrong_count_maximum": 2,
                "development_wrong_rate_wilson_upper_95": development_wrong_upper,
                "oos_wrong_rate_limit": oos_wrong_rate_limit,
                "public_seed_wrong_counts": [
                    item["ook_domain_counts_6_db"]["wrong"] for item in public["per_seed"]
                ],
            },
            "required_action": "Yeni yöntem yanlış kesin kararı seed-bazlı risk kapısıyla sınırlamalı; sınırdaki OOK örneklerini Sayısal'a zorlamak yerine abstention'a taşımalıdır.",
        },
        {
            "id": "F3A-03",
            "class": "shared-ook-boundary",
            "status": "confirmed",
            "evidence": {
                "failed_oos_checks": [
                    item["id"] for item in oos["scoring"]["checks"] if item["status"] == "failed"
                ],
                "common_family": "ook",
                "carrier_condition_db": 12.0,
                "domain_condition_db": 6.0,
            },
            "required_action": "F3B taşıyıcı varlığı ile sinyal alanı güvenini ayrı kapılar olarak korurken OOK için ortak zarf/temporal tanı kapsamını genişletmelidir.",
        },
    ]
    return {
        "schema_version": 1,
        "artifact_id": "phase04f3a-f2d-failure-analysis-v1",
        "phase": "PHASE-04-F3A",
        "status": "passed" if decisions_reproduced and public["stored_development_counts_reproduced"] else "failed",
        "f2d_evaluation_status": comparison["status"],
        "recorded_decisions_reproduced": decisions_reproduced,
        "open_seed_diagnostics": public,
        "root_causes": root_causes,
        "protected_inputs": {path: _sha256(ROOT / path) for path in PROTECTED_INPUTS},
        "next_phase_requirements": [
            "F3B başlamadan yeni açık geliştirme seed'leri F1/F2 popülasyonlarından ayrılmalıdır.",
            "Yeni binding ve OOS seed commitment'ları yöntem geliştirmeden önce oluşturulmalıdır.",
            "F2 kabul eşikleri gevşetilmemeli; OOK için seed-bazlı güvenlik payı eklenmelidir.",
            "F3B ayrı kullanıcı onayı olmadan başlatılmamalıdır.",
        ],
        "claim_boundary": "Salt-okunur F2D kök neden analizidir; yeni yöntem, eşik değişikliği, yeniden koşu veya ürün kararı değildir.",
    }
