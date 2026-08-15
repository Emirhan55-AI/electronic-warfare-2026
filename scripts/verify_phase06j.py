#!/usr/bin/env python3
"""Build and verify the portable PHASE-06J PS temporal core."""

from __future__ import annotations

import argparse
import ctypes
import functools
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.ps.candidate_transport import decode_packet, encode_packet
from reference.ps.temporal_vectors import build_all_files, canonical_bytes


FIXTURES = ROOT / "datasets" / "fixtures" / "phase06j"
EVIDENCE = ROOT / "results" / "evidence" / "phase06j"
OWNED_FILES = (
    "algorithm-contract.json", "host-build.json", "golden-equivalence.json",
    "toolchain.json", "physical-boundary.json", "system-limitations.json",
    "source-manifest.json", "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0021-PHASE06J-PS-TEMPORAL-CONFIRMATION.md",
    "docs/interfaces/PS_TEMPORAL_CANDIDATE_CONTRACT.md",
    "ps/phase06j/include/phase06j_temporal.h",
    "ps/phase06j/src/phase06j_temporal.c",
    "reference/ps/temporal_confirmation.py",
    "reference/ps/temporal_vectors.py",
    "scripts/generate_phase06j_vectors.py",
    "scripts/verify_phase06j.py",
    "tests/test_phase06j_model.py",
    "tests/test_phase06j_vectors.py",
    "tests/test_phase06j_verifier.py",
    "datasets/fixtures/phase06j/fixture-manifest.json",
    "datasets/fixtures/phase06j/golden-sequences.json",
    "datasets/fixtures/phase06j/packets.bin",
)


class Candidate(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("start", ctypes.c_uint16), ("end", ctypes.c_uint16), ("peak", ctypes.c_uint16),
        ("span", ctypes.c_uint16), ("pfa", ctypes.c_uint8), ("flags", ctypes.c_uint8),
        ("reserved0", ctypes.c_uint16), ("reserved1", ctypes.c_uint32),
        ("power", ctypes.c_uint64), ("noise", ctypes.c_uint64), ("threshold", ctypes.c_uint64),
    ]


class Event(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("event_id", ctypes.c_uint64), ("first_frame", ctypes.c_uint32),
        ("last_seen", ctypes.c_uint32), ("seen_count", ctypes.c_uint64),
        ("state", ctypes.c_uint8), ("observed", ctypes.c_uint8),
        ("reserved", ctypes.c_uint16), ("candidate", Candidate),
    ]


class FrameResult(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("frame_id", ctypes.c_uint32), ("active_count", ctypes.c_uint16),
        ("ended_count", ctypes.c_uint16), ("dropped", ctypes.c_uint16),
        ("reset_applied", ctypes.c_uint8), ("reserved", ctypes.c_uint8),
        ("evicted", ctypes.c_uint64), ("active", Event * 64), ("ended", Event * 64),
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _msvc() -> tuple[Path, Path] | None:
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not vswhere.is_file():
        return None
    query = subprocess.run(
        [str(vswhere), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if query.returncode or not query.stdout.strip():
        return None
    root = Path(query.stdout.strip())
    vcvars = root / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    compilers = sorted((root / "VC" / "Tools" / "MSVC").glob("*/bin/Hostx64/x64/cl.exe"), reverse=True)
    return (vcvars, compilers[0]) if vcvars.is_file() and compilers else None


def _compile_library(directory: Path) -> tuple[Path, str]:
    source = ROOT / "ps" / "phase06j" / "src" / "phase06j_temporal.c"
    include_j = ROOT / "ps" / "phase06j" / "include"
    include_i = ROOT / "ps" / "phase06i" / "include"
    if os.name == "nt":
        found = _msvc()
        if found is None:
            raise FileNotFoundError("MSVC C11 host compiler is unavailable")
        vcvars, _ = found
        output = directory / "phase06j_temporal.dll"
        object_file = directory / "phase06j_temporal.obj"
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX /LD '
            f'"{source}" /I"{include_j}" /I"{include_i}" /Fo"{object_file}" '
            f'/link /OUT:"{output}"'
        )
        build = subprocess.run(
            command, cwd=directory, shell=True,
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        family = "MSVC C11"
    else:
        compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if compiler is None:
            raise FileNotFoundError("C11 host compiler is unavailable")
        output = directory / "libphase06j_temporal.so"
        build = subprocess.run(
            [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared",
             str(source), f"-I{include_j}", f"-I{include_i}", "-o", str(output)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        family = "portable C11"
    if build.returncode or not output.is_file():
        raise RuntimeError(f"host C build failed ({build.returncode}):\n{build.stdout}\n{build.stderr}")
    return output, family


def _configure(library: ctypes.CDLL) -> None:
    library.phase06j_state_bytes.restype = ctypes.c_size_t
    library.phase06j_state_init.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    library.phase06j_state_init.restype = ctypes.c_int
    library.phase06j_state_reset.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    library.phase06j_state_reset.restype = ctypes.c_int
    library.phase06j_validate_packet.argtypes = [
        ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint16)
    ]
    library.phase06j_validate_packet.restype = ctypes.c_int
    library.phase06j_process_packet.argtypes = [
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(FrameResult)
    ]
    library.phase06j_process_packet.restype = ctypes.c_int


def _candidate(candidate: Candidate) -> dict[str, object]:
    return {
        "start_shifted_bin": candidate.start,
        "end_shifted_bin": candidate.end,
        "peak_shifted_bin": candidate.peak,
        "coarse_span_bins": candidate.span,
        "peak_power": candidate.power,
        "regional_noise": candidate.noise,
        "threshold": candidate.threshold,
        "pfa_select": candidate.pfa,
        "evaluate_center": bool(candidate.flags & 2),
    }


def _event(event: Event) -> dict[str, object]:
    states = {1: "tentative", 2: "confirmed", 3: "ended"}
    return {
        "event_id": event.event_id,
        "state": states[event.state],
        "first_frame_id": event.first_frame,
        "last_seen_frame_id": event.last_seen,
        "seen_count": event.seen_count,
        "observed_this_frame": bool(event.observed),
        "candidate": _candidate(event.candidate),
    }


def _result(result: FrameResult) -> dict[str, object]:
    return {
        "frame_id": result.frame_id,
        "active_events": [_event(result.active[index]) for index in range(result.active_count)],
        "ended_events": [_event(result.ended[index]) for index in range(result.ended_count)],
        "dropped_candidates": result.dropped,
        "evicted_history_count": result.evicted,
        "reset_applied": bool(result.reset_applied),
    }


def _buffer(data: bytes) -> ctypes.Array[ctypes.c_char]:
    return ctypes.create_string_buffer(data, len(data))


def _malformed_checks(library: ctypes.CDLL, good_packet: bytes) -> int:
    def validate(data: bytes) -> int:
        buffer = _buffer(data)
        return int(library.phase06j_validate_packet(buffer, len(data), None, None))

    checks = 0
    changed = bytearray(good_packet)
    changed[4] = 2
    assert validate(bytes(changed)) == -2
    checks += 1
    assert validate(good_packet[:-1]) in (-3, -4)
    checks += 1
    changed = bytearray(good_packet)
    changed[32] ^= 1
    assert validate(bytes(changed)) == -6
    checks += 1
    changed = bytearray(good_packet)
    changed[20] = 1
    assert validate(bytes(changed)) == -5
    checks += 1
    assert validate(encode_packet(0, (), status=1)) == -8
    checks += 1
    changed = bytearray(good_packet)
    changed[32 + 9] = 0
    payload = bytes(changed[32:-32])
    struct.pack_into("<I", changed, len(changed) - 8, zlib.crc32(payload))
    assert validate(bytes(changed)) == -7
    return checks + 1


@functools.lru_cache(maxsize=1)
def run_host_verification() -> dict[str, object]:
    golden = json.loads((FIXTURES / "golden-sequences.json").read_text(encoding="utf-8"))
    stream = (FIXTURES / "packets.bin").read_bytes()
    mismatch_count = 0
    decoded_records = 0
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06j-") as temporary:
        library_path, compiler = _compile_library(Path(temporary))
        library = ctypes.CDLL(str(library_path))
        _configure(library)
        state_bytes = int(library.phase06j_state_bytes())
        state = ctypes.create_string_buffer(state_bytes)
        if library.phase06j_state_init(state, state_bytes) != 0:
            raise AssertionError("C state initialization failed")
        first_record_packet: bytes | None = None
        for sequence in golden["sequences"]:
            if library.phase06j_state_reset(state, state_bytes) != 0:
                raise AssertionError("C state reset failed")
            for frame in sequence["frames"]:
                offset = int(frame["packet_offset"])
                length = int(frame["packet_bytes"])
                packet = stream[offset:offset + length]
                if len(packet) != length:
                    raise AssertionError("fixture packet bounds are invalid")
                if int(frame["candidate_count"]) and first_record_packet is None:
                    first_record_packet = packet
                packet_buffer = _buffer(packet)
                decoded_frame = ctypes.c_uint32()
                decoded_count = ctypes.c_uint16()
                code = library.phase06j_validate_packet(
                    packet_buffer, len(packet), ctypes.byref(decoded_frame), ctypes.byref(decoded_count)
                )
                if code != 0 or decoded_frame.value != frame["frame_id"] or decoded_count.value != frame["candidate_count"]:
                    raise AssertionError("C ABI decoder mismatch")
                output = FrameResult()
                code = library.phase06j_process_packet(
                    state, state_bytes, packet_buffer, len(packet), ctypes.byref(output)
                )
                if code != 0:
                    raise AssertionError(f"C temporal process failed: {code}")
                if _result(output) != frame["expected"]:
                    mismatch_count += 1
                decoded_records += decoded_count.value
        if first_record_packet is None:
            raise AssertionError("record-bearing fixture is missing")
        malformed_checks = _malformed_checks(library, first_record_packet)
        candidate = decode_packet(first_record_packet).candidates
        if library.phase06j_state_reset(state, state_bytes) != 0:
            raise AssertionError("C state reset failed before rejection-state check")
        first = encode_packet(0, candidate)
        first_buffer = _buffer(first)
        output = FrameResult()
        if library.phase06j_process_packet(state, state_bytes, first_buffer, len(first), ctypes.byref(output)) != 0:
            raise AssertionError("initial state-rejection packet failed")
        rejected = encode_packet(1, candidate, status=1)
        rejected_buffer = _buffer(rejected)
        if library.phase06j_process_packet(state, state_bytes, rejected_buffer, len(rejected), ctypes.byref(output)) != -8:
            raise AssertionError("status-marked packet was not rejected")
        second = encode_packet(1, candidate)
        second_buffer = _buffer(second)
        if library.phase06j_process_packet(state, state_bytes, second_buffer, len(second), ctypes.byref(output)) != 0:
            raise AssertionError("valid packet after rejection failed")
        if output.active_count != 1 or output.active[0].state != 2 or output.active[0].seen_count != 2:
            raise AssertionError("rejected packet changed temporal state")
        rejected_state_checks = 1
        if os.name == "nt":
            import _ctypes
            handle = library._handle
            del library
            _ctypes.FreeLibrary(handle)
    if mismatch_count:
        raise AssertionError(f"Python/C temporal mismatch count: {mismatch_count}")
    return {
        "compiler": compiler,
        "state_bytes": state_bytes,
        "frame_result_bytes": ctypes.sizeof(FrameResult),
        "sequence_count": golden["sequence_count"],
        "frame_count": golden["frame_count"],
        "candidate_records_checked": decoded_records,
        "active_event_outputs": golden["active_event_outputs"],
        "confirmed_event_outputs": golden["confirmed_event_outputs"],
        "ended_event_outputs": golden["ended_event_outputs"],
        "malformed_packet_checks": malformed_checks,
        "rejected_packet_state_unchanged_checks": rejected_state_checks,
        "mismatch_count": mismatch_count,
    }


def build_documents() -> dict[str, object]:
    host = run_host_verification()
    files = build_all_files()
    if any((FIXTURES / name).read_bytes() != data for name, data in files.items()):
        raise AssertionError("PHASE-06J fixtures are stale")
    return {
        "algorithm-contract.json": {
            "phase": "PHASE-06J", "status": "passed", "placement": "Zynq PS portable core",
            "source": "reference/detection/pipeline.py DetectionPipeline._update_tracks",
            "confirmation": "2 observations in a per-track 3-frame deque; confirmed state is sticky",
            "association": "previous inclusive span expanded by 2 bins; positive overlap required",
            "pair_order": ["descending overlap", "ascending peak displacement", "event ID", "current start bin", "current index"],
            "expiry": "two consecutive missing frames", "empty_frame": "one miss for every active track",
            "discontinuity": "reset before current frame", "uint32_wrap": "FFFFFFFF to 00000000 is consecutive",
            "admission": "descending peak-to-noise ratio, then peak bin, start bin, input index",
            "maximum_active_tracks": 64, "maximum_ended_history": 128,
        },
        "host-build.json": {
            "phase": "PHASE-06J", "status": "passed", "language": "portable C11",
            "compiler_family": host["compiler"], "compile": "passed", "link": "passed",
            "state_bytes": host["state_bytes"], "frame_result_bytes": host["frame_result_bytes"],
            "absolute_paths_recorded": False,
        },
        "golden-equivalence.json": {"phase": "PHASE-06J", "status": "passed", **{k: v for k, v in host.items() if k != "compiler"}},
        "toolchain.json": {
            "phase": "PHASE-06J", "status": "partial", "host_c": "ready_and_exercised",
            "petalinux": "not_found", "petalinux_project": "not_found", "zedboard_bsp": "not_found",
            "arm_cross_compiler": "not_found", "sysroot": "not_found", "xsa": "not_found",
            "device_tree_workflow": "not_defined", "arm_build": "blocked_toolchain",
            "arm_execution": "not_exercised", "wsl": "Ubuntu 22.04 WSL2 present without build tools",
        },
        "physical-boundary.json": {
            "phase": "PHASE-06J", "status": "deferred_separate_phase", "owner": "Zynq PS",
            "reason": "PHASE-06I ABI carries bins but not runtime RF center frequency or sample rate",
            "frequency_offset": "(shifted_bin - 2048) * sample_rate / 4096",
            "absolute_frequency": "RF_center + frequency_offset",
            "coarse_span_hz": "span_bins * sample_rate / 4096; not precise bandwidth",
            "precise_occupied_bandwidth": "not_implemented", "dbfs_or_dbm": "not_implemented_without normalization/calibration contract",
        },
        "system-limitations.json": {
            "phase": "PHASE-06J", "real_pl_ps_hardware_path": "not_verified",
            "dma_ip_driver_device_tree": "not_implemented", "phase06g_continuous_throughput": "not_supported",
            "phase06g_required_frame_gap_clocks": 476131, "petalinux": "blocked",
            "arm_execution": "not_exercised", "live_hackrf": "not_exercised",
            "pc_independent_system": "not_complete", "new_pl_logic": "none",
            "worst_case_pair_comparisons_per_frame_upper_bound": 5537792,
            "worst_case_admission_comparisons_per_frame_upper_bound": 84512,
        },
        "source-manifest.json": {
            "phase": "PHASE-06J", "status": "passed",
            "files": {name: sha256(ROOT / name) for name in SOURCE_FILES},
            "frozen_phase06i_packet_source": {"path": "datasets/fixtures/phase06i/transport-packets.bin", "sha256": sha256(ROOT / "datasets/fixtures/phase06i/transport-packets.bin")},
            "authoritative_temporal_source": {"path": "reference/detection/pipeline.py", "sha256": sha256(ROOT / "reference/detection/pipeline.py")},
        },
        "verification-summary.json": {
            "phase": "PHASE-06J", "overall": "passed", "abi_decoder": "passed",
            "host_c_build": "passed", "python_c_temporal_equivalence": "passed",
            "mismatch_count": 0, "arm_cross_compile": "blocked_toolchain", "arm_execution": "not_exercised",
            "physical_parameter_conversion": "not_implemented", "real_dma": "not_implemented",
            "hardware": "not_exercised", "live_hackrf": "not_exercised",
        },
    }


def write() -> None:
    documents = build_documents()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))


def check() -> bool:
    try:
        documents = build_documents()
        exact = all(
            (EVIDENCE / name).is_file() and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name])
            for name in OWNED_FILES
        )
        text = "".join((EVIDENCE / name).read_text(encoding="utf-8") for name in OWNED_FILES if (EVIDENCE / name).is_file()).casefold()
        safe = not any(token in text for token in ("c:\\users", "onedrive", "hostname", "timestamp"))
        return exact and safe and documents["verification-summary.json"]["overall"] == "passed"
    except (OSError, ValueError, AssertionError, RuntimeError, FileNotFoundError, json.JSONDecodeError):
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
    print(f"PHASE-06J verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
