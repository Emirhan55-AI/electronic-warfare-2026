#!/usr/bin/env python3
"""Verify the physical ST-06 PL/DMA and dual-core ARM pipeline profile."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-pipelined-dma-profile-v1.json"
CAPTURE = ROOT / "results/evidence/phase08/st06-pipelined-dma-profile-v1-runs.jsonl"
METADATA = ROOT / "results/evidence/phase08/st06-pipelined-dma-profile-v1-metadata.txt"
BINARY = ROOT / "build/p0/st06-dma-profile-arm-v1/p0-st06-dma-profile-run"
FIRMWARE = ROOT / "build/p0/st06-power-v2/firmware/p0-st06-full-power.bin"
INPUT = ROOT / "build/p0-throughput-physical/wideband-inputs/frame-0.ci8"
EXPECTED_BINARY_SHA256 = "6af0d5e71bc96463afecbbf99929573568ca6504c55fba797ec3665d7a5643b4"
EXPECTED_FIRMWARE_SHA256 = "61d42a482a47c9d46b3c165bc86d206a3cbb4f47db7517242f63b9f66f5f369a"
EXPECTED_INPUT_SHA256 = "2c40ece75dafd722b00d02a2f790bacf576664ae0e4bf789f281f7dc60206b11"
REQUIRED_FPS = 2_000_000 / 4096
FRAME_INTERVAL_MS = 1000.0 / REQUIRED_FPS
SOURCE_PATHS = (
    "platforms/embedded/p0/include/p0_dma_runtime.h",
    "platforms/embedded/p0/include/p0_st05_wideband.h",
    "platforms/embedded/p0/include/p0_st05_stream.h",
    "platforms/embedded/p0/include/p0_st06_power_runtime.h",
    "platforms/embedded/p0/src/p0_dma_runtime.c",
    "platforms/embedded/p0/src/p0_st05_wideband.c",
    "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
    "platforms/embedded/p0/src/p0_st05_stream.c",
    "platforms/embedded/p0/src/p0_st06_power_runtime.c",
    "platforms/embedded/p0/src/p0_st06_dma_profile_run.c",
    "scripts/verify_st06_pipelined_dma_profile.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in METADATA.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in values:
            raise ValueError("geçersiz fiziksel profil üst verisi")
        values[key] = value
    expected = {"fpga_state", "firmware", "kernel", "machine", "run_count"}
    if set(values) != expected:
        raise ValueError("fiziksel profil üst veri alanları değişmiş")
    return values


def _finite_positive(item: dict[str, Any], name: str) -> float:
    value = float(item.get(name, math.nan))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"geçersiz {name}")
    return value


def _runs() -> list[dict[str, Any]]:
    runs = [
        json.loads(line)
        for line in CAPTURE.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(runs) != 5:
        raise ValueError("beş fiziksel tekrar bekleniyordu")
    for run in runs:
        if run.get("schema") != "p0-st06-pipelined-dma-profile-v1":
            raise ValueError("beklenmeyen fiziksel profil şeması")
        if (
            run.get("queue_depth") != 4
            or run.get("warmup_frames") != 64
            or run.get("measured_frames") != 2000
            or run.get("completed_frames") != 2000
            or run.get("output_bytes_per_frame") != 32768
        ):
            raise ValueError("fiziksel profil çalışma zarfı değişmiş")
        required = _finite_positive(run, "required_frames_per_second")
        measured = _finite_positive(run, "measured_frames_per_second")
        margin = _finite_positive(run, "real_time_margin")
        elapsed = _finite_positive(run, "elapsed_seconds")
        process_cpu = _finite_positive(run, "process_cpu_seconds")
        core_equivalents = _finite_positive(run, "cpu_core_equivalents")
        dual_core_percent = _finite_positive(run, "dual_core_cpu_percent")
        if not math.isclose(required, REQUIRED_FPS, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("gerekli kare hızı değişmiş")
        if not math.isclose(margin, measured / required, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("gerçek zaman marjı tutarsız")
        if (
            core_equivalents > 2.05
            or not math.isclose(core_equivalents, process_cpu / elapsed, rel_tol=0.0, abs_tol=1e-6)
            or not math.isclose(dual_core_percent, core_equivalents * 50.0, rel_tol=0.0, abs_tol=1e-6)
        ):
            raise ValueError("işlemci kullanımı duvar saatiyle tutarsız")
        expected_status = "passed" if measured >= required else "failed"
        if run.get("status") != expected_status:
            raise ValueError("çalışma durumu ölçülen hızla tutarsız")
        for stage in ("dma_and_pl", "arm_decode_and_detector"):
            summary = run.get(stage, {})
            ordered = [
                _finite_positive(summary, name)
                for name in ("minimum_ms", "p50_ms", "p95_ms", "p99_ms", "maximum_ms")
            ]
            mean = _finite_positive(summary, "mean_ms")
            if ordered != sorted(ordered) or not ordered[0] <= mean <= ordered[-1]:
                raise ValueError(f"geçersiz {stage} gecikme özeti")
    return runs


def _aggregate(runs: list[dict[str, Any]], stage: str) -> dict[str, float]:
    values = [run[stage] for run in runs]
    return {
        "mean_of_mean_latency_ms": sum(float(item["mean_ms"]) for item in values) / len(values),
        "maximum_p95_latency_ms": max(float(item["p95_ms"]) for item in values),
        "maximum_p99_latency_ms": max(float(item["p99_ms"]) for item in values),
        "maximum_observed_latency_ms": max(float(item["maximum_ms"]) for item in values),
    }


def evaluate(generated_at_utc: str | None = None) -> dict[str, Any]:
    if _sha256(BINARY) != EXPECTED_BINARY_SHA256:
        raise ValueError("ARM profil ikilisi beklenen kaynak derlemesi değil")
    if _sha256(FIRMWARE) != EXPECTED_FIRMWARE_SHA256:
        raise ValueError("FPGA Manager ikilisi beklenen ST-06 imajı değil")
    if _sha256(INPUT) != EXPECTED_INPUT_SHA256 or INPUT.stat().st_size != 8192:
        raise ValueError("profil CI8 girdisi değişmiş")
    runs = _runs()
    metadata = _metadata()
    if (
        metadata["fpga_state"] != "operating"
        or metadata["firmware"] != "p0-st06-full-power.bin"
        or metadata["machine"] != "armv7l"
        or int(metadata["run_count"]) != len(runs)
    ):
        raise ValueError("kart üst verisi fiziksel çalışma zarfıyla uyuşmuyor")
    rates = [float(run["measured_frames_per_second"]) for run in runs]
    margins = [float(run["real_time_margin"]) for run in runs]
    core_equivalents = [float(run["cpu_core_equivalents"]) for run in runs]
    capacity_passed = all(rate >= REQUIRED_FPS for rate in rates)
    return {
        "schema": "phase08-st06-pipelined-dma-profile-v1",
        "status": "passed",
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "measurement_scope": "physical_pl_dma_plus_dual_core_arm_pipeline",
        "product_algorithm_changed": False,
        "st06_complete": False,
        "board": {
            "model": "Zynq Zed Development Board",
            "architecture": metadata["machine"],
            "kernel": metadata["kernel"],
            "fpga_manager_state": metadata["fpga_state"],
            "loaded_firmware": metadata["firmware"],
            "producer_affinity": "CPU0",
            "consumer_affinity": "CPU1",
            "queue_depth": 4,
        },
        "artifacts": {
            "binary_sha256": EXPECTED_BINARY_SHA256,
            "firmware_sha256": EXPECTED_FIRMWARE_SHA256,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "capture": str(CAPTURE.relative_to(ROOT)).replace("\\", "/"),
            "capture_sha256": _sha256(CAPTURE),
            "metadata": str(METADATA.relative_to(ROOT)).replace("\\", "/"),
            "metadata_sha256": _sha256(METADATA),
        },
        "deadline": {
            "sample_rate_hz": 2_000_000,
            "fft_size": 4096,
            "required_frames_per_second": REQUIRED_FPS,
            "frame_interval_ms": FRAME_INTERVAL_MS,
        },
        "measurement": {
            "run_count": len(runs),
            "measured_frames_per_run": 2000,
            "minimum_frames_per_second": min(rates),
            "mean_frames_per_second": sum(rates) / len(rates),
            "maximum_frames_per_second": max(rates),
            "minimum_real_time_margin": min(margins),
            "minimum_cpu_core_equivalents": min(core_equivalents),
            "mean_cpu_core_equivalents": sum(core_equivalents) / len(core_equivalents),
            "maximum_cpu_core_equivalents": max(core_equivalents),
            "maximum_dual_core_cpu_percent": max(core_equivalents) * 50.0,
            "dma_and_pl": _aggregate(runs, "dma_and_pl"),
            "arm_decode_and_detector": _aggregate(runs, "arm_decode_and_detector"),
        },
        "gates": {
            "measurement_integrity": True,
            "full_power_pl_loaded": True,
            "bounded_dual_core_pipeline_exercised": True,
            "sustained_end_to_end_real_time": capacity_passed,
            "product_lifecycle_integration": False,
            "controlled_rf_accuracy": False,
        },
        "source_sha256": {relative: _sha256(ROOT / relative) for relative in SOURCE_PATHS},
        "claim_boundary": [
            "The physical profile includes FPGA execution, DMA/driver copies, marked-power decode and the ST-05 ARM detector.",
            "It replays one recorded CI8 frame for throughput and does not prove live-RF detection accuracy or calibrated Pd/Pfa.",
            "Passing the sustained-rate gate does not integrate this path into the product service or complete ST-06.",
            "Any margin above 1.0 is reported as measured capacity, not reserved worst-case product headroom.",
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
        EVIDENCE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        recorded = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        report = evaluate(str(recorded["generated_at_utc"]))
        if report != recorded:
            raise AssertionError("ST-06 fiziksel boru hattı kanıtı kaynak veya ölçümle eşleşmiyor")
    print(json.dumps({"status": report["status"], "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
