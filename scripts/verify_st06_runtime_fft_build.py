#!/usr/bin/env python3
"""Record or verify the routed ST-06 runtime FFT build and its source identity."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / "build/p0/st06-rfft-v4-20260910"
DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-runtime-fft-build-20260910.json"
CAPACITY = {"slice_luts": 53_200, "slice_registers": 106_400,
            "block_ram_tiles": 140.0, "dsps": 220}
SOURCES = (
    "algorithms/fpga/p0/rtl/axis_hann_window_runtime.sv",
    "algorithms/fpga/p0/rtl/axis_fft_runtime_wrapper.sv",
    "algorithms/fpga/p0/rtl/amd_xfft_runtime_adapter.sv",
    "algorithms/fpga/p0/rtl/axis_fft_runtime_linear_power.sv",
    "algorithms/fpga/p0/rtl/axis_fft_power_normalizer.sv",
    "algorithms/fpga/p0/rtl/axis_p0_runtime_os_cfar.sv",
    "algorithms/fpga/p0/rtl/p0_dsp_runtime_fft_top.sv",
    "algorithms/fpga/p0/rtl/p0_detection_profile_control.sv",
    "platforms/embedded/p0/src/p0_dma_client.c",
    "platforms/embedded/p0/src/p0_dma_runtime.c",
    "platforms/embedded/p0/src/p0_ed_service.c",
    "platforms/embedded/p0/src/p0_ed_service_protocol.c",
    "platforms/embedded/p0/src/p0_ed_network_bridge.c",
    "platforms/embedded/p0/src/p0_pl_os_cfar.c",
    "platforms/embedded/p0/include/p0_dma_uapi.h",
    "platforms/embedded/p0/include/p0_ed_service_protocol.h",
    "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    "algorithms/p0/transport.py",
    "algorithms/p0/detection_config.py",
    "app/operator_console/live_ed.py",
    "app/operator_console/quick_scan_actions.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/qml/DetectionSettings.qml",
    "datasets/fixtures/phase06b/hann-runtime-coefficients-4096.mem",
    "datasets/fixtures/phase06b/hann-runtime-coefficients-8192.mem",
    "datasets/fixtures/phase06b/hann-runtime-coefficients-16384.mem",
    "scripts/create_st06_runtime_fft_vivado_project.tcl",
    "scripts/build_st06_runtime_fft_vivado.tcl",
    "scripts/st06_runtime_fft_ip_config.tcl",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resource(text: str, label: str) -> int | float:
    match = re.search(
        rf"^\|\s*{re.escape(label)}\*?\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"Kaynak satırı bulunamadı: {label}")
    value = float(match.group(1))
    return int(value) if value.is_integer() else value


def evaluate(build: Path) -> dict:
    reports = build / "vivado/reports"
    utilization_path = reports / "implementation-utilization-summary.rpt"
    hierarchy_path = reports / "synthesis-utilization.rpt"
    timing_path = reports / "implementation-timing-summary.rpt"
    route_path = reports / "route-status.rpt"
    bitstream_path = build / "hardware/p0_system_wrapper.bit.bin"
    xsa_path = build / "hardware/p0_system_50mhz.xsa"
    module_path = build / "software/lib/modules/6.12.40-xilinx-g31626ef92ff1/updates/p0_dma_client.ko"
    service_path = build / "software/usr/sbin/p0-ed-service"
    bridge_path = build / "software/usr/sbin/p0-ed-network-bridge"
    artifacts = (utilization_path, hierarchy_path, timing_path, route_path,
                 bitstream_path, xsa_path, module_path, service_path, bridge_path)
    missing = [str(path) for path in artifacts if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Eksik çalışma zamanı FFT ürünü: {missing}")

    utilization = utilization_path.read_text(encoding="utf-8", errors="replace")
    hierarchy = hierarchy_path.read_text(encoding="utf-8", errors="replace")
    timing = timing_path.read_text(encoding="utf-8", errors="replace")
    route = route_path.read_text(encoding="utf-8", errors="replace")
    resources = {
        "slice_luts": _resource(utilization, "Slice LUTs"),
        "slice_registers": _resource(utilization, "Slice Registers"),
        "block_ram_tiles": _resource(utilization, "Block RAM Tile"),
        "dsps": _resource(utilization, "DSPs"),
    }
    timing_match = re.search(
        r"^\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+"
        r"(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+",
        timing,
        flags=re.MULTILINE,
    )
    if timing_match is None:
        raise ValueError("Vivado zamanlama özeti çözülemedi")
    hann_match = re.search(
        r"^\|\s+hann\s+\|.*?\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        hierarchy,
        flags=re.MULTILINE,
    )
    if hann_match is None:
        raise ValueError("Hann hiyerarşi kaynağı çözülemedi")
    hann = {"total_luts": int(hann_match.group(1)),
            "block_ram_36": int(hann_match.group(6)),
            "block_ram_18": int(hann_match.group(7)),
            "dsps": int(hann_match.group(8))}
    checks = {
        "timing_constraints_met": "All user specified timing constraints are met." in timing,
        "setup_slack_positive": float(timing_match.group(1)) >= 0.0,
        "hold_slack_positive": float(timing_match.group(3)) >= 0.0,
        "routing_errors_zero": "# of nets with routing errors.......... :           0" in route,
        "resources_fit_zynq_7020": all(resources[key] <= CAPACITY[key] for key in resources),
        "hann_uses_block_ram": hann["block_ram_36"] + hann["block_ram_18"] > 0,
        "hann_lut_cost_bounded": hann["total_luts"] <= 256,
        "runtime_control_identity_present": "53540602" in (ROOT / SOURCES[7]).read_text(),
    }
    return {
        "schema": "phase08-st06-runtime-fft-build-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "routed Zynq-7020 Hann/4096-8192-16384 FFT/power/OS-CFAR build plus ARM product artifacts",
        "vivado": "2025.2",
        "device": "xc7z020clg484-1",
        "supported_fft_sizes": [4096, 8192, 16384],
        "timing": {"wns_ns": float(timing_match.group(1)),
                   "tns_ns": float(timing_match.group(2)),
                   "whs_ns": float(timing_match.group(3)),
                   "ths_ns": float(timing_match.group(4))},
        "resources": resources,
        "hann_resources": hann,
        "checks": checks,
        "source_sha256": {source: _digest(ROOT / source) for source in SOURCES},
        "artifact_sha256": {
            path.relative_to(build).as_posix(): _digest(path) for path in artifacts
        },
        "claim_boundary": {"hardware_executed": False, "hackrf_used": False,
                           "rf_pd_pfa_accepted": False, "cold_boot_accepted": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    observed = evaluate(args.build.resolve())
    if args.check:
        expected = json.loads(args.output.read_text(encoding="utf-8"))
        expected.pop("generated_at_utc", None)
        observed.pop("generated_at_utc", None)
        if observed != expected:
            print("Çalışma zamanı FFT build kanıtı güncel ürünlerle eşleşmiyor.", file=sys.stderr)
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({"status": observed["status"], "timing": observed["timing"],
                      "resources": observed["resources"], "checks": observed["checks"]},
                     ensure_ascii=False, indent=2))
    return 0 if observed["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
