#!/usr/bin/env python3
"""Validate the recorded same-machine UI performance A/B policy evidence."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from scipy.stats import mannwhitneyu


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "evidence" / "phase06g" / "ui-performance-characterization.json"
ALPHA = 0.05


def evaluate(document: dict[str, object]) -> dict[str, object]:
    baseline = document["baseline"]
    candidate = document["candidate"]
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise ValueError("baseline and candidate records are required")
    baseline_runs = baseline["runs"]
    candidate_runs = candidate["runs"]
    if not isinstance(baseline_runs, list) or not isinstance(candidate_runs, list):
        raise ValueError("run arrays are required")
    if len(baseline_runs) != 5 or len(candidate_runs) != 5:
        raise ValueError("policy requires exactly five baseline and five candidate runs")

    def validate_runs(runs: list[object]) -> list[int]:
        counts: list[int] = []
        for raw in runs:
            if not isinstance(raw, dict):
                raise ValueError("run record must be an object")
            if raw["exit_status"] != 0 or raw["test_passed"] is not True:
                raise ValueError("all characterization runs must finish and pass")
            ten = raw["ten_fps"]
            thirty = raw["thirty_fps"]
            if not isinstance(ten, dict) or not isinstance(thirty, dict):
                raise ValueError("both benchmark rates are required")
            if ten["rendered_frames"] < 12:
                raise ValueError("10 FPS functional floor failed")
            for metrics in (ten, thirty):
                if metrics["maximum_heartbeat_gap_ms"] >= 250.0:
                    raise ValueError("heartbeat bound failed")
                if metrics["waterfall_rows"] > 128:
                    raise ValueError("waterfall bound failed")
                if metrics["maximum_concurrent_tasks"] != 1:
                    raise ValueError("concurrency bound failed")
                if metrics["maximum_pending_intents"] > 1:
                    raise ValueError("queue bound failed")
                if metrics["active_tasks_after_stop"] != 0:
                    raise ValueError("stop cleanup bound failed")
            counts.append(int(thirty["rendered_frames"]))
        return counts

    baseline_counts = validate_runs(baseline_runs)
    candidate_counts = validate_runs(candidate_runs)
    baseline_median = float(statistics.median(baseline_counts))
    candidate_median = float(statistics.median(candidate_counts))
    statistic = mannwhitneyu(candidate_counts, baseline_counts, alternative="less", method="asymptotic")
    material_regression = candidate_median < baseline_median and float(statistic.pvalue) < ALPHA
    passed = not material_regression
    return {
        "status": "passed" if passed else "failed",
        "baseline_counts": baseline_counts,
        "candidate_counts": candidate_counts,
        "baseline_minimum": min(baseline_counts),
        "baseline_maximum": max(baseline_counts),
        "baseline_median": baseline_median,
        "candidate_minimum": min(candidate_counts),
        "candidate_maximum": max(candidate_counts),
        "candidate_median": candidate_median,
        "mann_whitney_u": float(statistic.statistic),
        "one_sided_p_value": float(statistic.pvalue),
        "alpha": ALPHA,
        "material_regression": material_regression,
    }


def check() -> bool:
    try:
        document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        observed = evaluate(document)
        return document["evaluation"] == observed and observed["status"] == "passed"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    passed = check()
    print(f"UI performance baseline policy: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
