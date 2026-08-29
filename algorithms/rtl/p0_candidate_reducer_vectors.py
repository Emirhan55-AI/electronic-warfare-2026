"""Deterministic vectors for the parallel P0 regional-median engine."""

from __future__ import annotations

import hashlib
import json

from .p0_candidate_reducer import reduce_candidates
from .p0_os_cfar_vectors import canonical_bytes, p0_os_cfar_vectors


FRAME_LENGTH = 4096


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    return tuple(shifted[index ^ 0x800] for index in range(FRAME_LENGTH))


def _selected_vectors() -> tuple[tuple[str, tuple[int, ...]], ...]:
    by_id = {vector.vector_id: vector.natural_power for vector in p0_os_cfar_vectors()}
    baseline = 1 << 30
    wideband = [baseline + ((index * 17) % 101) * 1000 for index in range(FRAME_LENGTH)]
    for index in range(700, 900):
        wideband[index] = 8 << 30
    return (
        ("all_zero", by_id["all_zero"]),
        ("multiple_tones", by_id["multiple_tones"]),
        ("extreme_unsigned_range", by_id["extreme_unsigned_range"]),
        ("real_phase06f_representative_hann", by_id["real_phase06f_representative_hann"]),
        ("wideband", _natural_from_shifted(wideband)),
    )


def build_vector_files() -> dict[str, bytes]:
    input_lines = []
    expected_lines = []
    rows = []
    for vector_id, natural in _selected_vectors():
        result = reduce_candidates(natural)
        for natural_index, power in enumerate(natural):
            word = power | (natural_index << 58)
            word |= int(natural_index == FRAME_LENGTH - 1) << 70
            input_lines.append(f"{word:018x}\n".encode("ascii"))
        for value in result.region_median_twice:
            expected_lines.append(f"{value:015x}\n".encode("ascii"))
        rows.append(
            {
                "vector_id": vector_id,
                "region_median_twice": list(result.region_median_twice),
            }
        )
    files = {
        "axis-power-input.mem": b"".join(input_lines),
        "region-median-twice-expected.mem": b"".join(expected_lines),
        "golden-vectors.json": canonical_bytes(
            {
                "schema_version": 1,
                "status": "passed",
                "frame_count": len(rows),
                "frame_length": FRAME_LENGTH,
                "regions_per_frame": 16,
                "vectors": rows,
            }
        ),
    }
    files["fixture-manifest.json"] = canonical_bytes(
        {
            "schema_version": 1,
            "status": "passed",
            "files": {
                name: {
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
                for name, payload in files.items()
            },
        }
    )
    return files
