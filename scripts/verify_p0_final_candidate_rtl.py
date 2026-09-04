#!/usr/bin/env python3
"""Verify sparse OS candidates and the complete P0 candidate-reducer RTL."""

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
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-final-rtl-v2.json"
COMMON_SOURCES = (
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_weak_candidate_grouping.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_weak_nomination_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_region_bank.sv",
)
FINAL_SOURCES = (
    *COMMON_SOURCES,
    ROOT / "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
)
SPARSE_TB = ROOT / "algorithms/fpga/p0/tb/tb_p0_sparse_os_candidate.sv"
FINAL_TB = ROOT / "algorithms/fpga/p0/tb/tb_p0_candidate_reducer.sv"
GUARD_TB = ROOT / "algorithms/fpga/p0/tb/tb_p0_candidate_guards.sv"
SPARSE_MANIFEST = ROOT / "datasets/fixtures/p0_sparse_os_candidate/fixture-manifest.json"
FINAL_MANIFEST = ROOT / "datasets/fixtures/p0_final_candidate/fixture-manifest.json"
SPARSE_PATTERN = re.compile(
    r"P0_SPARSE_OS_CANDIDATE_PASS frames=(?P<frames>\d+) records=(?P<records>\d+) "
    r"semantic=(?P<semantic>\d+) max_processing_cycles=(?P<cycles>\d+) "
    r"stability_checks=(?P<stability>\d+)"
)
FINAL_PATTERN = re.compile(
    r"P0_FINAL_CANDIDATE_PASS frames=(?P<frames>\d+) records=(?P<records>\d+) "
    r"semantic=(?P<semantic>\d+) max_processing_cycles=(?P<cycles>\d+) "
    r"stability_checks=(?P<stability>\d+)"
)
GUARD_PATTERN = re.compile(
    r"P0_CANDIDATE_GUARDS_PASS os_records=(?P<os_records>\d+) "
    r"fusion_overflow=(?P<fusion_overflow>\d+)"
)
MAX_PROCESSING_CYCLES = 50000
FRAME_LENGTH = 4096
CLOCK_HZ = 50_000_000


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


def _simulate(top: str, sources: tuple[Path, ...], pattern: re.Pattern[str]) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix=f"{top}-") as raw:
        executable = Path(raw) / f"{top}.vvp"
        compile_result = subprocess.run(
            [
                _tool("iverilog"),
                "-g2012",
                "-Wall",
                "-s",
                top,
                "-o",
                str(executable),
                *(str(path) for path in sources),
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
            [_tool("vvp"), str(executable)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = simulation.stdout + simulation.stderr
        match = pattern.search(output)
        if simulation.returncode != 0 or match is None:
            raise RuntimeError(output)
    return {name: int(value) for name, value in match.groupdict().items()}


def evaluate() -> dict[str, object]:
    sparse = _simulate(
        "tb_p0_sparse_os_candidate", (*COMMON_SOURCES, SPARSE_TB), SPARSE_PATTERN
    )
    final = _simulate("tb_p0_candidate_reducer", (*FINAL_SOURCES, FINAL_TB), FINAL_PATTERN)
    guards = _simulate(
        "tb_p0_candidate_guards",
        (
            ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
            ROOT / "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
            GUARD_TB,
        ),
        GUARD_PATTERN,
    )
    total_functional_cycles = FRAME_LENGTH + final["cycles"]
    passed = (
        sparse == {
            "frames": 8,
            "records": 157,
            "semantic": 151,
            "cycles": 42873,
            "stability": sparse["stability"],
        }
        and sparse["stability"] > 0
        and final == {
            "frames": 8,
            "records": 115,
            "semantic": 113,
            "cycles": 46339,
            "stability": final["stability"],
        }
        and final["stability"] > 0
        and guards == {"os_records": 1352, "fusion_overflow": 1}
        and final["cycles"] <= MAX_PROCESSING_CYCLES
        and total_functional_cycles < 102400
    )
    source_paths = (*FINAL_SOURCES, SPARSE_TB, FINAL_TB, GUARD_TB)
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "P0 sparse OS-CFAR candidate and final multiscale candidate-reducer RTL simulation",
        "simulator": "Icarus Verilog SystemVerilog 2012",
        "sparse_os_candidates": {
            "frames": sparse["frames"],
            "axis_records": sparse["records"],
            "semantic_candidates": sparse["semantic"],
            "candidate_metadata_mismatches": 0,
            "maximum_last_input_to_last_output_cycles": sparse["cycles"],
            "stalled_payload_stability_checks": sparse["stability"],
            "fixture_manifest_sha256": _sha256(SPARSE_MANIFEST),
        },
        "final_candidates": {
            "frames": final["frames"],
            "axis_records": final["records"],
            "semantic_candidates": final["semantic"],
            "candidate_metadata_mismatches": 0,
            "wideband_overlap_suppression_checked": True,
            "empty_frame_sentinel_checked": True,
            "out_of_range_frame_failed_closed": True,
            "malformed_frame_sticky_errors": True,
            "maximum_last_input_to_last_output_cycles": final["cycles"],
            "stalled_payload_stability_checks": final["stability"],
            "fixture_manifest_sha256": _sha256(FINAL_MANIFEST),
        },
        "capacity": {
            "clock_hz_for_capacity_only": CLOCK_HZ,
            "input_cycles_at_one_sample_per_cycle": FRAME_LENGTH,
            "maximum_sequential_functional_cycles": total_functional_cycles,
            "cycle_budget": 102400,
            "functional_frames_per_second": CLOCK_HZ / total_functional_cycles,
            "required_frames_per_second": 488.28125,
        },
        "guards": {
            "maximum_os_candidate_records": guards["os_records"],
            "maximum_os_capacity_passed_without_overflow": True,
            "fusion_overflow_failed_closed": bool(guards["fusion_overflow"]),
        },
        "architecture": {
            "os_detector": (
                "rank-24/32 strict and 6 dB weak Q32 decisions with classified sparse grouping"
            ),
            "wideband_detector": "regional recovery plus flanked fourth-region-order broad recovery",
            "fusion": "sorted merge; every OS candidate overlapping a recovery is suppressed",
            "output": "shifted-order candidate AXI stream with explicit empty sentinel",
        },
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in source_paths
        },
        "claim_boundary": (
            "Bit-true RTL simulation and functional cycle capacity only; PHASE-06I packetizer "
            "integration, synthesis, place-and-route, timing closure, DMA/driver integration, "
            "board execution and physical real-time acceptance remain open."
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
        print("P0 final aday RTL kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
