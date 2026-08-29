#!/usr/bin/env python3
"""Verify one physical P0 candidate packet against the frozen known-tone reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.ps.candidate_transport import decode_packet
from algorithms.rtl.p0_candidate_reducer import reduce_candidates
from algorithms.rtl.p0_os_cfar_vectors import p0_os_cfar_vectors


INPUT_BYTES = 8_192
INPUT_SHA256 = "59260fed535cd19e02682fa01e8170c3ea19c0585fec8e2d838d6172d8b1f209"
REFERENCE_VECTOR = "real_phase06f_representative_hann"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def expected_reduction():
    vectors = {vector.vector_id: vector for vector in p0_os_cfar_vectors()}
    return reduce_candidates(vectors[REFERENCE_VECTOR].natural_power)


def verify(packet_path: Path, input_path: Path) -> dict[str, object]:
    input_payload = input_path.read_bytes()
    if len(input_payload) != INPUT_BYTES:
        raise ValueError(f"CI8 giriş uzunluğu {INPUT_BYTES} bayt olmalıdır")
    input_sha256 = _sha256(input_payload)
    if input_sha256 != INPUT_SHA256:
        raise ValueError("CI8 giriş çerçevesi dondurulmuş bilinen-ton vektörü değil")

    packet_payload = packet_path.read_bytes()
    packet = decode_packet(packet_payload)
    expected = expected_reduction()
    exact_match = packet.candidates == expected.candidates
    passed = packet.status == 0 and exact_match

    result = {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "physical P0 known-tone candidate-packet equivalence",
        "input": {
            "bytes": len(input_payload),
            "sha256": input_sha256,
        },
        "packet": {
            "bytes": len(packet_payload),
            "sha256": _sha256(packet_payload),
            "frame_id": packet.frame_id,
            "status_flags": packet.status,
        },
        "reference": {
            "vector": REFERENCE_VECTOR,
            "os_candidates": len(expected.os_candidates),
            "recovery_candidates": len(expected.recovery_candidates),
            "final_candidates": len(expected.candidates),
        },
        "observed": {
            "final_candidates": len(packet.candidates),
            "candidate_field_equivalence": exact_match,
        },
        "claim_boundary": (
            "A passing result proves exact candidate-packet equivalence for one deterministic "
            "CI8 frame. It does not prove live-RF detection accuracy, calibrated RF units, "
            "sustained throughput or parameter-estimation accuracy."
        ),
    }
    if not passed:
        raise AssertionError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.packet, args.input)
    except (OSError, ValueError, AssertionError) as error:
        print(f"P0 fiziksel aday paketi doğrulanamadı: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
