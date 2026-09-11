#!/usr/bin/env python3
"""Verify the portable ST-05 wideband C implementation against Python."""

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
import time
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.st05_wideband import ST05WidebandDetector
from scripts.evaluate_st05_wideband import CONTRACT, _frames


ST05_EVIDENCE = ROOT / "results/evidence/phase08/st05-wideband-holdout-v2.json"
DEFAULT_OUTPUT = ROOT / "results/evidence/phase08/st06-wideband-c-equivalence-v5.json"
FRAME_BINS = 4096
MAXIMUM_FRAMES = 64
MAXIMUM_CANDIDATES = 64
MAXIMUM_UNRESOLVED = 64

DECISIONS = {
    "reference_unavailable": 0,
    "no_bounded_emission": 1,
    "retune_required": 2,
    "bounded_candidates": 3,
}
REASONS = {
    "independent_flanks_unavailable": 1,
    "nonhomogeneous_flanks": 2,
}


class CCandidate(ctypes.Structure):
    _fields_ = [
        ("start_bin", ctypes.c_uint32),
        ("end_bin", ctypes.c_uint32),
        ("peak_bin", ctypes.c_uint32),
        ("peak_power", ctypes.c_double),
        ("reference_power_per_bin", ctypes.c_double),
        ("threshold_power_per_bin", ctypes.c_double),
        ("observed_frames", ctypes.c_uint32),
        ("total_frames", ctypes.c_uint32),
    ]


class CUnresolved(ctypes.Structure):
    _fields_ = [
        ("start_bin", ctypes.c_uint32),
        ("end_bin", ctypes.c_uint32),
        ("reason", ctypes.c_uint32),
    ]


class CResult(ctypes.Structure):
    _fields_ = [
        ("decision", ctypes.c_uint32),
        ("candidate_count", ctypes.c_uint32),
        ("unresolved_count", ctypes.c_uint32),
        ("absolute_absence_supported", ctypes.c_uint32),
        ("relative_reference_power_per_bin", ctypes.c_double),
        ("candidates", CCandidate * MAXIMUM_CANDIDATES),
        ("unresolved", CUnresolved * MAXIMUM_UNRESOLVED),
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_msvc() -> tuple[Path, Path] | None:
    roots = (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    )
    installations: list[Path] = []
    for root in roots:
        installations.extend((root / "Microsoft Visual Studio").glob("*/BuildTools"))
        installations.extend((root / "Microsoft Visual Studio").glob("*/Community"))
        installations.extend((root / "Microsoft Visual Studio").glob("*/Professional"))
        installations.extend((root / "Microsoft Visual Studio").glob("*/Enterprise"))
    for installation in sorted(installations, reverse=True):
        vcvars = installation / "VC/Auxiliary/Build/vcvars64.bat"
        compilers = sorted(
            (installation / "VC/Tools/MSVC").glob("*/bin/Hostx64/x64/cl.exe"),
            reverse=True,
        )
        if vcvars.is_file() and compilers:
            return vcvars, compilers[0]
    return None


def _compile(directory: Path) -> tuple[Path, str, str]:
    include = ROOT / "platforms/embedded/p0/include"
    source = ROOT / "platforms/embedded/p0/src/p0_st05_wideband.c"
    if os.name == "nt" and (msvc := _find_msvc()) is not None:
        vcvars, compiler = msvc
        output = directory / "p0_st05_wideband.dll"
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX /LD '
            f'/I"{include}" "{source}" /link /OUT:"{output}"'
        )
        completed = subprocess.run(
            command,
            check=True,
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        return output, "MSVC C11 /O2 /W4 /WX", completed.stdout.strip()

    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        raise FileNotFoundError("C11 host compiler is unavailable")
    output = directory / (
        "p0_st05_wideband.dll" if os.name == "nt" else "libp0_st05_wideband.so"
    )
    completed = subprocess.run(
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
            str(source),
            "-lm",
            "-o",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    version = subprocess.run(
        [compiler, "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.splitlines()[0]
    return output, version, completed.stdout.strip()


def _configure(library: ctypes.CDLL) -> Any:
    function = library.p0_st05_wideband_process
    function.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(CResult),
    ]
    function.restype = ctypes.c_int
    return function


def _close_library(library: ctypes.CDLL) -> None:
    handle = library._handle
    del library
    if os.name == "nt":
        _ctypes.FreeLibrary(handle)


def _float_difference(left: float, right: float) -> tuple[float, float]:
    absolute = abs(left - right)
    relative = absolute / max(abs(left), abs(right), sys.float_info.min)
    return absolute, relative


def _run_sequence(
    function: Any,
    detector: ST05WidebandDetector,
    frames: np.ndarray,
) -> tuple[dict[str, Any], list[str], float, float]:
    contiguous = np.ascontiguousarray(frames, dtype=np.float64)
    expected = detector.process(contiguous)
    observed = CResult()
    status = function(
        contiguous.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        contiguous.shape[0],
        contiguous.shape[1],
        ctypes.byref(observed),
    )
    mismatches: list[str] = []
    maximum_absolute = 0.0
    maximum_relative = 0.0

    if status != 0:
        mismatches.append(f"status:{status}")
    if observed.decision != DECISIONS[expected.decision]:
        mismatches.append(
            f"decision:{observed.decision}!={DECISIONS[expected.decision]}"
        )
    if observed.absolute_absence_supported != int(expected.absolute_absence_supported):
        mismatches.append("absolute_absence_supported")
    if observed.candidate_count != len(expected.candidates):
        mismatches.append(
            f"candidate_count:{observed.candidate_count}!={len(expected.candidates)}"
        )
    if observed.unresolved_count != len(expected.unresolved_supports):
        mismatches.append(
            f"unresolved_count:{observed.unresolved_count}!={len(expected.unresolved_supports)}"
        )

    expected_reference = expected.relative_reference_power_per_bin
    if math.isnan(expected_reference):
        if not math.isnan(observed.relative_reference_power_per_bin):
            mismatches.append("relative_reference_nan")
    else:
        absolute, relative = _float_difference(
            observed.relative_reference_power_per_bin, expected_reference
        )
        maximum_absolute = max(maximum_absolute, absolute)
        maximum_relative = max(maximum_relative, relative)
        if not math.isclose(
            observed.relative_reference_power_per_bin,
            expected_reference,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            mismatches.append("relative_reference_power_per_bin")

    for index, wanted in enumerate(expected.candidates[: observed.candidate_count]):
        got = observed.candidates[index]
        integer_fields = (
            ("start_bin", got.start_bin, wanted.start_bin),
            ("end_bin", got.end_bin, wanted.end_bin),
            ("peak_bin", got.peak_bin, wanted.peak_bin),
            ("observed_frames", got.observed_frames, wanted.observed_frames),
            ("total_frames", got.total_frames, wanted.total_frames),
        )
        for name, left, right in integer_fields:
            if left != right:
                mismatches.append(f"candidate[{index}].{name}:{left}!={right}")
        float_fields = (
            ("peak_power", got.peak_power, wanted.peak_power),
            (
                "reference_power_per_bin",
                got.reference_power_per_bin,
                wanted.reference_power_per_bin,
            ),
            (
                "threshold_power_per_bin",
                got.threshold_power_per_bin,
                wanted.threshold_power_per_bin,
            ),
        )
        for name, left, right in float_fields:
            absolute, relative = _float_difference(left, right)
            maximum_absolute = max(maximum_absolute, absolute)
            maximum_relative = max(maximum_relative, relative)
            if not math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12):
                mismatches.append(f"candidate[{index}].{name}")

    for index, wanted in enumerate(
        expected.unresolved_supports[: observed.unresolved_count]
    ):
        got = observed.unresolved[index]
        if (got.start_bin, got.end_bin, got.reason) != (
            wanted.start_bin,
            wanted.end_bin,
            REASONS[wanted.reason],
        ):
            mismatches.append(f"unresolved[{index}]")

    record = {
        "python_decision": expected.decision,
        "c_decision": int(observed.decision),
        "python_candidate_count": len(expected.candidates),
        "c_candidate_count": int(observed.candidate_count),
        "python_unresolved_count": len(expected.unresolved_supports),
        "c_unresolved_count": int(observed.unresolved_count),
        "matched": not mismatches,
    }
    return record, mismatches, maximum_absolute, maximum_relative


def _api_boundary_checks(function: Any) -> dict[str, Any]:
    result = CResult()
    valid = np.ones((8, FRAME_BINS), dtype=np.float64)
    seven = valid[:7]
    sixty_five = np.ones((65, FRAME_BINS), dtype=np.float64)
    wrong_bins = np.ones((8, FRAME_BINS - 1), dtype=np.float64)
    nonfinite = valid.copy()
    nonfinite[0, 0] = np.nan
    negative = valid.copy()
    negative[0, 0] = -1.0

    checks = {
        "null_input": function(None, 8, FRAME_BINS, ctypes.byref(result)),
        "null_result": function(
            valid.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            8,
            FRAME_BINS,
            None,
        ),
        "too_few_frames": function(
            seven.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            7,
            FRAME_BINS,
            ctypes.byref(result),
        ),
        "too_many_frames": function(
            sixty_five.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            65,
            FRAME_BINS,
            ctypes.byref(result),
        ),
        "wrong_bin_count": function(
            wrong_bins.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            8,
            FRAME_BINS - 1,
            ctypes.byref(result),
        ),
        "nonfinite_power": function(
            nonfinite.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            8,
            FRAME_BINS,
            ctypes.byref(result),
        ),
        "negative_power": function(
            negative.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            8,
            FRAME_BINS,
            ctypes.byref(result),
        ),
    }
    return {
        "status": "passed" if all(value == -1 for value in checks.values()) else "failed",
        "expected_status": -1,
        "observed": checks,
    }


def evaluate() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    recorded_st05 = json.loads(ST05_EVIDENCE.read_text(encoding="utf-8"))
    expected_hashes = {
        (item["scene"], int(item["trial"])): item["frame_power_sha256"]
        for item in recorded_st05["records"]
    }
    detector = ST05WidebandDetector()
    records: list[dict[str, Any]] = []
    mismatch_details: list[dict[str, Any]] = []
    input_hash_mismatches = 0
    maximum_absolute = 0.0
    maximum_relative = 0.0
    started = time.perf_counter()
    compiler = ""
    compiler_output = ""

    with tempfile.TemporaryDirectory(prefix="st06-wideband-c-") as raw:
        library_path, compiler, compiler_output = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = _configure(library)
        api_checks = _api_boundary_checks(function)
        for scene_index, scene in enumerate(contract["scenes"]):
            for trial_index in range(int(contract["trials_per_scene"])):
                seed = (
                    int(contract["holdout_seed_base"])
                    + scene_index * 10_000
                    + trial_index
                )
                frames = _frames(
                    scene,
                    seed=seed,
                    count=int(contract["frames_per_sequence"]),
                )
                frame_hash = hashlib.sha256(frames.tobytes()).hexdigest()
                if frame_hash != expected_hashes[(scene["id"], trial_index)]:
                    input_hash_mismatches += 1
                result, mismatches, absolute, relative = _run_sequence(
                    function, detector, frames
                )
                maximum_absolute = max(maximum_absolute, absolute)
                maximum_relative = max(maximum_relative, relative)
                record = {
                    "scene": scene["id"],
                    "family": scene["family"],
                    "trial": trial_index,
                    "seed": seed,
                    "frame_power_sha256": frame_hash,
                    **result,
                }
                records.append(record)
                if mismatches and len(mismatch_details) < 32:
                    mismatch_details.append(
                        {
                            "scene": scene["id"],
                            "trial": trial_index,
                            "mismatches": mismatches,
                        }
                    )
        del function
        _close_library(library)

    elapsed = time.perf_counter() - started
    mismatch_count = sum(not item["matched"] for item in records)
    passed = (
        len(records) == len(expected_hashes) == 960
        and mismatch_count == 0
        and input_hash_mismatches == 0
        and api_checks["status"] == "passed"
    )
    source_paths = (
        "algorithms/p0/st05_wideband.py",
        "config/st05_wideband_evaluation.json",
        "platforms/embedded/p0/include/p0_st05_wideband.h",
        "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
        "platforms/embedded/p0/src/p0_st05_wideband.c",
        "scripts/evaluate_st05_wideband.py",
        "scripts/verify_st06_wideband_c.py",
    )
    return {
        "schema": "phase08-st06-wideband-c-equivalence-v5",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "product_algorithm_changed": False,
        "target": "portable C11 host build; intended PS logic",
        "arm_execution_performed": False,
        "rtl_implementation_present": False,
        "st06_c_ps_reference_complete": passed,
        "st06_complete": False,
        "compiler": compiler,
        "compiler_output": compiler_output,
        "corpus": {
            "source": "results/evidence/phase08/st05-wideband-holdout-v2.json",
            "sequences": len(records),
            "frames": len(records) * int(contract["frames_per_sequence"]),
            "input_hash_mismatches": input_hash_mismatches,
        },
        "equivalence": {
            "sequence_mismatches": mismatch_count,
            "decision_and_integer_fields": "exact",
            "floating_point_tolerance": {"relative": 1e-12, "absolute": 1e-12},
            "maximum_observed_absolute_difference": maximum_absolute,
            "maximum_observed_relative_difference": maximum_relative,
            "mismatch_details": mismatch_details,
        },
        "api_boundary_checks": api_checks,
        "host_elapsed_seconds_observation": elapsed,
        "performance_claim": "none; this Windows x64 observation is not an ARM or product throughput result",
        "records": records,
        "source_sha256": {name: _sha256(ROOT / name) for name in source_paths},
        "supersedes": "results/evidence/phase08/st06-wideband-c-equivalence-v4.json",
        "implementation_note": "Seed windows remain lazy and support regions are now grouped during the integration scan; decisions and boundaries remain identical.",
        "claim_boundary": [
            "This proves host-compiled C11/Python equivalence on the frozen synthetic ST-05 corpus only.",
            "It does not prove ARM execution, fixed-point equivalence, RTL behavior, timing closure, live RF, Pd/Pfa, or product acceptance.",
            "The C API accepts 8 through 64 frames; the frozen profile exercises eight-frame sequences.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 wideband C/Python equivalence")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        parser.error("Önceki ST-06 kanıtının üzerine yazılmaz.")
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
                "sequences": report["corpus"]["sequences"],
                "sequence_mismatches": report["equivalence"]["sequence_mismatches"],
                "input_hash_mismatches": report["corpus"]["input_hash_mismatches"],
                "api_boundary_checks": report["api_boundary_checks"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
