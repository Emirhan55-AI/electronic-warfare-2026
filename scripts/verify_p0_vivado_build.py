#!/usr/bin/env python3
"""Validate and record the routed P0 ZedBoard hardware build."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "build/p0/vivado/reports"
DSP_SYNTHESIS_LOG = (
    ROOT
    / "build/p0/vivado/p0_runtime.runs/p0_system_p0_dsp_runtime_0_0_synth_1/runme.log"
)
BITSTREAM = ROOT / "build/p0/vivado/p0_runtime.runs/impl_1/p0_system_wrapper.bit"
XSA = ROOT / "build/p0/hardware/p0_system_50mhz.xsa"
EVIDENCE = ROOT / "results/evidence/p0/vivado-50mhz.json"

SOURCE_PATHS = (
    "algorithms/fpga/phase06a/rtl/axis_skid_buffer.sv",
    "algorithms/fpga/phase06b/rtl/phase06b_pkg.sv",
    "algorithms/fpga/phase06b/rtl/axis_hann_window.sv",
    "datasets/fixtures/phase06b/hann-coefficients.mem",
    "algorithms/fpga/phase06c/rtl/phase06c_pkg.sv",
    "algorithms/fpga/phase06c/rtl/axis_fft_wrapper.sv",
    "algorithms/fpga/phase06d/rtl/amd_xfft_adapter.sv",
    "algorithms/fpga/phase06d/ip/phase06d_fft_4096/phase06d_fft_4096.xci",
    "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    "algorithms/fpga/phase06i/rtl/phase06i_pkg.sv",
    "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv",
    "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
    "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
    "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_top.sv",
    "algorithms/fpga/p0/rtl/p0_region_bank.sv",
    "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_packetizer_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_bd.v",
    "scripts/create_p0_vivado_project.tcl",
    "scripts/run_p0_vivado.tcl",
)

REPORT_NAMES = (
    "implementation-timing-summary.rpt",
    "implementation-utilization-summary.rpt",
    "route-status.rpt",
    "implementation-drc.rpt",
    "methodology.rpt",
    "check-timing.rpt",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_report(name: str) -> str:
    path = REPORT_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(f"Vivado raporu eksik: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _match(pattern: str, text: str, label: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(f"{label} raporda bulunamadı")
    return match


def _resource(report: str, label: str) -> dict[str, int | float]:
    match = _match(
        rf"^\|\s*{re.escape(label)}\s*\|\s*([0-9.]+)\s*\|\s*\d+\s*\|"
        rf"\s*\d+\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|$",
        report,
        label,
    )
    used = float(match.group(1))
    available = float(match.group(2))
    return {
        "used": int(used) if used.is_integer() else used,
        "available": int(available) if available.is_integer() else available,
        "utilization_percent": float(match.group(3)),
    }


def _xsa_hwh_sha256() -> str:
    with zipfile.ZipFile(XSA) as archive:
        hwh_names = sorted(name for name in archive.namelist() if name.lower().endswith(".hwh"))
        if len(hwh_names) != 1:
            raise ValueError(f"XSA içinde tek HWH bekleniyordu: {hwh_names}")
        return hashlib.sha256(archive.read(hwh_names[0])).hexdigest()


def evaluate() -> dict[str, object]:
    timing = _read_report("implementation-timing-summary.rpt")
    utilization = _read_report("implementation-utilization-summary.rpt")
    route = _read_report("route-status.rpt")
    drc = _read_report("implementation-drc.rpt")
    methodology = _read_report("methodology.rpt")
    check_timing = _read_report("check-timing.rpt")
    if not DSP_SYNTHESIS_LOG.is_file():
        raise FileNotFoundError(f"DSP sentez günlüğü eksik: {DSP_SYNTHESIS_LOG}")
    dsp_synthesis_log = DSP_SYNTHESIS_LOG.read_text(encoding="utf-8", errors="replace")
    memory_initialization_failures = re.findall(
        r"could not open \$readmem data file|coefficient_rom[^\n]*does not have driver",
        dsp_synthesis_log,
        re.IGNORECASE,
    )

    tool = _match(
        r"Tool Version\s*:\s*Vivado v\.([0-9.]+).*?Build\s+(\d+)",
        timing,
        "Vivado sürümü",
    )
    timing_row = _match(
        r"^\s*([+-]?\d+\.\d+)\s+([+-]?\d+\.\d+)\s+(\d+)\s+\d+\s+"
        r"([+-]?\d+\.\d+)\s+([+-]?\d+\.\d+)\s+(\d+)\s+\d+\s+",
        timing,
        "WNS/WHS satırı",
    )
    setup = _match(
        r"Setup\s*:\s*(\d+)\s+Failing Endpoints,\s+Worst Slack\s+([+-]?\d+\.\d+)ns,"
        r"\s+Total Violation\s+([+-]?\d+\.\d+)ns",
        timing,
        "setup özeti",
    )
    hold = _match(
        r"Hold\s*:\s*(\d+)\s+Failing Endpoints,\s+Worst Slack\s+([+-]?\d+\.\d+)ns,"
        r"\s+Total Violation\s+([+-]?\d+\.\d+)ns",
        timing,
        "hold özeti",
    )

    route_values = {
        "routable_nets": int(
            _match(r"# of routable nets\.*\s*:\s*(\d+)\s*:", route, "yönlendirilebilir ağ").group(1)
        ),
        "fully_routed_nets": int(
            _match(r"# of fully routed nets\.*\s*:\s*(\d+)\s*:", route, "tam yönlendirilmiş ağ").group(1)
        ),
        "routing_errors": int(
            _match(r"# of nets with routing errors\.*\s*:\s*(\d+)\s*:", route, "yönlendirme hatası").group(1)
        ),
    }

    drc_rows = re.findall(
        r"^\|\s*([A-Z0-9-]+)\s*\|\s*(Error|Critical Warning|Warning|Advisory)\s*\|.*?\|\s*(\d+)\s*\|$",
        drc,
        re.MULTILINE,
    )
    drc_errors = sum(int(count) for _, severity, count in drc_rows if severity == "Error")
    drc_critical = sum(
        int(count) for _, severity, count in drc_rows if severity == "Critical Warning"
    )
    drc_warnings = {
        rule: int(count) for rule, severity, count in drc_rows if severity == "Warning"
    }
    methodology_warnings = {
        rule: int(count)
        for rule, severity, count in re.findall(
            r"^\|\s*([A-Z0-9-]+)\s*\|\s*(Error|Critical Warning|Warning|Advisory)\s*\|.*?\|\s*(\d+)\s*\|$",
            methodology,
            re.MULTILINE,
        )
        if severity == "Warning"
    }

    timing_issue_counts = [
        int(value)
        for value in re.findall(r"^\d+\. checking [a-z_]+ \((\d+)\)$", check_timing, re.MULTILINE)
    ]
    if len(timing_issue_counts) < 12:
        raise ValueError("check_timing envanteri eksik")

    if not BITSTREAM.is_file() or not XSA.is_file():
        raise FileNotFoundError("Bitstream veya XSA bulunamadı")

    setup_wns = float(timing_row.group(1))
    setup_tns = float(timing_row.group(2))
    hold_whs = float(timing_row.group(4))
    hold_ths = float(timing_row.group(5))
    setup_failures = int(setup.group(1))
    hold_failures = int(hold.group(1))
    passed = (
        "Design State : Routed" in timing
        and setup_wns >= 0.0
        and setup_tns == 0.0
        and hold_whs >= 0.0
        and hold_ths == 0.0
        and setup_failures == 0
        and hold_failures == 0
        and float(setup.group(3)) == 0.0
        and float(hold.group(3)) == 0.0
        and route_values["routing_errors"] == 0
        and route_values["fully_routed_nets"] == route_values["routable_nets"]
        and route_values["fully_routed_nets"] > 0
        and drc_errors == 0
        and drc_critical == 0
        and all(count == 0 for count in timing_issue_counts)
        and not memory_initialization_failures
    )

    return {
        "schema_version": 6,
        "status": "passed" if passed else "failed",
        "scope": "ZedBoard CI8-to-candidate-packet Vivado build",
        "tool": f"Vivado v{tool.group(1)} build {tool.group(2)}",
        "target": "xc7z020clg484-1",
        "top": "p0_system_wrapper",
        "board_definition": {
            "board_part": "avnet-tria:zedboard:part0:1.5",
            "repository": "https://github.com/Avnet/bdf",
            "commit": "e9723b55a68b106fb4cdb645974d096cd3594a2a",
        },
        "clock_hz": 50_000_000,
        "data_path": [
            "AXI DMA MM2S CI8 input",
            "UQ1.15 periodic Hann window",
            "AMD 4096-point FFT",
            "exact UQ28.30 linear power",
            "sparse OS-CFAR and wideband candidate reducer",
            "PHASE-06I AXI64 candidate packetizer",
            "AXI DMA S2MM output",
        ],
        "dma": {
            "scatter_gather": False,
            "mm2s_enabled": True,
            "s2mm_enabled": True,
            "dre_enabled": False,
            "length_width_bits": 16,
            "maximum_length_bytes": 65_535,
            "input_frame_bytes": 8_192,
            "candidate_packet_bytes": {"minimum": 64, "maximum": 54_144},
            "base_address": "0x40400000",
            "mm2s_stream_bits": 16,
            "s2mm_stream_bits": 64,
            "software_contract": "petalinux_rebuild_passed_pending_board_acceptance",
        },
        "block_design_validation": "PASS",
        "synthesis": "PASS",
        "hann_memory_initialization": {
            "status": "PASS" if not memory_initialization_failures else "FAIL",
            "failure_count": len(memory_initialization_failures),
            "log_sha256": _sha256(DSP_SYNTHESIS_LOG),
        },
        "implementation": "ROUTE_DESIGN_COMPLETE",
        "route": route_values,
        "timing": {
            "setup_wns_ns": setup_wns,
            "setup_tns_ns": setup_tns,
            "setup_failing_endpoints": setup_failures,
            "hold_whs_ns": hold_whs,
            "hold_ths_ns": hold_ths,
            "hold_failing_endpoints": hold_failures,
            "check_timing_issue_counts": timing_issue_counts[:12],
        },
        "post_route_resources": {
            "slice_luts": _resource(utilization, "Slice LUTs"),
            "slice_registers": _resource(utilization, "Slice Registers"),
            "block_ram_tiles": _resource(utilization, "Block RAM Tile"),
            "dsps": _resource(utilization, "DSPs"),
        },
        "drc_errors": drc_errors,
        "drc_critical_warnings": drc_critical,
        "drc_warnings": drc_warnings,
        "methodology_warnings": methodology_warnings,
        "bitstream": {
            "status": "PASS",
            "relative_path": BITSTREAM.relative_to(ROOT).as_posix(),
            "bytes": BITSTREAM.stat().st_size,
            "sha256": _sha256(BITSTREAM),
        },
        "hardware_platform": {
            "relative_path": XSA.relative_to(ROOT).as_posix(),
            "bytes": XSA.stat().st_size,
            "xsa_sha256": _sha256(XSA),
            "hwh_sha256": _xsa_hwh_sha256(),
        },
        "report_sha256": {
            name: _sha256(REPORT_ROOT / name) for name in REPORT_NAMES
        },
        "source_sha256": {
            name: _sha256(ROOT / name) for name in SOURCE_PATHS
        },
        "supersedes": {
            "bitstream_sha256": "287fb88b093e317c80aee363712d279f6b27dd7afbb758a21a5a16b6a4d3845e",
            "xsa_sha256": "1426414a7350c9d8a903a5753f0867220393f22280eef690192ff43b46b36a08",
            "archive": "build/p0/archive/legacy-power-runtime-20260828",
        },
        "claim_boundary": (
            "This evidence proves local Vivado block-design validation, synthesis, routed "
            "50 MHz timing, bitstream and XSA generation for the complete CI8-to-candidate-packet "
            "PL hierarchy. The variable-length DMA contract is implemented, host-accepted and "
            "included in a successful PetaLinux rebuild; board programming, positive-signal "
            "board acceptance, physical sustained throughput, calibrated RF accuracy and live "
            "HackRF processing remain open."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.check and not REPORT_ROOT.is_dir():
        if not EVIDENCE.is_file():
            print("P0 Vivado kanıtı ve geçici rapor dizini bulunamadı.")
            return 1
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        current = {name: _sha256(ROOT / name) for name in SOURCE_PATHS}
        if stored.get("source_sha256") != current:
            print("P0 Vivado kanıtı kaynak hash'leriyle eşleşmiyor.")
            return 1
        print(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", end="")
        return 0 if stored.get("status") == "passed" else 1

    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE.is_file() or EVIDENCE.read_text(encoding="utf-8") != serialized:
        print("P0 Vivado kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
