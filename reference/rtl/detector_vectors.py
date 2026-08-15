"""Deterministic PHASE-06G regional-detector vectors and comparisons."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from reference.detection.cfar import DetectorConfig, LinearPowerDetector

from .regional_detector import (
    FRAME_LENGTH,
    PFA_VALUES,
    POWER_MAX,
    REGION_SIZE,
    detect_frame,
    natural_to_shifted,
    regional_fixed_values,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_POWER_SOURCE = ROOT / "datasets" / "fixtures" / "phase06f" / "real-power-expected.mem"
REAL_VECTOR_SOURCE = ROOT / "datasets" / "fixtures" / "phase06d" / "golden-vectors.json"


@dataclass(frozen=True)
class DetectorVector:
    vector_id: str
    natural_power: tuple[int, ...]
    pfa_select: int = 1
    evaluate_center: bool = True
    source: str = "synthetic integer power"
    boundary_case: bool = False


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    if len(shifted) != FRAME_LENGTH:
        raise ValueError("Shifted vector 4096 bin olmalıdır.")
    return tuple(shifted[natural_to_shifted(index)] for index in range(FRAME_LENGTH))


def _shifted_uniform(value: int) -> list[int]:
    return [value] * FRAME_LENGTH


def _with_tones(base: int, tones: dict[int, int]) -> tuple[int, ...]:
    shifted = _shifted_uniform(base)
    for shifted_index, power in tones.items():
        shifted[shifted_index] = power
    return _natural_from_shifted(shifted)


def _synthetic_vectors() -> list[DetectorVector]:
    baseline = 1 << 30
    strong = 32 << 30
    _, default_threshold = regional_fixed_values(2 * baseline, 1)
    vectors = [
        DetectorVector("all_zero", tuple([0] * FRAME_LENGTH), pfa_select=0),
        DetectorVector("uniform_noise", tuple([baseline] * FRAME_LENGTH), pfa_select=2, evaluate_center=False),
        DetectorVector("one_strong_tone", _with_tones(baseline, {1000: strong})),
        DetectorVector("multiple_tones_different_regions", _with_tones(baseline, {300: strong, 1300: strong + 7, 2500: strong + 11, 3600: strong + 13})),
        DetectorVector("two_tones_same_region", _with_tones(baseline, {700: strong, 750: strong + 1})),
        DetectorVector("tones_at_region_boundaries", _with_tones(baseline, {255: strong, 256: strong + 1, 511: strong + 2, 512: strong + 3})),
        DetectorVector("shifted_positive_frequency_region", _with_tones(baseline, {2200: strong})),
        DetectorVector("shifted_negative_frequency_region", _with_tones(baseline, {1500: strong})),
        DetectorVector("excluded_first_twenty", _with_tones(baseline, {0: strong, 19: strong})),
        DetectorVector("excluded_last_twenty", _with_tones(baseline, {4076: strong, 4095: strong})),
        DetectorVector("threshold_equal", _with_tones(baseline, {1000: default_threshold}), boundary_case=True),
        DetectorVector("threshold_one_lsb_above", _with_tones(baseline, {1000: default_threshold + 1}), boundary_case=True),
        DetectorVector("threshold_one_lsb_below", _with_tones(baseline, {1000: default_threshold - 1}), boundary_case=True),
        DetectorVector("extreme_uq28_30", _with_tones(POWER_MAX, {20: 0, 2048: POWER_MAX}), pfa_select=2),
        DetectorVector("identical_values_center_excluded", tuple([17 << 30] * FRAME_LENGTH), pfa_select=0, evaluate_center=False),
    ]
    return vectors


def _real_vectors() -> list[DetectorVector]:
    powers = tuple(int(line, 16) for line in REAL_POWER_SOURCE.read_text(encoding="ascii").splitlines() if line)
    if len(powers) != 11 * FRAME_LENGTH:
        raise ValueError("Frozen PHASE-06F gerçek power kaynağı 11 frame içermelidir.")
    metadata = json.loads(REAL_VECTOR_SOURCE.read_text(encoding="utf-8"))
    by_name = {item["vector_id"]: int(item["frame_index"]) for item in metadata["vectors"]}
    selected = ("single_tone", "negative_frequency_tone", "multiple_tones", "two_tone", "representative_hann")
    return [
        DetectorVector(
            f"real_phase06f_{name}",
            powers[by_name[name] * FRAME_LENGTH : (by_name[name] + 1) * FRAME_LENGTH],
            source="frozen PHASE-06F real AMD FFT linear power",
        )
        for name in selected
    ]


def detector_vectors() -> tuple[DetectorVector, ...]:
    return tuple(_synthetic_vectors() + _real_vectors())


def _pack_input(vector: DetectorVector) -> bytes:
    lines = []
    for natural_index, power in enumerate(vector.natural_power):
        word = power
        word |= natural_index << 58
        word |= int(natural_index == FRAME_LENGTH - 1) << 70
        word |= vector.pfa_select << 71
        word |= int(vector.evaluate_center) << 73
        lines.append(f"{word:019x}\n".encode("ascii"))
    return b"".join(lines)


def _pack_expected(vector: DetectorVector) -> tuple[bytes, dict[str, object]]:
    result = detect_frame(
        vector.natural_power,
        pfa_select=vector.pfa_select,
        evaluate_center=vector.evaluate_center,
    )
    lines = []
    for cell in result.cells:
        word = cell.input_power
        word |= cell.natural_index << 58
        word |= cell.shifted_index << 70
        word |= cell.median_twice << 82
        word |= cell.noise_power << 141
        word |= cell.threshold_power << 199
        word |= int(cell.evaluated) << 261
        word |= int(cell.detected) << 262
        word |= cell.pfa_select << 263
        word |= int(cell.evaluate_center) << 265
        lines.append(f"{word:067x}\n".encode("ascii"))

    shifted_float = np.asarray(
        [vector.natural_power[index ^ 0x800] for index in range(FRAME_LENGTH)], dtype=np.float64
    )
    floating = LinearPowerDetector(
        DetectorConfig(
            method="regional",
            pfa=PFA_VALUES[vector.pfa_select],
            evaluate_center=vector.evaluate_center,
        )
    ).detect(shifted_float)
    fixed_shifted_detected = np.zeros(FRAME_LENGTH, dtype=np.bool_)
    fixed_shifted_threshold = np.zeros(FRAME_LENGTH, dtype=np.float64)
    for cell in result.cells:
        fixed_shifted_detected[cell.shifted_index] = cell.detected
        fixed_shifted_threshold[cell.shifted_index] = float(cell.threshold_power)
    decision_difference = fixed_shifted_detected != floating.detected_mask
    false_positive = int(np.count_nonzero(fixed_shifted_detected & ~floating.detected_mask))
    false_negative = int(np.count_nonzero(~fixed_shifted_detected & floating.detected_mask))
    threshold_error = np.abs(fixed_shifted_threshold - floating.threshold_power)
    evaluated = floating.evaluated_mask
    summary = {
        "vector_id": vector.vector_id,
        "source": vector.source,
        "pfa": PFA_VALUES[vector.pfa_select],
        "pfa_select": vector.pfa_select,
        "evaluate_center": vector.evaluate_center,
        "boundary_case": vector.boundary_case,
        "evaluated_cells": int(np.count_nonzero(evaluated)),
        "fixed_detections": int(np.count_nonzero(fixed_shifted_detected)),
        "floating_detections": int(np.count_nonzero(floating.detected_mask)),
        "decision_mismatches": int(np.count_nonzero(decision_difference)),
        "false_positive_differences": false_positive,
        "false_negative_differences": false_negative,
        "maximum_threshold_integer_error": float(np.max(threshold_error[evaluated])) if np.any(evaluated) else 0.0,
        "region_medians_twice": list(result.region_medians_twice),
        "region_noise": list(result.region_noise),
        "region_threshold": list(result.region_threshold),
    }
    return b"".join(lines), summary


def build_vector_files() -> dict[str, bytes]:
    vectors = detector_vectors()
    input_payload = b"".join(_pack_input(vector) for vector in vectors)
    expected_parts = []
    comparisons = []
    for vector in vectors:
        expected, comparison = _pack_expected(vector)
        expected_parts.append(expected)
        comparisons.append(comparison)
    expected_payload = b"".join(expected_parts)
    non_boundary_mismatches = sum(
        row["decision_mismatches"] for row in comparisons if not row["boundary_case"]
    )
    golden = {
        "phase": "PHASE-06G",
        "status": "passed" if non_boundary_mismatches == 0 else "failed",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(vectors),
        "samples": len(vectors) * FRAME_LENGTH,
        "synthetic_frames": sum(vector.source.startswith("synthetic") for vector in vectors),
        "real_phase06f_frames": sum(vector.source.startswith("frozen") for vector in vectors),
        "acceptance_policy": {
            "bit_true_to_rtl": "bit-exact all output fields",
            "float_to_fixed_non_boundary_decisions": "zero mismatches",
            "boundary_cases": "reported separately without post-hoc tolerance",
        },
        "vectors": comparisons,
        "non_boundary_decision_mismatches": non_boundary_mismatches,
        "real_power_source": {
            "path": "datasets/fixtures/phase06f/real-power-expected.mem",
            "sha256": hashlib.sha256(REAL_POWER_SOURCE.read_bytes()).hexdigest(),
        },
    }
    golden_payload = canonical_bytes(golden)
    files = {
        "axis-power-input.mem": input_payload,
        "detector-expected.mem": expected_payload,
        "golden-vectors.json": golden_payload,
    }
    manifest = {
        "phase": "PHASE-06G",
        "status": golden["status"],
        "files": {name: {"bytes": len(payload), "sha256": sha256_bytes(payload)} for name, payload in files.items()},
        "immutable_source": {
            "path": "datasets/fixtures/phase06f/real-power-expected.mem",
            "sha256": hashlib.sha256(REAL_POWER_SOURCE.read_bytes()).hexdigest(),
        },
    }
    files["fixture-manifest.json"] = canonical_bytes(manifest)
    return files
