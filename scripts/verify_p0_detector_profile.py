"""Verify the canonical P0 OS-CFAR profile and empirical false-alarm behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0 import P0_DETECTOR_PROFILE, OSCFARDetector, os_cfar_false_alarm_probability


EVIDENCE_PATH = ROOT / "results" / "evidence" / "p0" / "detector-profile.json"
FRAME_LENGTH = 4096
RADIUS = P0_DETECTOR_PROFILE.reference_cells_per_side + P0_DETECTOR_PROFILE.guard_cells_per_side
Z_99 = 2.5758293035489004


def _scenario_results() -> list[dict[str, object]]:
    detector = OSCFARDetector()
    rng = np.random.default_rng(7301)
    scenarios: list[tuple[str, np.ndarray, tuple[int, ...], str]] = []

    noise = rng.exponential(1.0, FRAME_LENGTH)
    scenarios.append(("noise-only", noise, (), "bounded_false_alarm"))

    strong = rng.exponential(1.0, FRAME_LENGTH)
    strong[2048] = 100.0
    scenarios.append(("single-strong-narrow", strong, (2048,), "all_targets"))

    near = np.ones(FRAME_LENGTH, dtype=np.float64)
    near[2048] = np.nextafter(P0_DETECTOR_PROFILE.threshold_coefficient, np.inf)
    scenarios.append(("weak-near-threshold", near, (2048,), "all_targets"))

    adjacent = rng.exponential(1.0, FRAME_LENGTH)
    adjacent[1800] = 90.0
    adjacent[1805] = 75.0
    scenarios.append(("two-adjacent-signals", adjacent, (1800, 1805), "separate_targets"))

    wide = rng.exponential(1.0, FRAME_LENGTH)
    wide[2396:2405] += 80.0
    scenarios.append(("wide-signal", wide, tuple(range(2396, 2405)), "wide_support"))

    edge = rng.exponential(1.0, FRAME_LENGTH)
    edge[RADIUS] = 100.0
    scenarios.append(("edge-signal", edge, (RADIUS,), "all_targets"))

    interferers = rng.exponential(1.0, FRAME_LENGTH)
    interferers[2000] = 100.0
    for index in (1978, 1980, 1982, 1984, 2016, 2018, 2020):
        interferers[index] += 20.0
    scenarios.append(("multiple-local-interferers", interferers, (2000,), "all_targets"))

    changing = np.concatenate((rng.exponential(1.0, FRAME_LENGTH // 2), rng.exponential(4.0, FRAME_LENGTH // 2)))
    changing[1024] = 100.0
    changing[3072] = 400.0
    scenarios.append(("changing-local-noise-floor", changing, (1024, 3072), "all_targets"))

    output: list[dict[str, object]] = []
    for frame_id, (name, power, targets, rule) in enumerate(scenarios):
        result = detector.process(power, frame_id=frame_id)
        detected = set(int(index) for index in np.flatnonzero(result.detections))
        if rule == "bounded_false_alarm":
            passed = len(detected) <= 3
        elif rule == "separate_targets":
            passed = all(target in detected for target in targets) and len(result.candidates) >= 2
        elif rule == "wide_support":
            passed = sum(target in detected for target in targets) >= 5
        else:
            passed = all(target in detected for target in targets)
        output.append(
            {
                "scenario": name,
                "target_bins": list(targets),
                "detected_target_count": sum(target in detected for target in targets),
                "total_detection_count": len(detected),
                "candidate_count": len(result.candidates),
                "status": "passed" if passed else "failed",
            }
        )
    return output


def _empirical_false_alarm() -> dict[str, object]:
    rng = np.random.default_rng(20260816)
    false_alarms = 0
    evaluated_cells = 0
    profile = P0_DETECTOR_PROFILE
    window_size = 2 * RADIUS + 1
    for _ in range(8):
        power = rng.exponential(1.0, (32, FRAME_LENGTH))
        windows = np.lib.stride_tricks.sliding_window_view(power, window_size, axis=1)
        references = np.concatenate(
            (
                windows[:, :, : profile.reference_cells_per_side],
                windows[:, :, RADIUS + profile.guard_cells_per_side + 1 :],
            ),
            axis=2,
        )
        statistic = np.partition(references, profile.order_statistic_rank - 1, axis=2)[:, :, profile.order_statistic_rank - 1]
        cuts = power[:, RADIUS:-RADIUS]
        false_alarms += int(np.count_nonzero(cuts > profile.threshold_coefficient * statistic))
        evaluated_cells += int(cuts.size)
    observed = false_alarms / evaluated_cells
    denominator = 1.0 + Z_99 * Z_99 / evaluated_cells
    center = (observed + Z_99 * Z_99 / (2.0 * evaluated_cells)) / denominator
    half_width = Z_99 * np.sqrt(
        observed * (1.0 - observed) / evaluated_cells + Z_99 * Z_99 / (4.0 * evaluated_cells * evaluated_cells)
    ) / denominator
    lower = float(center - half_width)
    upper = float(center + half_width)
    return {
        "distribution_assumption": "independent identically distributed exponential square-law power",
        "frame_count": 256,
        "evaluated_cell_count": evaluated_cells,
        "false_alarm_count": false_alarms,
        "configured_pfa": profile.desired_pfa,
        "observed_false_alarm_probability": observed,
        "confidence_method": "two-sided 99% Wilson interval",
        "confidence_lower": lower,
        "confidence_upper": upper,
        "acceptance": "configured Pfa must lie inside the finite-sample 99% interval",
        "status": "passed" if lower <= profile.desired_pfa <= upper else "failed",
    }


def evaluate() -> dict[str, object]:
    profile = P0_DETECTOR_PROFILE
    scenarios = _scenario_results()
    false_alarm = _empirical_false_alarm()
    theoretical = os_cfar_false_alarm_probability(
        profile.threshold_coefficient,
        profile.reference_count,
        profile.order_statistic_rank,
    )
    passed = false_alarm["status"] == "passed" and all(item["status"] == "passed" for item in scenarios)
    return {
        "schema_version": 1,
        "checkpoint": "P0 Mandatory Closure Block A",
        "status": "passed" if passed else "failed",
        "method": {
            "ktr_intent": "OS-CFAR local adaptive detection",
            "ktr_numeric_constants": "not specified",
        },
        "engineering_profile": {
            "name": profile.name,
            "reference_cells_per_side": profile.reference_cells_per_side,
            "guard_cells_per_side": profile.guard_cells_per_side,
            "reference_count": profile.reference_count,
            "order_statistic_rank": profile.order_statistic_rank,
            "desired_pfa": profile.desired_pfa,
            "threshold_coefficient": profile.threshold_coefficient,
            "theoretical_pfa_recomputed": theoretical,
            "edge_policy": profile.edge_policy,
            "comparison_rule": profile.comparison_rule,
            "coefficient_equation": "Pfa(alpha)=product(i=0..k-1)((N-i)/(N-i+alpha))",
        },
        "deterministic_scenarios": scenarios,
        "empirical_false_alarm": false_alarm,
        "claim_boundary": "Host mathematical evidence under the stated exponential-noise model; not live RF, ARM, or ZedBoard execution.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    else:
        if not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
            print("detector profile evidence is missing or stale", file=sys.stderr)
            return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
