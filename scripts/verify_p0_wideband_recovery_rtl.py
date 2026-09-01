#!/usr/bin/env python3
"""Verify the P0 regional-median and wideband-recovery RTL chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-wideband-rtl-v2.json"
SOURCES = (
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_region_bank.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    ROOT / "algorithms/fpga/p0/tb/tb_p0_wideband_recovery.sv",
)
VECTOR_MANIFEST = ROOT / "datasets/fixtures/p0_wideband_recovery/fixture-manifest.json"
PASS_PATTERN = re.compile(
    r"P0_WIDEBAND_RECOVERY_PASS frames=(?P<frames>\d+) records=(?P<records>\d+) "
    r"semantic=(?P<semantic>\d+) max_processing_cycles=(?P<cycles>\d+) "
    r"stability_checks=(?P<stability>\d+)"
)
MAX_PROCESSING_CYCLES = 50000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    fallback = Path(r"C:\msys64\ucrt64\bin") / f"{name}.exe"
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError(f"{name} bulunamadı")


def evaluate() -> dict[str, object]:
    iverilog = _tool("iverilog")
    vvp = _tool("vvp")
    with tempfile.TemporaryDirectory(prefix="p0-wideband-recovery-") as raw:
        executable = Path(raw) / "p0_wideband_recovery.vvp"
        compile_result = subprocess.run(
            [
                iverilog,
                "-g2012",
                "-Wall",
                "-s",
                "tb_p0_wideband_recovery",
                "-o",
                str(executable),
                *(str(path) for path in SOURCES),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        simulation = subprocess.run(
            [vvp, str(executable)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = simulation.stdout + simulation.stderr
        match = PASS_PATTERN.search(output)
        if simulation.returncode != 0 or match is None:
            raise RuntimeError(output)

    frames = int(match.group("frames"))
    records = int(match.group("records"))
    semantic = int(match.group("semantic"))
    cycles = int(match.group("cycles"))
    stability = int(match.group("stability"))
    passed = (
        frames == 8
        and records == 27
        and semantic == 24
        and cycles <= MAX_PROCESSING_CYCLES
        and stability > 0
    )
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "P0 parallel regional-median and wideband-recovery RTL simulation",
        "simulator": "Icarus Verilog SystemVerilog 2012",
        "vectors": {
            "frames": frames,
            "axis_records": records,
            "semantic_candidates": semantic,
            "candidate_metadata_mismatches": 0,
            "empty_frame_sentinel_checked": True,
            "out_of_range_frame_failed_closed": True,
            "malformed_frame_sticky_error": True,
            "candidate_overflow_sticky": False,
            "stalled_payload_stability_checks": stability,
            "fixture_manifest_sha256": _sha256(VECTOR_MANIFEST),
        },
        "latency": {
            "maximum_last_input_to_last_output_cycles": cycles,
            "acceptance_limit_cycles": MAX_PROCESSING_CYCLES,
            "clock_hz_for_capacity_only": 50_000_000,
            "maximum_processing_milliseconds_at_50mhz": cycles / 50_000.0,
        },
        "architecture": {
            "regional_median": "16 parallel exact radix rank-127/128 engines",
            "integration_bins": 32,
            "integrated_threshold_coefficient": "Q48",
            "minimum_recovery_span_bins": 41,
            "maximum_gap_bins": 1,
            "peak_tie_policy": "first maximum in shifted order",
            "candidate_capacity": 96,
            "broad_reference_region_rank": 4,
            "broad_minimum_recovery_span_bins": 257,
            "broad_flank_policy": "one complete region beyond each support edge",
        },
        "source_sha256": {path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCES},
        "claim_boundary": (
            "Icarus bit-true simulation of the median plus wideband-recovery chain only; "
            "OS-candidate fusion, PHASE-06I integration, synthesis, timing closure, board "
            "execution and real-time acceptance remain open."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("P0 geniş bant kurtarma RTL kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
