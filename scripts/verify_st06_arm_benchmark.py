#!/usr/bin/env python3
"""Verify the isolated ST-06 detector timing measured on the ZedBoard ARM."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-arm-algorithm-timing-v2.json"
BASELINE_CAPTURE = ROOT / "results/evidence/phase08/st06-arm-benchmark-v1-runs.jsonl"
OPTIMIZED_CAPTURE = ROOT / "results/evidence/phase08/st06-arm-benchmark-v3-runs.jsonl"
C_EQUIVALENCE = ROOT / "results/evidence/phase08/st06-wideband-c-equivalence-v3.json"
UQ_EQUIVALENCE = ROOT / "results/evidence/phase08/st06-wideband-uq28-30-v4.json"
STREAM_EQUIVALENCE = ROOT / "results/evidence/phase08/st06-wideband-stream-v3.json"

SOURCE_PATHS = (
    "platforms/embedded/p0/include/p0_st05_wideband.h",
    "platforms/embedded/p0/include/p0_st05_stream.h",
    "platforms/embedded/p0/src/p0_st05_wideband.c",
    "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
    "platforms/embedded/p0/src/p0_st05_stream.c",
    "platforms/embedded/p0/src/p0_st05_benchmark.c",
    "scripts/verify_st06_arm_benchmark.py",
)

SAMPLE_RATE_HZ = 2_000_000
FFT_SIZE = 4096
REQUIRED_FRAMES_PER_SECOND = SAMPLE_RATE_HZ / FFT_SIZE
FRAME_INTERVAL_MS = 1000.0 / REQUIRED_FRAMES_PER_SECOND
EXPECTED_RUNS = 5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_capture(path: Path, schema: str, state_bytes: int) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    runs = [json.loads(line) for line in lines if line.strip()]
    if len(runs) != EXPECTED_RUNS:
        raise ValueError(f"{path.name}: {EXPECTED_RUNS} ölçüm bekleniyordu")
    for run in runs:
        if run.get("schema") != schema:
            raise ValueError(f"{path.name}: beklenmeyen ölçüm şeması")
        if run.get("warmup_frames") != 16 or run.get("measured_frames_per_scenario") != 256:
            raise ValueError(f"{path.name}: ölçüm uzunluğu değişmiş")
        if run.get("state_bytes") != state_bytes:
            raise ValueError(f"{path.name}: durum belleği değişmiş")
        for scenario, checksum in (("noise", 265), ("wide_signal", 561030)):
            measurement = run.get(scenario, {})
            if measurement.get("checksum") != checksum:
                raise ValueError(f"{path.name}: {scenario} karar sağlama toplamı değişmiş")
            for field in (
                "minimum_ms",
                "median_ms",
                "p95_ms",
                "p99_ms",
                "maximum_ms",
                "mean_ms",
                "frames_per_second",
            ):
                value = float(measurement.get(field, math.nan))
                if not math.isfinite(value) or value <= 0.0:
                    raise ValueError(f"{path.name}: {scenario}.{field} geçersiz")
    return runs


def _aggregate(runs: list[dict[str, Any]], scenario: str) -> dict[str, float]:
    measurements = [run[scenario] for run in runs]
    return {
        "minimum_frames_per_second": min(
            float(item["frames_per_second"]) for item in measurements
        ),
        "mean_frames_per_second": sum(
            float(item["frames_per_second"]) for item in measurements
        ) / len(measurements),
        "maximum_frames_per_second": max(
            float(item["frames_per_second"]) for item in measurements
        ),
        "mean_of_mean_latency_ms": sum(
            float(item["mean_ms"]) for item in measurements
        ) / len(measurements),
        "maximum_p95_latency_ms": max(float(item["p95_ms"]) for item in measurements),
        "maximum_p99_latency_ms": max(float(item["p99_ms"]) for item in measurements),
        "maximum_observed_latency_ms": max(
            float(item["maximum_ms"]) for item in measurements
        ),
    }


def evaluate(generated_at_utc: str | None = None) -> dict[str, Any]:
    baseline = _load_capture(
        BASELINE_CAPTURE, "p0-st06-arm-benchmark-v1", 262152
    )
    optimized = _load_capture(
        OPTIMIZED_CAPTURE, "p0-st06-arm-benchmark-v3", 328840
    )
    c_equivalence = _load_json(C_EQUIVALENCE)
    uq_equivalence = _load_json(UQ_EQUIVALENCE)
    stream_equivalence = _load_json(STREAM_EQUIVALENCE)
    baseline_wide = _aggregate(baseline, "wide_signal")
    optimized_noise = _aggregate(optimized, "noise")
    optimized_wide = _aggregate(optimized, "wide_signal")
    equivalence_passed = (
        c_equivalence.get("status") == "passed"
        and c_equivalence.get("equivalence", {}).get("sequence_mismatches") == 0
        and uq_equivalence.get("status") == "passed"
        and uq_equivalence.get("equivalence", {}).get(
            "floating_to_uq28_30_decision_or_shape_mismatches"
        ) == 0
        and uq_equivalence.get("equivalence", {}).get(
            "uq28_30_python_to_c_mismatches"
        ) == 0
        and stream_equivalence.get("status") == "passed"
        and stream_equivalence.get("stream_mismatches") == 0
    )
    isolated_timing_passed = (
        min(
            optimized_noise["minimum_frames_per_second"],
            optimized_wide["minimum_frames_per_second"],
        )
        >= REQUIRED_FRAMES_PER_SECOND
        and max(
            optimized_noise["maximum_observed_latency_ms"],
            optimized_wide["maximum_observed_latency_ms"],
        )
        <= FRAME_INTERVAL_MS
    )
    passed = equivalence_passed and isolated_timing_passed
    return {
        "schema": "phase08-st06-arm-algorithm-timing-v2",
        "status": "passed" if passed else "failed",
        "generated_at_utc": generated_at_utc
        or datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "measurement_scope": "isolated_arm_detector_kernel",
        "arm_algorithm_kernel_measured": True,
        "dma_transfer_included": False,
        "pl_full_power_image_loaded": False,
        "product_algorithm_changed": False,
        "st06_complete": False,
        "board": {
            "model": "Zynq Zed Development Board",
            "architecture": "armv7l",
            "cpu": "dual ARM Cortex-A9; ARMv7 part 0xc09",
            "cpu_features_observed": "vfp edsp neon vfpv3 vfpd32",
            "kernel": "6.12.40-xilinx-g31626ef92ff1",
            "fpga_manager_state": "operating",
            "cpu_frequency": "not exposed by this image",
            "affinity": "scheduler default; taskset unavailable",
        },
        "build": {
            "compiler": "arm-linux-gnueabihf-gcc 11.4.0",
            "flags": [
                "-std=c11",
                "-O3",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-mcpu=cortex-a9",
                "-mfpu=neon",
                "-mfloat-abi=hard",
            ],
            "baseline_binary_sha256":
                "920b38c03627c8be557260fe2b6077c19c92ee02bc16846c2bd84eef7009f43b",
            "optimized_binary_sha256":
                "d043ea18f2b6339ed37d02b5e0f1cd57e9beee95c7a7369c0d5b652aa8ce5f2b",
        },
        "deadline": {
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "fft_size": FFT_SIZE,
            "required_frames_per_second": REQUIRED_FRAMES_PER_SECOND,
            "frame_interval_ms": FRAME_INTERVAL_MS,
        },
        "baseline_context": {
            "capture": str(BASELINE_CAPTURE.relative_to(ROOT)).replace("\\", "/"),
            "capture_sha256": _sha256(BASELINE_CAPTURE),
            "wide_signal": baseline_wide,
        },
        "optimized_measurement": {
            "capture": str(OPTIMIZED_CAPTURE.relative_to(ROOT)).replace("\\", "/"),
            "capture_sha256": _sha256(OPTIMIZED_CAPTURE),
            "run_count": len(optimized),
            "noise": optimized_noise,
            "wide_signal": optimized_wide,
            "minimum_real_time_margin": min(
                optimized_noise["minimum_frames_per_second"],
                optimized_wide["minimum_frames_per_second"],
            )
            / REQUIRED_FRAMES_PER_SECOND,
            "worst_case_remaining_budget_ms": FRAME_INTERVAL_MS
            - max(
                optimized_noise["maximum_observed_latency_ms"],
                optimized_wide["maximum_observed_latency_ms"],
            ),
            "wide_signal_mean_speedup_over_baseline":
                baseline_wide["mean_of_mean_latency_ms"]
                / optimized_wide["mean_of_mean_latency_ms"],
        },
        "equivalence_evidence": {
            "c": str(C_EQUIVALENCE.relative_to(ROOT)).replace("\\", "/"),
            "uq28_30": str(UQ_EQUIVALENCE.relative_to(ROOT)).replace("\\", "/"),
            "stream": str(STREAM_EQUIVALENCE.relative_to(ROOT)).replace("\\", "/"),
            "passed": equivalence_passed,
        },
        "gates": {
            "decision_equivalence": equivalence_passed,
            "isolated_arm_kernel_real_time": isolated_timing_passed,
            "full_power_dma_integration": False,
            "sustained_end_to_end_real_time": False,
            "product_lifecycle_integration": False,
        },
        "source_sha256": {
            relative: _sha256(ROOT / relative) for relative in SOURCE_PATHS
        },
        "claim_boundary": [
            "Ölçüm gerçek ZedBoard ARM çekirdeğinde yapılmıştır.",
            "Ölçülen süre yalnızca sekiz karelik kayan ST-05 karar çekirdeğidir.",
            "32 KiB FPGA güç çerçevesinin DMA aktarımı ve ürün servis döngüsü bu ölçüme dahil değildir.",
            "Bu kayıt FPGA bit akışının karta yüklendiğini veya ST-06'nın tamamlandığını kanıtlamaz.",
            "Baz sürüm yalnızca aynı kartta ölçülen tarihsel binary karşılaştırmasıdır; kabul kararı optimize kaynak ve eşdeğerlik kanıtlarına bağlıdır.",
        ],
        "supersedes": "results/evidence/phase08/st06-arm-algorithm-timing-v1.json",
        "verifier_correction": (
            "v1 eşdeğerlik sayaçlarını kanıtın kökünden okudu; v2 sayaçları "
            "equivalence nesnesinden okuyarak aynı fiziksel ölçümleri doğru değerlendirir."
        ),
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
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        recorded = _load_json(EVIDENCE)
        report = evaluate(str(recorded["generated_at_utc"]))
        if report != recorded:
            raise AssertionError("ST-06 ARM zamanlama kanıtı kaynak veya girdilerle eşleşmiyor")
    print(
        json.dumps(
            {
                "status": report["status"],
                "minimum_frames_per_second": report["optimized_measurement"][
                    "wide_signal"
                ]["minimum_frames_per_second"],
                "maximum_observed_latency_ms": report["optimized_measurement"][
                    "wide_signal"
                ]["maximum_observed_latency_ms"],
                "minimum_real_time_margin": report["optimized_measurement"][
                    "minimum_real_time_margin"
                ],
                "end_to_end_gate": report["gates"]["sustained_end_to_end_real_time"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
