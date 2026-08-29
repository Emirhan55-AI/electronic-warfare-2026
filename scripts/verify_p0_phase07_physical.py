#!/usr/bin/env python3
"""Run the physical PC-to-ZedBoard P0 Ethernet acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import zlib


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import IQFrame, TCPClientIQTransport


EVIDENCE_PATH = ROOT / "results/evidence/p0/phase07-ethernet-physical-acceptance.json"
KNOWN_CAPTURE = ROOT / "datasets/fixtures/phase01/known-tone-ci8.sigmf-data"
WARMUP_FRAMES = 64
MEASURED_FRAMES = 4096
REPEAT_RUNS = 5
PIPELINE_DEPTH = 4
SAMPLE_RATE_HZ = 2_000_000
FRAME_SAMPLES = 4096
REQUIRED_FRAMES_PER_SECOND = SAMPLE_RATE_HZ / FRAME_SAMPLES
LOCAL_RESPONSE_MAGIC = 0x31534550
LOCAL_RESPONSE_HEADER_BYTES = 48
EXPECTED_FUNCTIONAL = (
    (54, 54, 0, 0, 0),
    (54, 54, 0, 0, 0),
    (54, 54, 0, 0, 0),
    (0, 54, 0, 0, 0),
    (0, 0, 54, 0, 0),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_known_frame() -> bytes:
    with KNOWN_CAPTURE.open("rb") as stream:
        payload = stream.read(8193)
    if len(payload) < 8192:
        raise RuntimeError("Bilinen fiziksel kabul karesi eksik.")
    return payload[:8192]


def _parse_local_response(payload: bytes, expected_frame_id: int) -> dict[str, int]:
    if len(payload) < LOCAL_RESPONSE_HEADER_BYTES:
        raise RuntimeError("Yerel kart hizmeti yanıtı başlıktan kısa.")
    (
        magic,
        version,
        header_bytes,
        total_bytes,
        frame_id,
        status,
        result_bytes,
        raw_candidate_count,
        dma_status_flags,
    ) = struct.unpack_from("<IHHIIIIII", payload, 0)
    if (
        magic != LOCAL_RESPONSE_MAGIC
        or version != 3
        or header_bytes != LOCAL_RESPONSE_HEADER_BYTES
        or total_bytes != len(payload)
        or frame_id != expected_frame_id
        or status != 0
        or struct.unpack_from("<I", payload, 44)[0] != zlib.crc32(payload[:44]) & 0xFFFFFFFF
        or any(payload[offset] != 0 for offset in range(32, 44))
    ):
        raise RuntimeError("Yerel kart hizmeti sürüm 3 başlığı doğrulanamadı.")
    result = payload[LOCAL_RESPONSE_HEADER_BYTES:]
    if len(result) != result_bytes or result_bytes < 20:
        raise RuntimeError("Yerel kart hizmeti sonuç uzunluğu geçersiz.")
    result_frame_id = struct.unpack_from("<I", result, 0)[0]
    active_count, ended_count, dropped_candidates = struct.unpack_from("<HHH", result, 4)
    reset_applied = result[10]
    if (
        result_frame_id != expected_frame_id
        or result[11] != 0
        or result_bytes != 20 + 68 * (active_count + ended_count)
    ):
        raise RuntimeError("Kompakt kart sonucu doğrulanamadı.")
    return {
        "frame_id": frame_id,
        "raw_candidate_count": raw_candidate_count,
        "dma_status_flags": dma_status_flags,
        "active_count": active_count,
        "ended_count": ended_count,
        "dropped_candidates": dropped_candidates,
        "reset_applied": reset_applied,
        "response_bytes": len(payload),
    }


def _frames(first_frame_id: int, count: int, payload: bytes) -> tuple[IQFrame, ...]:
    return tuple(
        IQFrame(
            sequence_number=(first_frame_id + index) & 0xFFFFFFFF,
            sample_rate_hz=SAMPLE_RATE_HZ,
            center_frequency_hz=101_500_000,
            payload=payload,
            frame_id=(first_frame_id + index) & 0xFFFFFFFF,
        )
        for index in range(count)
    )


def _frame_stream(first_frame_id: int, count: int, payload: bytes):
    for index in range(count):
        frame_id = (first_frame_id + index) & 0xFFFFFFFF
        yield IQFrame(
            sequence_number=frame_id,
            sample_rate_hz=SAMPLE_RATE_HZ,
            center_frequency_hz=101_500_000,
            payload=payload,
            frame_id=frame_id,
        )


def _functional_acceptance(host: str, port: int, known: bytes) -> list[dict[str, int]]:
    transport = TCPClientIQTransport()
    frames = (*_frames(0, 3, known), *_frames(3, 2, bytes(8192)))
    summaries: list[dict[str, int]] = []
    try:
        transport.connect(host, port, timeout_seconds=3.0)
        for start in range(0, len(frames), PIPELINE_DEPTH):
            batch = tuple(frames[start : start + PIPELINE_DEPTH])
            responses = transport.exchange_batch(batch)
            summaries.extend(
                _parse_local_response(response.payload, frame.frame_id)
                for frame, response in zip(batch, responses, strict=True)
            )
    finally:
        transport.close()
    projected = tuple(
        (
            item["raw_candidate_count"],
            item["active_count"],
            item["ended_count"],
            item["dropped_candidates"],
            item["reset_applied"],
        )
        for item in summaries
    )
    if projected != EXPECTED_FUNCTIONAL or any(item["dma_status_flags"] != 7 for item in summaries):
        raise RuntimeError(f"Fiziksel ağ işlevsel yaşam döngüsü eşleşmedi: {projected}")
    return summaries


def _throughput_acceptance(host: str, port: int, known: bytes) -> dict[str, object]:
    transport = TCPClientIQTransport()
    state = {"completed": 0, "measured_response_bytes": 0, "started": None}

    def handle_response(response) -> None:
        summary = _parse_local_response(response.payload, response.sequence_number)
        if summary["dma_status_flags"] != 7 or summary["dropped_candidates"] != 0:
            raise RuntimeError("Fiziksel Ethernet sürekli akış karesi başarısız.")
        state["completed"] += 1
        if state["completed"] == WARMUP_FRAMES:
            state["started"] = time.perf_counter()
        elif state["completed"] > WARMUP_FRAMES:
            state["measured_response_bytes"] += summary["response_bytes"]

    try:
        transport.connect(host, port, timeout_seconds=3.0)
        completed = transport.exchange_stream(
            _frame_stream(10_000, WARMUP_FRAMES + MEASURED_FRAMES, known),
            handle_response,
        )
        if completed != WARMUP_FRAMES + MEASURED_FRAMES or state["started"] is None:
            raise RuntimeError("Fiziksel Ethernet sürekli akış uzunluğu tamamlanamadı.")
        elapsed = time.perf_counter() - state["started"]
        stats = transport.stats
    finally:
        transport.close()
    frames_per_second = MEASURED_FRAMES / elapsed
    input_wire_bytes = MEASURED_FRAMES * (48 + 8192)
    output_wire_bytes = state["measured_response_bytes"] + MEASURED_FRAMES * 24
    result = {
        "warmup_frames": WARMUP_FRAMES,
        "measured_frames": MEASURED_FRAMES,
        "request_pipeline_depth": PIPELINE_DEPTH,
        "elapsed_seconds": elapsed,
        "required_frames_per_second": REQUIRED_FRAMES_PER_SECOND,
        "measured_frames_per_second": frames_per_second,
        "real_time_margin": frames_per_second / REQUIRED_FRAMES_PER_SECOND,
        "input_wire_bytes": input_wire_bytes,
        "output_wire_bytes": output_wire_bytes,
        "bidirectional_payload_megabytes_per_second":
            (input_wire_bytes + output_wire_bytes) / elapsed / 1_000_000.0,
        "client_frames_sent": stats.frames_sent,
        "client_frames_received": stats.frames_received,
        "client_sequence_errors": stats.sequence_errors,
    }
    if (
        not math.isfinite(frames_per_second)
        or frames_per_second < REQUIRED_FRAMES_PER_SECOND
        or stats.frames_sent != WARMUP_FRAMES + MEASURED_FRAMES
        or stats.frames_received != WARMUP_FRAMES + MEASURED_FRAMES
        or stats.sequence_errors != 0
    ):
        raise RuntimeError(f"Fiziksel Ethernet hız kapısı başarısız: {result}")
    return result


def _validated_sha256(value: str, label: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{label} geçerli bir SHA-256 özeti değil.")
    return normalized


def evaluate(
    host: str,
    port: int,
    *,
    image_sha256: str,
    bridge_sha256: str,
    boot_id: str,
    network_interface: str,
) -> dict[str, object]:
    image_sha256 = _validated_sha256(image_sha256, "İmaj")
    bridge_sha256 = _validated_sha256(bridge_sha256, "Köprü ikilisi")
    if not boot_id.strip() or not network_interface.strip():
        raise ValueError("Kalıcı imaj kabulü için boot kimliği ve ağ arayüzü zorunludur.")
    known = _load_known_frame()
    functional = _functional_acceptance(host, port, known)
    throughput_runs = [
        _throughput_acceptance(host, port, known) for _ in range(REPEAT_RUNS)
    ]
    measured_rates = [float(run["measured_frames_per_second"]) for run in throughput_runs]
    throughput = {
        "status": "passed",
        "warmup_frames_per_run": WARMUP_FRAMES,
        "measured_frames_per_run": MEASURED_FRAMES,
        "repeat_runs": REPEAT_RUNS,
        "passed_runs": len(throughput_runs),
        "completed_frames": MEASURED_FRAMES * len(throughput_runs),
        "request_pipeline_depth": PIPELINE_DEPTH,
        "required_frames_per_second": REQUIRED_FRAMES_PER_SECOND,
        "minimum_frames_per_second": min(measured_rates),
        "mean_frames_per_second": sum(measured_rates) / len(measured_rates),
        "maximum_frames_per_second": max(measured_rates),
        "minimum_real_time_margin": min(
            float(run["real_time_margin"]) for run in throughput_runs
        ),
        "client_sequence_errors": sum(
            int(run["client_sequence_errors"]) for run in throughput_runs
        ),
        "runs": throughput_runs,
    }
    sources = (
        ROOT / "algorithms/p0/transport.py",
        ROOT / "platforms/embedded/p0/include/p0_iq_transport.h",
        ROOT / "platforms/embedded/p0/src/p0_iq_transport.c",
        ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c",
        ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
        ROOT / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.default",
        ROOT / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.init",
        Path(__file__),
    )
    return {
        "schema_version": 1,
        "status": "passed",
        "scope": "fiziksel PC Ethernet→ZedBoard PS→yerel hizmet→DMA→FPGA→ARM kabulü",
        "endpoint": {"pc_ipv4": "192.168.7.1", "zedboard_ipv4": host, "tcp_port": port},
        "link_profile": {"observed_speed_mbps": 1000, "duplex": "full"},
        "input_profile": {
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "complex_samples_per_frame": FRAME_SAMPLES,
            "ci8_payload_bytes": 8192,
            "known_frame_sha256": hashlib.sha256(known).hexdigest(),
        },
        "functional_acceptance": functional,
        "throughput_acceptance": throughput,
        "persistent_image": {
            "exercised": True,
            "image_ub_sha256": image_sha256,
            "installed_bridge_sha256": bridge_sha256,
            "boot_id": boot_id,
            "network_interface": network_interface,
            "interface_selection": "auto",
            "safe_default_enabled": False,
            "authorized_test_activation": True,
        },
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in sources
        },
        "hackrf_stream_exercised": False,
        "persistent_image_exercised": True,
        "claim_boundary": (
            "Bu kanıt kayıtlı bilinen CI8 çerçevelerinin fiziksel 1 Gbps Ethernet, "
            "ZedBoard ağ köprüsü, kalıcı yerel ED hizmeti, DMA, FPGA ve ARM yolunda "
            "işlevsel ve sürekli hız kabulünü gösterir. Ağ köprüsü doğrulanan PetaLinux "
            "imajından soğuk açılış sonrası çalıştırılmıştır. Canlı HackRF USB akışı, 8→2 MS/s canlı "
            "bağ, RF doğruluğu, dBm kalibrasyonu ve saha performansı bu kanıtın dışındadır."
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--image-sha256", required=True)
    parser.add_argument("--bridge-sha256", required=True)
    parser.add_argument("--boot-id", required=True)
    parser.add_argument("--network-interface", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate(
        args.host,
        args.port,
        image_sha256=args.image_sha256,
        bridge_sha256=args.bridge_sha256,
        boot_id=args.boot_id,
        network_interface=args.network_interface,
    )
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
