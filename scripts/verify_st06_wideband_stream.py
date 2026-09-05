#!/usr/bin/env python3
"""Verify the bounded eight-frame ST-05 C stream lifecycle."""

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
from scripts.verify_st06_wideband_c import (
    CResult,
    _close_library,
    _find_msvc,
    _run_sequence,
)


DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-wideband-stream-v3.json"
SEQUENCES_PER_SCENE = 8
FRAMES_PER_STREAM = 16


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compile(directory: Path) -> tuple[Path, str]:
    include = ROOT / "platforms/embedded/p0/include"
    sources = (
        ROOT / "platforms/embedded/p0/src/p0_st05_wideband.c",
        ROOT / "platforms/embedded/p0/src/p0_st05_stream.c",
    )
    if os.name == "nt" and (msvc := _find_msvc()) is not None:
        vcvars, _ = msvc
        output = directory / "p0_st05_stream.dll"
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
    output = directory / ("p0_st05_stream.dll" if os.name == "nt" else "libp0_st05_stream.so")
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


def _configure(library: ctypes.CDLL) -> tuple[Any, Any, Any, Any]:
    wideband = library.p0_st05_wideband_process
    wideband.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(CResult),
    ]
    wideband.restype = ctypes.c_int
    state_bytes = library.p0_st05_stream_state_bytes
    state_bytes.argtypes = []
    state_bytes.restype = ctypes.c_size_t
    initialize = library.p0_st05_stream_init
    initialize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    initialize.restype = ctypes.c_int
    reset = library.p0_st05_stream_reset
    reset.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    reset.restype = ctypes.c_int
    update = library.p0_st05_stream_update
    update.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        ctypes.POINTER(CResult),
        ctypes.POINTER(ctypes.c_int),
    ]
    update.restype = ctypes.c_int
    return wideband, state_bytes, initialize, reset, update


def _result_signature(result: CResult) -> tuple[Any, ...]:
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


def evaluate() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    detector = ST05WidebandDetector()
    records: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    warmup_validity_errors = 0
    result_windows = 0
    reset_checks = 0
    invalid_transaction_checks = 0

    with tempfile.TemporaryDirectory(prefix="st06-stream-") as raw:
        library_path, compiler = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        wideband, state_bytes_fn, initialize, reset, update = _configure(library)
        state_size = int(state_bytes_fn())
        state_words = (ctypes.c_double * math.ceil(state_size / ctypes.sizeof(ctypes.c_double)))()
        state = ctypes.cast(state_words, ctypes.c_void_p)
        if initialize(state, state_size) != 0:
            raise RuntimeError("stream initialization failed")

        for scene_index, scene in enumerate(contract["scenes"]):
            for stream_index in range(SEQUENCES_PER_SCENE):
                if reset(state, state_size) != 0:
                    raise RuntimeError("stream reset failed")
                reset_checks += 1
                seed = int(contract["holdout_seed_base"]) + scene_index * 10_000 + stream_index
                frames = _frames(scene, seed=seed, count=FRAMES_PER_STREAM)
                accepted = []
                for frame_index, frame in enumerate(frames):
                    contiguous = np.ascontiguousarray(frame, dtype=np.float64)
                    observed = CResult()
                    result_valid = ctypes.c_int(-1)
                    status = update(
                        state,
                        state_size,
                        contiguous.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                        contiguous.size,
                        ctypes.byref(observed),
                        ctypes.byref(result_valid),
                    )
                    expected_valid = frame_index >= 7
                    if status != 0 or bool(result_valid.value) != expected_valid:
                        warmup_validity_errors += 1
                    if not expected_valid:
                        continue
                    result_windows += 1
                    window = np.ascontiguousarray(frames[frame_index - 7 : frame_index + 1])
                    _, expected_mismatches, _, _ = _run_sequence(
                        wideband,
                        detector,
                        window,
                    )
                    expected = detector.process(window)
                    expected_signature = (
                        {"reference_unavailable": 0, "no_bounded_emission": 1,
                         "retune_required": 2, "bounded_candidates": 3}[expected.decision],
                        int(expected.absolute_absence_supported),
                        tuple(
                            (item.start_bin, item.end_bin, item.peak_bin,
                             item.observed_frames, item.total_frames)
                            for item in expected.candidates
                        ),
                        tuple(
                            (item.start_bin, item.end_bin,
                             {"independent_flanks_unavailable": 1,
                              "nonhomogeneous_flanks": 2}[item.reason])
                            for item in expected.unresolved_supports
                        ),
                    )
                    matched = not expected_mismatches and _result_signature(observed) == expected_signature
                    accepted.append(matched)
                    if not matched and len(mismatches) < 32:
                        mismatches.append(
                            {"scene": scene["id"], "stream": stream_index,
                             "frame": frame_index}
                        )
                records.append(
                    {
                        "scene": scene["id"],
                        "family": scene["family"],
                        "stream": stream_index,
                        "seed": seed,
                        "windows": len(accepted),
                        "matched_windows": sum(accepted),
                    }
                )

        snapshot = bytes(state_words)
        bad = np.ones(4096, dtype=np.float64)
        bad[0] = np.nan
        observed = CResult()
        result_valid = ctypes.c_int(-1)
        status = update(
            state,
            state_size,
            bad.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            bad.size,
            ctypes.byref(observed),
            ctypes.byref(result_valid),
        )
        invalid_transaction_checks += int(status == -1 and bytes(state_words) == snapshot)
        function_objects = (wideband, state_bytes_fn, initialize, reset, update)
        del function_objects, wideband, state_bytes_fn, initialize, reset, update
        _close_library(library)

    mismatch_count = sum(
        item["matched_windows"] != item["windows"] for item in records
    )
    passed = (
        len(records) == len(contract["scenes"]) * SEQUENCES_PER_SCENE
        and result_windows == len(records) * 9
        and mismatch_count == 0
        and not mismatches
        and warmup_validity_errors == 0
        and reset_checks == len(records)
        and invalid_transaction_checks == 1
    )
    sources = (
        "algorithms/p0/st05_wideband.py",
        "config/st05_wideband_evaluation.json",
        "platforms/embedded/p0/include/p0_st05_wideband.h",
        "platforms/embedded/p0/src/p0_st05_wideband.c",
        "platforms/embedded/p0/include/p0_st05_stream.h",
        "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
        "platforms/embedded/p0/src/p0_st05_stream.c",
        "scripts/verify_st06_wideband_stream.py",
    )
    return {
        "schema": "phase08-st06-wideband-stream-v3",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "st06_stream_lifecycle_complete": passed,
        "st06_complete": False,
        "compiler": compiler,
        "state_bytes": state_size,
        "streams": len(records),
        "frames_per_stream": FRAMES_PER_STREAM,
        "evaluated_sliding_windows": result_windows,
        "warmup_validity_errors": warmup_validity_errors,
        "stream_mismatches": mismatch_count,
        "mismatch_details": mismatches,
        "reset_checks": reset_checks,
        "invalid_update_transaction_checks": invalid_transaction_checks,
        "records": records,
        "source_sha256": {name: _sha256(ROOT / name) for name in sources},
        "supersedes": "results/evidence/phase08/st06-wideband-stream-v2.json",
        "claim_boundary": [
            "This verifies a bounded eight-frame sliding C state and reset/error lifecycle on synthetic host data.",
            "Frame order inside the ring is irrelevant because the selected detector uses commutative frame means and occupancy counts.",
            "ARM timing, DMA integration, RTL routing, live RF, Pd/Pfa, and product acceptance remain open.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 C stream lifecycle verifier")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        parser.error("Önceki ST-06 akış kanıtının üzerine yazılmaz.")
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "streams": report["streams"],
                "windows": report["evaluated_sliding_windows"],
                "mismatches": report["stream_mismatches"],
                "state_bytes": report["state_bytes"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
