#!/usr/bin/env python3
"""Verify the P0 final reducer to PHASE-06I AXI64 packetizer integration."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-reducer-packetizer.json"
FIXTURE_ROOT = ROOT / "datasets/fixtures/p0_candidate_reducer_packetizer"

SOURCES = (
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
    ROOT / "algorithms/fpga/phase06i/rtl/phase06i_pkg.sv",
    ROOT / "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_packetizer_top.sv",
    ROOT / "algorithms/fpga/p0/tb/tb_p0_candidate_reducer_packetizer.sv",
)
FIXTURE_FILES = (
    FIXTURE_ROOT / "transport-axis64-expected.mem",
    FIXTURE_ROOT / "golden-vectors.json",
    FIXTURE_ROOT / "fixture-manifest.json",
)
PASS_PATTERN = re.compile(
    r"P0_PACKETIZER_PASS frames=(?P<frames>\d+) candidates=(?P<candidates>\d+) "
    r"beats=(?P<beats>\d+) output_stalls=(?P<stalls>\d+) "
    r"stability_checks=(?P<stability>\d+)"
)


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


def _fixtures_are_current() -> bool:
    from generate_p0_candidate_reducer_packetizer_vectors import build_vector_files

    generated = build_vector_files()
    return all(
        (FIXTURE_ROOT / name).is_file()
        and (FIXTURE_ROOT / name).read_bytes() == payload
        for name, payload in generated.items()
    )


def _simulate() -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="p0-packetizer-") as raw:
        executable = Path(raw) / "p0_packetizer.vvp"
        compile_result = subprocess.run(
            [
                _tool("iverilog"),
                "-g2012",
                "-Wall",
                "-s",
                "tb_p0_candidate_reducer_packetizer",
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
            [_tool("vvp"), str(executable)],
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
    return {name: int(value) for name, value in match.groupdict().items()}


def evaluate() -> dict[str, object]:
    if not _fixtures_are_current():
        raise RuntimeError("P0 reducer packetizer fixture'ları güncel değil")
    metrics = _simulate()
    expected = {"frames": 5, "candidates": 61, "beats": 345, "stalls": 30, "stability": 30}
    passed = metrics == expected
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "P0 final candidate reducer to PHASE-06I AXI64 packetizer integration",
        "simulator": "Icarus Verilog SystemVerilog 2012",
        "metrics": metrics,
        "fixture_manifest_sha256": _sha256(FIXTURE_ROOT / "fixture-manifest.json"),
        "architecture": {
            "reducer": "p0_candidate_reducer_top",
            "packetizer": "axis_candidate_packetizer",
            "axi_data_width_bits": 64,
            "packet_frame_count": 5,
            "semantic_candidates": 61,
            "candidate_loss": 0,
            "duplicate_records": 0,
            "backpressure_payload_stability": "passed",
            "empty_frame_and_frame_id_sequence": "passed",
        },
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCES
        },
        "claim_boundary": (
            "The final reducer is connected to the frozen PHASE-06I AXI64 packetizer and "
            "verified in RTL simulation. DMA IP, PS driver, two-buffer ownership, pin-assigned "
            "board top, bitstream and physical execution remain outside this gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("P0 reducer-packetizer kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
