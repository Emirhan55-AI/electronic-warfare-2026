#!/usr/bin/env python3
"""Verify the isolated ST-06 full-power ZedBoard Vivado build."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VARIANT = "st06-power-v2"
VARIANT_ROOT = ROOT / "build/p0" / VARIANT
REPORT_ROOT = VARIANT_ROOT / "vivado/reports"
DSP_SYNTHESIS_LOG = (
    VARIANT_ROOT
    / "vivado/p0_runtime.runs/p0_system_p0_dsp_runtime_0_0_synth_1/runme.log"
)
BITSTREAM = VARIANT_ROOT / "vivado/p0_runtime.runs/impl_1/p0_system_wrapper.bit"
XSA = VARIANT_ROOT / "hardware/p0_system_50mhz.xsa"
BASELINE = ROOT / "results/evidence/p0/vivado-50mhz-adr0040-p03.json"
EVIDENCE = ROOT / "results/evidence/phase08/st06-power-vivado-v1.json"

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
    "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv",
    "algorithms/fpga/p0/rtl/p0_dsp_runtime_top.sv",
    "algorithms/fpga/p0/rtl/p0_dsp_runtime_bd.v",
    "scripts/create_st06_power_vivado_project.tcl",
    "scripts/run_p0_vivado.tcl",
    "scripts/verify_st06_power_vivado.py",
    "results/evidence/p0/vivado-50mhz-adr0040-p03.json",
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
        hwh = sorted(name for name in archive.namelist() if name.lower().endswith(".hwh"))
        if len(hwh) != 1:
            raise ValueError(f"XSA içinde tek HWH bekleniyordu: {hwh}")
        return hashlib.sha256(archive.read(hwh[0])).hexdigest()


def _difference(current: dict[str, int | float], baseline: dict[str, object]) -> dict[str, float]:
    current_used = float(current["used"])
    baseline_used = float(baseline["used"])
    return {
        "absolute": current_used - baseline_used,
        "relative_percent": (current_used - baseline_used) / baseline_used * 100.0,
    }


def evaluate(generated_at_utc: str | None = None) -> dict[str, object]:
    timing = _read_report("implementation-timing-summary.rpt")
    utilization = _read_report("implementation-utilization-summary.rpt")
    route = _read_report("route-status.rpt")
    drc = _read_report("implementation-drc.rpt")
    methodology = _read_report("methodology.rpt")
    check_timing = _read_report("check-timing.rpt")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if baseline.get("status") != "passed" or baseline.get("build_variant") != "p03":
        raise ValueError("P03 karşılaştırma kanıtı geçerli değil")
    if not BITSTREAM.is_file() or not XSA.is_file() or not DSP_SYNTHESIS_LOG.is_file():
        raise FileNotFoundError("ST-06 bitstream, XSA veya DSP sentez günlüğü eksik")

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
    resources = {
        "slice_luts": _resource(utilization, "Slice LUTs"),
        "slice_registers": _resource(utilization, "Slice Registers"),
        "block_ram_tiles": _resource(utilization, "Block RAM Tile"),
        "dsps": _resource(utilization, "DSPs"),
    }
    baseline_resources = baseline["post_route_resources"]
    resource_delta = {
        name: _difference(value, baseline_resources[name])
        for name, value in resources.items()
    }
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
    synthesis_log = DSP_SYNTHESIS_LOG.read_text(encoding="utf-8", errors="replace")
    initialization_failures = re.findall(
        r"could not open \$readmem data file|coefficient_rom[^\n]*does not have driver",
        synthesis_log,
        re.IGNORECASE,
    )
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
        and len(timing_issue_counts) >= 12
        and all(count == 0 for count in timing_issue_counts)
        and not initialization_failures
    )
    return {
        "schema": "phase08-st06-power-vivado-v1",
        "status": "passed" if passed else "failed",
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "st06_complete": False,
        "build_variant": VARIANT,
        "tool": f"Vivado v{tool.group(1)} build {tool.group(2)}",
        "target": "xc7z020clg484-1",
        "clock_hz": 50_000_000,
        "data_path": [
            "AXI DMA MM2S CI8 input",
            "UQ1.15 periodic Hann window",
            "AMD 4096-point FFT",
            "exact UQ28.30 linear power",
            "OS-CFAR decision metadata",
            "4096 natural-order AXI64 power words to PS",
        ],
        "dma": {
            "input_frame_bytes": 8192,
            "output_frame_bytes": 32768,
            "output_words": 4096,
            "output_word_bits": 64,
            "maximum_length_bytes": 65535,
            "output_fits_length_field": 32768 <= 65535,
        },
        "synthesis": "PASS",
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
        "post_route_resources": resources,
        "p03_comparison": {
            "baseline_path": BASELINE.relative_to(ROOT).as_posix(),
            "baseline_sha256": _sha256(BASELINE),
            "baseline_resources": baseline_resources,
            "resource_delta": resource_delta,
            "baseline_setup_wns_ns": baseline["timing"]["setup_wns_ns"],
            "baseline_hold_whs_ns": baseline["timing"]["hold_whs_ns"],
        },
        "hann_memory_initialization": {
            "status": "PASS" if not initialization_failures else "FAIL",
            "failure_count": len(initialization_failures),
            "log_sha256": _sha256(DSP_SYNTHESIS_LOG),
        },
        "drc_errors": drc_errors,
        "drc_critical_warnings": drc_critical,
        "drc_warnings": drc_warnings,
        "methodology_warnings": methodology_warnings,
        "bitstream": {
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
        "report_sha256": {name: _sha256(REPORT_ROOT / name) for name in REPORT_NAMES},
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCE_PATHS},
        "claim_boundary": [
            "This proves synthesis, routed 50 MHz timing, resource use, bitstream and XSA generation for the isolated full-power FPGA option.",
            "The generated image has not been loaded onto the board and is not the product image.",
            "ARM execution time, DMA lifecycle, sustained throughput, live RF, Pd/Pfa and field acceptance remain open.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 tam güç Vivado doğrulayıcısı")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        if EVIDENCE.exists():
            parser.error("Önceki ST-06 Vivado kanıtının üzerine yazılmaz.")
        result = evaluate()
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        if not EVIDENCE.is_file():
            print("ST-06 Vivado kanıtı bulunamadı.")
            return 1
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        result = evaluate(str(stored.get("generated_at_utc", "")))
        if stored != result:
            print("ST-06 Vivado kanıtı güncel kaynak ve çıktılarla eşleşmiyor.")
            return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "resources": result["post_route_resources"],
                "timing": result["timing"],
                "p03_resource_delta": result["p03_comparison"]["resource_delta"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
