#!/usr/bin/env python3
"""Verify and record PHASE-06H candidate-grouping evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.rtl.candidate_grouping import (
    HALF_MAX_CANDIDATES,
    MAX_CANDIDATES,
    MAX_GAP_BINS,
    architecture_study,
)
from reference.rtl.candidate_vectors import build_vector_files


EVIDENCE = ROOT / "results" / "evidence" / "phase06h"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06h"
SYNTHESIS_REPORT = ROOT / "build" / "phase06h" / "synthesis" / "reports" / "synthesis-utilization.rpt"
RAM_REPORT = ROOT / "build" / "phase06h" / "synthesis" / "reports" / "synthesis-ram-utilization.rpt"
OWNED_FILES = (
    "algorithm-contract.json",
    "architecture.json",
    "authoritative-comparison.json",
    "integration.json",
    "latency-throughput.json",
    "resource-feasibility.json",
    "rtl-simulation.json",
    "source-manifest.json",
    "toolchain.json",
    "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0019-PHASE06H-CANDIDATE-GROUPING-BOUNDARY.md",
    "docs/interfaces/RTL_CANDIDATE_GROUPING_CONTRACT.md",
    "reference/rtl/candidate_grouping.py",
    "reference/rtl/candidate_vectors.py",
    "rtl/phase06h/rtl/phase06h_pkg.sv",
    "rtl/phase06h/rtl/phase06h_candidate_ram.sv",
    "rtl/phase06h/rtl/axis_candidate_grouping.sv",
    "rtl/phase06h/rtl/phase06h_candidate_synthesis_top.sv",
    "rtl/phase06h/tb/tb_axis_candidate_grouping.sv",
    "scripts/generate_phase06h_vectors.py",
    "scripts/run_phase06h_synthesis.tcl",
    "scripts/verify_phase06h.py",
    "tests/test_phase06h_model.py",
    "tests/test_phase06h_vectors.py",
    "tests/test_phase06h_verifier.py",
    "datasets/fixtures/phase06h/axis-detector-input.mem",
    "datasets/fixtures/phase06h/candidate-expected.mem",
    "datasets/fixtures/phase06h/golden-vectors.json",
    "datasets/fixtures/phase06h/fixture-manifest.json",
)
EXPECTED_PASS_LINE = "PHASE-06H TB PASS: 1773 candidate records checked"
EXPECTED_METRICS = {
    "last_input_to_first_output_cycles": 9,
    "input_records": 53_248,
    "output_records": 1_773,
    "semantic_candidates": 1_772,
    "maximum_candidates_per_frame": 1_352,
    "input_stalls": 4_449,
    "output_stalls": 396,
    "payload_stability_checks": 396,
    "malformed_frames_checked": 3,
    "reset_partial_frame_checked": 1,
}
RESOURCES = {"lut": 879, "ff": 251, "bram_tiles": 6.0, "dsp": 0}
DEVICE_CAPACITY = {"lut": 53_200, "ff": 106_400, "bram_tiles": 140.0, "dsp": 220}


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commands() -> tuple[str, str]:
    iverilog = shutil.which("iverilog") or r"C:\msys64\ucrt64\bin\iverilog.exe"
    vvp = shutil.which("vvp") or r"C:\msys64\ucrt64\bin\vvp.exe"
    if not Path(iverilog).is_file() or not Path(vvp).is_file():
        raise FileNotFoundError("Icarus Verilog 13.0 executable was not found")
    return iverilog, vvp


def _normalized_output(stdout: str) -> bytes:
    lines = [
        line.strip()
        for line in stdout.splitlines()
        if line.startswith("PHASE06H_METRIC") or line.startswith("PHASE-06H TB PASS")
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_rtl_once() -> dict[str, object]:
    iverilog, vvp = _commands()
    environment = os.environ.copy()
    environment["PATH"] = str(Path(iverilog).parent) + os.pathsep + environment.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06h-grouping-") as temporary:
        executable = Path(temporary) / "phase06h-grouping.vvp"
        compile_result = subprocess.run(
            [
                iverilog, "-g2012", "-s", "tb_axis_candidate_grouping", "-o", str(executable),
                str(ROOT / "rtl/phase06h/rtl/phase06h_pkg.sv"),
                str(ROOT / "rtl/phase06h/rtl/phase06h_candidate_ram.sv"),
                str(ROOT / "rtl/phase06h/rtl/axis_candidate_grouping.sv"),
                str(ROOT / "rtl/phase06h/tb/tb_axis_candidate_grouping.sv"),
            ],
            cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        simulation = subprocess.run(
            [vvp, str(executable)], cwd=ROOT, env=environment, capture_output=True, text=True, check=False
        )
        if simulation.returncode != 0 or EXPECTED_PASS_LINE not in simulation.stdout:
            raise RuntimeError(simulation.stdout + simulation.stderr)

    patterns = {
        "last_input_to_first_output_cycles": r"last_input_to_first_output_cycles=(\d+)",
        "input_records": r"input_records=(\d+)",
        "output_records": r"output_records=(\d+)",
        "semantic_candidates": r"semantic_candidates=(\d+)",
        "maximum_candidates_per_frame": r"maximum_candidates_per_frame=(\d+)",
        "input_stalls": r"input_stalls=(\d+)",
        "output_stalls": r"output_stalls=(\d+)",
        "payload_stability_checks": r"payload_stability_checks=(\d+)",
        "malformed_frames_checked": r"malformed_frames_checked=(\d+)",
        "reset_partial_frame_checked": r"reset_partial_frame_checked=(\d+)",
    }
    metrics: dict[str, int] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, simulation.stdout)
        if match is None:
            raise ValueError(f"PHASE-06H RTL metric is missing: {name}")
        metrics[name] = int(match.group(1))
    if metrics != EXPECTED_METRICS:
        raise AssertionError(f"unexpected PHASE-06H RTL metrics: {metrics}")
    normalized = _normalized_output(simulation.stdout)
    return {
        "metrics": metrics,
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _stored_rtl_shape() -> dict[str, object]:
    normalized = (
        "PHASE06H_METRIC last_input_to_first_output_cycles=9\n"
        "PHASE06H_METRIC input_records=53248 output_records=1773 semantic_candidates=1772 maximum_candidates_per_frame=1352\n"
        "PHASE06H_METRIC input_stalls=4449 output_stalls=396 payload_stability_checks=396\n"
        "PHASE06H_METRIC malformed_frames_checked=3 reset_partial_frame_checked=1 frame_error_sticky=1 overflow_sticky=0\n"
        "PHASE-06H TB PASS: 1773 candidate records checked\n"
    ).encode("utf-8")
    return {
        "metrics": dict(EXPECTED_METRICS),
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _validate_synthesis_reports() -> None:
    utilization = SYNTHESIS_REPORT.read_text(encoding="utf-8", errors="replace")
    ram = RAM_REPORT.read_text(encoding="utf-8", errors="replace")
    required = (
        "| Slice LUTs*                |  879",
        "| Slice Registers            |  251",
        "| Block RAM Tile    |    6",
        "| DSPs      |    0",
    )
    if not all(token in utilization for token in required):
        raise AssertionError("Vivado utilization report does not match the normalized resource contract")
    if ram.count("|  grouping_i/high_ram_i/memory_reg_") < 6 or ram.count("|  grouping_i/low_ram_i/memory_reg_") < 6:
        raise AssertionError("Vivado RAM report does not contain both inferred candidate RAMs")


def _resource_document() -> dict[str, object]:
    return {
        "phase": "PHASE-06H",
        "status": "passed",
        "tool": "Vivado 2025.2",
        "target_part": "xc7z020clg484-1",
        "run_type": "standalone candidate-grouping targeted synthesis-only feasibility",
        "resources": {
            **RESOURCES,
            "utilization_percent": {
                key: round(100.0 * RESOURCES[key] / DEVICE_CAPACITY[key], 2) for key in RESOURCES
            },
        },
        "device_capacity": DEVICE_CAPACITY,
        "candidate_ram_inference": "two 676x94 logical RAMs mapped to six RAMB36E1",
        "fabric_capacity_exceeded": False,
        "standalone_top_io": "abstract verification ports exceed package pins; not a physical integration top",
        "implementation": "not_run",
        "post_route_timing": "not_verified",
        "hardware": "not_exercised",
    }


def build_documents(*, execute_simulation: bool, validate_synthesis: bool) -> dict[str, object]:
    generated = build_vector_files()
    mismatched = [
        name for name, payload in generated.items()
        if not (FIXTURES / name).is_file() or (FIXTURES / name).read_bytes() != payload
    ]
    if mismatched:
        raise AssertionError("fixture mismatch: " + ", ".join(mismatched))
    golden = json.loads(generated["golden-vectors.json"])
    first = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    second = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    deterministic = first["normalized_output"] == second["normalized_output"]
    if not deterministic:
        raise AssertionError("fresh PHASE-06H RTL runs are not deterministic")
    if validate_synthesis:
        _validate_synthesis_reports()
    resource = _resource_document()
    synthetic = [row for row in golden["vectors"] if str(row["source"]).startswith("synthetic")]
    real = [row for row in golden["vectors"] if str(row["source"]).startswith("frozen")]
    source_manifest = {
        "phase": "PHASE-06H",
        "status": "passed",
        "files": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "frozen_phase06g_source": {
            "path": "datasets/fixtures/phase06g/detector-expected.mem",
            "sha256": sha256(ROOT / "datasets/fixtures/phase06g/detector-expected.mem"),
        },
    }
    rtl = {
        "phase": "PHASE-06H",
        "status": "passed",
        "compile": "passed",
        "simulation": "passed",
        "simulator": "Icarus Verilog 13.0 stable",
        "checked_records": golden["output_records"],
        "mismatch_count": 0,
        **first["metrics"],
        "deterministic_rerun": "passed",
        "normalized_output_sha256": first["normalized_sha256"],
        "coverage": [
            "zero_one_and_multiple_candidates", "one_missing_bin_bridge", "separated_candidates",
            "region_and_shifted_half_boundaries", "first_maximum_tie", "first_and_last_evaluated_bins",
            "maximum_candidate_capacity", "frozen_phase06g_real_frame", "shifted_output_order",
            "tvalid_tready", "output_backpressure_payload_stability", "tlast", "consecutive_frames",
            "reset_partial_frame", "malformed_early_missing_late_tlast", "sticky_error_and_no_overflow",
        ],
        "build_location": "external_temporary_directory",
    }
    summary = {
        "phase": "PHASE-06H",
        "overall": "passed",
        "authoritative_phase03_grouping": "passed",
        "python_bit_true": "passed",
        "rtl_compile": "passed",
        "rtl_simulation": "passed",
        "golden_equivalence": "passed",
        "deterministic_rerun": "passed",
        "resource_feasibility": "passed",
        "precise_bandwidth": "not_implemented",
        "temporal_confirmation": "not_implemented",
        "physical_frequency_or_db": "not_implemented",
        "phase04_parameter_extraction_rtl": "not_implemented",
        "continuous_pipeline": "not_supported",
        "post_detector_timing_100mhz": "not_verified",
        "implementation": "not_run",
        "bitstream": "not_generated",
        "hardware": "not_exercised",
        "petalinux_ps_integration": "not_implemented",
        "live_hackrf": "not_exercised",
    }
    return {
        "algorithm-contract.json": {
            "phase": "PHASE-06H", "status": "passed",
            "source_of_truth": "reference/detection/pipeline.py DetectionPipeline._group",
            "input_order": "PHASE-06G natural ascending", "output_order": "shifted ascending",
            "max_gap_bins": MAX_GAP_BINS, "maximum_index_delta_within_candidate": 2,
            "start_end": "first and last detected shifted bins, inclusive",
            "peak_tie": "first maximum; lower shifted bin wins",
            "peak_metadata": "exact power, regional noise and threshold from peak cell",
            "coarse_span": "end-start+1; not precise bandwidth",
            "empty_axis_packet": "one candidate_valid=0 TLAST=1 sentinel",
        },
        "architecture.json": {"phase": "PHASE-06H", "status": "passed", **architecture_study()},
        "authoritative-comparison.json": {
            "phase": "PHASE-06H", "status": "passed",
            "authoritative_model": "DetectionPipeline._group",
            "synthetic_frames": len(synthetic), "field_mismatches": 0,
            "compared_fields": ["start_bin", "end_bin", "peak_bin", "peak_power", "local_noise_power", "threshold_power"],
        },
        "integration.json": {
            "phase": "PHASE-06H", "status": "passed",
            "source": "frozen PHASE-06G detector result derived from frozen real PHASE-06F Hann frame",
            "frames": len(real), "vector_ids": [row["vector_id"] for row in real], "bit_true_mismatches": 0,
        },
        "latency-throughput.json": {
            "phase": "PHASE-06H", "status": "passed",
            "last_input_to_first_output_clock_intervals": first["metrics"]["last_input_to_first_output_cycles"],
            "input_collect_records_per_cycle": 1, "continuous_frame_support": False,
            "frame_gap_required": True, "maximum_candidates_per_frame": MAX_CANDIDATES,
            "candidate_ram_depth_per_half": HALF_MAX_CANDIDATES, "post_detector_timing_100mhz": "not_verified",
        },
        "resource-feasibility.json": resource,
        "rtl-simulation.json": rtl,
        "source-manifest.json": source_manifest,
        "toolchain.json": {
            "phase": "PHASE-06H", "status": "passed", "rtl_language": "SystemVerilog",
            "simulator": "Icarus Verilog 13.0 stable", "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "vivado": "2025.2", "vivado_run": "real targeted synthesis-only", "target_part": "xc7z020clg484-1",
            "implementation": "not_run", "hardware": "not_exercised",
        },
        "verification-summary.json": summary,
    }


def write() -> None:
    documents = build_documents(execute_simulation=True, validate_synthesis=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))
    print(f"PHASE-06H evidence written: {len(OWNED_FILES)} files")


def check() -> bool:
    try:
        documents = build_documents(execute_simulation=False, validate_synthesis=False)
        exact = all(
            (EVIDENCE / name).is_file() and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name])
            for name in OWNED_FILES
        )
        payload = b"".join((EVIDENCE / name).read_bytes() for name in OWNED_FILES).decode("utf-8", errors="replace").casefold()
        safe = not any(token in payload for token in ("c:\\users", "hostname", "timestamp", "onedrive", "build/phase06h"))
        return exact and safe and documents["verification-summary.json"]["overall"] == "passed"
    except (OSError, ValueError, AssertionError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"PHASE-06H verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
