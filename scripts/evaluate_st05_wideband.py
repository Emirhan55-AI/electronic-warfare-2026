"""Run the frozen ST-05 wideband reference holdout once and write evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.p0.detection import MultiscaleDetector
from algorithms.p0.st05_wideband import ST05_WIDEBAND_PROFILE, ST05WidebandDetector
from algorithms.p0.temporal import TemporalConfirmation


CONTRACT = ROOT / "config/st05_wideband_evaluation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile(scene: dict[str, Any], active: bool) -> np.ndarray:
    bins = np.arange(4096, dtype=np.float64)
    shape = scene["shape"]
    if shape == "flat":
        values = np.ones(4096, dtype=np.float64)
    elif shape == "slope_12db":
        values = np.power(10.0, np.linspace(-6.0, 6.0, 4096) / 10.0)
    elif shape == "step_12db":
        values = np.ones(4096, dtype=np.float64)
        values[2048:] = 10.0 ** 1.2
    elif shape == "supports":
        values = np.ones(4096, dtype=np.float64)
    else:
        raise ValueError(f"unknown scene shape: {shape}")
    if active:
        for start, stop, excess in scene.get("supports", []):
            values[int(start):int(stop)] += float(excess)
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0) or bins.size != values.size:
        raise AssertionError("invalid generated power profile")
    return values


def _frames(scene: dict[str, Any], *, seed: int, count: int) -> np.ndarray:
    active_frames = int(scene.get("active_frames", count))
    rng = np.random.default_rng(seed)
    records = []
    for frame_index in range(count):
        profile = _profile(scene, frame_index < active_frames)
        records.append(rng.exponential(scale=profile))
    return np.asarray(records, dtype=np.float64)


def _overlap_metrics(
    truth_start: int,
    truth_stop: int,
    observed_start: int,
    observed_end: int,
) -> tuple[float, float, float]:
    observed_stop = observed_end + 1
    intersection = max(0, min(truth_stop, observed_stop) - max(truth_start, observed_start))
    truth_width = truth_stop - truth_start
    observed_width = observed_stop - observed_start
    union = truth_width + observed_width - intersection
    coverage = intersection / truth_width
    iou = intersection / union if union else 0.0
    overreach = (observed_width - intersection) / truth_width
    return coverage, iou, overreach


def _current_candidates(frames: np.ndarray) -> tuple[Any, ...]:
    detector = MultiscaleDetector()
    tracker = TemporalConfirmation(association_tolerance_bins=8)
    confirmed: list[Any] = []
    reported_tracks: set[int] = set()
    for frame_index, frame in enumerate(frames):
        tracks = tracker.update(detector.recovery_candidates(frame), frame_id=frame_index)
        for item in tracks:
            if (
                item.state == "confirmed"
                and item.observed_this_frame
                and item.track_id not in reported_tracks
            ):
                confirmed.append(item.candidate)
                reported_tracks.add(item.track_id)
    return tuple(confirmed)


def _candidate_metrics(
    scene: dict[str, Any],
    candidates: tuple[Any, ...],
    *,
    decision: str,
    absolute_absence_supported: bool,
) -> dict[str, Any]:
    supports = [tuple(item) for item in scene.get("supports", [])]
    expected = scene["expected"]
    truth = [(int(start), int(stop)) for start, stop, _ in supports]
    pair_scores = []
    for start, stop in truth:
        pair_scores.append([
            _overlap_metrics(start, stop, int(item.start_bin), int(item.end_bin))
            for item in candidates
        ])
    assignments: dict[int, tuple[int, tuple[float, float, float]]] = {}
    used_candidates: set[int] = set()
    ranked_pairs = sorted(
        (
            (metrics[0], metrics[1], -metrics[2], truth_index, candidate_index, metrics)
            for truth_index, row in enumerate(pair_scores)
            for candidate_index, metrics in enumerate(row)
        ),
        reverse=True,
    )
    for coverage, _, _, truth_index, candidate_index, metrics in ranked_pairs:
        if coverage < 0.8 or truth_index in assignments or candidate_index in used_candidates:
            continue
        assignments[truth_index] = (candidate_index, metrics)
        used_candidates.add(candidate_index)
    matched = [truth_index in assignments for truth_index in range(len(truth))]
    boundary_successes = [
        truth_index in assignments
        and assignments[truth_index][1][0] >= 0.85
        and assignments[truth_index][1][2] <= 0.25
        for truth_index in range(len(truth))
    ]

    if expected == "detect_each":
        passed = bool(truth) and all(matched) and len(candidates) == len(truth)
        boundary_passed = bool(truth) and all(boundary_successes)
    elif expected == "merge_hull":
        hull_start = min(start for start, _ in truth)
        hull_stop = max(stop for _, stop in truth)
        hull = [
            _overlap_metrics(hull_start, hull_stop, int(item.start_bin), int(item.end_bin))
            for item in candidates
        ]
        best_hull = max(hull, key=lambda row: (row[0], row[1], -row[2]), default=(0.0, 0.0, math.inf))
        passed = len(candidates) == 1 and best_hull[0] >= 0.85 and best_hull[2] <= 0.25
        boundary_passed = passed
    elif expected == "retune_required":
        passed = decision == "retune_required" and not candidates
        boundary_passed = passed
    elif expected == "no_absolute_absence":
        passed = not absolute_absence_supported
        boundary_passed = passed
    elif expected == "no_candidate":
        passed = not candidates
        boundary_passed = passed
    else:
        raise ValueError(f"unknown expected result: {expected}")
    return {
        "candidate_count": len(candidates),
        "decision": decision,
        "absolute_absence_supported": absolute_absence_supported,
        "truth_matched": matched,
        "truth_boundaries_passed": boundary_successes,
        "passed": bool(passed),
        "boundary_passed": bool(boundary_passed),
    }


def _summarize(records: list[dict[str, Any]], method: str) -> dict[str, Any]:
    method_records = [item[method] | {"family": item["family"], "expected": item["expected"]} for item in records]
    by_family: dict[str, dict[str, Any]] = {}
    for family in sorted({item["family"] for item in method_records}):
        group = [item for item in method_records if item["family"] == family]
        by_family[family] = {
            "trials": len(group),
            "passed": sum(item["passed"] for item in group),
            "pass_rate": sum(item["passed"] for item in group) / len(group),
            "boundary_passed": sum(item["boundary_passed"] for item in group),
            "bounded_candidate_events": sum(item["candidate_count"] > 0 for item in group),
            "absolute_absence_claims": sum(item["absolute_absence_supported"] for item in group),
        }
    return {"families": by_family}


def evaluate(contract: dict[str, Any]) -> dict[str, Any]:
    frame_count = int(contract["frames_per_sequence"])
    trial_count = int(contract["trials_per_scene"])
    seed_base = int(contract["holdout_seed_base"])
    proposed = ST05WidebandDetector()
    records = []
    for scene_index, scene in enumerate(contract["scenes"]):
        for trial_index in range(trial_count):
            seed = seed_base + scene_index * 10_000 + trial_index
            frames = _frames(scene, seed=seed, count=frame_count)
            current_candidates = _current_candidates(frames)
            proposed_result = proposed.process(frames)
            records.append({
                "scene": scene["id"],
                "family": scene["family"],
                "expected": scene["expected"],
                "trial": trial_index,
                "seed": seed,
                "frame_power_sha256": hashlib.sha256(frames.tobytes()).hexdigest(),
                "current": _candidate_metrics(
                    scene,
                    current_candidates,
                    decision=("bounded_candidates" if current_candidates else "no_candidate"),
                    absolute_absence_supported=True,
                ),
                "proposed": _candidate_metrics(
                    scene,
                    proposed_result.candidates,
                    decision=proposed_result.decision,
                    absolute_absence_supported=proposed_result.absolute_absence_supported,
                ),
            })

    summaries = {
        "current": _summarize(records, "current"),
        "proposed": _summarize(records, "proposed"),
    }
    gates = contract["acceptance"]
    proposed_families = summaries["proposed"]["families"]
    gate_results = {
        "positive_detection": proposed_families["positive"]["pass_rate"] >= gates["minimum_detection_rate"],
        "positive_boundaries": (
            proposed_families["positive"]["boundary_passed"] / proposed_families["positive"]["trials"]
            >= gates["minimum_boundary_rate"]
        ),
        "strong_weak_separation": proposed_families["separation"]["pass_rate"] >= gates["minimum_separation_rate"],
        "close_merge": proposed_families["merge"]["pass_rate"] >= gates["minimum_merge_rate"],
        "temporal_positive": proposed_families["temporal_positive"]["pass_rate"] >= gates["minimum_temporal_rate"],
        "temporal_negative": proposed_families["temporal_negative"]["pass_rate"] >= gates["minimum_temporal_rate"],
        "negative_false_events": proposed_families["negative"]["bounded_candidate_events"] == gates["required_false_bounded_events"],
        "edge_retune": proposed_families["edge"]["pass_rate"] >= gates["required_edge_retune_rate"],
        "no_absolute_absence_claims": sum(
            family["absolute_absence_claims"] for family in proposed_families.values()
        ) == gates["required_absolute_absence_claims"],
    }
    selected = all(gate_results.values())
    sources = (
        "algorithms/p0/detection.py",
        "algorithms/p0/temporal.py",
        "algorithms/p0/st05_wideband.py",
        "scripts/evaluate_st05_wideband.py",
    )
    return {
        "schema": "phase08-st05-wideband-holdout-v2",
        "status": "python_reference_selected" if selected else "holdout_failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "st05_complete": selected,
        "st06_complete": False,
        "contract_sha256": _sha256(CONTRACT),
        "profile": asdict(ST05_WIDEBAND_PROFILE),
        "gate_results": gate_results,
        "summaries": summaries,
        "records": records,
        "source_sha256": {name: _sha256(ROOT / name) for name in sources},
        "supersedes": "results/evidence/phase08/st05-wideband-holdout-v1.json",
        "verifier_correction": "Distinct truth supports require distinct candidates; current baseline events are counted once per track.",
        "claim_boundary": contract["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-05 frozen wideband holdout evaluator")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        parser.error("Önceki ST-05 kanıtının üzerine yazılmaz.")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "frozen_before_holdout":
        parser.error("ST-05 değerlendirme sözleşmesi dondurulmamış.")
    report = evaluate(contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "st05_complete": report["st05_complete"],
        "gate_results": report["gate_results"],
    }, ensure_ascii=False))
    return 0 if report["st05_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
