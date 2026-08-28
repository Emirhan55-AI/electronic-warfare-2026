"""Deterministic vectors for the P0 PL OS-CFAR cell-decision core."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from algorithms.p0.detection import OSCFARDetector, P0_DETECTOR_PROFILE

from .p0_os_cfar import (
    ALPHA_Q32,
    COEFFICIENT_FRACTION_BITS,
    FRAME_LENGTH,
    POWER_WIDTH,
    RADIUS,
    detect_frame,
    natural_to_shifted,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_POWER_SOURCE = ROOT / "datasets" / "fixtures" / "phase06f" / "real-power-expected.mem"
REAL_VECTOR_SOURCE = ROOT / "datasets" / "fixtures" / "phase06d" / "golden-vectors.json"


@dataclass(frozen=True)
class P0OSCFARVector:
    vector_id: str
    natural_power: tuple[int, ...]
    source: str = "deterministic synthetic UQ28.30 power"
    boundary_case: bool = False


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    if len(shifted) != FRAME_LENGTH:
        raise ValueError("Shifted vector 4096 hücre içermelidir.")
    return tuple(shifted[natural_to_shifted(index)] for index in range(FRAME_LENGTH))


def _with_shifted_values(baseline: int, replacements: dict[int, int]) -> tuple[int, ...]:
    shifted = [baseline] * FRAME_LENGTH
    for index, value in replacements.items():
        shifted[index] = value
    return _natural_from_shifted(shifted)


def _synthetic_vectors() -> list[P0OSCFARVector]:
    baseline = 1 << 30
    strong = 32 << 30
    threshold_floor = (baseline * ALPHA_Q32) >> COEFFICIENT_FRACTION_BITS

    duplicate_pattern = [baseline + ((index * 17) % 7) * 123 for index in range(FRAME_LENGTH)]
    duplicate_pattern[20] = strong
    duplicate_pattern[21] = strong + 1
    duplicate_pattern[1000] = strong + 2
    duplicate_pattern[4075] = strong + 3

    maximum = (1 << POWER_WIDTH) - 1
    extreme_pattern = [maximum if index % 5 else maximum - 1 for index in range(FRAME_LENGTH)]
    extreme_pattern[2048] = 0

    return [
        P0OSCFARVector("all_zero", tuple([0] * FRAME_LENGTH)),
        P0OSCFARVector("uniform_noise", tuple([baseline] * FRAME_LENGTH)),
        P0OSCFARVector(
            "multiple_tones",
            _with_shifted_values(
                baseline,
                {20: strong, 255: strong + 1, 2048: strong + 2, 4075: strong + 3},
            ),
        ),
        P0OSCFARVector(
            "excluded_shifted_edges",
            _with_shifted_values(baseline, {0: strong, 19: strong + 1, 4076: strong + 2, 4095: strong + 3}),
        ),
        P0OSCFARVector("duplicate_reference_transitions", _natural_from_shifted(duplicate_pattern)),
        P0OSCFARVector(
            "threshold_floor",
            _with_shifted_values(baseline, {1000: threshold_floor}),
            boundary_case=True,
        ),
        P0OSCFARVector(
            "threshold_floor_plus_one",
            _with_shifted_values(baseline, {1000: threshold_floor + 1}),
            boundary_case=True,
        ),
        P0OSCFARVector("extreme_unsigned_range", _natural_from_shifted(extreme_pattern)),
    ]


def _real_vectors() -> list[P0OSCFARVector]:
    powers = tuple(int(line, 16) for line in REAL_POWER_SOURCE.read_text(encoding="ascii").splitlines() if line)
    if len(powers) != 11 * FRAME_LENGTH:
        raise ValueError("Dondurulmuş PHASE-06F güç kaynağı 11 kare içermelidir.")
    metadata = json.loads(REAL_VECTOR_SOURCE.read_text(encoding="utf-8"))
    frame_by_name = {item["vector_id"]: int(item["frame_index"]) for item in metadata["vectors"]}
    selected = ("single_tone", "multiple_tones", "representative_hann")
    return [
        P0OSCFARVector(
            f"real_phase06f_{name}",
            powers[frame_by_name[name] * FRAME_LENGTH : (frame_by_name[name] + 1) * FRAME_LENGTH],
            source="frozen PHASE-06F AMD FFT linear-power output",
        )
        for name in selected
    ]


def p0_os_cfar_vectors() -> tuple[P0OSCFARVector, ...]:
    return tuple(_synthetic_vectors() + _real_vectors())


def _pack_input(vector: P0OSCFARVector) -> bytes:
    lines = []
    for natural_index, power in enumerate(vector.natural_power):
        word = power
        word |= natural_index << 58
        word |= int(natural_index == FRAME_LENGTH - 1) << 70
        lines.append(f"{word:018x}\n".encode("ascii"))
    return b"".join(lines)


def _pack_expected(vector: P0OSCFARVector) -> tuple[bytes, dict[str, object]]:
    fixed = detect_frame(vector.natural_power)
    expected = b"".join(f"{word:016x}\n".encode("ascii") for word in fixed.dma_words_natural)

    shifted = np.asarray(
        [vector.natural_power[index ^ 0x800] for index in range(FRAME_LENGTH)],
        dtype=np.float64,
    )
    floating = OSCFARDetector().process(shifted, frame_id=0)
    fixed_detected = np.asarray(fixed.detected_shifted, dtype=np.bool_)
    fixed_evaluated = np.asarray(fixed.evaluated_shifted, dtype=np.bool_)
    decision_difference = fixed_detected != floating.detections
    evaluated_difference = fixed_evaluated != np.isfinite(floating.threshold_power)
    return expected, {
        "vector_id": vector.vector_id,
        "source": vector.source,
        "boundary_case": vector.boundary_case,
        "evaluated_cells": int(np.count_nonzero(fixed_evaluated)),
        "fixed_detections": int(np.count_nonzero(fixed_detected)),
        "floating_detections": int(np.count_nonzero(floating.detections)),
        "decision_mismatches": int(np.count_nonzero(decision_difference)),
        "evaluation_mask_mismatches": int(np.count_nonzero(evaluated_difference)),
    }


def build_vector_files() -> dict[str, bytes]:
    vectors = p0_os_cfar_vectors()
    input_payload = b"".join(_pack_input(vector) for vector in vectors)
    expected_parts: list[bytes] = []
    comparisons: list[dict[str, object]] = []
    for vector in vectors:
        expected, comparison = _pack_expected(vector)
        expected_parts.append(expected)
        comparisons.append(comparison)
    expected_payload = b"".join(expected_parts)

    non_boundary_mismatches = sum(
        int(row["decision_mismatches"])
        for row in comparisons
        if not bool(row["boundary_case"])
    )
    evaluation_mask_mismatches = sum(int(row["evaluation_mask_mismatches"]) for row in comparisons)
    golden = {
        "profile": P0_DETECTOR_PROFILE.name,
        "status": "passed" if non_boundary_mismatches == 0 and evaluation_mask_mismatches == 0 else "failed",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(vectors),
        "samples": len(vectors) * FRAME_LENGTH,
        "synthetic_frames": sum(vector.source.startswith("deterministic") for vector in vectors),
        "real_phase06f_frames": sum(vector.source.startswith("frozen") for vector in vectors),
        "alpha_float64": P0_DETECTOR_PROFILE.threshold_coefficient,
        "alpha_q32": ALPHA_Q32,
        "acceptance_policy": {
            "integer_model_to_rtl": "bit-exact 64-bit DMA words",
            "float_to_fixed_non_boundary_decisions": "zero mismatches",
            "evaluation_mask": "zero mismatches",
            "boundary_cases": "reported separately without tolerance",
        },
        "vectors": comparisons,
        "non_boundary_decision_mismatches": non_boundary_mismatches,
        "evaluation_mask_mismatches": evaluation_mask_mismatches,
        "real_power_source": {
            "path": "datasets/fixtures/phase06f/real-power-expected.mem",
            "sha256": hashlib.sha256(REAL_POWER_SOURCE.read_bytes()).hexdigest(),
        },
    }
    golden_payload = canonical_bytes(golden)
    files = {
        "axis-power-input.mem": input_payload,
        "dma-expected.mem": expected_payload,
        "golden-vectors.json": golden_payload,
    }
    manifest = {
        "profile": P0_DETECTOR_PROFILE.name,
        "status": golden["status"],
        "files": {
            name: {"bytes": len(payload), "sha256": sha256_bytes(payload)}
            for name, payload in files.items()
        },
        "immutable_source": golden["real_power_source"],
    }
    files["fixture-manifest.json"] = canonical_bytes(manifest)
    return files
