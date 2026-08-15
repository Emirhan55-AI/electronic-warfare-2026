#!/usr/bin/env python3
"""Verify and record PHASE-06G regional-detector evidence."""

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

from reference.rtl.detector_vectors import build_vector_files
from reference.rtl.regional_detector import (
    COEFFICIENT_FRACTION_BITS,
    COMBINED_COEFFICIENTS,
    NOISE_COEFFICIENT,
    PFA_VALUES,
    THRESHOLD_COEFFICIENTS,
    architecture_study,
    coefficient_study,
)


EVIDENCE = ROOT / "results" / "evidence" / "phase06g"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06g"
SYNTHESIS_REPORT = ROOT / "build" / "phase06g" / "synthesis" / "reports" / "synthesis-utilization-summary.rpt"
DETECTOR_REPORT = ROOT / "build" / "phase06g" / "synthesis" / "reports" / "detector-utilization.rpt"
OWNED_FILES = (
    "algorithm-contract.json",
    "architecture-study.json",
    "coefficient-study.json",
    "integration.json",
    "latency.json",
    "phase03-comparison.json",
    "python-model-result.json",
    "resource-feasibility.json",
    "rtl-simulation.json",
    "source-manifest.json",
    "toolchain.json",
    "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0017-PHASE06G-REGIONAL-DETECTOR.md",
    "docs/interfaces/RTL_REGIONAL_DETECTOR_CONTRACT.md",
    "reference/rtl/regional_detector.py",
    "reference/rtl/detector_vectors.py",
    "rtl/phase06g/rtl/phase06g_pkg.sv",
    "rtl/phase06g/rtl/axis_regional_detector.sv",
    "rtl/phase06g/rtl/phase06g_detector_synthesis_top.sv",
    "rtl/phase06g/tb/tb_axis_regional_detector.sv",
    "scripts/generate_phase06g_vectors.py",
    "scripts/run_phase06g_synthesis.tcl",
    "scripts/verify_phase06g.py",
    "tests/test_phase06g_model.py",
    "tests/test_phase06g_vectors.py",
    "tests/test_phase06g_verifier.py",
    "datasets/fixtures/phase06g/axis-power-input.mem",
    "datasets/fixtures/phase06g/detector-expected.mem",
    "datasets/fixtures/phase06g/golden-vectors.json",
    "datasets/fixtures/phase06g/fixture-manifest.json",
)
EXPECTED_PASS_LINE = "PHASE-06G TB PASS: 81920 detector results checked"
EXPECTED_METRICS = {
    "last_input_to_first_output_cycles": 476_131,
    "input_stalls": 9_215_056,
    "output_stalls": 13_659,
    "payload_stability_checks": 13_659,
    "malformed_frames_checked": 4,
}
TOTAL_RESOURCES = {"lut": 5275, "ff": 7957, "bram_tiles": 21.0, "dsp": 46}
DETECTOR_RESOURCES = {"lut": 959, "ff": 352, "bram_tiles": 6.5, "dsp": 8}
DEVICE_CAPACITY = {"lut": 53200, "ff": 106400, "bram_tiles": 140.0, "dsp": 220}


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
        if line.startswith("PHASE06G_METRIC") or line.startswith("PHASE-06G TB PASS")
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_rtl_once() -> dict[str, object]:
    iverilog, vvp = _commands()
    environment = os.environ.copy()
    environment["PATH"] = str(Path(iverilog).parent) + os.pathsep + environment.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06g-detector-") as temporary:
        executable = Path(temporary) / "phase06g-detector.vvp"
        compile_result = subprocess.run(
            [
                iverilog,
                "-g2012",
                "-s",
                "tb_axis_regional_detector",
                "-o",
                str(executable),
                str(ROOT / "rtl/phase06g/rtl/phase06g_pkg.sv"),
                str(ROOT / "rtl/phase06g/rtl/axis_regional_detector.sv"),
                str(ROOT / "rtl/phase06g/tb/tb_axis_regional_detector.sv"),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        simulation = subprocess.run(
            [vvp, str(executable)], cwd=ROOT, env=environment, capture_output=True, text=True, check=False
        )
        if simulation.returncode != 0 or EXPECTED_PASS_LINE not in simulation.stdout:
            raise RuntimeError(simulation.stdout + simulation.stderr)
    latency = re.search(r"last_input_to_first_output_cycles=(\d+)", simulation.stdout)
    stalls = re.search(r"input_stalls=(\d+) output_stalls=(\d+) payload_stability_checks=(\d+)", simulation.stdout)
    malformed = re.search(r"malformed_frames_checked=(\d+) frame_error_sticky=1", simulation.stdout)
    if latency is None or stalls is None or malformed is None:
        raise ValueError("PHASE-06G RTL metric output is incomplete")
    metrics = {
        "last_input_to_first_output_cycles": int(latency.group(1)),
        "input_stalls": int(stalls.group(1)),
        "output_stalls": int(stalls.group(2)),
        "payload_stability_checks": int(stalls.group(3)),
        "malformed_frames_checked": int(malformed.group(1)),
    }
    if metrics != EXPECTED_METRICS:
        raise AssertionError(f"unexpected PHASE-06G RTL metrics: {metrics}")
    normalized = _normalized_output(simulation.stdout)
    return {
        "metrics": metrics,
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _stored_rtl_shape() -> dict[str, object]:
    normalized = (
        "PHASE06G_METRIC last_input_to_first_output_cycles=476131\n"
        "PHASE06G_METRIC input_stalls=9215056 output_stalls=13659 payload_stability_checks=13659\n"
        "PHASE06G_METRIC malformed_frames_checked=4 frame_error_sticky=1\n"
        "PHASE-06G TB PASS: 81920 detector results checked\n"
    ).encode("utf-8")
    return {
        "metrics": dict(EXPECTED_METRICS),
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _validate_synthesis_reports() -> None:
    total_text = SYNTHESIS_REPORT.read_text(encoding="utf-8", errors="replace")
    detector_text = DETECTOR_REPORT.read_text(encoding="utf-8", errors="replace")
    required_total = ("| Slice LUTs*                | 5275", "| Slice Registers            | 7957", "| Block RAM Tile    |   21", "| DSPs           |   46")
    required_detector = ("| Slice LUTs*                |  959", "| Slice Registers            |  352", "| Block RAM Tile    |  6.5", "| DSPs           |    8")
    if not all(token in total_text for token in required_total) or not all(token in detector_text for token in required_detector):
        raise AssertionError("Vivado synthesis resource reports do not match the normalized resource contract")


def _resource_document() -> dict[str, object]:
    return {
        "phase": "PHASE-06G",
        "status": "passed",
        "tool": "Vivado 2025.2",
        "target_part": "xc7z020clg484-1",
        "run_type": "targeted synthesis-only feasibility",
        "integrated_top": "real PHASE-06E FFT wrapper/IP + PHASE-06F power + PHASE-06G detector",
        "total": {
            **TOTAL_RESOURCES,
            "utilization_percent": {
                key: round(100.0 * TOTAL_RESOURCES[key] / DEVICE_CAPACITY[key], 2) for key in TOTAL_RESOURCES
            },
        },
        "detector_contribution": {
            **DETECTOR_RESOURCES,
            "utilization_percent": {
                key: round(100.0 * DETECTOR_RESOURCES[key] / DEVICE_CAPACITY[key], 2) for key in DETECTOR_RESOURCES
            },
        },
        "device_capacity": DEVICE_CAPACITY,
        "capacity_exceeded": False,
        "implementation": "not_run_for_phase06g",
        "post_detector_timing_100mhz": "not_verified",
        "hardware": "not_exercised",
    }


def build_documents(*, execute_simulation: bool, validate_synthesis: bool) -> dict[str, object]:
    generated = build_vector_files()
    mismatched = [name for name, payload in generated.items() if not (FIXTURES / name).is_file() or (FIXTURES / name).read_bytes() != payload]
    if mismatched:
        raise AssertionError("fixture mismatch: " + ", ".join(mismatched))
    golden = json.loads(generated["golden-vectors.json"])
    first = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    second = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    deterministic = first["normalized_output"] == second["normalized_output"]
    if validate_synthesis:
        _validate_synthesis_reports()

    comparisons = golden["vectors"]
    boundary = [row for row in comparisons if row["boundary_case"]]
    real_rows = [row for row in comparisons if row["source"].startswith("frozen")]
    all_mismatches = sum(row["decision_mismatches"] for row in comparisons)
    non_boundary_mismatches = sum(row["decision_mismatches"] for row in comparisons if not row["boundary_case"])
    resource = _resource_document()
    fixed_study = coefficient_study()
    fixed_study.update(
        {
            "phase": "PHASE-06G",
            "status": "passed",
            "selected": {
                "fractional_bits": COEFFICIENT_FRACTION_BITS,
                "noise_integer": NOISE_COEFFICIENT,
                "threshold_integers": list(THRESHOLD_COEFFICIENTS),
                "combined_integers": list(COMBINED_COEFFICIENTS),
                "pfa_values": list(PFA_VALUES),
            },
            "maximum_fixture_threshold_integer_error": max(row["maximum_threshold_integer_error"] for row in comparisons),
            "maximum_real_phase06f_threshold_integer_error": max(row["maximum_threshold_integer_error"] for row in real_rows),
        }
    )
    rtl_simulation = {
        "phase": "PHASE-06G",
        "status": "passed",
        "compile": "passed",
        "simulation": "passed",
        "simulator": "Icarus Verilog 13.0 stable",
        "checked_results": golden["samples"],
        "mismatch_count": 0,
        **first["metrics"],
        "deterministic_rerun": "passed" if deterministic else "failed",
        "normalized_output_sha256": first["normalized_sha256"],
        "coverage": [
            "median",
            "noise",
            "threshold",
            "evaluation_mask",
            "decision",
            "natural_shifted_index",
            "tlast",
            "reset_partial_frame",
            "backpressure_payload_stability",
            "consecutive_frames",
            "region_boundaries",
            "malformed_early_missing_late_tlast",
            "no_drop_no_duplication",
        ],
        "build_location": "external_temporary_directory",
    }
    source_manifest = {
        "phase": "PHASE-06G",
        "status": "passed",
        "files": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "frozen_phase06f_source": {
            "path": "datasets/fixtures/phase06f/real-power-expected.mem",
            "sha256": sha256(ROOT / "datasets/fixtures/phase06f/real-power-expected.mem"),
        },
    }
    overall = deterministic and non_boundary_mismatches == 0 and not resource["capacity_exceeded"]
    return {
        "algorithm-contract.json": {
            "phase": "PHASE-06G",
            "status": "passed",
            "source_of_truth": "reference/detection/cfar.py regional detector",
            "frame_length": 4096,
            "regions": 16,
            "region_size": 256,
            "median": "arithmetic mean of sorted elements 127 and 128; represented as exact median_twice",
            "noise": "median / ln(2)",
            "threshold": "noise * (-ln(Pfa))",
            "decision": "evaluated and power > threshold",
            "pfa_values": list(PFA_VALUES),
            "default_pfa": 1e-4,
            "default_evaluate_center": True,
            "shift_mapping": "shifted_index = natural_index XOR 0x800",
            "excluded_shifted_bins": [[0, 19], [4076, 4095]],
            "center_exclusion_when_disabled": 2048,
            "zero_region": "zero noise, zero threshold, strict comparison keeps zero undetected",
            "malformed_frame": "discard with sticky error; resynchronize at known boundary or next TLAST",
        },
        "architecture-study.json": {"phase": "PHASE-06G", "status": "passed", **architecture_study()},
        "coefficient-study.json": fixed_study,
        "integration.json": {
            "phase": "PHASE-06G",
            "status": "passed",
            "source": "frozen normalized PHASE-06F real AMD FFT linear-power output",
            "frames": len(real_rows),
            "samples": len(real_rows) * 4096,
            "vector_ids": [row["vector_id"] for row in real_rows],
            "bit_true_mismatches": 0,
            "phase03_decision_mismatches": sum(row["decision_mismatches"] for row in real_rows),
        },
        "latency.json": {
            "phase": "PHASE-06G",
            "status": "passed",
            "last_input_to_first_output_clock_intervals": first["metrics"]["last_input_to_first_output_cycles"],
            "input_collect_samples_per_cycle": 1,
            "continuous_frame_support": False,
            "ping_pong_buffer": False,
            "frame_gap_required": True,
            "post_detector_timing_100mhz": "not_verified",
        },
        "phase03-comparison.json": {
            "phase": "PHASE-06G",
            "status": "passed" if non_boundary_mismatches == 0 else "failed",
            "floating_reference": "reference/detection/cfar.py float64 regional detector",
            "fixed_reference": "reference/rtl/regional_detector.py integer bit-true detector",
            "frames": golden["frame_count"],
            "samples": golden["samples"],
            "all_decision_mismatches": all_mismatches,
            "non_boundary_decision_mismatches": non_boundary_mismatches,
            "false_positive_differences": sum(row["false_positive_differences"] for row in comparisons),
            "false_negative_differences": sum(row["false_negative_differences"] for row in comparisons),
            "boundary_cases": boundary,
        },
        "python-model-result.json": {
            "phase": "PHASE-06G",
            "status": "passed",
            "model": "independent Python arbitrary-precision integer regional detector",
            "frames": golden["frame_count"],
            "samples": golden["samples"],
            "synthetic_frames": golden["synthetic_frames"],
            "real_phase06f_frames": golden["real_phase06f_frames"],
            "bit_true_self_consistency": "passed",
        },
        "resource-feasibility.json": resource,
        "rtl-simulation.json": rtl_simulation,
        "source-manifest.json": source_manifest,
        "toolchain.json": {
            "phase": "PHASE-06G",
            "status": "passed",
            "rtl_language": "SystemVerilog",
            "simulator": "Icarus Verilog 13.0 stable",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "vivado": "2025.2",
            "vivado_run": "real targeted synthesis-only",
            "target_part": "xc7z020clg484-1",
            "implementation": "not_run_for_phase06g",
            "hardware": "not_exercised",
        },
        "verification-summary.json": {
            "phase": "PHASE-06G",
            "overall": "passed" if overall else "failed",
            "algorithm_contract": "passed",
            "median_definition": "passed",
            "architecture_study": "passed",
            "fixed_point_study": "passed",
            "python_bit_true": "passed",
            "phase03_non_boundary_decisions": "passed" if non_boundary_mismatches == 0 else "failed",
            "rtl_compile": "passed",
            "rtl_simulation": "passed",
            "rtl_bit_exact": "passed",
            "deterministic_rerun": "passed" if deterministic else "failed",
            "resource_feasibility": "passed",
            "cell_grouping": "not_implemented",
            "temporal_confirmation": "not_implemented",
            "parameter_extraction_rtl": "not_implemented",
            "post_detector_timing_100mhz": "not_verified",
            "implementation": "not_run",
            "bitstream": "not_generated",
            "hardware": "not_exercised",
            "live_hackrf": "not_exercised",
        },
    }


def write() -> None:
    documents = build_documents(execute_simulation=True, validate_synthesis=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))
    print(f"PHASE-06G evidence written: {len(OWNED_FILES)} files")


def check() -> bool:
    try:
        documents = build_documents(execute_simulation=False, validate_synthesis=False)
        exact = all(
            (EVIDENCE / name).is_file() and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name])
            for name in OWNED_FILES
        )
        payload = b"".join((EVIDENCE / name).read_bytes() for name in OWNED_FILES).decode("utf-8", errors="replace").casefold()
        safe = not any(token in payload for token in ("c:\\users", "hostname", "timestamp", "onedrive", "build/phase06g"))
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
    print(f"PHASE-06G verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
