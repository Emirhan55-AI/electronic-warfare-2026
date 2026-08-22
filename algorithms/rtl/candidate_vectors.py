"""Deterministic PHASE-06H grouping fixtures and packed RTL vectors."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .candidate_grouping import axis_candidate_records, group_detector_cells
from .detector_vectors import detector_vectors
from .regional_detector import DetectorCell, FRAME_LENGTH, detect_frame, is_evaluated


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GroupingVector:
    vector_id: str
    cells: tuple[DetectorCell, ...]
    source: str


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _synthetic_cells(
    detections: dict[int, int], *, pfa_select: int = 1, evaluate_center: bool = True
) -> tuple[DetectorCell, ...]:
    cells: list[DetectorCell] = []
    for natural_index in range(FRAME_LENGTH):
        shifted_index = natural_index ^ 0x800
        evaluated = is_evaluated(shifted_index, evaluate_center)
        region = shifted_index >> 8
        noise = (1000 + region) if evaluated else 0
        threshold = (2000 + region) if evaluated else 0
        power = detections.get(shifted_index, threshold)
        detected = shifted_index in detections
        if detected and (not evaluated or power <= threshold):
            raise ValueError("Synthetic detection must be evaluated and strictly above threshold")
        cells.append(
            DetectorCell(
                natural_index=natural_index,
                shifted_index=shifted_index,
                region_index=region,
                input_power=power,
                median_twice=0,
                noise_power=noise,
                threshold_power=threshold,
                evaluated=evaluated,
                detected=detected,
                pfa_select=pfa_select,
                evaluate_center=evaluate_center,
            )
        )
    return tuple(cells)


def grouping_vectors() -> tuple[GroupingVector, ...]:
    maximum = {index: 10_000 + index for index in range(20, 4076, 3)}
    real = next(vector for vector in detector_vectors() if vector.vector_id == "real_phase06f_representative_hann")
    return (
        GroupingVector("no_candidate", _synthetic_cells({}), "synthetic grouping contract"),
        GroupingVector("one_bin", _synthetic_cells({100: 5000}), "synthetic grouping contract"),
        GroupingVector("multi_bin", _synthetic_cells({300: 5000, 301: 7000, 302: 6000}), "synthetic grouping contract"),
        GroupingVector("two_separated", _synthetic_cells({400: 5000, 401: 6000, 410: 7000}), "synthetic grouping contract"),
        GroupingVector("one_missing_bin_bridged", _synthetic_cells({500: 7000, 502: 8000}), "synthetic grouping contract"),
        GroupingVector("region_boundary", _synthetic_cells({767: 7000, 768: 8000}), "synthetic grouping contract"),
        GroupingVector("equal_peak_first_wins", _synthetic_cells({900: 9000, 901: 9000}), "synthetic grouping contract"),
        GroupingVector("first_evaluated", _synthetic_cells({20: 5000}), "synthetic grouping contract"),
        GroupingVector("last_evaluated", _synthetic_cells({4075: 5000}), "synthetic grouping contract"),
        GroupingVector("shifted_half_order", _synthetic_cells({30: 6000, 2050: 7000, 3000: 8000}), "synthetic grouping contract"),
        GroupingVector(
            "center_exclusion_bridged",
            _synthetic_cells({2047: 7000, 2049: 8000}, evaluate_center=False),
            "synthetic grouping contract",
        ),
        GroupingVector("maximum_candidate_count", _synthetic_cells(maximum), "synthetic architectural bound"),
        GroupingVector(
            "real_phase06g_representative_hann",
            detect_frame(real.natural_power, pfa_select=real.pfa_select, evaluate_center=real.evaluate_center).cells,
            "frozen PHASE-06G detector output",
        ),
    )


def _pack_input(vector: GroupingVector) -> bytes:
    lines: list[bytes] = []
    for cell in vector.cells:
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
        word |= int(cell.natural_index == FRAME_LENGTH - 1) << 266
        lines.append(f"{word:067x}\n".encode("ascii"))
    return b"".join(lines)


def _pack_expected(vector: GroupingVector) -> tuple[bytes, dict[str, object]]:
    candidates = group_detector_cells(vector.cells)
    axis = axis_candidate_records(candidates)
    lines: list[bytes] = []
    for record in axis:
        candidate = record.candidate
        word = 0
        if candidate is not None:
            word |= candidate.peak_power
            word |= candidate.start_shifted_bin << 58
            word |= candidate.end_shifted_bin << 70
            word |= candidate.peak_shifted_bin << 82
            word |= candidate.coarse_span_bins << 94
            word |= candidate.regional_noise << 106
            word |= candidate.threshold << 164
            word |= candidate.pfa_select << 226
            word |= int(candidate.evaluate_center) << 228
        word |= int(record.candidate_valid) << 229
        word |= int(record.tlast) << 230
        lines.append(f"{word:058x}\n".encode("ascii"))
    return b"".join(lines), {
        "vector_id": vector.vector_id,
        "source": vector.source,
        "detected_cells": sum(cell.detected for cell in vector.cells),
        "semantic_candidates": len(candidates),
        "axis_records": len(axis),
        "candidates": [
            {
                "start_shifted_bin": item.start_shifted_bin,
                "end_shifted_bin": item.end_shifted_bin,
                "peak_shifted_bin": item.peak_shifted_bin,
                "coarse_span_bins": item.coarse_span_bins,
                "peak_power": item.peak_power,
                "regional_noise": item.regional_noise,
                "threshold": item.threshold,
            }
            for item in candidates
        ],
    }


def build_vector_files() -> dict[str, bytes]:
    vectors = grouping_vectors()
    input_payload = b"".join(_pack_input(vector) for vector in vectors)
    expected_parts: list[bytes] = []
    summaries: list[dict[str, object]] = []
    for vector in vectors:
        payload, summary = _pack_expected(vector)
        expected_parts.append(payload)
        summaries.append(summary)
    expected_payload = b"".join(expected_parts)
    golden = {
        "phase": "PHASE-06H",
        "status": "passed",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(vectors),
        "input_records": len(vectors) * FRAME_LENGTH,
        "output_records": sum(int(row["axis_records"]) for row in summaries),
        "semantic_candidates": sum(int(row["semantic_candidates"]) for row in summaries),
        "vectors": summaries,
    }
    files = {
        "axis-detector-input.mem": input_payload,
        "candidate-expected.mem": expected_payload,
        "golden-vectors.json": canonical_bytes(golden),
    }
    files["fixture-manifest.json"] = canonical_bytes(
        {
            "phase": "PHASE-06H",
            "status": "passed",
            "files": {
                name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in files.items()
            },
            "frozen_phase06g_source": {
                "path": "datasets/fixtures/phase06g/detector-expected.mem",
                "sha256": hashlib.sha256(
                    (ROOT / "datasets/fixtures/phase06g/detector-expected.mem").read_bytes()
                ).hexdigest(),
            },
        }
    )
    return files
