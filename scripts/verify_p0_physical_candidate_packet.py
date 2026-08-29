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

from algorithms.ps.candidate_transport import CandidatePacket, decode_packet
from algorithms.ps.temporal_confirmation import AuthoritativeTemporalOracle, TemporalEvent
from algorithms.rtl.p0_candidate_reducer import reduce_candidates
from algorithms.rtl.p0_os_cfar_vectors import p0_os_cfar_vectors


INPUT_BYTES = 8_192
INPUT_SHA256 = "59260fed535cd19e02682fa01e8170c3ea19c0585fec8e2d838d6172d8b1f209"
REFERENCE_VECTOR = "real_phase06f_representative_hann"
SERVICE_FRAME_COUNT = 5


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def expected_reduction():
    vectors = {vector.vector_id: vector for vector in p0_os_cfar_vectors()}
    return reduce_candidates(vectors[REFERENCE_VECTOR].natural_power)


def _service_event(event: TemporalEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "state": event.state,
        "first_frame_id": event.first_frame_id,
        "last_seen_frame_id": event.last_seen_frame_id,
        "seen_count": event.seen_count,
        "observed_this_frame": event.observed_this_frame,
        "start_bin": event.candidate.start_shifted_bin,
        "end_bin": event.candidate.end_shifted_bin,
        "peak_bin": event.candidate.peak_shifted_bin,
        "peak_power_uq28_30": event.candidate.peak_power,
        "noise_power_uq28_30": event.candidate.regional_noise,
        "threshold_power_uq32_30": event.candidate.threshold,
    }


def expected_service_frames(packet_path: Path) -> list[dict[str, object]]:
    physical_packet = decode_packet(packet_path.read_bytes())
    candidates = physical_packet.candidates
    oracle = AuthoritativeTemporalOracle()
    frames: list[dict[str, object]] = []
    for request_frame_id in range(SERVICE_FRAME_COUNT):
        frame_candidates = candidates if request_frame_id < 3 else ()
        packet_frame_id = (physical_packet.frame_id + request_frame_id + 1) & 0xFFFF_FFFF
        frame = oracle.process(CandidatePacket(frame_id=packet_frame_id, candidates=frame_candidates))
        frames.append({
            "frame_id": request_frame_id,
            "raw_candidate_count": len(frame_candidates),
            "active_count": len(frame.active_events),
            "ended_count": len(frame.ended_events),
            "dropped_candidates": frame.dropped_candidates,
            "active": [_service_event(event) for event in frame.active_events],
            "ended": [_service_event(event) for event in frame.ended_events],
        })
    return frames


def verify_service(packet_path: Path, service_paths: list[Path]) -> dict[str, object]:
    if len(service_paths) != SERVICE_FRAME_COUNT:
        raise ValueError(f"fiziksel servis sonucu {SERVICE_FRAME_COUNT} kare içermelidir")
    expected_frames = expected_service_frames(packet_path)
    hashes: dict[str, str] = {}
    summaries: list[dict[str, object]] = []
    compared_fields = (
        "frame_id", "raw_candidate_count", "active_count", "ended_count",
        "dropped_candidates", "active", "ended",
    )
    for index, (expected, path) in enumerate(zip(expected_frames, service_paths, strict=True)):
        payload = path.read_bytes()
        actual = json.loads(payload.decode("utf-8"))
        if actual.get("dma_status_flags") != 7:
            raise AssertionError(f"servis karesi {index} DMA tamamlama bayrakları 0x7 değil")
        projected = {field: actual.get(field) for field in compared_fields}
        if projected != expected:
            raise AssertionError(f"servis karesi {index} zamansal referanstan farklı")
        hashes[path.name] = _sha256(payload)
        summaries.append({
            "frame_id": actual["frame_id"],
            "raw_candidate_count": actual["raw_candidate_count"],
            "active_count": actual["active_count"],
            "ended_count": actual["ended_count"],
        })
    return {
        "status": "passed",
        "rule": "2-of-3 confirmation; two consecutive missing frames expire a track",
        "dma_status_flags": 7,
        "event_field_equivalence": True,
        "frames": summaries,
        "physical_result_sha256": hashes,
    }


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
    parser.add_argument("--service-frame", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        result = verify(args.packet, args.input)
        if args.service_frame:
            result["service_lifecycle"] = verify_service(args.packet, args.service_frame)
    except (OSError, ValueError, AssertionError) as error:
        print(f"P0 fiziksel aday paketi doğrulanamadı: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
