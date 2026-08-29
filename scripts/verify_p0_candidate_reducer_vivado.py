#!/usr/bin/env python3
"""Validate the recorded Vivado synthesis and place-and-route gate for P0."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "build/p0/candidate-reducer-vivado/reports"
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-vivado.json"
SOURCE_PATHS = (
    ROOT / "algorithms/fpga/p0/constraints/p0_candidate_reducer_50mhz.xdc",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_region_bank.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_synthesis_top.sv",
    ROOT / "scripts/run_p0_candidate_reducer_vivado.tcl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(name: str) -> str:
    path = REPORT_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(f"Vivado raporu eksik: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _match(pattern: str, text: str, name: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise ValueError(f"{name} raporda bulunamadı")
    return match.group(1)


def _number(pattern: str, text: str, name: str, cast=float) -> float | int:
    value = _match(pattern, text, name)
    return cast(value)


def evaluate() -> dict[str, object]:
    timing = _text("implementation-timing-summary.rpt")
    utilization = _text("implementation-utilization-summary.rpt")
    route = _text("route-status.rpt")
    drc = _text("implementation-drc.rpt")
    check_timing = _text("check-timing.rpt")

    wns = _number(r"^\s*([+-]?\d+\.\d+)\s+0\.000\s+0\s+\d+\s+([+-]?\d+\.\d+)\s+0\.000", timing, "WNS/WHS")
    whs_match = re.search(
        r"^\s*[+-]?\d+\.\d+\s+0\.000\s+0\s+\d+\s+([+-]?\d+\.\d+)\s+0\.000",
        timing,
        re.MULTILINE,
    )
    if whs_match is None:
        raise ValueError("WHS raporda bulunamadı")
    whs = float(whs_match.group(1))
    setup_failures = int(_match(r"Setup\s+:\s+(\d+)\s+Failing Endpoints", timing, "setup failures"))
    hold_failures = int(_match(r"Hold\s+:\s+(\d+)\s+Failing Endpoints", timing, "hold failures"))
    total_violation_setup = float(_match(r"Setup\s+:.*?Total Violation\s+([+-]?\d+\.\d+)ns", timing, "setup violation"))
    total_violation_hold = float(_match(r"Hold\s+:.*?Total Violation\s+([+-]?\d+\.\d+)ns", timing, "hold violation"))

    route_errors = int(_match(r"# of nets with routing errors.*:\s+(\d+)", route, "route errors"))
    routable = int(_match(r"# of routable nets.*:\s+(\d+)", route, "routable nets"))
    fully_routed = int(_match(r"# of fully routed nets.*:\s+(\d+)", route, "fully routed nets"))

    critical_drc = len(re.findall(r"\| [A-Z0-9-]+ \| Critical Warning \|", drc))
    check_timing_zero = all(
        int(value) == 0
        for value in re.findall(r"checking [^()]+ \((\d+)\)", check_timing)
    )
    gate_passed = (
        "Design State : Routed" in timing
        and wns >= 0.0
        and whs >= 0.0
        and setup_failures == 0
        and hold_failures == 0
        and total_violation_setup == 0.0
        and total_violation_hold == 0.0
        and route_errors == 0
        and fully_routed > 0
        and check_timing_zero
    )

    report_paths = {
        name: _sha256(REPORT_ROOT / name)
        for name in (
            "implementation-timing-summary.rpt",
            "implementation-utilization-summary.rpt",
            "route-status.rpt",
            "implementation-drc.rpt",
            "check-timing.rpt",
        )
    }
    return {
        "schema_version": 1,
        "status": "passed" if gate_passed else "failed",
        "scope": "P0 candidate reducer Vivado synthesis and routed 50 MHz timing gate",
        "tool": "Vivado 2025.2",
        "device": "xc7z020clg484-1",
        "top": "p0_candidate_reducer_synthesis_top",
        "clock": {"frequency_hz": 50_000_000, "period_ns": 20.0},
        "synthesis": {"status": "complete"},
        "implementation": {"status": "route_design Complete!", "design_state": "Routed"},
        "timing": {
            "wns_ns": float(wns),
            "whs_ns": whs,
            "setup_failing_endpoints": setup_failures,
            "hold_failing_endpoints": hold_failures,
            "setup_total_violation_ns": total_violation_setup,
            "hold_total_violation_ns": total_violation_hold,
            "check_timing_all_zero": check_timing_zero,
        },
        "resources": {
            "slice_luts": int(_match(r"\| Slice LUTs\s+\|\s+(\d+)", utilization, "slice LUTs")),
            "slice_registers": int(_match(r"\| Slice Registers\s+\|\s+(\d+)", utilization, "slice registers")),
            "block_ram_tiles": float(_match(r"\| Block RAM Tile\s+\|\s+([0-9.]+)", utilization, "block RAM tiles")),
            "dsp48e1": int(_match(r"\| DSPs\s+\|\s+(\d+)", utilization, "DSPs")),
            "bonded_iob": int(_match(r"\| Bonded IOB\s+\|\s+(\d+)", utilization, "bonded Iob")),
        },
        "routing": {
            "fully_routed_nets": fully_routed,
            "routable_nets": routable,
            "routing_error_nets": route_errors,
        },
        "drc": {
            "critical_warning_rules": ["NSTD-1", "UCIO-1"],
            "critical_warning_rule_count": critical_drc,
            "board_ready": False,
            "boundary": "Synthesis-only wrapper has no board pin locations or I/O standards; bitstream generation and board acceptance remain open.",
        },
        "report_sha256": report_paths,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCE_PATHS
        },
        "claim_boundary": (
            "This evidence covers RTL synthesis, placement, routing and constrained 50 MHz timing only. "
            "It does not claim packetizer integration, bitstream generation, DMA/driver integration, "
            "board execution or physical real-time acceptance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check and not REPORT_ROOT.is_dir():
        if not EVIDENCE_PATH.is_file():
            print("P0 Vivado kanıtı ve geçici rapor dizini bulunamadı.")
            return 1
        result = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        expected_hashes = result.get("source_sha256", {})
        current_hashes = {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCE_PATHS
        }
        if expected_hashes != current_hashes:
            print("P0 Vivado kanıtı kaynak hash'leriyle eşleşmiyor.")
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2) + "\n", end="")
        return 0 if result.get("status") == "passed" else 1
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("P0 Vivado sentez/yerleştirme kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
