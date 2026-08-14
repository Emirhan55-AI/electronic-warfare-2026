"""Deterministic PHASE-06A AXI/golden vector construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .frame_stats import (
    ENERGY_WIDTH,
    ERROR_EARLY_TLAST,
    ERROR_MISSING_TLAST,
    FRAME_LENGTH,
    INDEX_WIDTH,
    POWER_WIDTH,
    SAMPLE_COUNT_WIDTH,
    AxisFrameStatsModel,
    frame_stats,
    pack_ci8_bytes,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE01_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _corner_vectors() -> list[tuple[str, tuple[int, ...]]]:
    zero = (0x0000,) * FRAME_LENGTH
    minimum = (0x8080,) * FRAME_LENGTH
    maximum = (0x7F7F,) * FRAME_LENGTH
    alternating = tuple(0x8080 if index % 2 == 0 else 0x7F7F for index in range(FRAME_LENGTH))
    impulse = tuple(0x8080 if index == 137 else 0 for index in range(FRAME_LENGTH))
    tie = tuple(0x7F7F if index in (23, 99) else 0 for index in range(FRAME_LENGTH))
    return [
        ("all_zero", zero),
        ("all_minimum", minimum),
        ("all_maximum", maximum),
        ("alternating_extrema", alternating),
        ("single_impulse", impulse),
        ("equal_two_peaks", tie),
    ]


def build_vector_files() -> tuple[dict[str, bytes], dict[str, object]]:
    source = PHASE01_DATA.read_bytes()
    words = pack_ci8_bytes(source)
    if len(words) != 4 * FRAME_LENGTH:
        raise ValueError("PHASE-01 fixture dört frame içermelidir.")
    phase01_results = [
        frame_stats(words[index * FRAME_LENGTH : (index + 1) * FRAME_LENGTH])
        for index in range(4)
    ]
    input_hex = "".join(f"{word:04x}\n" for word in words).encode("ascii")
    expected_mem = "".join(f"{result.packed72():018x}\n" for result in phase01_results).encode("ascii")

    corners = [
        {"vector_id": name, **frame_stats(vector).as_dict()}
        for name, vector in _corner_vectors()
    ]
    protocol = AxisFrameStatsModel()
    early_result = None
    for index in range(3):
        early_result = protocol.accept(0x0001, tlast=index == 2)
    missing = AxisFrameStatsModel()
    missing_result = None
    for _ in range(FRAME_LENGTH):
        missing_result = missing.accept(0, tlast=False)
    missing.accept(0, tlast=False)
    missing.accept(0, tlast=True)
    after_recovery = None
    for index in range(FRAME_LENGTH):
        after_recovery = missing.accept(0, tlast=index == FRAME_LENGTH - 1)
    if early_result is None or missing_result is None or after_recovery is None:
        raise AssertionError("Protocol vektörü sonuç üretmedi.")
    golden = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "frame_length": FRAME_LENGTH,
        "bit_widths": {
            "power": POWER_WIDTH,
            "energy": ENERGY_WIDTH,
            "peak_index": INDEX_WIDTH,
            "sample_count": SAMPLE_COUNT_WIDTH,
        },
        "tie_break": "first_peak_index",
        "phase01_frames": [
            {"frame_index": index, **result.as_dict()}
            for index, result in enumerate(phase01_results)
        ],
        "corner_vectors": corners,
        "protocol_vectors": {
            "early_tlast": early_result.as_dict(),
            "missing_tlast": missing_result.as_dict(),
            "late_tlast_recoveries": missing.late_tlast_recoveries,
            "after_recovery": after_recovery.as_dict(),
            "expected_error_codes": {
                "early_tlast": ERROR_EARLY_TLAST,
                "missing_tlast": ERROR_MISSING_TLAST,
            },
        },
    }
    golden_bytes = _canonical(golden)
    files = {
        "axis-input.hex": input_hex,
        "axis-expected.mem": expected_mem,
        "golden-vectors.json": golden_bytes,
    }
    manifest = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "claim_boundary": "Bit-doğru sentetik/fixture vektörleridir; RTL simülasyon veya FPGA sonucu değildir.",
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
