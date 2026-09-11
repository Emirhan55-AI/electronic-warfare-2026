#!/usr/bin/env python3
"""Verify ST-05 decisions across the PL UQ28.30 power boundary."""

from __future__ import annotations

import argparse
import _ctypes
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from algorithms.p0.st05_wideband import ST05WidebandDetector
from scripts.evaluate_st05_wideband import CONTRACT, _frames
from scripts.verify_st06_wideband_c import (
    CResult,
    ST05_EVIDENCE,
    _close_library,
    _compile,
    _configure,
    _run_sequence,
)


DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-wideband-uq28-30-v6.json"
FRACTIONAL_BITS = 30
SCALE = 1 << FRACTIONAL_BITS
POWER_WIDTH = 58
MAXIMUM_REACHABLE_POWER = 1 << 57


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quantize(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scaled = np.rint(np.asarray(frames, dtype=np.float64) * SCALE)
    if not np.all(np.isfinite(scaled)) or np.any(scaled < 0.0):
        raise ValueError("invalid power for UQ28.30 conversion")
    if np.any(scaled > MAXIMUM_REACHABLE_POWER):
        raise OverflowError("power exceeds the proven PL reachable range")
    encoded = np.ascontiguousarray(scaled.astype(np.uint64))
    decoded = np.ascontiguousarray(encoded.astype(np.float64) / SCALE)
    return encoded, decoded


def _shape(result: Any) -> tuple[Any, ...]:
    return (
        result.decision,
        result.absolute_absence_supported,
        tuple(
            (
                item.start_bin,
                item.end_bin,
                item.peak_bin,
                item.observed_frames,
                item.total_frames,
            )
            for item in result.candidates
        ),
        tuple(
            (item.start_bin, item.end_bin, item.reason)
            for item in result.unresolved_supports
        ),
    )


def _stress_checks(function: Any, detector: ST05WidebandDetector) -> dict[str, Any]:
    vectors = {
        "all_zero": np.zeros((8, 4096), dtype=np.float64),
        "maximum_reachable": np.full(
            (8, 4096), MAXIMUM_REACHABLE_POWER / SCALE, dtype=np.float64
        ),
        "alternating_extremes": np.tile(
            np.asarray([0.0, MAXIMUM_REACHABLE_POWER / SCALE], dtype=np.float64),
            (8, 2048),
        ),
    }
    observed = {}
    for name, frames in vectors.items():
        _, mismatches, _, _ = _run_sequence(function, detector, frames)
        observed[name] = {"matched": not mismatches, "mismatches": mismatches}

    overflow_rejected = False
    try:
        _quantize(
            np.full(
                (8, 4096),
                (MAXIMUM_REACHABLE_POWER * 2) / SCALE,
                dtype=np.float64,
            )
        )
    except OverflowError:
        overflow_rejected = True
    return {
        "status": "passed"
        if all(item["matched"] for item in observed.values()) and overflow_rejected
        else "failed",
        "vectors": observed,
        "above_reachable_range_rejected": overflow_rejected,
    }


def evaluate() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    st05 = json.loads(ST05_EVIDENCE.read_text(encoding="utf-8"))
    recorded_hashes = {
        (item["scene"], int(item["trial"])): item["frame_power_sha256"]
        for item in st05["records"]
    }
    detector = ST05WidebandDetector()
    records: list[dict[str, Any]] = []
    quantized_shape_mismatches = 0
    c_shape_mismatches = 0
    corpus_hash_mismatches = 0
    maximum_input_error = 0.0
    maximum_encoded_power = 0
    mismatch_details: list[dict[str, Any]] = []
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="st06-uq28-30-") as raw:
        library_path, compiler, _ = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = _configure(library)
        stress = _stress_checks(function, detector)
        for scene_index, scene in enumerate(contract["scenes"]):
            for trial in range(int(contract["trials_per_scene"])):
                seed = int(contract["holdout_seed_base"]) + scene_index * 10_000 + trial
                frames = _frames(
                    scene,
                    seed=seed,
                    count=int(contract["frames_per_sequence"]),
                )
                frame_hash = hashlib.sha256(frames.tobytes()).hexdigest()
                corpus_hash_mismatches += int(
                    frame_hash != recorded_hashes[(scene["id"], trial)]
                )
                encoded, decoded = _quantize(frames)
                maximum_encoded_power = max(maximum_encoded_power, int(encoded.max()))
                maximum_input_error = max(
                    maximum_input_error,
                    float(np.max(np.abs(decoded - frames))),
                )
                floating = detector.process(frames)
                quantized = detector.process(decoded)
                quantized_match = _shape(floating) == _shape(quantized)
                c_record, c_mismatches, _, _ = _run_sequence(
                    function, detector, decoded
                )
                c_match = not c_mismatches
                quantized_shape_mismatches += int(not quantized_match)
                c_shape_mismatches += int(not c_match)
                records.append(
                    {
                        "scene": scene["id"],
                        "family": scene["family"],
                        "trial": trial,
                        "seed": seed,
                        "source_frame_sha256": frame_hash,
                        "encoded_frame_sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
                        "floating_to_uq28_30_shape_match": quantized_match,
                        "uq28_30_python_to_c_match": c_match,
                        "decision": quantized.decision,
                        "candidate_count": len(quantized.candidates),
                    }
                )
                if (not quantized_match or not c_match) and len(mismatch_details) < 32:
                    mismatch_details.append(
                        {
                            "scene": scene["id"],
                            "trial": trial,
                            "floating_shape": _shape(floating),
                            "quantized_shape": _shape(quantized),
                            "c": c_record,
                            "c_mismatches": c_mismatches,
                        }
                    )
        del function
        _close_library(library)

    elapsed = time.perf_counter() - started
    passed = (
        len(records) == len(recorded_hashes) == 960
        and corpus_hash_mismatches == 0
        and quantized_shape_mismatches == 0
        and c_shape_mismatches == 0
        and stress["status"] == "passed"
        and maximum_encoded_power <= MAXIMUM_REACHABLE_POWER
    )
    sources = (
        "algorithms/p0/st05_wideband.py",
        "config/st05_wideband_evaluation.json",
        "platforms/embedded/p0/include/p0_st05_wideband.h",
        "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
        "platforms/embedded/p0/src/p0_st05_wideband.c",
        "scripts/evaluate_st05_wideband.py",
        "scripts/verify_st06_wideband_c.py",
        "scripts/verify_st06_wideband_fixed_point.py",
        "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    )
    return {
        "schema": "phase08-st06-wideband-uq28-30-v6",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "st06_fixed_point_boundary_complete": passed,
        "st06_complete": False,
        "format": {
            "name": "UQ28.30 linear power",
            "word_bits": POWER_WIDTH,
            "fractional_bits": FRACTIONAL_BITS,
            "scale": SCALE,
            "maximum_reachable_raw": MAXIMUM_REACHABLE_POWER,
        },
        "corpus": {
            "source": "results/evidence/phase08/st05-wideband-holdout-v2.json",
            "sequences": len(records),
            "frames": len(records) * int(contract["frames_per_sequence"]),
            "source_hash_mismatches": corpus_hash_mismatches,
            "maximum_encoded_power_observed": maximum_encoded_power,
            "maximum_input_quantization_error": maximum_input_error,
            "half_lsb": 0.5 / SCALE,
        },
        "equivalence": {
            "floating_to_uq28_30_decision_or_shape_mismatches": quantized_shape_mismatches,
            "uq28_30_python_to_c_mismatches": c_shape_mismatches,
            "mismatch_details": mismatch_details,
        },
        "stress": stress,
        "compiler": compiler,
        "host_elapsed_seconds_observation": elapsed,
        "performance_claim": "none; this is not an ARM, RTL, DMA, or product throughput measurement",
        "records": records,
        "source_sha256": {name: _sha256(ROOT / name) for name in sources},
        "supersedes": "results/evidence/phase08/st06-wideband-uq28-30-v5.json",
        "verifier_correction": "V6 binds the decision-equivalent single-pass support grouping; lazy seed, median and representable-overflow corrections are retained.",
        "claim_boundary": [
            "This verifies decision and boundary stability after the existing PL UQ28.30 power quantization on the frozen synthetic corpus.",
            "The C detector still executes floating-point arithmetic after decoding; no claim of an all-integer ST-05 RTL implementation is made.",
            "ARM timing, RTL integration, DMA transport, live RF, Pd/Pfa, and product acceptance remain open.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 UQ28.30 boundary verifier")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        parser.error("Önceki ST-06 sabit nokta kanıtının üzerine yazılmaz.")
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "sequences": report["corpus"]["sequences"],
                "floating_to_uq28_30_mismatches": report["equivalence"][
                    "floating_to_uq28_30_decision_or_shape_mismatches"
                ],
                "uq28_30_python_to_c_mismatches": report["equivalence"][
                    "uq28_30_python_to_c_mismatches"
                ],
                "stress": report["stress"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
