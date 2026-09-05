#!/usr/bin/env python3
"""Verify real-ARM timing for marked PL power-frame decode plus ST-05."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-power-arm-timing-v1.json"
CAPTURE = ROOT / "results/evidence/phase08/st06-power-runtime-benchmark-v3-runs.jsonl"
REQUIRED_FPS = 2_000_000 / 4096
FRAME_INTERVAL_MS = 1000.0 / REQUIRED_FPS
EXPECTED_BINARY_SHA256 = (
    "a5265432b0f3fdef6a2dc23191a6235c78e2eb564c63af635642ddc705475894"
)
SOURCE_PATHS = (
    "platforms/embedded/p0/include/p0_pl_os_cfar.h",
    "platforms/embedded/p0/include/p0_st05_wideband.h",
    "platforms/embedded/p0/include/p0_st05_stream.h",
    "platforms/embedded/p0/include/p0_st06_power_runtime.h",
    "platforms/embedded/p0/src/p0_st05_wideband.c",
    "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
    "platforms/embedded/p0/src/p0_st05_stream.c",
    "platforms/embedded/p0/src/p0_st06_power_runtime.c",
    "platforms/embedded/p0/src/p0_st06_power_benchmark.c",
    "scripts/verify_st06_power_arm_benchmark.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runs() -> list[dict[str, Any]]:
    runs = [
        json.loads(line)
        for line in CAPTURE.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(runs) != 5:
        raise ValueError("beş fiziksel tekrar bekleniyordu")
    for run in runs:
        if run.get("schema") != "p0-st06-power-runtime-benchmark-v3":
            raise ValueError("beklenmeyen benchmark şeması")
        if run.get("warmup_frames") != 16 or run.get("measured_frames_per_scenario") != 256:
            raise ValueError("benchmark uzunluğu değişmiş")
        for scenario, checksum in (("noise", 265), ("wide_signal", 561030)):
            item = run.get(scenario, {})
            if item.get("checksum") != checksum:
                raise ValueError("karar sağlama toplamı değişmiş")
            for field in (
                "minimum_ms", "median_ms", "p95_ms", "p99_ms",
                "maximum_ms", "mean_ms", "frames_per_second",
            ):
                value = float(item.get(field, math.nan))
                if not math.isfinite(value) or value <= 0.0:
                    raise ValueError(f"geçersiz {scenario}.{field}")
    return runs


def _aggregate(runs: list[dict[str, Any]], scenario: str) -> dict[str, float]:
    values = [run[scenario] for run in runs]
    return {
        "minimum_frames_per_second": min(float(item["frames_per_second"]) for item in values),
        "mean_frames_per_second": sum(float(item["frames_per_second"]) for item in values) / len(values),
        "maximum_frames_per_second": max(float(item["frames_per_second"]) for item in values),
        "mean_of_mean_latency_ms": sum(float(item["mean_ms"]) for item in values) / len(values),
        "maximum_p95_latency_ms": max(float(item["p95_ms"]) for item in values),
        "maximum_p99_latency_ms": max(float(item["p99_ms"]) for item in values),
        "maximum_observed_latency_ms": max(float(item["maximum_ms"]) for item in values),
    }


def evaluate(generated_at_utc: str | None = None) -> dict[str, Any]:
    runs = _runs()
    noise = _aggregate(runs, "noise")
    wide = _aggregate(runs, "wide_signal")
    minimum_fps = min(
        noise["minimum_frames_per_second"], wide["minimum_frames_per_second"]
    )
    maximum_p99 = max(noise["maximum_p99_latency_ms"], wide["maximum_p99_latency_ms"])
    maximum_observed = max(
        noise["maximum_observed_latency_ms"], wide["maximum_observed_latency_ms"]
    )
    mean_capacity_passed = minimum_fps >= REQUIRED_FPS
    p99_deadline_passed = maximum_p99 <= FRAME_INTERVAL_MS
    every_observation_passed = maximum_observed <= FRAME_INTERVAL_MS
    return {
        "schema": "phase08-st06-power-arm-timing-v1",
        "status": "passed",
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "measurement_scope": "marked_power_decode_plus_arm_detector_kernel",
        "dma_transfer_included": False,
        "pl_full_power_image_loaded": False,
        "product_algorithm_changed": False,
        "st06_complete": False,
        "board": {
            "model": "Zynq Zed Development Board",
            "architecture": "armv7l",
            "cpu": "dual ARM Cortex-A9; ARMv7 part 0xc09",
            "kernel": "6.12.40-xilinx-g31626ef92ff1",
            "fpga_manager_state": "operating",
            "affinity": "scheduler default; taskset unavailable",
        },
        "build": {
            "compiler": "arm-linux-gnueabihf-gcc 11.4.0",
            "flags": [
                "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
                "-mcpu=cortex-a9", "-mfpu=neon", "-mfloat-abi=hard",
            ],
            "binary_sha256": EXPECTED_BINARY_SHA256,
        },
        "input": {
            "bytes_per_frame": 32768,
            "format": "4096 natural-order marked UQ28.30 power words",
            "capture": str(CAPTURE.relative_to(ROOT)).replace("\\", "/"),
            "capture_sha256": _sha256(CAPTURE),
            "run_count": len(runs),
            "measured_frames_per_scenario_per_run": 256,
        },
        "deadline": {
            "sample_rate_hz": 2_000_000,
            "fft_size": 4096,
            "required_frames_per_second": REQUIRED_FPS,
            "frame_interval_ms": FRAME_INTERVAL_MS,
        },
        "measurement": {
            "noise": noise,
            "wide_signal": wide,
            "minimum_mean_capacity_margin": minimum_fps / REQUIRED_FPS,
            "worst_case_remaining_budget_ms": FRAME_INTERVAL_MS - maximum_observed,
        },
        "gates": {
            "measurement_integrity": True,
            "isolated_mean_capacity": mean_capacity_passed,
            "isolated_p99_deadline": p99_deadline_passed,
            "every_observed_frame_deadline": every_observation_passed,
            "full_power_dma_integration": False,
            "pipelined_end_to_end_capacity": False,
            "product_lifecycle_integration": False,
        },
        "source_sha256": {relative: _sha256(ROOT / relative) for relative in SOURCE_PATHS},
        "claim_boundary": [
            "This real-board measurement includes marked 32 KiB frame decoding and the ST-05 ARM kernel.",
            "It excludes PL execution time, DMA transfer, driver copies, network transport, and product-service scheduling.",
            "Mean and p99 isolated capacity pass, but observed scheduler outliers exceed one frame interval.",
            "A bounded producer-consumer pipeline and sustained end-to-end card test are required before ST-06 acceptance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("--write veya --check seçeneklerinden tam biri gerekir")
    if args.write:
        if EVIDENCE.exists():
            raise FileExistsError(f"kanıt dosyası zaten var: {EVIDENCE}")
        report = evaluate()
        EVIDENCE.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        recorded = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        report = evaluate(str(recorded["generated_at_utc"]))
        if report != recorded:
            raise AssertionError("ST-06 güç/ARM kanıtı kaynak veya ölçümle eşleşmiyor")
    print(json.dumps({"status": report["status"], "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
