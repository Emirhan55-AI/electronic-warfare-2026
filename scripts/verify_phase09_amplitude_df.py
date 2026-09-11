"""Build/check deterministic PHASE-09 amplitude-DF numerical evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE, ManualAmplitudeDF


DEFAULT_OUTPUT = ROOT / "results" / "evidence" / "phase09" / "amplitude-df-numeric-v1.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def circular_delta(angle_deg: float, truth_deg: float) -> float:
    return (angle_deg - truth_deg + 180.0) % 360.0 - 180.0


def power_pattern_dbfs(angle_deg: float, truth_deg: float) -> float:
    delta = math.radians(circular_delta(angle_deg, truth_deg))
    forward = max(math.cos(delta), 0.0) ** 4
    back = max(-math.cos(delta), 0.0) ** 2
    independent_variation = 0.18 * math.sin(math.radians(11.0 * angle_deg + 7.0 * truth_deg + 13.0))
    return -38.0 + 25.0 * forward + 3.0 * back + independent_variation


def evaluate_grid(step_deg: int) -> dict[str, object]:
    estimates: list[float] = []
    truths: list[float] = []
    statuses: dict[str, int] = {}
    for truth in range(360):
        model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
        for frame_id, angle in enumerate(range(0, 360, step_deg)):
            model.add(
                DFMeasurement.create(
                    angle_deg=float(angle),
                    relative_power_db=power_pattern_dbfs(float(angle), float(truth)),
                    frequency_hz=145_000_000.0,
                    confidence=0.95,
                    channel_bandwidth_hz=12_500.0,
                    receiver_binding="numeric-holdout|145MHz|12.5kHz|fixed-gain",
                    frame_id=frame_id,
                    source="SAYISAL DOĞRULAMA",
                )
            )
        estimate = model.estimate()
        statuses[estimate.status] = statuses.get(estimate.status, 0) + 1
        estimates.append(estimate.estimated_angle_deg)
        truths.append(float(truth))
    errors = [ManualAmplitudeDF.angular_error_deg(estimate, truth) for estimate, truth in zip(estimates, truths)]
    ordered = sorted(errors)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    return {
        "angular_step_deg": step_deg,
        "scene_count": len(errors),
        "status_counts": statuses,
        "rms_error_deg": ManualAmplitudeDF.rms_error_deg(estimates, truths),
        "p95_error_deg": p95,
        "maximum_error_deg": max(errors),
        "ideal_uniform_grid_rms_deg": step_deg / math.sqrt(12.0),
    }


def negative_gate_statuses() -> dict[str, str]:
    cases: dict[str, ManualAmplitudeDF] = {}

    clustered = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
    for frame_id, angle in enumerate(range(0, 120, 5)):
        clustered.add(DFMeasurement.create(
            angle_deg=angle, relative_power_db=-10.0 - abs(angle - 40.0) / 4.0,
            frequency_hz=145_000_000.0, confidence=0.95, channel_bandwidth_hz=12_500.0,
            receiver_binding="fixed", frame_id=frame_id,
        ))
    cases["clustered_angles"] = clustered

    front_back = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
    for frame_id, angle in enumerate(range(0, 360, 15)):
        distance = min(angle, 360 - angle)
        back_distance = abs(angle - 180)
        power = max(-9.0 - distance / 8.0, -9.5 - back_distance / 8.0)
        front_back.add(DFMeasurement.create(
            angle_deg=angle, relative_power_db=power, frequency_hz=145_000_000.0,
            confidence=0.95, channel_bandwidth_hz=12_500.0,
            receiver_binding="fixed", frame_id=frame_id,
        ))
    cases["front_back_ambiguity"] = front_back

    changed_gain = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
    for frame_id, angle in enumerate(range(0, 360, 15)):
        changed_gain.add(DFMeasurement.create(
            angle_deg=angle, relative_power_db=-10.0 - angle / 20.0,
            frequency_hz=145_000_000.0, confidence=0.95, channel_bandwidth_hz=12_500.0,
            receiver_binding="gain-a" if angle != 345 else "gain-b", frame_id=frame_id,
        ))
    cases["receiver_binding_change"] = changed_gain
    return {name: model.estimate().status for name, model in cases.items()}


def build_report() -> dict[str, object]:
    grids = [evaluate_grid(step) for step in (45, 30, 15)]
    negative = negative_gate_statuses()
    passed = (
        grids[0]["status_counts"] == {"YETERSİZ AÇI": 360}
        and grids[1]["status_counts"] == {"YETERSİZ AÇI": 360}
        and grids[2]["status_counts"] == {"LOB HAZIR": 360}
        and float(grids[-1]["rms_error_deg"]) <= 5.0
        and negative == {
            "clustered_angles": "YETERSİZ AÇI KAPSAMI",
            "front_back_ambiguity": "ÖN/ARKA BELİRSİZ",
            "receiver_binding_change": "ALICI AYARI DEĞİŞTİ",
        }
    )
    return {
        "schema": "teknofest.phase09.amplitude-df-numeric.v1",
        "status": "passed" if passed else "failed",
        "method": "same-channel linear power by measured angle; raw argmax; no interpolation",
        "profile": {
            "id": FIELD_AMPLITUDE_DF_PROFILE.profile_id,
            "minimum_distinct_angles": FIELD_AMPLITUDE_DF_PROFILE.minimum_distinct_angles,
            "maximum_angular_gap_deg": FIELD_AMPLITUDE_DF_PROFILE.maximum_angular_gap_deg,
            "minimum_peak_prominence_db": FIELD_AMPLITUDE_DF_PROFILE.minimum_peak_prominence_db,
            "minimum_front_to_back_db": FIELD_AMPLITUDE_DF_PROFILE.minimum_front_to_back_db,
            "average_domain": "linear_power",
        },
        "rms_definition": "sqrt(mean(wrap180(estimated_deg - truth_deg)^2))",
        "uniform_grid_quantization_reference": "step_deg/sqrt(12); ideal uniform truth phase only",
        "grid_evaluations": grids,
        "negative_gate_statuses": negative,
        "source_sha256": {
            "algorithms/p0/df.py": digest(ROOT / "algorithms" / "p0" / "df.py"),
            "scripts/verify_phase09_amplitude_df.py": digest(Path(__file__)),
        },
        "claim_boundary": (
            "Deterministic independent angle-power scenes validate circular error, raw-maximum logic and "
            "fail-closed gates. They do not establish antenna, multipath or field RMS accuracy."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        try:
            expected = args.output.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"kanıt okunamadı: {exc}", file=sys.stderr)
            return 2
        if expected != payload:
            print("PHASE-09 genlik yön bulma kanıtı güncel kaynakla eşleşmiyor.", file=sys.stderr)
            return 1
        print(f"PASS: {args.output}")
        return 0 if report["status"] == "passed" else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(args.output)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
