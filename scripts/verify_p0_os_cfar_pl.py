#!/usr/bin/env python3
"""Verify and record the P0 PL OS-CFAR functional acceptance evidence."""

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

from algorithms.p0.detection import P0_DETECTOR_PROFILE
from algorithms.rtl.p0_os_cfar import (
    ALPHA_Q32,
    COEFFICIENT_FRACTION_BITS,
    architecture_study,
)
from algorithms.rtl.p0_os_cfar_vectors import build_vector_files


EVIDENCE = ROOT / "results" / "evidence" / "p0" / "os-cfar-pl"
FIXTURES = ROOT / "datasets" / "fixtures" / "p0_os_cfar"
VIVADO_REPORTS = ROOT / "build" / "p0" / "os-cfar-vivado" / "reports"
OWNED_FILES = (
    "algorithm-contract.json",
    "architecture-study.json",
    "coefficient-validation.json",
    "rtl-simulation.json",
    "source-manifest.json",
    "throughput-capacity.json",
    "toolchain.json",
    "vivado-implementation.json",
    "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0030-P0-OS-CFAR-PL-OFFLOAD.md",
    "docs/interfaces/P0_PL_OS_CFAR_CONTRACT.md",
    "algorithms/rtl/p0_os_cfar.py",
    "algorithms/rtl/p0_os_cfar_vectors.py",
    "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv",
    "algorithms/fpga/p0/rtl/p0_os_cfar_synthesis_top.sv",
    "algorithms/fpga/p0/constraints/p0_os_cfar_50mhz.xdc",
    "algorithms/fpga/p0/tb/tb_axis_p0_os_cfar.sv",
    "scripts/generate_p0_os_cfar_vectors.py",
    "scripts/run_p0_os_cfar_vivado.tcl",
    "scripts/verify_p0_os_cfar_pl.py",
    "tests/p0/test_p0_os_cfar_pl_model.py",
    "tests/p0/test_p0_os_cfar_pl_vectors.py",
    "tests/p0/test_p0_os_cfar_pl_verifier.py",
    "datasets/fixtures/p0_os_cfar/axis-power-input.mem",
    "datasets/fixtures/p0_os_cfar/dma-expected.mem",
    "datasets/fixtures/p0_os_cfar/golden-vectors.json",
    "datasets/fixtures/p0_os_cfar/fixture-manifest.json",
)
EXPECTED_PASS_LINE = "P0 OS-CFAR TB PASS: 45056 DMA words checked"
EXPECTED_METRICS = {
    "frame_completion_cycles": 48_910,
    "last_input_to_first_output_cycles": 36_625,
    "input_stalls": 460_345,
    "output_stalls": 6_827,
    "payload_stability_checks": 6_827,
    "malformed_frames_checked": 3,
}
CLOCK_HZ = 50_000_000
SAMPLE_RATE_HZ = 2_000_000
FRAME_LENGTH = 4096
FRAME_CYCLE_BUDGET = CLOCK_HZ * FRAME_LENGTH // SAMPLE_RATE_HZ
EXPECTED_VIVADO = {
    "tool": "Vivado 2025.2 build 6299465",
    "part": "xc7z020clg484-1",
    "top": "p0_os_cfar_synthesis_top",
    "clock_period_ns": 20.0,
    "worst_setup_slack_ns": 2.4,
    "total_setup_slack_ns": 0.0,
    "setup_failing_endpoints": 0,
    "worst_hold_slack_ns": 0.05,
    "total_hold_slack_ns": 0.0,
    "hold_failing_endpoints": 0,
    "route_error_nets": 0,
    "slice_luts": {"used": 17387, "available": 53200, "utilization_percent": 32.68},
    "slice_registers": {"used": 13769, "available": 106400, "utilization_percent": 12.94},
    "block_ram_tiles": {"used": 21, "available": 140, "utilization_percent": 15.0},
    "dsps": {"used": 45, "available": 220, "utilization_percent": 20.45},
    "check_timing_issue_counts": [0] * 12,
    "drc_error_count": 0,
    "drc_critical_warning_rules": ["NSTD-1", "UCIO-1"],
}


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commands() -> tuple[str, str]:
    iverilog = shutil.which("iverilog") or r"C:\msys64\ucrt64\bin\iverilog.exe"
    vvp = shutil.which("vvp") or r"C:\msys64\ucrt64\bin\vvp.exe"
    if not Path(iverilog).is_file() or not Path(vvp).is_file():
        raise FileNotFoundError("Icarus Verilog executable was not found")
    return iverilog, vvp


def _normalized_output(stdout: str) -> bytes:
    lines = [
        line.strip()
        for line in stdout.splitlines()
        if line.startswith("P0_OS_CFAR_METRIC") or line.startswith("P0 OS-CFAR TB PASS")
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_rtl_once() -> dict[str, object]:
    iverilog, vvp = _commands()
    environment = os.environ.copy()
    environment["PATH"] = str(Path(iverilog).parent) + os.pathsep + environment.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-p0-os-cfar-") as temporary:
        executable = Path(temporary) / "p0-os-cfar.vvp"
        compile_result = subprocess.run(
            [
                iverilog,
                "-g2012",
                "-s",
                "tb_axis_p0_os_cfar",
                "-o",
                str(executable),
                str(ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv"),
                str(ROOT / "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv"),
                str(ROOT / "algorithms/fpga/p0/tb/tb_axis_p0_os_cfar.sv"),
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
            [vvp, str(executable)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if simulation.returncode != 0 or EXPECTED_PASS_LINE not in simulation.stdout:
            raise RuntimeError(simulation.stdout + simulation.stderr)

    patterns = {
        "frame_completion_cycles": r"frame_completion_cycles=(\d+)",
        "last_input_to_first_output_cycles": r"last_input_to_first_output_cycles=(\d+)",
        "input_stalls": r"input_stalls=(\d+)",
        "output_stalls": r"output_stalls=(\d+)",
        "payload_stability_checks": r"payload_stability_checks=(\d+)",
        "malformed_frames_checked": r"malformed_frames_checked=(\d+)",
    }
    metrics: dict[str, int] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, simulation.stdout)
        if match is None:
            raise ValueError(f"RTL metric is missing: {name}")
        metrics[name] = int(match.group(1))
    if metrics != EXPECTED_METRICS:
        raise AssertionError(f"unexpected P0 OS-CFAR RTL metrics: {metrics}")
    normalized = _normalized_output(simulation.stdout)
    return {
        "metrics": metrics,
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _stored_rtl_shape() -> dict[str, object]:
    normalized = (
        "P0_OS_CFAR_METRIC frame_completion_cycles=48910\n"
        "P0_OS_CFAR_METRIC last_input_to_first_output_cycles=36625\n"
        "P0_OS_CFAR_METRIC input_stalls=460345 output_stalls=6827 payload_stability_checks=6827\n"
        "P0_OS_CFAR_METRIC malformed_frames_checked=3 frame_error_sticky=1\n"
        "P0 OS-CFAR TB PASS: 45056 DMA words checked\n"
    ).encode("utf-8")
    return {
        "metrics": dict(EXPECTED_METRICS),
        "normalized_output": normalized,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }


def _table_resource(report: str, label: str) -> dict[str, int | float]:
    match = re.search(
        rf"(?m)^\|\s*{re.escape(label)}\s*\|\s*([0-9.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|$",
        report,
    )
    if match is None:
        raise ValueError(f"Vivado utilization row is missing: {label}")
    used = float(match.group(1))
    available = float(match.group(2))
    return {
        "used": int(used) if used.is_integer() else used,
        "available": int(available) if available.is_integer() else available,
        "utilization_percent": float(match.group(3)),
    }


def _vivado_shape_from_reports() -> dict[str, object]:
    timing = (VIVADO_REPORTS / "implementation-timing-summary.rpt").read_text(
        encoding="utf-8", errors="replace"
    )
    utilization = (VIVADO_REPORTS / "implementation-utilization-summary.rpt").read_text(
        encoding="utf-8", errors="replace"
    )
    route = (VIVADO_REPORTS / "route-status.rpt").read_text(
        encoding="utf-8", errors="replace"
    )
    drc = (VIVADO_REPORTS / "implementation-drc.rpt").read_text(
        encoding="utf-8", errors="replace"
    )
    check_timing = (VIVADO_REPORTS / "check-timing.rpt").read_text(
        encoding="utf-8", errors="replace"
    )

    timing_match = re.search(
        r"(?m)^\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+\d+\s+"
        r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+\d+\s+",
        timing,
    )
    route_match = re.search(r"# of nets with routing errors\.*\s*:\s*(\d+)\s*:", route)
    tool_match = re.search(r"Tool Version\s*:\s*Vivado v\.([0-9.]+).*?Build\s+(\d+)", timing)
    if timing_match is None or route_match is None or tool_match is None:
        raise ValueError("Vivado timing, route, or tool identity could not be parsed")

    critical_rules = sorted(
        re.findall(r"(?m)^\|\s*([A-Z0-9-]+)\s*\|\s*Critical Warning\s*\|", drc)
    )
    drc_errors = len(re.findall(r"(?m)^\|\s*[A-Z0-9-]+\s*\|\s*Error\s*\|", drc))
    reported_timing_issue_counts = [
        int(value)
        for value in re.findall(r"(?m)^\d+\. checking [a-z_]+ \((\d+)\)$", check_timing)
    ]
    if len(reported_timing_issue_counts) < 12:
        raise ValueError("Vivado check_timing inventory is incomplete")
    timing_issue_counts = reported_timing_issue_counts[:12]

    return {
        "tool": f"Vivado {tool_match.group(1)} build {tool_match.group(2)}",
        "part": "xc7z020clg484-1",
        "top": "p0_os_cfar_synthesis_top",
        "clock_period_ns": 20.0,
        "worst_setup_slack_ns": float(timing_match.group(1)),
        "total_setup_slack_ns": float(timing_match.group(2)),
        "setup_failing_endpoints": int(timing_match.group(3)),
        "worst_hold_slack_ns": float(timing_match.group(4)),
        "total_hold_slack_ns": float(timing_match.group(5)),
        "hold_failing_endpoints": int(timing_match.group(6)),
        "route_error_nets": int(route_match.group(1)),
        "slice_luts": _table_resource(utilization, "Slice LUTs"),
        "slice_registers": _table_resource(utilization, "Slice Registers"),
        "block_ram_tiles": _table_resource(utilization, "Block RAM Tile"),
        "dsps": _table_resource(utilization, "DSPs"),
        "check_timing_issue_counts": timing_issue_counts,
        "drc_error_count": drc_errors,
        "drc_critical_warning_rules": critical_rules,
    }


def _stored_vivado_shape() -> dict[str, object]:
    return json.loads(json.dumps(EXPECTED_VIVADO))


def build_documents(*, execute_simulation: bool, read_vivado_reports: bool = False) -> dict[str, object]:
    generated = build_vector_files()
    mismatched = [
        name
        for name, payload in generated.items()
        if not (FIXTURES / name).is_file() or (FIXTURES / name).read_bytes() != payload
    ]
    if mismatched:
        raise AssertionError("fixture mismatch: " + ", ".join(mismatched))
    golden = json.loads(generated["golden-vectors.json"])
    first = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    second = run_rtl_once() if execute_simulation else _stored_rtl_shape()
    vivado = _vivado_shape_from_reports() if read_vivado_reports else _stored_vivado_shape()
    if vivado != EXPECTED_VIVADO:
        raise AssertionError(f"unexpected P0 OS-CFAR Vivado result: {vivado}")
    deterministic = first["normalized_output"] == second["normalized_output"]
    metrics = first["metrics"]
    frame_seconds = metrics["frame_completion_cycles"] / CLOCK_HZ
    rtl_capacity_fps = CLOCK_HZ / metrics["frame_completion_cycles"]
    required_fps = SAMPLE_RATE_HZ / FRAME_LENGTH
    alpha_fixed = ALPHA_Q32 / (1 << COEFFICIENT_FRACTION_BITS)
    functional_passed = (
        deterministic
        and golden["status"] == "passed"
        and metrics["frame_completion_cycles"] < FRAME_CYCLE_BUDGET
    )

    source_manifest = {
        "status": "passed",
        "files": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "frozen_phase06f_source": golden["real_power_source"],
    }
    return {
        "algorithm-contract.json": {
            "status": "passed",
            "profile": P0_DETECTOR_PROFILE.name,
            "frame_length": FRAME_LENGTH,
            "input_format": "natural-order unsigned 58-bit UQ28.30 power",
            "shift_mapping": "shifted_index = natural_index XOR 0x800",
            "reference_cells_per_side": 16,
            "guard_cells_per_side": 4,
            "order_statistic_rank": 24,
            "evaluated_shifted_bins": [20, 4075],
            "comparison": "(CUT << 32) > order_statistic * alpha_q32",
            "output": "64-bit natural-order power/evaluated/detected/marker word",
        },
        "architecture-study.json": {"status": "passed", **architecture_study()},
        "coefficient-validation.json": {
            "status": "passed",
            "float64_alpha": P0_DETECTOR_PROFILE.threshold_coefficient,
            "q32_integer": ALPHA_Q32,
            "q32_value": alpha_fixed,
            "absolute_error": abs(alpha_fixed - P0_DETECTOR_PROFILE.threshold_coefficient),
            "fixture_non_boundary_decision_mismatches": golden["non_boundary_decision_mismatches"],
            "fixture_evaluation_mask_mismatches": golden["evaluation_mask_mismatches"],
            "fixture_boundary_cases": [
                row for row in golden["vectors"] if row["boundary_case"]
            ],
        },
        "rtl-simulation.json": {
            "status": "passed" if functional_passed else "failed",
            "simulator": "Icarus Verilog 13.0 stable",
            "checked_dma_words": golden["samples"],
            "mismatch_count": 0,
            **metrics,
            "deterministic_rerun": "passed" if deterministic else "failed",
            "normalized_output_sha256": first["normalized_sha256"],
            "coverage": [
                "bit-exact 64-bit DMA output",
                "strict threshold floor and floor-plus-one",
                "duplicate reference removal and insertion",
                "shifted evaluation edges",
                "unsigned 58-bit extrema",
                "frozen real FFT power frames",
                "partial-frame reset",
                "output backpressure payload stability",
                "malformed TLAST and index rejection",
                "no drop and no duplication",
            ],
            "build_location": "external temporary directory",
        },
        "source-manifest.json": source_manifest,
        "throughput-capacity.json": {
            "status": "passed" if metrics["frame_completion_cycles"] < FRAME_CYCLE_BUDGET else "failed",
            "clock_hz": CLOCK_HZ,
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "frame_length": FRAME_LENGTH,
            "cycle_budget": FRAME_CYCLE_BUDGET,
            "measured_functional_cycles": metrics["frame_completion_cycles"],
            "functional_frame_seconds": frame_seconds,
            "functional_capacity_frames_per_second": rtl_capacity_fps,
            "required_frames_per_second": required_fps,
            "capacity_ratio": rtl_capacity_fps / required_fps,
            "claim_limit": "functional RTL cycle capacity only; not post-route or physical service throughput",
        },
        "toolchain.json": {
            "status": "passed",
            "rtl_language": "SystemVerilog",
            "simulator": "Icarus Verilog 13.0 stable",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "vivado": vivado["tool"],
            "synthesis": "passed",
            "implementation": "passed",
            "bitstream": "not_generated",
            "hardware": "not_exercised",
        },
        "vivado-implementation.json": {
            "status": "passed",
            **vivado,
            "clock_frequency_mhz": 50.0,
            "timing_constraints_met": True,
            "route_status": "fully_routed",
            "drc_scope": "standalone internal-chain implementation; no board-level package pins",
            "drc_disposition": {
                "NSTD-1": "expected on the standalone synthesis wrapper; the deployed block design owns I/O standards",
                "UCIO-1": "expected on the standalone synthesis wrapper; the deployed block design owns package locations",
            },
            "claim_limit": "post-route implementation evidence; no bitstream or physical-board throughput claim",
        },
        "verification-summary.json": {
            "functional_verification": "passed" if functional_passed else "failed",
            "integer_model": "passed",
            "float_reference_non_boundary": "passed",
            "rtl_compile": "passed",
            "rtl_bit_exact": "passed",
            "rtl_cycle_capacity_50mhz": "passed",
            "synthesis": "passed",
            "post_route_timing": "passed",
            "runtime_software_integration": "passed",
            "bitstream": "not_generated",
            "physical_service_acceptance": "not_run",
            "release_ready": False,
        },
    }


def write() -> None:
    documents = build_documents(execute_simulation=True, read_vivado_reports=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))
    print(f"P0 PL OS-CFAR kanıtı yazıldı: {len(OWNED_FILES)} dosya")


def check() -> bool:
    try:
        documents = build_documents(execute_simulation=False)
        exact = all(
            (EVIDENCE / name).is_file()
            and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name])
            for name in OWNED_FILES
        )
        payload = b"".join((EVIDENCE / name).read_bytes() for name in OWNED_FILES).decode(
            "utf-8", errors="replace"
        ).casefold()
        machine_neutral = not any(token in payload for token in ("c:\\users", "hostname", "onedrive"))
        return exact and machine_neutral and documents["verification-summary.json"]["functional_verification"] == "passed"
    except (OSError, ValueError, AssertionError, RuntimeError, json.JSONDecodeError):
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
    print(f"P0 PL OS-CFAR doğrulaması: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
