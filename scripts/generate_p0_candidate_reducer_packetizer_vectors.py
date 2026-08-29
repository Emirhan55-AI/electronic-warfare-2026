#!/usr/bin/env python3
"""Generate the deterministic P0 reducer-to-PHASE-06I AXI64 fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.ps.candidate_transport import encode_packet
from algorithms.rtl.p0_candidate_reducer import reduce_candidates
from algorithms.rtl.p0_os_cfar_vectors import canonical_bytes
from algorithms.rtl.p0_wideband_recovery_vectors import selected_vectors


OUTPUT = ROOT / "datasets/fixtures/p0_candidate_reducer_packetizer"
INPUT = ROOT / "datasets/fixtures/p0_wideband_recovery/axis-power-input.mem"


def _packet_mem(packet: bytes) -> bytes:
    words = [packet[offset : offset + 8] for offset in range(0, len(packet), 8)]
    lines = []
    for index, word in enumerate(words):
        if len(word) != 8:
            raise AssertionError("PHASE-06I packet is not AXI64 aligned")
        observed = int.from_bytes(word, "little") | (int(index == len(words) - 1) << 64)
        lines.append(f"{observed:017x}\n".encode("ascii"))
    return b"".join(lines)


def build_vector_files() -> dict[str, bytes]:
    expected = []
    rows = []
    frame_id = 0
    for vector_id, natural, source in selected_vectors():
        result = reduce_candidates(natural)
        packet = encode_packet(frame_id, result.candidates)
        payload = _packet_mem(packet)
        expected.append(payload)
        rows.append(
            {
                "vector_id": vector_id,
                "source": source,
                "frame_id": frame_id,
                "candidate_count": len(result.candidates),
                "packet_bytes": len(packet),
                "axis64_beats": len(payload.splitlines()),
            }
        )
        frame_id += 1
    expected_payload = b"".join(expected)
    golden = canonical_bytes(
        {
            "schema_version": 1,
            "status": "passed",
            "frame_count": len(rows),
            "candidate_count": sum(row["candidate_count"] for row in rows),
            "axis64_beats": sum(row["axis64_beats"] for row in rows),
            "vectors": rows,
        }
    )
    manifest_files = {
        "transport-axis64-expected.mem": expected_payload,
        "golden-vectors.json": golden,
    }
    manifest = canonical_bytes(
        {
            "schema_version": 1,
            "status": "passed",
            "files": {
                name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in manifest_files.items()
            },
            "shared_axis_power_input": {
                "path": "datasets/fixtures/p0_wideband_recovery/axis-power-input.mem",
                "bytes": INPUT.stat().st_size,
                "sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
            },
        }
    )
    manifest_files["fixture-manifest.json"] = manifest
    return manifest_files


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = build_vector_files()
    for name, payload in files.items():
        (OUTPUT / name).write_bytes(payload)
    print(json.dumps(json.loads(files["golden-vectors.json"]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
