#!/usr/bin/env python3
"""Verify the fixed-point P0 sparse-candidate reduction contract."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import MultiscaleDetector
from algorithms.ps.candidate_transport import decode_packet, encode_packet
from algorithms.rtl.candidate_grouping import CandidateRecord
from algorithms.rtl.p0_candidate_reducer import (
    FIXED_COEFFICIENT_BITS,
    INTEGRATED_THRESHOLD_Q48,
    NOISE_Q48,
    OS_THRESHOLD_Q48,
    REGIONAL_THRESHOLD_Q48,
    architecture_study,
    reduce_candidates,
)
from algorithms.rtl.p0_os_cfar_vectors import p0_os_cfar_vectors


EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-reference.json"
POWER_SCALE = 1 << 30


def _quantize(value: float) -> int:
    return int(math.floor(value * POWER_SCALE + 0.5))


def _floating_candidates(natural: tuple[int, ...]) -> tuple[CandidateRecord, ...]:
    shifted = np.asarray(
        [natural[index ^ 0x800] for index in range(4096)], dtype=np.float64
    ) / POWER_SCALE
    result = MultiscaleDetector().process(shifted, frame_id=0)
    return tuple(
        CandidateRecord(
            candidate.start_bin,
            candidate.end_bin,
            candidate.peak_bin,
            _quantize(candidate.peak_power),
            _quantize(candidate.noise_power_per_bin),
            _quantize(candidate.threshold_power),
            1,
            False,
        )
        for candidate in result.candidates
    )


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    return tuple(shifted[index ^ 0x800] for index in range(4096))


def _additional_vectors() -> tuple[tuple[str, tuple[int, ...]], ...]:
    baseline = 1 << 30
    sloped = [baseline + index * 10_000 for index in range(4096)]
    wideband = [baseline + ((index * 17) % 101) * 1000 for index in range(4096)]
    for index in range(700, 900):
        wideband[index] = 8 << 30
    two_wideband = [baseline + ((index * 29) % 127) * 2000 for index in range(4096)]
    for start, stop, level in ((500, 610, 7), (2800, 2960, 9)):
        for index in range(start, stop):
            two_wideband[index] = level << 30
    return (
        ("sloped_noise", _natural_from_shifted(sloped)),
        ("wideband", _natural_from_shifted(wideband)),
        ("two_wideband", _natural_from_shifted(two_wideband)),
    )


def evaluate() -> dict[str, object]:
    vectors = tuple(
        (vector.vector_id, vector.natural_power) for vector in p0_os_cfar_vectors()
    ) + _additional_vectors()
    rows = []
    mismatches = 0
    packet_mismatches = 0
    for frame_id, (vector_id, natural) in enumerate(vectors):
        reduced = reduce_candidates(natural)
        expected = _floating_candidates(natural)
        mismatch = reduced.candidates != expected
        mismatches += int(mismatch)
        packet = encode_packet(frame_id, reduced.candidates)
        decoded = decode_packet(packet)
        packet_mismatch = decoded.frame_id != frame_id or decoded.candidates != reduced.candidates
        packet_mismatches += int(packet_mismatch)
        rows.append(
            {
                "vector_id": vector_id,
                "candidate_count": len(reduced.candidates),
                "os_candidate_count": len(reduced.os_candidates),
                "recovery_candidate_count": len(reduced.recovery_candidates),
                "candidate_metadata_mismatch": mismatch,
                "phase06i_packet_mismatch": packet_mismatch,
            }
        )
    scale = 1 << FIXED_COEFFICIENT_BITS
    coefficient_errors = {
        "os_threshold": OS_THRESHOLD_Q48 / scale - 8.58014304069906,
        "regional_noise": NOISE_Q48 / scale - 1.0 / (2.0 * math.log(2.0)),
        "regional_threshold": REGIONAL_THRESHOLD_Q48 / scale - 5.0 / (4.0 * math.log(2.0)),
        "integrated_threshold": INTEGRATED_THRESHOLD_Q48 / scale - 40.0 / math.log(2.0),
    }
    coefficients_passed = all(abs(value) <= 0.5 / scale for value in coefficient_errors.values())
    passed = mismatches == 0 and packet_mismatches == 0 and coefficients_passed
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "P0 sparse final-candidate fixed-point reference",
        "profile": {
            "os_cfar": "P0_OS_CFAR_EXPONENTIAL_PFA_1E4",
            "region_bins": 256,
            "integration_bins": 32,
            "minimum_recovery_span_bins": 41,
            "maximum_gap_bins": 1,
            "fixed_coefficient_bits": FIXED_COEFFICIENT_BITS,
        },
        "equivalence": {
            "frames": len(vectors),
            "candidate_metadata_mismatches": mismatches,
            "phase06i_packet_mismatches": packet_mismatches,
            "vectors": rows,
        },
        "coefficient_error": coefficient_errors,
        "architecture": architecture_study(),
        "claim_boundary": (
            "Bit-true software reference and existing PHASE-06I packet reuse; "
            "SystemVerilog, synthesis, PetaLinux image, physical execution and real-time "
            "acceptance are not yet complete."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("P0 aday azaltıcı kanıtı eksik veya güncel değil.", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
