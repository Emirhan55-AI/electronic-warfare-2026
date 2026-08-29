"""Deterministic vectors for the complete P0 RTL candidate reducer."""

from __future__ import annotations

import hashlib

from .candidate_grouping import axis_candidate_records
from .p0_candidate_reducer import reduce_candidates
from .p0_os_cfar_vectors import canonical_bytes
from .p0_wideband_recovery_vectors import (
    FRAME_LENGTH,
    build_vector_files as build_wideband_files,
    selected_vectors,
)


def _pack_expected(natural: tuple[int, ...]) -> tuple[bytes, dict[str, object]]:
    result = reduce_candidates(natural)
    axis = axis_candidate_records(result.candidates)
    lines = []
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
        "os_candidates": len(result.os_candidates),
        "recovery_candidates": len(result.recovery_candidates),
        "semantic_candidates": len(result.candidates),
        "axis_records": len(axis),
        "candidates": [
            {
                "start_shifted_bin": candidate.start_shifted_bin,
                "end_shifted_bin": candidate.end_shifted_bin,
                "peak_shifted_bin": candidate.peak_shifted_bin,
                "coarse_span_bins": candidate.coarse_span_bins,
                "peak_power": candidate.peak_power,
                "regional_noise": candidate.regional_noise,
                "threshold": candidate.threshold,
            }
            for candidate in result.candidates
        ],
    }


def build_vector_files() -> dict[str, bytes]:
    expected = []
    counts = []
    rows = []
    for vector_id, natural, source in selected_vectors():
        payload, summary = _pack_expected(natural)
        expected.append(payload)
        counts.append(f"{int(summary['axis_records']):04x}\n".encode("ascii"))
        rows.append({"vector_id": vector_id, "source": source, **summary})
    files = {
        "candidate-expected.mem": b"".join(expected),
        "expected-record-counts.mem": b"".join(counts),
        "golden-vectors.json": canonical_bytes(
            {
                "schema_version": 1,
                "status": "passed",
                "frame_length": FRAME_LENGTH,
                "frame_count": len(rows),
                "output_records": sum(int(row["axis_records"]) for row in rows),
                "semantic_candidates": sum(int(row["semantic_candidates"]) for row in rows),
                "vectors": rows,
            }
        ),
    }
    shared_input = build_wideband_files()["axis-power-input.mem"]
    files["fixture-manifest.json"] = canonical_bytes(
        {
            "schema_version": 1,
            "status": "passed",
            "files": {
                name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in files.items()
            },
            "shared_axis_power_input": {
                "path": "datasets/fixtures/p0_wideband_recovery/axis-power-input.mem",
                "bytes": len(shared_input),
                "sha256": hashlib.sha256(shared_input).hexdigest(),
            },
        }
    )
    return files
