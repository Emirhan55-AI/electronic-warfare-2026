"""Deterministic PHASE-06I packet and AXI64 vector generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reference.rtl.candidate_grouping import axis_candidate_records, group_detector_cells
from reference.rtl.candidate_vectors import grouping_vectors

from .candidate_transport import ABI_VERSION, MAX_FRAME_BYTES, decode_packet, encode_packet


ROOT = Path(__file__).resolve().parents[2]


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _candidate_axis_mem() -> tuple[bytes, list[dict[str, object]], bytes]:
    input_lines: list[bytes] = []
    packets: list[bytes] = []
    summaries: list[dict[str, object]] = []
    for frame_id, vector in enumerate(grouping_vectors()):
        semantic = group_detector_cells(vector.cells)
        for record in axis_candidate_records(semantic):
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
            input_lines.append(f"{word:058x}\n".encode("ascii"))
        packet = encode_packet(frame_id, semantic)
        decoded = decode_packet(packet)
        if decoded.candidates != semantic:
            raise AssertionError("PHASE-06I ABI round trip changed candidate semantics")
        packets.append(packet)
        summaries.append({
            "frame_id": frame_id,
            "vector_id": vector.vector_id,
            "candidate_count": len(semantic),
            "packet_bytes": len(packet),
            "crc32": f"{int.from_bytes(packet[-8:-4], 'little'):08x}",
        })
    return b"".join(input_lines), summaries, b"".join(packets)


def _axis64_mem(packet_stream: bytes, summaries: list[dict[str, object]]) -> bytes:
    lines: list[bytes] = []
    offset = 0
    for summary in summaries:
        size = int(summary["packet_bytes"])
        packet = packet_stream[offset:offset + size]
        offset += size
        for beat_offset in range(0, size, 8):
            word = int.from_bytes(packet[beat_offset:beat_offset + 8], "little")
            last = int(beat_offset + 8 == size)
            lines.append(f"{last:x}{word:016x}\n".encode("ascii"))
    if offset != len(packet_stream):
        raise AssertionError("packet stream accounting mismatch")
    return b"".join(lines)


def build_vector_files() -> dict[str, bytes]:
    candidate_input, summaries, packet_stream = _candidate_axis_mem()
    axis64 = _axis64_mem(packet_stream, summaries)
    golden = {
        "phase": "PHASE-06I",
        "status": "passed",
        "abi_version": ABI_VERSION,
        "frame_count": len(summaries),
        "input_candidate_axis_records": len(candidate_input.splitlines()),
        "semantic_candidates": sum(int(row["candidate_count"]) for row in summaries),
        "output_axis64_beats": len(axis64.splitlines()),
        "packet_stream_bytes": len(packet_stream),
        "maximum_frame_bytes": MAX_FRAME_BYTES,
        "frames": summaries,
    }
    files = {
        "candidate-axis-input.mem": candidate_input,
        "transport-axis64-expected.mem": axis64,
        "transport-packets.bin": packet_stream,
        "golden-vectors.json": canonical_bytes(golden),
    }
    files["fixture-manifest.json"] = canonical_bytes({
        "phase": "PHASE-06I",
        "status": "passed",
        "files": {
            name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            for name, payload in files.items()
        },
        "frozen_phase06h_source": {
            "path": "datasets/fixtures/phase06h/candidate-expected.mem",
            "sha256": hashlib.sha256((ROOT / "datasets/fixtures/phase06h/candidate-expected.mem").read_bytes()).hexdigest(),
        },
    })
    return files
