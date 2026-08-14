"""Deterministic PHASE-06B coefficient and AXI vector construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .frame_stats import FRAME_LENGTH, pack_ci8_bytes
from .hann_window import (
    COEFFICIENT_FRACTION_BITS,
    OUTPUT_COMPONENT_WIDTH,
    OUTPUT_FRACTION_BITS,
    OUTPUT_WORD_WIDTH,
    quantized_hann_coefficients,
    unique_hann_coefficients,
    window_frame,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE01_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
SELECTED_INDICES = (0, 1, 6, 137, 2047, 2048, 2049, 4095)


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _words_bytes(words: tuple[int, ...], width: int) -> bytes:
    return b"".join(word.to_bytes(width, "little", signed=False) for word in words)


def _corner_frames() -> list[tuple[str, tuple[int, ...]]]:
    return [
        ("all_zero", (0x0000,) * FRAME_LENGTH),
        ("all_minimum", (0x8080,) * FRAME_LENGTH),
        ("all_maximum", (0x7F7F,) * FRAME_LENGTH),
        (
            "alternating_extrema",
            tuple(0x8080 if index % 2 == 0 else 0x7F7F for index in range(FRAME_LENGTH)),
        ),
        (
            "single_impulse",
            tuple(0x8080 if index == 137 else 0 for index in range(FRAME_LENGTH)),
        ),
        ("constant_complex", (0x40C0,) * FRAME_LENGTH),
    ]


def build_vector_files() -> tuple[dict[str, bytes], dict[str, object]]:
    source = PHASE01_DATA.read_bytes()
    source_words = pack_ci8_bytes(source)
    if len(source_words) != 4 * FRAME_LENGTH:
        raise ValueError("PHASE-01 fixture dört frame içermelidir.")
    frames = [
        (f"phase01_frame_{index}", source_words[index * FRAME_LENGTH : (index + 1) * FRAME_LENGTH])
        for index in range(4)
    ] + _corner_frames()
    coefficients = quantized_hann_coefficients()
    expected_frames = [window_frame(words, coefficients) for _, words in frames]
    input_words = tuple(word for _, words in frames for word in words)
    expected_words = tuple(word for words in expected_frames for word in words)
    coefficient_mem = "".join(f"{value:04x}\n" for value in unique_hann_coefficients()).encode("ascii")
    input_hex = "".join(f"{word:04x}\n" for word in input_words).encode("ascii")
    expected_mem = "".join(f"{word:08x}\n" for word in expected_words).encode("ascii")
    records = []
    for frame_index, ((vector_id, words), outputs) in enumerate(zip(frames, expected_frames, strict=True)):
        records.append(
            {
                "vector_id": vector_id,
                "frame_index": frame_index,
                "sample_offset": frame_index * FRAME_LENGTH,
                "sample_count": FRAME_LENGTH,
                "input_sha256": _sha256(_words_bytes(words, 2)),
                "output_sha256": _sha256(_words_bytes(outputs, 4)),
                "selected_outputs": [
                    {"sample_index": index, "word": f"{outputs[index]:08x}"}
                    for index in SELECTED_INDICES
                ],
            }
        )
    golden = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(frames),
        "total_samples": len(input_words),
        "coefficient_format": f"UQ1.{COEFFICIENT_FRACTION_BITS}",
        "output_component_format": f"SQ1.{OUTPUT_FRACTION_BITS}",
        "output_component_width": OUTPUT_COMPONENT_WIDTH,
        "output_word_width": OUTPUT_WORD_WIDTH,
        "rounding": "nearest_ties_away_from_zero",
        "overflow": "mathematically_bounded_no_saturation_no_wrap",
        "vectors": records,
    }
    golden_bytes = _canonical(golden)
    files = {
        "hann-coefficients.mem": coefficient_mem,
        "axis-input.hex": input_hex,
        "axis-expected.mem": expected_mem,
        "golden-vectors.json": golden_bytes,
    }
    manifest = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "claim_boundary": (
            "Sabit nokta Hann katsayıları ve bit-doğru vektörlerdir; FFT, sentez veya FPGA sonucu değildir."
        ),
        "source": {
            "file": "datasets/fixtures/phase01/known-tone-ci8.sigmf-data",
            "sha256": _sha256(source),
            "frames": 4,
        },
        "files": [
            {"file": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in files.items()
        ],
    }
    files["fixture-manifest.json"] = _canonical(manifest)
    return files, manifest
