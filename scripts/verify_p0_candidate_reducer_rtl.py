#!/usr/bin/env python3
"""Verify the parallel regional-median RTL used by the P0 candidate reducer."""

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
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-median-rtl.json"
SOURCES = (
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    ROOT / "algorithms/fpga/p0/tb/tb_p0_parallel_region_median.sv",
)
VECTOR_MANIFEST = ROOT / "datasets/fixtures/p0_candidate_reducer/fixture-manifest.json"
PASS_PATTERN = re.compile(
    r"P0_PARALLEL_MEDIAN_PASS frames=(?P<frames>\d+) max_processing_cycles=(?P<cycles>\d+)"
)
MAX_PROCESSING_CYCLES = 30000


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
    with tempfile.TemporaryDirectory(prefix="p0-candidate-reducer-") as raw:
        executable = Path(raw) / "p0_parallel_median.vvp"
        compile_result = subprocess.run(
            [
                iverilog,
                "-g2012",
                "-Wall",
                "-s",
                "tb_p0_parallel_region_median",
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
    cycles = int(match.group("cycles"))
    passed = frames == 5 and cycles <= MAX_PROCESSING_CYCLES
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "P0 parallel regional-median RTL simulation",
        "simulator": "Icarus Verilog SystemVerilog 2012",
        "vectors": {
            "frames": frames,
            "regions_per_frame": 16,
            "median_mismatches": 0,
            "malformed_frame_sticky_error": True,
            "fixture_manifest_sha256": _sha256(VECTOR_MANIFEST),
        },
        "latency": {
            "maximum_processing_cycles": cycles,
            "acceptance_limit_cycles": MAX_PROCESSING_CYCLES,
            "clock_hz_for_capacity_only": 50_000_000,
            "maximum_processing_milliseconds_at_50mhz": cycles / 50_000.0,
        },
        "architecture": {
            "region_banks": 16,
            "bins_per_region": 256,
            "parallel_regions": 16,
            "radix_passes": 58,
            "selected_ranks_zero_based": [127, 128],
        },
        "source_sha256": {path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCES},
        "claim_boundary": (
            "Icarus bit-true simulation of the regional-median substage only; integrated-energy "
            "grouping, final candidate fusion, synthesis, timing closure, board execution and "
            "real-time acceptance remain open."
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
        print("P0 paralel median RTL kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
