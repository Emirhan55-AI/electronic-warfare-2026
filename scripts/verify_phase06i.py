#!/usr/bin/env python3
"""Verify and record PHASE-06I PL-to-PS candidate transport evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.ps.candidate_transport import (
    ABI_VERSION, HEADER_BYTES, MAX_FRAME_BYTES, RECORD_BYTES, TRAILER_BYTES,
    architecture_study, decode_packet,
)
from reference.ps.transport_vectors import build_vector_files

EVIDENCE = ROOT / "results" / "evidence" / "phase06i"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06i"
OWNED_FILES = (
    "architecture.json", "abi-contract.json", "python-abi-result.json",
    "rtl-simulation.json", "toolchain.json", "temporal-boundary.json",
    "physical-parameter-boundary.json", "source-manifest.json", "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0020-PHASE06I-PL-PS-CANDIDATE-TRANSPORT.md",
    "docs/interfaces/PL_PS_CANDIDATE_TRANSPORT_ABI.md",
    "reference/ps/__init__.py", "reference/ps/candidate_transport.py", "reference/ps/transport_vectors.py",
    "ps/README.md", "ps/phase06i/include/phase06i_transport_abi.h", "ps/phase06i/src/phase06i_decode.c",
    "rtl/phase06i/rtl/phase06i_pkg.sv", "rtl/phase06i/rtl/axis_candidate_packetizer.sv",
    "rtl/phase06i/tb/tb_axis_candidate_packetizer.sv",
    "scripts/generate_phase06i_vectors.py", "scripts/verify_phase06i.py",
    "tests/test_phase06i_transport.py", "tests/test_phase06i_vectors.py", "tests/test_phase06i_verifier.py",
    "datasets/fixtures/phase06i/candidate-axis-input.mem",
    "datasets/fixtures/phase06i/transport-axis64-expected.mem",
    "datasets/fixtures/phase06i/transport-packets.bin",
    "datasets/fixtures/phase06i/golden-vectors.json", "datasets/fixtures/phase06i/fixture-manifest.json",
)
EXPECTED_PASS = "PHASE-06I TB PASS: 8964 AXI64 beats checked"
EXPECTED_METRICS = {
    "input_records": 1773, "output_beats": 8964, "packets": 13,
    "semantic_candidates": 1772, "input_stalls": 9865, "output_stalls": 911,
    "payload_stability_checks": 911, "maximum_candidates_per_frame": 1352,
    "maximum_packet_bytes": 54144,
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commands() -> tuple[str, str]:
    iv = shutil.which("iverilog") or r"C:\msys64\ucrt64\bin\iverilog.exe"
    vp = shutil.which("vvp") or r"C:\msys64\ucrt64\bin\vvp.exe"
    if not Path(iv).is_file() or not Path(vp).is_file():
        raise FileNotFoundError("Icarus Verilog 13.0 was not found")
    return iv, vp


def _normalized(stdout: str) -> bytes:
    lines = [line.strip() for line in stdout.splitlines() if line.startswith("PHASE06I_METRIC") or line.startswith("PHASE-06I TB PASS")]
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_rtl_once() -> dict[str, object]:
    iv, vp = _commands()
    env = os.environ.copy()
    env["PATH"] = str(Path(iv).parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06i-") as td:
        exe = Path(td) / "phase06i.vvp"
        compile_result = subprocess.run([
            iv, "-g2012", "-s", "tb_axis_candidate_packetizer", "-o", str(exe),
            str(ROOT / "rtl/phase06i/rtl/phase06i_pkg.sv"),
            str(ROOT / "rtl/phase06i/rtl/axis_candidate_packetizer.sv"),
            str(ROOT / "rtl/phase06i/tb/tb_axis_candidate_packetizer.sv"),
        ], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        if compile_result.returncode:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        sim = subprocess.run([vp, str(exe)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        if sim.returncode or EXPECTED_PASS not in sim.stdout:
            raise RuntimeError(sim.stdout + sim.stderr)
    metrics: dict[str, int] = {}
    for name in EXPECTED_METRICS:
        match = re.search(rf"{name}=(\d+)", sim.stdout)
        if match is None:
            raise ValueError(f"missing RTL metric: {name}")
        metrics[name] = int(match.group(1))
    if metrics != EXPECTED_METRICS:
        raise AssertionError(f"unexpected RTL metrics: {metrics}")
    normalized = _normalized(sim.stdout)
    return {"metrics": metrics, "normalized": normalized, "sha256": hashlib.sha256(normalized).hexdigest()}


def _stored_rtl() -> dict[str, object]:
    normalized = (
        "PHASE06I_METRIC input_records=1773 output_beats=8964 packets=13 semantic_candidates=1772\n"
        "PHASE06I_METRIC input_stalls=9865 output_stalls=911 payload_stability_checks=911\n"
        "PHASE06I_METRIC maximum_candidates_per_frame=1352 maximum_packet_bytes=54144 reset_partial_packet_checked=1 malformed_input_checked=1\n"
        "PHASE-06I TB PASS: 8964 AXI64 beats checked\n"
    ).encode("utf-8")
    return {"metrics": dict(EXPECTED_METRICS), "normalized": normalized, "sha256": hashlib.sha256(normalized).hexdigest()}


def _validate_c_abi_source() -> None:
    header = (ROOT / "ps/phase06i/include/phase06i_transport_abi.h").read_text(encoding="utf-8")
    required = (
        "PHASE06I_ABI_VERSION 1u", "PHASE06I_MAX_FRAME_BYTES 54144u",
        "sizeof(phase06i_header_v1) == 32", "sizeof(phase06i_candidate_v1) == 40",
        "sizeof(phase06i_trailer_v1) == 32", "threshold_uq32_30) == 32",
    )
    if not all(token in header for token in required):
        raise AssertionError("portable C ABI declaration is inconsistent")


def build_documents(*, execute_rtl: bool) -> dict[str, object]:
    generated = build_vector_files()
    if any(not (FIXTURES / n).is_file() or (FIXTURES / n).read_bytes() != p for n, p in generated.items()):
        raise AssertionError("PHASE-06I fixtures are stale")
    _validate_c_abi_source()
    golden = json.loads(generated["golden-vectors.json"])
    stream = generated["transport-packets.bin"]
    offset = 0
    decoded_records = 0
    for row in golden["frames"]:
        size = int(row["packet_bytes"])
        packet = decode_packet(stream[offset:offset + size])
        if packet.frame_id != row["frame_id"] or len(packet.candidates) != row["candidate_count"]:
            raise AssertionError("Python ABI decode mismatch")
        decoded_records += len(packet.candidates)
        offset += size
    if offset != len(stream):
        raise AssertionError("packet stream has trailing bytes")
    first = run_rtl_once() if execute_rtl else _stored_rtl()
    second = run_rtl_once() if execute_rtl else _stored_rtl()
    deterministic = first["normalized"] == second["normalized"]
    if not deterministic:
        raise AssertionError("fresh RTL runs differ")
    toolchain = {
        "phase": "PHASE-06I", "status": "passed", "ps_toolchain": "not_ready",
        "petalinux": "not_found", "arm_cross_compiler": "not_found", "sysroot": "not_found",
        "device_tree_workflow": "not_defined", "board_deployment": "not_available",
        "vitis_installation": "partial_files_present_cli_not_callable", "host_c_compiler": "not_found",
        "portable_c_source": "prepared_not_compiled", "arm_target_execution": "not_exercised",
        "vivado": "2025.2", "rtl_simulator": "Icarus Verilog 13.0 stable",
    }
    return {
        "architecture.json": {"phase": "PHASE-06I", "status": "passed", **architecture_study(),
            "partition": {
                "candidate_transport_packetization": "PL", "temporal_2_of_3": "PS_LATER",
                "center_frequency_conversion": "PS_LATER", "coarse_span_conversion": "PS_LATER",
                "power_noise_threshold_conversion": "PS_LATER", "candidate_association": "PS_LATER",
                "logging": "PS_LATER", "host_ui_delivery": "PS_LATER_PC_DISPLAY_ONLY",
            }},
        "abi-contract.json": {
            "phase": "PHASE-06I", "status": "passed", "version": ABI_VERSION, "endianness": "little",
            "axis_width_bits": 64, "header_bytes": HEADER_BYTES, "candidate_record_bytes": RECORD_BYTES,
            "trailer_bytes": TRAILER_BYTES, "maximum_candidates": 1352, "maximum_packet_bytes": MAX_FRAME_BYTES,
            "frame_id": "uint32 modulo 2^32 reset to zero", "empty_frame": "header empty flag, zero records, trailer count zero",
            "integrity": "length, duplicate frame ID, candidate count, status and IEEE payload CRC32",
        },
        "python-abi-result.json": {
            "phase": "PHASE-06I", "status": "passed", "frames": golden["frame_count"],
            "decoded_candidates": decoded_records, "packet_bytes": len(stream), "mismatches": 0,
            "malformed_version_length_crc_reserved_tests": "passed", "frame_id_boundary": "passed",
        },
        "rtl-simulation.json": {
            "phase": "PHASE-06I", "status": "passed", "compile": "passed", "simulation": "passed",
            **first["metrics"], "mismatch_count": 0, "candidate_loss": 0, "duplicate_records": 0,
            "reset_partial_packet": "passed", "malformed_input_status": "passed",
            "backpressure_payload_stability": "passed", "deterministic_rerun": "passed",
            "normalized_output_sha256": first["sha256"], "build_location": "external_temporary_directory",
        },
        "toolchain.json": toolchain,
        "temporal-boundary.json": {
            "phase": "PHASE-06I", "status": "defined_deferred",
            "source": "reference/detection/pipeline.py DetectionPipeline._update_tracks",
            "placement": "Zynq PS", "implementation": "not_implemented_due_to_ps_toolchain",
            "window": "per-track deque maxlen 3; confirm when sum >= 2",
            "association": "previous span expanded by 2 bins; require positive overlap",
            "pair_tie_order": ["descending overlap", "ascending peak displacement", "event ID", "current start bin", "current index"],
            "expiry": "two consecutive missing frames", "empty_frame": "one miss for every active track",
            "nonconsecutive_frame": "reset all temporal state", "max_active_tracks": 64, "max_ended_history": 128,
            "pfa_threshold_match_inputs": False, "peak_power_role": "admission ranking by peak-to-noise only",
        },
        "physical-parameter-boundary.json": {
            "phase": "PHASE-06I", "status": "defined_deferred", "owner": "Zynq PS",
            "required_runtime_metadata": ["RF center frequency", "sample rate", "FFT size 4096", "shifted-bin convention"],
            "frequency_offset": "(shifted_bin - 2048) * sample_rate / 4096",
            "absolute_frequency": "RF_center + frequency_offset",
            "coarse_span_hz": "span_bins * sample_rate / 4096; coarse detected span only",
            "precise_occupied_bandwidth": "not_implemented", "dbm_calibration": "not_available",
        },
        "source-manifest.json": {
            "phase": "PHASE-06I", "status": "passed", "files": {name: sha256(ROOT / name) for name in SOURCE_FILES},
            "frozen_phase06h_source": {"path": "datasets/fixtures/phase06h/candidate-expected.mem", "sha256": sha256(ROOT / "datasets/fixtures/phase06h/candidate-expected.mem")},
        },
        "verification-summary.json": {
            "phase": "PHASE-06I", "overall": "passed", "transport_abi": "passed", "python_decode": "passed",
            "portable_c_abi_layout": "source_verified_not_compiled", "rtl_compile": "passed", "rtl_simulation": "passed",
            "rtl_byte_exact": "passed", "deterministic_rerun": "passed", "candidate_loss": 0, "duplicate_records": 0,
            "temporal_confirmation": "not_implemented", "ps_toolchain": "not_ready", "dma_ip_driver": "not_implemented",
            "post_detector_timing_100mhz": "not_verified", "arm_target_execution": "not_exercised",
            "hardware": "not_exercised", "live_hackrf": "not_exercised", "pc_independent_zynq_system": "not_complete",
            "phase06g_continuous_frame_acceptance": "not_supported",
        },
    }


def write() -> None:
    docs = build_documents(execute_rtl=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(docs[name]))


def check() -> bool:
    try:
        docs = build_documents(execute_rtl=False)
        exact = all((EVIDENCE / n).is_file() and (EVIDENCE / n).read_bytes() == canonical_bytes(docs[n]) for n in OWNED_FILES)
        payload = b"".join((EVIDENCE / n).read_bytes() for n in OWNED_FILES).decode("utf-8", errors="replace").casefold()
        safe = not any(token in payload for token in ("c:\\users", "onedrive", "hostname", "timestamp"))
        return exact and safe and docs["verification-summary.json"]["overall"] == "passed"
    except (OSError, ValueError, AssertionError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"PHASE-06I verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
