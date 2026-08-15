"""Deterministic PHASE-06J PS temporal-confirmation vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reference.ps.candidate_transport import CandidatePacket, decode_packet, encode_packet
from reference.ps.temporal_confirmation import AuthoritativeTemporalOracle
from reference.rtl.candidate_grouping import CandidateRecord


ROOT = Path(__file__).resolve().parents[2]
PHASE06I_STREAM = ROOT / "datasets" / "fixtures" / "phase06i" / "transport-packets.bin"
PHASE06I_GOLDEN = ROOT / "datasets" / "fixtures" / "phase06i" / "golden-vectors.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _candidate(bin_index: int, *, end: int | None = None, peak: int | None = None,
               power: int = 1000, noise: int = 100, threshold: int = 500,
               pfa: int = 0, center: bool = True) -> CandidateRecord:
    end_bin = bin_index if end is None else end
    return CandidateRecord(
        start_shifted_bin=bin_index,
        end_shifted_bin=end_bin,
        peak_shifted_bin=bin_index if peak is None else peak,
        peak_power=power,
        regional_noise=noise,
        threshold=threshold,
        pfa_select=pfa,
        evaluate_center=center,
    )


def _maximum_candidates() -> tuple[CandidateRecord, ...]:
    golden = json.loads(PHASE06I_GOLDEN.read_text(encoding="utf-8"))
    stream = PHASE06I_STREAM.read_bytes()
    offset = 0
    for row in golden["frames"]:
        size = int(row["packet_bytes"])
        packet = decode_packet(stream[offset:offset + size])
        if row["vector_id"] == "maximum_candidate_count":
            return packet.candidates
        offset += size
    raise AssertionError("frozen PHASE-06I maximum-candidate packet is missing")


def scenario_packets() -> tuple[tuple[str, tuple[CandidatePacket, ...]], ...]:
    c = _candidate
    return (
        ("zero_detections", tuple(CandidatePacket(i, ()) for i in range(3))),
        ("one_of_three_expiry", (
            CandidatePacket(0, (c(100),)), CandidatePacket(1, ()), CandidatePacket(2, ()),
        )),
        ("two_of_three_with_one_miss", (
            CandidatePacket(0, (c(120),)), CandidatePacket(1, ()), CandidatePacket(2, (c(122),)),
        )),
        ("three_of_three_moving", (
            CandidatePacket(0, (c(200),)), CandidatePacket(1, (c(201),)), CandidatePacket(2, (c(202),)),
        )),
        ("outside_tolerance_birth_and_expiry", (
            CandidatePacket(0, (c(300),)), CandidatePacket(1, (c(303),)), CandidatePacket(2, (c(303),)),
        )),
        ("ambiguous_equal_distance_event_id_tie", (
            CandidatePacket(0, (c(500, power=3000, noise=100), c(504, power=2000, noise=100))),
            CandidatePacket(1, (c(502, power=4000, noise=100), c(506, power=2500, noise=100))),
        )),
        ("nonconsecutive_frame_resets", (
            CandidatePacket(10, (c(700),)), CandidatePacket(11, (c(700),)), CandidatePacket(13, (c(700),)),
        )),
        ("uint32_frame_wrap_is_consecutive", (
            CandidatePacket(0xFFFF_FFFE, (c(800),)),
            CandidatePacket(0xFFFF_FFFF, (c(800),)),
            CandidatePacket(0, (c(800),)),
        )),
        ("ended_history_ring_eviction", (
            CandidatePacket(0, tuple(c(1000 + 3 * i, power=2000 + i) for i in range(64))),
            CandidatePacket(1, ()), CandidatePacket(2, ()),
            CandidatePacket(3, tuple(c(1200 + 3 * i, power=3000 + i) for i in range(64))),
            CandidatePacket(4, ()), CandidatePacket(5, ()),
            CandidatePacket(6, (c(1400, power=4000), c(1403, power=4001))),
            CandidatePacket(7, ()), CandidatePacket(8, ()),
        )),
        ("maximum_candidate_frame", (CandidatePacket(0, _maximum_candidates()),)),
    )


def build_vector_files() -> dict[str, bytes]:
    stream = bytearray()
    sequences: list[dict[str, object]] = []
    input_records = 0
    active_outputs = 0
    confirmed_outputs = 0
    ended_outputs = 0
    for sequence_id, packets in scenario_packets():
        oracle = AuthoritativeTemporalOracle()
        frames: list[dict[str, object]] = []
        for packet in packets:
            encoded = encode_packet(packet.frame_id, packet.candidates, status=packet.status)
            result = oracle.process(packet)
            frames.append({
                "frame_id": packet.frame_id,
                "candidate_count": len(packet.candidates),
                "packet_offset": len(stream),
                "packet_bytes": len(encoded),
                "expected": result.as_dict(),
            })
            stream.extend(encoded)
            input_records += len(packet.candidates)
            active_outputs += len(result.active_events)
            confirmed_outputs += sum(item.state == "confirmed" for item in result.active_events)
            ended_outputs += len(result.ended_events)
        sequences.append({"sequence_id": sequence_id, "frames": frames})
    golden = {
        "phase": "PHASE-06J",
        "status": "passed",
        "source": "reference/detection/pipeline.py DetectionPipeline._update_tracks",
        "sequence_count": len(sequences),
        "frame_count": sum(len(item[1]) for item in scenario_packets()),
        "candidate_records_checked": input_records,
        "active_event_outputs": active_outputs,
        "confirmed_event_outputs": confirmed_outputs,
        "ended_event_outputs": ended_outputs,
        "maximum_candidates": 1352,
        "maximum_active_tracks": 64,
        "sequences": sequences,
    }
    return {"golden-sequences.json": canonical_bytes(golden), "packets.bin": bytes(stream)}


def manifest(files: dict[str, bytes]) -> bytes:
    document = {
        "phase": "PHASE-06J",
        "status": "passed",
        "files": {
            name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())
        },
        "frozen_phase06i_source": {
            "path": "datasets/fixtures/phase06i/transport-packets.bin",
            "sha256": hashlib.sha256(PHASE06I_STREAM.read_bytes()).hexdigest(),
        },
    }
    return canonical_bytes(document)


def build_all_files() -> dict[str, bytes]:
    files = build_vector_files()
    files["fixture-manifest.json"] = manifest(files)
    return files
