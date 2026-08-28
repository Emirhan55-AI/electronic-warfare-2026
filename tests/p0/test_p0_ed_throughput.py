from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "platforms/embedded/p0/src/p0_ed_throughput_run.c"
STAGE_PROFILE_SOURCE = ROOT / "platforms/embedded/p0/src/p0_ed_stage_profile_run.c"
RECIPE = ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb"
VERIFY_PATH = ROOT / "scripts/verify_p0_ed_throughput_physical.py"
SPEC = importlib.util.spec_from_file_location("verify_p0_ed_throughput_physical", VERIFY_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def _physical_result(frame_rate: float = 600.0) -> dict[str, object]:
    elapsed = 4096.0 / frame_rate
    required = 2_000_000.0 / 4096.0
    return {
        "schema_version": 1,
        "status": "passed",
        "scope": "yerel PL-DMA-ARM ED hizmeti",
        "profile": {
            "sample_rate_hz": 2_000_000,
            "frame_samples": 4096,
            "warmup_frames": 64,
            "measured_frames": 4096,
        },
        "completion": {
            "completed_frames": 4096,
            "request_failures": 0,
            "service_failures": 0,
            "sequence_failures": 0,
            "dma_flag_failures": 0,
            "dropped_candidates": 0,
        },
        "throughput": {
            "elapsed_seconds": elapsed,
            "required_frames_per_second": required,
            "measured_frames_per_second": frame_rate,
            "real_time_margin": frame_rate / required,
        },
        "latency_seconds": {
            "minimum": 0.0010,
            "p50": 0.0012,
            "p95": 0.0015,
            "p99": 0.0018,
            "maximum": 0.0020,
        },
        "expected_dma_status_flags": 7,
    }


def _artifacts(tmp_path: Path, result: dict[str, object]) -> tuple[Path, ...]:
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    paths = [result_path]
    for name in ("frame.ci8", "image.ub", "throughput", "service"):
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        paths.append(path)
    return tuple(paths)


def test_runtime_and_recipe_preserve_locked_physical_gate() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    recipe = RECIPE.read_text(encoding="utf-8")

    for token in (
        "P0_ED_FRAME_SAMPLES 4096U",
        "P0_ED_EXPECTED_DMA_FLAGS 7U",
        "CLOCK_MONOTONIC",
        "P0_ED_REQUEST_FLAG_RESET",
        "service_connection_t",
        "open_connection(&connection, socket_path)",
        "close_connection(&connection)",
        "measured_frames_per_second >= required_frames_per_second",
        "response.result.dropped_candidates",
    ):
        assert token in source
    for token in (
        "file://p0_ed_throughput_run.c",
        "-o ${S}/p0-ed-throughput-run",
        "install -m 0755 ${S}/p0-ed-throughput-run",
        "file://p0_ed_stage_profile_run.c",
        'P0_HOT_PATH_CFLAGS = "-O3"',
        "-o ${S}/p0-ed-stage-profile-run",
        "install -m 0755 ${S}/p0-ed-stage-profile-run",
    ):
        assert token in recipe


def test_stage_profiler_measures_the_exact_pl_pipeline_stages() -> None:
    source = STAGE_PROFILE_SOURCE.read_text(encoding="utf-8")

    for token in (
        "p0_pl_os_cfar_decode(",
        "!pl_decisions_present",
        "p0_multiscale_process_pl(",
        "p0_candidate_records_encode(",
        "phase06j_process_candidates(",
        'print_summary("pl_frame_decode"',
        'print_summary("candidate_detection"',
        'print_summary("candidate_record_encode"',
        'print_summary("temporal_association"',
    ):
        assert token in source


def test_physical_verifier_accepts_only_the_registered_profile(tmp_path: Path) -> None:
    evidence = VERIFY.verify(*_artifacts(tmp_path, _physical_result()))

    assert evidence["status"] == "passed"
    assert evidence["locked_profile"]["measured_frames"] == 4096
    assert evidence["throughput"]["real_time_margin"] > 1.0


def test_physical_verifier_rejects_sub_realtime_result(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="did not sustain"):
        VERIFY.verify(*_artifacts(tmp_path, _physical_result(frame_rate=400.0)))
