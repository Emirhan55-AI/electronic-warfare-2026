#!/usr/bin/env python3
"""Verify the marked PL power-frame to bounded ST-05 ARM runtime path."""

from __future__ import annotations

import argparse
import _ctypes
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.st05_wideband import ST05WidebandDetector
from scripts.evaluate_st05_wideband import CONTRACT, _frames
from scripts.verify_st06_wideband_c import CResult, _find_msvc


DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-power-runtime-v3.json"
SEQUENCES_PER_SCENE = 4
FRAMES_PER_STREAM = 16
FRAME_BINS = 4096
FRAME_BYTES = FRAME_BINS * 8
POWER_SCALE = 1 << 30
OUTPUT_MARKER = np.uint64(0xA << 60)
EVALUATED_MASK = np.uint64(1 << 58)


class CRuntime(ctypes.Structure):
    _fields_ = [
        ("shifted_power", ctypes.c_void_p),
        ("shifted_power_uq28_30", ctypes.c_void_p),
        ("shifted_detections", ctypes.c_void_p),
        ("stream_state", ctypes.c_void_p),
        ("stream_state_bytes", ctypes.c_size_t),
        ("last_frame_id", ctypes.c_uint32),
        ("has_frame_id", ctypes.c_int),
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compile(directory: Path) -> tuple[Path, str]:
    include = ROOT / "platforms/embedded/p0/include"
    sources = (
        ROOT / "platforms/embedded/p0/src/p0_st05_wideband.c",
        ROOT / "platforms/embedded/p0/src/p0_st05_stream.c",
        ROOT / "platforms/embedded/p0/src/p0_st06_power_runtime.c",
    )
    if os.name == "nt" and (msvc := _find_msvc()) is not None:
        vcvars, _ = msvc
        output = directory / "p0_st06_power_runtime.dll"
        source_args = " ".join(f'"{source}"' for source in sources)
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX /LD '
            f'/I"{include}" {source_args} /link /OUT:"{output}"'
        )
        subprocess.run(
            command,
            check=True,
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        return output, "MSVC C11 /O2 /W4 /WX"
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        raise FileNotFoundError("C11 host compiler is unavailable")
    output = directory / (
        "p0_st06_power_runtime.dll"
        if os.name == "nt"
        else "libp0_st06_power_runtime.so"
    )
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-shared",
            "-fPIC",
            f"-I{include}",
            *(str(source) for source in sources),
            "-lm",
            "-o",
            str(output),
        ],
        check=True,
    )
    return output, Path(compiler).name


def _configure(library: ctypes.CDLL) -> tuple[Any, Any, Any]:
    initialize = library.p0_st06_power_runtime_init
    initialize.argtypes = [ctypes.POINTER(CRuntime)]
    initialize.restype = ctypes.c_int
    release = library.p0_st06_power_runtime_release
    release.argtypes = [ctypes.POINTER(CRuntime)]
    release.restype = None
    process = library.p0_st06_power_runtime_process
    process.argtypes = [
        ctypes.POINTER(CRuntime),
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(CResult),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    process.restype = ctypes.c_int
    return initialize, release, process


def _packet(frame: np.ndarray, *, marked: bool = True) -> tuple[np.ndarray, np.ndarray]:
    quantized = np.rint(np.asarray(frame, dtype=np.float64) * POWER_SCALE).astype(
        np.uint64
    )
    decoded = quantized.astype(np.float64) / POWER_SCALE
    shifted_words = quantized.copy()
    if marked:
        shifted_words |= OUTPUT_MARKER
        shifted_words[20 : FRAME_BINS - 20] |= EVALUATED_MASK
    natural_words = np.empty(FRAME_BINS, dtype="<u8")
    shifted_indices = np.arange(FRAME_BINS, dtype=np.uint64)
    natural_words[np.bitwise_xor(shifted_indices, FRAME_BINS // 2)] = shifted_words
    return np.ascontiguousarray(natural_words.view(np.uint8)), decoded


def _signature(result: CResult) -> tuple[Any, ...]:
    return (
        int(result.decision),
        int(result.absolute_absence_supported),
        tuple(
            (
                result.candidates[index].start_bin,
                result.candidates[index].end_bin,
                result.candidates[index].peak_bin,
                result.candidates[index].observed_frames,
                result.candidates[index].total_frames,
            )
            for index in range(result.candidate_count)
        ),
        tuple(
            (
                result.unresolved[index].start_bin,
                result.unresolved[index].end_bin,
                result.unresolved[index].reason,
            )
            for index in range(result.unresolved_count)
        ),
    )


def _expected_signature(detector: ST05WidebandDetector, frames: np.ndarray) -> tuple[Any, ...]:
    expected = detector.process(frames)
    return (
        {
            "reference_unavailable": 0,
            "no_bounded_emission": 1,
            "retune_required": 2,
            "bounded_candidates": 3,
        }[expected.decision],
        int(expected.absolute_absence_supported),
        tuple(
            (
                item.start_bin,
                item.end_bin,
                item.peak_bin,
                item.observed_frames,
                item.total_frames,
            )
            for item in expected.candidates
        ),
        tuple(
            (
                item.start_bin,
                item.end_bin,
                {
                    "independent_flanks_unavailable": 1,
                    "nonhomogeneous_flanks": 2,
                }[item.reason],
            )
            for item in expected.unresolved_supports
        ),
    )


def _call(
    process: Any,
    runtime: CRuntime,
    frame_id: int,
    reset_requested: bool,
    packet: np.ndarray,
) -> tuple[int, CResult, int, int]:
    result = CResult()
    result_valid = ctypes.c_int(-1)
    context_reset = ctypes.c_int(-1)
    status = process(
        ctypes.byref(runtime),
        frame_id,
        int(reset_requested),
        packet.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        packet.size,
        ctypes.byref(result),
        ctypes.byref(result_valid),
        ctypes.byref(context_reset),
    )
    return status, result, result_valid.value, context_reset.value


def evaluate() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    detector = ST05WidebandDetector()
    records: list[dict[str, Any]] = []
    mismatch_details: list[dict[str, Any]] = []
    evaluated_windows = 0
    warmup_errors = 0
    lifecycle_checks = 0

    with tempfile.TemporaryDirectory(prefix="st06-power-runtime-") as raw:
        library_path, compiler = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        initialize, release, process = _configure(library)
        for scene_index, scene in enumerate(contract["scenes"]):
            for stream_index in range(SEQUENCES_PER_SCENE):
                runtime = CRuntime()
                if initialize(ctypes.byref(runtime)) != 0:
                    raise RuntimeError("power runtime initialization failed")
                seed = int(contract["holdout_seed_base"]) + scene_index * 10_000 + stream_index
                frames = _frames(scene, seed=seed, count=FRAMES_PER_STREAM)
                decoded_frames = []
                matched = 0
                try:
                    for frame_index, frame in enumerate(frames):
                        packet, decoded = _packet(frame)
                        decoded_frames.append(decoded)
                        status, observed, valid, context_reset = _call(
                            process,
                            runtime,
                            frame_index,
                            frame_index == 0,
                            packet,
                        )
                        expected_valid = frame_index >= 7
                        if (
                            status != 0
                            or bool(valid) != expected_valid
                            or bool(context_reset) != (frame_index == 0)
                        ):
                            warmup_errors += 1
                        if not expected_valid:
                            continue
                        evaluated_windows += 1
                        expected = _expected_signature(
                            detector,
                            np.ascontiguousarray(
                                decoded_frames[frame_index - 7 : frame_index + 1]
                            ),
                        )
                        if _signature(observed) == expected:
                            matched += 1
                        elif len(mismatch_details) < 32:
                            mismatch_details.append(
                                {
                                    "scene": scene["id"],
                                    "stream": stream_index,
                                    "frame": frame_index,
                                }
                            )
                finally:
                    release(ctypes.byref(runtime))
                records.append(
                    {
                        "scene": scene["id"],
                        "stream": stream_index,
                        "windows": 9,
                        "matched_windows": matched,
                    }
                )

        runtime = CRuntime()
        if initialize(ctypes.byref(runtime)) != 0:
            raise RuntimeError("power runtime lifecycle initialization failed")
        try:
            source = _frames(contract["scenes"][3], seed=909090, count=16)
            decoded = []
            for frame_id in range(7):
                packet, quantized = _packet(source[frame_id])
                decoded.append(quantized)
                status, _, valid, _ = _call(
                    process, runtime, frame_id, frame_id == 0, packet
                )
                lifecycle_checks += int(status == 0 and valid == 0)

            bad, _ = _packet(source[7])
            bad = bad.copy()
            bad[:8] &= np.uint8(0x0F)
            status, _, _, _ = _call(process, runtime, 7, False, bad)
            lifecycle_checks += int(status == -1)

            packet, quantized = _packet(source[7])
            decoded.append(quantized)
            status, observed, valid, context_reset = _call(
                process, runtime, 7, False, packet
            )
            lifecycle_checks += int(
                status == 0
                and valid == 1
                and context_reset == 0
                and _signature(observed)
                == _expected_signature(detector, np.ascontiguousarray(decoded))
            )

            unmarked, _ = _packet(source[8], marked=False)
            status, _, _, _ = _call(process, runtime, 8, False, unmarked)
            lifecycle_checks += int(status == -1)

            packet, _ = _packet(source[8])
            status, _, valid, context_reset = _call(
                process, runtime, 20, False, packet
            )
            lifecycle_checks += int(
                status == 0 and valid == 0 and context_reset == 1
            )
            for offset in range(1, 8):
                packet, _ = _packet(source[8 + offset])
                status, _, valid, context_reset = _call(
                    process, runtime, 20 + offset, False, packet
                )
                lifecycle_checks += int(
                    status == 0
                    and valid == int(offset == 7)
                    and context_reset == 0
                )
        finally:
            release(ctypes.byref(runtime))
        function_objects = (initialize, release, process)
        del function_objects, initialize, release, process
        handle = library._handle
        del library
        if os.name == "nt":
            _ctypes.FreeLibrary(handle)

    mismatched_windows = sum(
        item["windows"] - item["matched_windows"] for item in records
    )
    expected_lifecycle_checks = 7 + 1 + 1 + 1 + 1 + 7
    passed = (
        len(records) == len(contract["scenes"]) * SEQUENCES_PER_SCENE
        and evaluated_windows == len(records) * 9
        and mismatched_windows == 0
        and not mismatch_details
        and warmup_errors == 0
        and lifecycle_checks == expected_lifecycle_checks
    )
    sources = (
        "algorithms/p0/st05_wideband.py",
        "config/st05_wideband_evaluation.json",
        "platforms/embedded/p0/include/p0_pl_os_cfar.h",
        "platforms/embedded/p0/src/p0_pl_os_cfar.c",
        "platforms/embedded/p0/include/p0_st05_wideband.h",
        "platforms/embedded/p0/src/p0_st05_wideband.c",
        "platforms/embedded/p0/include/p0_st05_stream.h",
        "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
        "platforms/embedded/p0/src/p0_st05_stream.c",
        "platforms/embedded/p0/include/p0_st06_power_runtime.h",
        "platforms/embedded/p0/src/p0_st06_power_runtime.c",
        "scripts/verify_st06_power_runtime.py",
    )
    return {
        "schema": "phase08-st06-power-runtime-v3",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "st06_power_runtime_complete": passed,
        "st06_complete": False,
        "compiler": compiler,
        "input_contract": {
            "bins": FRAME_BINS,
            "bytes": FRAME_BYTES,
            "natural_order": True,
            "output_marker_required_on_every_word": True,
            "fft_shift_applied_on_arm": True,
        },
        "streams": len(records),
        "frames_per_stream": FRAMES_PER_STREAM,
        "evaluated_sliding_windows": evaluated_windows,
        "warmup_or_context_errors": warmup_errors,
        "decision_or_shape_mismatches": mismatched_windows,
        "mismatch_details": mismatch_details,
        "lifecycle": {
            "passed_checks": lifecycle_checks,
            "expected_checks": expected_lifecycle_checks,
            "mixed_format_packet_rejected_without_consuming_frame": True,
            "unmarked_packet_rejected_without_consuming_frame": True,
            "frame_discontinuity_resets_eight_frame_context": True,
        },
        "records": records,
        "source_sha256": {name: _sha256(ROOT / name) for name in sources},
        "supersedes": "results/evidence/phase08/st06-power-runtime-v2.json",
        "claim_boundary": [
            "This verifies marked 4096-word PL power-frame decoding, FFT shift, sliding decisions, and context lifecycle on synthetic host data.",
            "It does not measure DMA, load a bitstream, alter the product service, or prove live-RF accuracy.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 PL power runtime verifier")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        parser.error("Önceki ST-06 güç çalışma kanıtının üzerine yazılmaz.")
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "streams": report["streams"],
                "windows": report["evaluated_sliding_windows"],
                "mismatches": report["decision_or_shape_mismatches"],
                "lifecycle": report["lifecycle"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
