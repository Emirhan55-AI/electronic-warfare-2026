"""Deterministic manual amplitude-DF acceptance fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0 import DFMeasurement, ManualAmplitudeDF


SCENES = (
    ("clear-single-maximum", 60.0, ((0, -30, .9), (30, -20, .9), (60, -8, .95), (90, -19, .9), (120, -29, .9))),
    ("flat-noisy-pattern", None, ((0, -20.0, .4), (90, -20.2, .4), (180, -19.9, .4), (270, -20.1, .4))),
    ("two-close-maxima", 45.0, ((0, -25, .8), (30, -16, .8), (45, -10, .8), (60, -10.3, .8), (90, -17, .8))),
    ("low-snr", 120.0, ((0, -42, .2), (60, -41, .2), (120, -39.5, .2), (180, -41.2, .2), (240, -42.1, .2))),
    ("missing-truth-angle", 180.0, ((90, -25, .7), (150, -12, .7), (210, -13, .7), (270, -24, .7))),
    ("duplicate-angle", 270.0, ((180, -25, .8), (270, -9, .9), (270, -11, .7), (0, -22, .8), (90, -27, .8))),
    ("zero-360-wrap", 0.0, ((350, -11, .9), (0, -8, .9), (10, -10, .9), (180, -30, .9))),
)


def evaluate() -> dict[str, object]:
    results = []
    estimates: list[float] = []
    truths: list[float] = []
    overall = True
    for scene_id, truth, points in SCENES:
        model = ManualAmplitudeDF()
        for index, (angle, power, confidence) in enumerate(points):
            model.add(DFMeasurement.create(angle_deg=angle, relative_power_db=power, frequency_hz=145_000_000.0, confidence=confidence, timestamp_utc=f"2026-01-01T00:00:{index:02d}Z"))
        estimate = model.estimate()
        error = None if truth is None else model.angular_error_deg(estimate.estimated_angle_deg, truth)
        tolerance = 30.0 if scene_id == "missing-truth-angle" else 0.0
        if scene_id in {"flat-noisy-pattern", "two-close-maxima", "low-snr", "missing-truth-angle"}:
            status_ok = estimate.status == "BELİRSİZ MAKSİMUM"
        else:
            status_ok = estimate.status == "LOB HAZIR"
        passed = status_ok and (error is None or error <= tolerance)
        overall = overall and passed
        if truth is not None:
            estimates.append(estimate.estimated_angle_deg)
            truths.append(truth)
        results.append({"fixture": scene_id, "ground_truth_deg": truth, "estimated_deg": estimate.estimated_angle_deg, "raw_maximum_deg": estimate.raw_maximum_angle_deg, "angular_error_deg": error, "tolerance_deg": tolerance if truth is not None else None, "confidence": estimate.confidence, "df_status": estimate.status, "status": "passed" if passed else "failed"})
    rms = ManualAmplitudeDF.rms_error_deg(estimates, truths)
    return {"schema_version": 1, "status": "passed" if overall else "failed", "algorithm": "raw amplitude argmax; no interpolation", "scenes": results, "rms_error_deg": rms, "claim_boundary": "Deterministic angle-power fixtures; not a calibrated antenna or live RF field test."}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
