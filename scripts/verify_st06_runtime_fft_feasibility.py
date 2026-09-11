#!/usr/bin/env python3
"""Build and record a bounded OOC feasibility probe for runtime FFT length."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / "build/p0/st06-runtime-fft-probe"
DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-runtime-fft-feasibility-20260910.json"
PART_CAPACITY = {"slice_luts": 53200, "slice_registers": 106400, "bram_tiles": 140.0, "dsps": 220}
CURRENT_FULL = {"slice_luts": 19895, "slice_registers": 17716, "bram_tiles": 23.5, "dsps": 53}
REQUIRED_PROPERTIES = {
    "fixed4096": {
        "CONFIG.transform_length": "4096",
        "CONFIG.run_time_configurable_transform_length": "false",
        "s_axis_config_tdata": "8",
        "m_axis_data_tuser": "16",
    },
    "runtime16384": {
        "CONFIG.transform_length": "16384",
        "CONFIG.run_time_configurable_transform_length": "true",
        "s_axis_config_tdata": "16",
        "m_axis_data_tuser": "16",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_vivado(explicit: str | None) -> str:
    candidates = [
        explicit,
        shutil.which("vivado"),
        r"C:\AMDDesignTools\2025.2\Vivado\bin\vivado.bat",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise FileNotFoundError("Vivado bulunamadı; --vivado ile yürütülebilir yolu verin")


def _run_probe(build_dir: Path, vivado: str | None) -> None:
    executable = _find_vivado(vivado)
    if build_dir.exists():
        if build_dir.name != "st06-runtime-fft-probe" or "build" not in build_dir.parts:
            raise ValueError(f"Güvenli olmayan temizleme hedefi: {build_dir}")
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [executable, "-mode", "batch", "-source", str(ROOT / "scripts/probe_st06_runtime_fft.tcl"),
         "-tclargs", str(build_dir)],
        cwd=ROOT,
        check=True,
    )


def _properties(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    section = ""
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line == "PORT_WIDTHS":
            section = "ports"
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key if section != "ports" else key] = value
    return result


def _resource(report: str, label: str) -> float:
    pattern = rf"^\|\s*{re.escape(label)}\*?\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|"
    match = re.search(pattern, report, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"Kaynak satırı bulunamadı: {label}")
    return float(match.group(1))


def _resources(path: Path) -> dict[str, int | float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    raw = {
        "slice_luts": _resource(text, "Slice LUTs"),
        "slice_registers": _resource(text, "Slice Registers"),
        "bram_tiles": _resource(text, "Block RAM Tile"),
        "dsps": _resource(text, "DSPs"),
    }
    return {key: int(value) if value.is_integer() else value for key, value in raw.items()}


def evaluate(build_dir: Path) -> dict[str, Any]:
    fixed_properties_path = build_dir / "properties-fixed4096.txt"
    runtime_properties_path = build_dir / "properties-runtime16384.txt"
    fixed_report_path = build_dir / "utilization-fixed4096.rpt"
    runtime_report_path = build_dir / "utilization-runtime16384.rpt"
    required = (fixed_properties_path, runtime_properties_path, fixed_report_path, runtime_report_path)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Eksik Vivado çıktıları: {missing}")

    properties = {
        "fixed4096": _properties(fixed_properties_path),
        "runtime16384": _properties(runtime_properties_path),
    }
    property_checks = {
        profile: {
            key: observed.get(key) == expected
            for key, expected in REQUIRED_PROPERTIES[profile].items()
        }
        for profile, observed in properties.items()
    }
    fixed = _resources(fixed_report_path)
    runtime = _resources(runtime_report_path)
    delta = {key: runtime[key] - fixed[key] for key in fixed}
    estimated_full = {key: CURRENT_FULL[key] + delta[key] for key in fixed}
    estimated_percent = {
        key: round(100.0 * estimated_full[key] / PART_CAPACITY[key], 3)
        for key in fixed
    }
    capacity_checks = {
        key: estimated_full[key] <= PART_CAPACITY[key]
        for key in fixed
    }
    synth_checks = {
        profile: observed.get("STATUS", "").startswith("synth_design Complete!")
        for profile, observed in properties.items()
    }
    passed = all(synth_checks.values()) and all(capacity_checks.values()) and all(
        all(checks.values()) for checks in property_checks.values()
    )

    source_paths = (
        ROOT / "scripts/probe_st06_runtime_fft.tcl",
        ROOT / "scripts/phase06d_ip_config.tcl",
        ROOT / "scripts/verify_st06_runtime_fft_feasibility.py",
    )
    return {
        "schema": "phase08-st06-runtime-fft-feasibility-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "scope": "Vivado out-of-context FFT IP synthesis and conservative full-design resource estimate",
        "device": properties["runtime16384"].get("PART"),
        "vivado": properties["runtime16384"].get("VIVADO"),
        "profiles": {
            "fixed4096": {
                "properties": {key: properties["fixed4096"].get(key) for key in REQUIRED_PROPERTIES["fixed4096"]},
                "resources": fixed,
            },
            "runtime16384": {
                "supported_lengths": [4096, 8192, 16384],
                "config_nfft_values": {"4096": 12, "8192": 13, "16384": 14},
                "config_layout": "NFFT in s_axis_config_tdata[3:0], forward/inverse bit in bit 8",
                "properties": {key: properties["runtime16384"].get(key) for key in REQUIRED_PROPERTIES["runtime16384"]},
                "resources": runtime,
            },
        },
        "resource_delta": delta,
        "current_routed_full_design": CURRENT_FULL,
        "estimated_full_design_after_ip_replacement": estimated_full,
        "estimated_full_design_utilization_percent": estimated_percent,
        "checks": {
            "ooc_synthesis": synth_checks,
            "properties": property_checks,
            "estimated_capacity": capacity_checks,
        },
        "conclusions": {
            "fft_ip_runtime_length_feasible": passed,
            "full_design_synthesized": False,
            "full_design_routed": False,
            "timing_closed": False,
            "rtl_integrated": False,
            "dma_arm_protocol_integrated": False,
            "hardware_verified": False,
            "ui_may_claim_fpga_runtime_fft": False,
        },
        "required_integration_surfaces": [
            "Hann window coefficient memory and runtime frame boundary",
            "FFT adapter configuration handshake and 14-bit bin index",
            "power/OS-CFAR memories, counters, and runtime frame length",
            "DMA input/output capacities and versioned frame metadata",
            "ARM decoder, candidate pipeline, and network protocol arrays",
            "PC request/response framing and verified UI readback",
            "full Vivado implementation, RTL/reference equivalence, and physical board tests",
        ],
        "source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path) for path in source_paths},
        "artifact_sha256": {str(path.relative_to(build_dir)).replace("\\", "/"): _sha256(path) for path in required},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--vivado")
    parser.add_argument("--run-vivado", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    build_dir = args.build_dir.resolve()
    if args.run_vivado:
        _run_probe(build_dir, args.vivado)
    observed = evaluate(build_dir)
    if args.check:
        expected = json.loads(args.output.read_text(encoding="utf-8"))
        for volatile in ("generated_at", "artifact_sha256"):
            expected.pop(volatile, None)
            observed.pop(volatile, None)
        if observed != expected:
            print("Runtime FFT feasibility evidence does not match", file=sys.stderr)
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(observed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(observed, indent=2, ensure_ascii=False))
    return 0 if observed["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
