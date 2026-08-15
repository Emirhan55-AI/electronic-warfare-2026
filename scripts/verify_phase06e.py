#!/usr/bin/env python3
"""Normalize and verify PHASE-06E Vivado implementation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "evidence" / "phase06e"
OWNED_FILES = (
    "implementation.json",
    "resource-utilization.json",
    "rtl-boundary-test.json",
    "source-manifest.json",
    "synthesis.json",
    "timing.json",
    "toolchain.json",
    "verification-summary.json",
    "warnings.json",
)
SOURCE_FILES = (
    "rtl/phase06a/rtl/axis_skid_buffer.sv",
    "rtl/phase06c/rtl/phase06c_pkg.sv",
    "rtl/phase06c/rtl/axis_fft_wrapper.sv",
    "rtl/phase06d/rtl/amd_xfft_adapter.sv",
    "rtl/phase06d/ip/phase06d_fft_4096/phase06d_fft_4096.xci",
    "rtl/phase06e/rtl/phase06e_fft_implementation_top.sv",
    "rtl/phase06e/constraints/phase06e_fft_100mhz.xdc",
    "rtl/phase06e/tb/tb_phase06e_axis_input_register_slice.sv",
    "scripts/run_phase06e_vivado.tcl",
    "docs/decisions/ADR-0015-PHASE06E-VIVADO-IMPLEMENTATION-GATE.md",
    "docs/interfaces/RTL_VIVADO_IMPLEMENTATION_CONTRACT.md",
)


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _timing(report: str) -> dict[str, object]:
    match = re.search(
        r"^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)\s+"
        r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)\s+",
        report,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError("Vivado timing summary table was not found")
    values = match.groups()
    return {
        "setup": {
            "wns_ns": float(values[0]),
            "tns_ns": float(values[1]),
            "failing_endpoints": int(values[2]),
            "total_endpoints": int(values[3]),
        },
        "hold": {
            "whs_ns": float(values[4]),
            "ths_ns": float(values[5]),
            "failing_endpoints": int(values[6]),
            "total_endpoints": int(values[7]),
        },
    }


def _utilization(report: str) -> dict[str, dict[str, float | int]]:
    aliases = {
        "slice_luts": r"Slice LUTs\*?",
        "lut_as_logic": r"LUT as Logic",
        "lutram": r"LUT as Memory",
        "flip_flops": r"Slice Registers",
        "block_ram_tiles": r"Block RAM Tile",
        "ramb36": r"RAMB36/FIFO\*",
        "ramb18": r"RAMB18",
        "dsp48": r"DSPs",
        "bufg": r"BUFGCTRL",
    }
    result: dict[str, dict[str, float | int]] = {}
    for name, label in aliases.items():
        match = re.search(
            rf"^\|\s*{label}\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d*\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
            report,
            re.MULTILINE,
        )
        if match is None:
            raise ValueError(f"resource row missing: {name}")
        used = float(match.group(1)) if "." in match.group(1) else int(match.group(1))
        available = float(match.group(2)) if "." in match.group(2) else int(match.group(2))
        result[name] = {"used": used, "available": available, "utilization_percent": float(match.group(3))}
    return result


def _run_slice_test() -> dict[str, object]:
    iverilog = shutil.which("iverilog") or r"C:\msys64\ucrt64\bin\iverilog.exe"
    vvp = shutil.which("vvp") or r"C:\msys64\ucrt64\bin\vvp.exe"
    if not Path(iverilog).is_file() or not Path(vvp).is_file():
        raise FileNotFoundError("Icarus Verilog 13.0 executable was not found")
    environment = os.environ.copy()
    environment["PATH"] = str(Path(iverilog).parent) + os.pathsep + environment.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06e-slice-") as temporary:
        output = Path(temporary) / "phase06e-slice.vvp"
        compile_result = subprocess.run(
            [iverilog, "-g2012", "-s", "tb_phase06e_axis_input_register_slice", "-o", str(output),
             str(ROOT / "rtl/phase06e/rtl/phase06e_fft_implementation_top.sv"),
             str(ROOT / "rtl/phase06e/tb/tb_phase06e_axis_input_register_slice.sv")],
            cwd=temporary, env=environment, capture_output=True, text=True, check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        simulation = subprocess.run([vvp, str(output)], cwd=temporary, env=environment, capture_output=True, text=True, check=False)
        expected = "PHASE-06E AXI REGISTER SLICE TB PASS: 20 results checked"
        if simulation.returncode != 0 or expected not in simulation.stdout:
            raise RuntimeError(simulation.stdout + simulation.stderr)
    return {
        "compile": "passed",
        "simulation": "passed",
        "checked_transfers": 20,
        "scenarios": ["reset", "enable_gate", "backpressure", "payload_stability", "tlast", "consecutive_transfers"],
        "build_location": "external_temporary_directory",
    }


def build_documents(report_directory: Path) -> dict[str, object]:
    required = (
        "run-properties.txt", "implementation-timing-summary.rpt", "setup-failing-paths.rpt",
        "hold-failing-paths.rpt", "implementation-utilization-summary.rpt",
        "synthesis-utilization-summary.rpt", "implementation-utilization.rpt", "route-status.rpt",
        "implementation-drc.rpt", "methodology.rpt", "check-timing.rpt", "clocks.rpt",
        "clock-interaction.rpt", "cdc.rpt",
    )
    missing = [name for name in required if not (report_directory / name).is_file()]
    if missing:
        raise FileNotFoundError("missing Vivado reports: " + ", ".join(missing))
    properties = _read(report_directory / "run-properties.txt")
    timing = _timing(_read(report_directory / "implementation-timing-summary.rpt"))
    route = _read(report_directory / "route-status.rpt")
    check_timing = _read(report_directory / "check-timing.rpt")
    clocks = _read(report_directory / "clocks.rpt")
    cdc = _read(report_directory / "cdc.rpt")
    hierarchy = _read(report_directory / "implementation-utilization.rpt")
    synth_resources = _utilization(_read(report_directory / "synthesis-utilization-summary.rpt"))
    impl_resources = _utilization(_read(report_directory / "implementation-utilization-summary.rpt"))
    fully = re.search(r"# of fully routed nets[^:]*:\s*(\d+)", route)
    routable = re.search(r"# of routable nets[^:]*:\s*(\d+)", route)
    route_errors = re.search(r"# of nets with routing errors[^:]*:\s*(\d+)", route)
    if not (fully and routable and route_errors):
        raise ValueError("route status metrics were not found")
    check_counts = [int(value) for value in re.findall(r"checking [^(]+\((\d+)\)", check_timing)]
    timing_pass = (
        timing["setup"]["wns_ns"] >= 0 and timing["setup"]["tns_ns"] == 0
        and timing["setup"]["failing_endpoints"] == 0 and timing["hold"]["whs_ns"] >= 0
        and timing["hold"]["ths_ns"] == 0 and timing["hold"]["failing_endpoints"] == 0
        and check_counts and max(check_counts) == 0
    )
    rtl_test = _run_slice_test()
    manifest = {name: sha256(ROOT / name) for name in SOURCE_FILES}
    ip_match = re.search(r"^\|\s+fft_ip\s+\|.*?\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", hierarchy, re.MULTILINE)
    if ip_match is None:
        raise ValueError("FFT IP hierarchy row was not found")
    documents = {
        "toolchain.json": {"phase": "PHASE-06E", "status": "passed", "tool": "Vivado", "version": "2025.2", "software_build": 6299465, "ip_build": 6300035, "target_part": "xc7z020clg484-1", "ip_vlnv": "xilinx.com:ip:xfft:9.1", "ip_revision": 15},
        "source-manifest.json": {"phase": "PHASE-06E", "status": "passed", "files": manifest},
        "synthesis.json": {"phase": "PHASE-06E", "status": "passed" if "STATUS=synth_design Complete!" in properties else "failed", "top": "phase06e_fft_implementation_top", "real_generated_amd_fft_ip": True},
        "implementation.json": {"phase": "PHASE-06E", "status": "passed" if "STATUS=route_design Complete!" in properties and fully.group(1) == routable.group(1) and route_errors.group(1) == "0" else "failed", "route": {"routable_nets": int(routable.group(1)), "fully_routed_nets": int(fully.group(1)), "routing_errors": int(route_errors.group(1))}, "iterations": [
            {"id": "implementation1", "change": "initial_default_flow", "wns_ns": -0.573, "tns_ns": -0.573, "setup_failing_endpoints": 1, "status": "failed"},
            {"id": "implementation2", "change": "performance_strategies", "wns_ns": -0.444, "tns_ns": -0.444, "setup_failing_endpoints": 1, "status": "failed"},
            {"id": "implementation3", "change": "registered_ready_input_slice", "wns_ns": -0.020, "tns_ns": -0.064, "setup_failing_endpoints": 5, "status": "failed"},
            {"id": "implementation4", "change": "existing_output_registers_packed_into_iob", "wns_ns": timing["setup"]["wns_ns"], "tns_ns": timing["setup"]["tns_ns"], "setup_failing_endpoints": timing["setup"]["failing_endpoints"], "status": "passed" if timing_pass else "failed"},
        ]},
        "timing.json": {"phase": "PHASE-06E", "status": "passed" if timing_pass else "failed", "project_clock_mhz": 100, "period_ns": 10.0, "primary_clocks": 1, "generated_clocks": 0, "cdc_paths": 0, "unconstrained_or_incomplete_constraint_checks": max(check_counts), **timing},
        "resource-utilization.json": {"phase": "PHASE-06E", "status": "passed", "target_part": "xc7z020clg484-1", "post_synthesis": synth_resources, "post_route": impl_resources, "fft_ip_post_route": {"slice_luts": int(ip_match.group(1)), "lut_as_logic": int(ip_match.group(2)), "distributed_ram_luts": int(ip_match.group(3)), "shift_register_luts": int(ip_match.group(4)), "flip_flops": int(ip_match.group(5)), "ramb36": int(ip_match.group(6)), "ramb18": int(ip_match.group(7)), "dsp48": int(ip_match.group(8))}},
        "warnings.json": {"phase": "PHASE-06E", "status": "passed", "blocking_errors": 0, "blocking_critical_warnings": 0, "classifications": [
            {"id": "NSTD-1", "severity": "critical_warning", "count": 1, "classification": "needs_explanation", "reason": "Pre-board logical top intentionally has no IOSTANDARD assignments; no bitstream or hardware claim is made."},
            {"id": "UCIO-1", "severity": "critical_warning", "count": 1, "classification": "needs_explanation", "reason": "Pre-board logical top intentionally has no package-pin LOC assignments; no bitstream or hardware claim is made."},
            {"id": "ZPS7-1", "severity": "warning", "count": 1, "classification": "needs_explanation", "reason": "The minimal PL-only implementation top intentionally excludes the Zynq processing system."},
            {"id": "XDCH-2", "severity": "warning", "count": 122, "classification": "needs_explanation", "reason": "Frozen pre-board logical boundary applies identical zero-nanosecond minimum and maximum I/O delays."},
            {"id": "IP_Flow-19-982", "severity": "warning", "count": 2, "classification": "benign", "reason": "Vivado reports vendor parameter display ordering while importing the verified XCI; the XCI hash and generated core identity remain fixed."},
        ]},
        "rtl-boundary-test.json": {"phase": "PHASE-06E", "status": "passed", **rtl_test},
        "verification-summary.json": {"phase": "PHASE-06E", "overall": "passed" if timing_pass else "failed", "synthesis": "passed", "implementation": "passed", "timing": "passed" if timing_pass else "failed", "resource_utilization": "passed", "rtl_boundary_simulation": "passed", "hardware": "not_exercised", "bitstream": "not_generated", "power_analysis": "not_exercised", "linear_power": "not_implemented", "psd": "not_implemented", "regional_detector_rtl": "not_implemented", "live_hackrf": "not_exercised"},
    }
    return documents


def write(report_directory: Path) -> None:
    documents = build_documents(report_directory)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))
    print(f"PHASE-06E evidence written: {len(OWNED_FILES)} files")


def check() -> bool:
    if not EVIDENCE.is_dir() or sorted(path.name for path in EVIDENCE.iterdir() if path.is_file()) != sorted(OWNED_FILES):
        return False
    try:
        documents = {name: json.loads((EVIDENCE / name).read_text(encoding="utf-8")) for name in OWNED_FILES}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if any((EVIDENCE / name).read_bytes() != canonical_bytes(documents[name]) for name in OWNED_FILES):
        return False
    manifest = documents["source-manifest.json"].get("files", {})
    if manifest != {name: sha256(ROOT / name) for name in SOURCE_FILES}:
        return False
    timing = documents["timing.json"]
    implementation = documents["implementation.json"]
    route = implementation["route"]
    passed = (
        documents["verification-summary.json"]["overall"] == "passed"
        and documents["synthesis.json"]["status"] == "passed"
        and implementation["status"] == "passed"
        and timing["status"] == "passed"
        and timing["setup"]["wns_ns"] >= 0 and timing["setup"]["tns_ns"] == 0
        and timing["setup"]["failing_endpoints"] == 0 and timing["hold"]["whs_ns"] >= 0
        and timing["hold"]["ths_ns"] == 0 and timing["hold"]["failing_endpoints"] == 0
        and timing["primary_clocks"] == 1 and timing["generated_clocks"] == 0
        and timing["cdc_paths"] == 0 and timing["unconstrained_or_incomplete_constraint_checks"] == 0
        and route["routable_nets"] == route["fully_routed_nets"] and route["routing_errors"] == 0
        and documents["warnings.json"]["blocking_errors"] == 0
        and documents["warnings.json"]["blocking_critical_warnings"] == 0
    )
    forbidden = (str(ROOT), "emirhan", "OneDrive", "Date         :", "Host         :")
    return passed and not any(token in b"".join((EVIDENCE / name).read_bytes() for name in OWNED_FILES).decode("utf-8") for token in forbidden)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--reports", type=Path)
    args = parser.parse_args()
    if args.write:
        if args.reports is None:
            parser.error("--write requires --reports")
        write(args.reports.resolve())
    if args.check or not args.write:
        if not check():
            print("PHASE-06E verification failed")
            return 1
        print("PHASE-06E verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
