"""KTR-4.2 / PÇ-02–03: kayıtlı karar kapılarını değiştirmeden incele."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.parameters.f3_estimator import carrier_evidence_v4
from algorithms.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.parameters.f4_domain import (
    DEFAULT_MODEL_PATH, classify_domain_v5, extract_domain_vector_v5,
    minimum_margin_for_family,
)
from algorithms.parameters.f5_estimator import F5ParameterEstimator
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from app.operator_console.measurement_record import read_measurement, replay_measurement, utc_now


def diagnose(path):
    document, frames = read_measurement(path)
    result = replay_measurement(path)  # Includes current source/profile integrity checks.
    values = dict(document["intent"])
    values["span"] = AnalysisSpan(**values["span"])
    if values["context"] is not None:
        context = dict(values["context"])
        context["candidates"] = tuple(MeasurementCandidate(**item) for item in context["candidates"])
        context["owner_observed_frames"] = tuple(context["owner_observed_frames"])
        values["context"] = MeasurementContext(**context)
    intent = MeasurementIntent(**values)
    vector = extract_domain_vector_v5(frames, intent.span.lower_shifted_bin, intent.span.upper_shifted_bin)
    model = json.loads(DEFAULT_MODEL_PATH.read_text(encoding="utf-8"))
    snr = result.snr_estimate_db.value
    domain = classify_domain_v5(vector, snr_db=float(snr) if snr is not None else float("nan"), model=model)
    carrier = None
    gates = {}
    estimator = F5ParameterEstimator
    if result.emission_center_frequency.state == "valid" and result.snr_estimate_db.state == "valid":
        processor = SpectrumProcessor(SpectrumConfig(**document["spectrum_config"]))
        spectra = tuple(processor.process(frame, sample_rate_hz=document["sample_rate_hz"],
            center_frequency_hz=document["center_frequency_hz"]) for frame in frames)
        evidence = carrier_evidence_v4(intent, spectra, result.emission_center_frequency.value, vector)
        if evidence is not None:
            carrier = asdict(evidence)
            gates = {
                "snr": snr >= estimator.LOW_SNR_ABSTENTION_DB,
                "prominence": evidence.prominence_db >= estimator.CARRIER_PROMINENCE_DB_MINIMUM_V4,
                "share": evidence.share >= estimator.CARRIER_SHARE_MINIMUM_V4,
                "all_frame_prominences": min(evidence.frame_prominences_db) >= estimator.CARRIER_FRAME_PROMINENCE_DB_MINIMUM_V4,
                "artifact_rejection": not (
                    evidence.spectral_entropy >= estimator.CARRIER_ARTIFACT_SPECTRAL_ENTROPY_MINIMUM_V4
                    and evidence.envelope_skewness <= estimator.CARRIER_ARTIFACT_ENVELOPE_SKEWNESS_MAXIMUM_V4),
            }
    legacy_decision = asdict(domain)
    legacy_domain_gates = {"snr": snr is not None and snr >= model["thresholds"]["minimum_snr_db"]}
    if domain.nearest_family is not None:
        legacy_domain_gates.update({
            "distance": domain.distance <= model["thresholds"]["maximum_distance"],
            "margin": domain.margin >= minimum_margin_for_family(model, domain.nearest_family),
        })
    automatic = document.get("automatic_signal_domain", {})
    confidence = automatic.get("confidence")
    confidence_threshold = automatic.get("confidence_threshold", 0.90)
    domain_gates = {
        "snr": snr is not None and snr >= 4.0,
        "confidence": confidence is not None and confidence >= confidence_threshold,
    }
    product_domain = asdict(result.signal_domain)
    return {
        "record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": document["source"],
        "carrier_state": result.carrier_line_frequency.state,
        "carrier_reason": result.carrier_line_frequency.reason,
        "carrier_evidence": carrier,
        "carrier_gates": {key: bool(value) for key, value in gates.items()},
        "domain": product_domain,
        "domain_gates": {key: bool(value) for key, value in domain_gates.items()},
        "domain_thresholds": {
            "minimum_snr_db": 4.0,
            "confidence_threshold": confidence_threshold,
        },
        "product_domain": product_domain,
        "legacy_domain_diagnostic": legacy_decision,
        "legacy_domain_gates": {
            key: bool(value) for key, value in legacy_domain_gates.items()
        },
        "legacy_domain_thresholds": model["thresholds"],
    }


def run(bench, output):
    original = json.loads((bench / "report.json").read_text(encoding="utf-8"))
    rows = []
    for measurement in original["measurements"]:
        path = bench / measurement["record"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != measurement["sha256"]:
            raise ValueError("Ölçüm arşivi rapordaki özetle eşleşmiyor.")
        row = diagnose(path)
        row["family"] = measurement["family"]
        rows.append(row)
    summary = {}
    for family in sorted({row["family"] for row in rows}):
        subset = [row for row in rows if row["family"] == family]
        summary[family] = {
            "count": len(subset),
            "carrier_failed_gates": dict(Counter(key for row in subset for key, passed in row["carrier_gates"].items() if not passed)),
            "domain_reasons": dict(Counter(row["product_domain"]["reason"] or "valid" for row in subset)),
            "domain_failed_gates": dict(Counter(key for row in subset for key, passed in row["domain_gates"].items() if not passed)),
        }
    report = {"schema": "parameter-gate-diagnostic-v1", "created_utc": utc_now(),
        "requirements": ["KTR-4.2", "KTR-4.2-F1", "PÇ-03"], "acceptance": "not_evaluated",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_report_sha256": hashlib.sha256((bench / "report.json").read_bytes()).hexdigest(),
        "summary": summary, "measurements": rows}
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    with output.open("xb") as stream:
        stream.write(payload)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.bench, args.output)
