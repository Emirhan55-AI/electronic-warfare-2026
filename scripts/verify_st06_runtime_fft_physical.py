#!/usr/bin/env python3
"""Exercise every supported FPGA FFT size with bounded digital I/Q traffic."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.p0 import (  # noqa: E402
    IQFrame,
    TCPClientIQTransport,
    decode_local_ed_response,
)
from algorithms.p0.detection_config import (  # noqa: E402
    DetectionProfile,
    exchange_profile,
)

FFT_SIZES = (4096, 8192, 16384)
WARMUP_FRAMES = 256


def _payload(fft_size: int, seed: int) -> bytes:
    generator = random.Random(seed)
    return bytes(generator.randrange(-48, 49) & 0xFF for _ in range(2 * fft_size))


def _exercise(host: str, port: int, fft_size: int, frame_count: int) -> dict:
    payload = _payload(fft_size, 0x53540602 ^ fft_size)
    transport = TCPClientIQTransport()
    responses = []
    measurement_started = None

    def receive(response) -> None:
        nonlocal measurement_started
        if response.sequence_number + 1 == WARMUP_FRAMES:
            measurement_started = time.perf_counter()
        elif response.sequence_number >= WARMUP_FRAMES:
            responses.append(response)

    try:
        transport.connect(host, port, timeout_seconds=10.0)
        frames = (
            IQFrame(index, 2_000_000, 101_500_000, payload, frame_id=index)
            for index in range(WARMUP_FRAMES + frame_count)
        )
        transport.exchange_stream(frames, receive)
    finally:
        transport.close()
    if measurement_started is None:
        raise RuntimeError("FFT hız ölçümü ısınma aralığını tamamlayamadı.")
    elapsed = time.perf_counter() - measurement_started
    decoded = [
        decode_local_ed_response(response.payload, response.sequence_number)
        for response in responses
    ]
    fps = len(decoded) / elapsed
    required_fps = 2_000_000 / fft_size
    response_digest = hashlib.sha256()
    for response in responses:
        response_digest.update(len(response.payload).to_bytes(4, "little"))
        response_digest.update(response.payload)
    stats = asdict(transport.stats)
    checks = {
        "all_frames_returned": len(decoded) == frame_count,
        "frame_ids_match": all(
            item.frame_id == WARMUP_FRAMES + index
            for index, item in enumerate(decoded)
        ),
        "dma_status_valid": all(item.dma_status_flags == 7 for item in decoded),
        "transport_integrity": (
            stats["crc_errors"] == 0
            and stats["sequence_errors"] == 0
            and stats["queue_drops"] == 0
        ),
        "network_rate_meets_realtime": fps >= required_fps,
    }
    return {
        "fft_size": fft_size,
        "iq_bytes_per_frame": len(payload),
        "warmup_frames": WARMUP_FRAMES,
        "frames": len(decoded),
        "elapsed_seconds": elapsed,
        "frames_per_second": fps,
        "required_frames_per_second": required_fps,
        "realtime_margin": fps / required_fps,
        "raw_candidate_total": sum(item.raw_candidate_count for item in decoded),
        "maximum_active_events": max((item.active_count for item in decoded), default=0),
        "stimulus_sha256": hashlib.sha256(payload).hexdigest(),
        "responses_sha256": response_digest.hexdigest(),
        "transport": stats,
        "checks": checks,
    }


def run(host: str, port: int, frame_count: int) -> dict:
    initial = exchange_profile(host, port)
    if not initial.runtime_fft_supported:
        raise RuntimeError("Kart imajı çalışma zamanı FPGA FFT seçimini desteklemiyor.")
    active = initial
    cases = []
    restore_error = None
    try:
        for fft_size in FFT_SIZES:
            active = exchange_profile(host, port, profile=DetectionProfile(
                active.generation,
                initial.alpha_q32,
                initial.weak_alpha_q32,
                fft_size,
                True,
            ))
            readback = exchange_profile(host, port)
            case = _exercise(host, port, fft_size, frame_count)
            case["profile"] = asdict(readback)
            case["checks"]["exact_profile_readback"] = readback == active
            cases.append(case)
    finally:
        try:
            current = exchange_profile(host, port)
            if (
                current.fft_size,
                current.alpha_q32,
                current.weak_alpha_q32,
            ) != (
                initial.fft_size,
                initial.alpha_q32,
                initial.weak_alpha_q32,
            ):
                exchange_profile(host, port, profile=DetectionProfile(
                    current.generation,
                    initial.alpha_q32,
                    initial.weak_alpha_q32,
                    initial.fft_size,
                    True,
                ))
        except Exception as exc:  # preserve the primary failure while recording restore state
            restore_error = str(exc)
    final = exchange_profile(host, port)
    checks = {
        "all_fft_sizes_exercised": [case["fft_size"] for case in cases] == list(FFT_SIZES),
        "all_case_checks_passed": all(
            all(case["checks"].values()) for case in cases
        ),
        "initial_profile_restored": (
            final.alpha_q32,
            final.weak_alpha_q32,
            final.fft_size,
        ) == (
            initial.alpha_q32,
            initial.weak_alpha_q32,
            initial.fft_size,
        ),
        "profile_generation_advanced": final.generation > initial.generation,
        "restore_error_absent": restore_error is None,
    }
    return {
        "schema": "phase08-st06-runtime-fft-physical-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "ZedBoard dynamic FPGA FFT profile plus bounded digital Ethernet/ARM/DMA/PL processing",
        "host": host,
        "port": port,
        "initial_profile": asdict(initial),
        "final_profile": asdict(final),
        "frame_count_per_size": frame_count,
        "cases": cases,
        "checks": checks,
        "restore_error": restore_error,
        "claim_boundary": {
            "hackrf_used": False,
            "rf_input_used": False,
            "pd_pfa_acceptance": False,
            "cold_boot_acceptance": False,
            "persistent_boot_files_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--frames", type=int, default=512)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 4 <= args.frames <= 16_384:
        parser.error("--frames 4..16384 aralığında olmalıdır")
    result = run(args.host, args.port, args.frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "cases": [
            {
                "fft_size": case["fft_size"],
                "frames_per_second": case["frames_per_second"],
                "realtime_margin": case["realtime_margin"],
                "checks": case["checks"],
            }
            for case in result["cases"]
        ],
        "checks": result["checks"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
