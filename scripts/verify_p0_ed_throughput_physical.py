#!/usr/bin/env python3
"""Verify the pre-registered physical P0 sustained-throughput acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEASURED_FRAMES = 4096
WARMUP_FRAMES = 64
SAMPLE_RATE_HZ = 2_000_000
FRAME_SAMPLES = 4096
REQUIRED_FRAMES_PER_SECOND = SAMPLE_RATE_HZ / FRAME_SAMPLES
SOURCE_PATHS = {
    "p0_ed_throughput_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_throughput_run.c",
    "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
    "p0_ed_service_protocol.c": ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
    "p0_ed_pipeline.c": ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "p0_dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AssertionError(f"{name} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise AssertionError(f"{name} is not finite")
    return parsed


def verify(
    result_path: Path,
    input_path: Path,
    image_path: Path,
    throughput_binary_path: Path,
    service_binary_path: Path,
) -> dict[str, object]:
    result = _load(result_path)
    profile = result.get("profile")
    completion = result.get("completion")
    throughput = result.get("throughput")
    latency = result.get("latency_seconds")
    if not all(isinstance(item, dict) for item in (profile, completion, throughput, latency)):
        raise AssertionError("physical result sections are missing")
    if result.get("schema_version") != 1 or result.get("status") != "passed":
        raise AssertionError("physical throughput tool did not report a passed result")
    expected_profile = {
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "frame_samples": FRAME_SAMPLES,
        "warmup_frames": WARMUP_FRAMES,
        "measured_frames": MEASURED_FRAMES,
    }
    if profile != expected_profile:
        raise AssertionError(f"physical profile differs from the locked gate: {profile}")
    expected_completion = {
        "completed_frames": MEASURED_FRAMES,
        "request_failures": 0,
        "service_failures": 0,
        "sequence_failures": 0,
        "dma_flag_failures": 0,
        "dropped_candidates": 0,
    }
    if completion != expected_completion:
        raise AssertionError(f"physical completion gate failed: {completion}")
    if result.get("expected_dma_status_flags") != 7:
        raise AssertionError("physical DMA completion contract is not 0x7")

    elapsed = _finite_number(throughput.get("elapsed_seconds"), "elapsed_seconds")
    required = _finite_number(
        throughput.get("required_frames_per_second"), "required_frames_per_second"
    )
    measured = _finite_number(
        throughput.get("measured_frames_per_second"), "measured_frames_per_second"
    )
    margin = _finite_number(throughput.get("real_time_margin"), "real_time_margin")
    if elapsed <= 0.0 or not math.isclose(required, REQUIRED_FRAMES_PER_SECOND, abs_tol=1e-9):
        raise AssertionError("throughput timing profile differs from the locked gate")
    calculated = MEASURED_FRAMES / elapsed
    if not math.isclose(measured, calculated, rel_tol=0.0, abs_tol=1e-6):
        raise AssertionError("reported frame rate does not match elapsed time")
    if measured < REQUIRED_FRAMES_PER_SECOND or margin < 1.0:
        raise AssertionError("physical service did not sustain the 2 MS/s frame rate")
    if not math.isclose(
        margin, measured / REQUIRED_FRAMES_PER_SECOND, rel_tol=0.0, abs_tol=1e-6
    ):
        raise AssertionError("reported real-time margin is inconsistent")

    ordered_latency = [
        _finite_number(latency.get(name), f"latency_seconds.{name}")
        for name in ("minimum", "p50", "p95", "p99", "maximum")
    ]
    if ordered_latency[0] <= 0.0 or ordered_latency != sorted(ordered_latency):
        raise AssertionError("latency characterization is invalid")
    for artifact in (
        result_path,
        input_path,
        image_path,
        throughput_binary_path,
        service_binary_path,
        *SOURCE_PATHS.values(),
    ):
        if not artifact.is_file():
            raise AssertionError(f"required artifact is missing: {artifact}")

    return {
        "schema_version": 1,
        "status": "passed",
        "scope": "fiziksel ZedBoard PL-DMA-ARM sürekli işleme kabulü",
        "locked_profile": expected_profile,
        "completion": expected_completion,
        "throughput": {
            "elapsed_seconds": elapsed,
            "required_frames_per_second": required,
            "measured_frames_per_second": measured,
            "real_time_margin": margin,
        },
        "latency_seconds": dict(zip(
            ("minimum", "p50", "p95", "p99", "maximum"), ordered_latency, strict=True
        )),
        "artifact_sha256": {
            "physical_result.json": _sha256(result_path),
            "acceptance-frame.ci8": _sha256(input_path),
            "image.ub": _sha256(image_path),
            "p0-ed-throughput-run": _sha256(throughput_binary_path),
            "p0-ed-service": _sha256(service_binary_path),
        },
        "source_sha256": {name: _sha256(path) for name, path in SOURCE_PATHS.items()},
        "claim_boundary": (
            "Deterministik kart içi yerel hizmet yüküdür; canlı HackRF, USB/Ethernet "
            "aktarımı, RF duyarlılığı, kalibrasyon veya saha doğruluğu değildir."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("input", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("throughput_binary", type=Path)
    parser.add_argument("service_binary", type=Path)
    arguments = parser.parse_args()
    evidence = verify(
        arguments.result,
        arguments.input,
        arguments.image,
        arguments.throughput_binary,
        arguments.service_binary,
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
