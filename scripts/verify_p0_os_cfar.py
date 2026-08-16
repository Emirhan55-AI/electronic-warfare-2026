"""Compile the portable P0 OS-CFAR C11 core and compare it with Python."""

from __future__ import annotations

import argparse
import _ctypes
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0 import OSCFARConfig, OSCFARDetector


class Config(ctypes.Structure):
    _fields_ = [("reference", ctypes.c_uint32), ("guard", ctypes.c_uint32), ("rank", ctypes.c_uint32), ("coefficient", ctypes.c_double), ("gap", ctypes.c_uint32)]


class Candidate(ctypes.Structure):
    _fields_ = [("start", ctypes.c_uint32), ("end", ctypes.c_uint32), ("peak", ctypes.c_uint32), ("peak_power", ctypes.c_double), ("noise", ctypes.c_double), ("threshold", ctypes.c_double)]


def _msvc() -> tuple[Path, Path] | None:
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not vswhere.is_file():
        return None
    query = subprocess.run(
        [str(vswhere), "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if query.returncode or not query.stdout.strip():
        return None
    root = Path(query.stdout.strip())
    vcvars = root / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    compilers = sorted((root / "VC" / "Tools" / "MSVC").glob("*/bin/Hostx64/x64/cl.exe"), reverse=True)
    return (vcvars, compilers[0]) if vcvars.is_file() and compilers else None


def _compile(directory: Path) -> tuple[Path, str]:
    source = ROOT / "ps" / "p0" / "src" / "p0_os_cfar.c"
    include = ROOT / "ps" / "p0" / "include"
    if (msvc := _msvc()) is not None:
        vcvars, compiler = msvc
        output = directory / "p0_os_cfar.dll"
        command = f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX /LD /I"{include}" "{source}" /link /OUT:"{output}"'
        subprocess.run(command, check=True, cwd=directory, shell=True)
        return output, "MSVC C11"
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        raise FileNotFoundError("C11 host compiler is unavailable")
    output = directory / ("p0_os_cfar.dll" if __import__("os").name == "nt" else "libp0_os_cfar.so")
    subprocess.run([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", f"-I{include}", str(source), "-o", str(output)], check=True)
    return output, Path(compiler).name


def verify() -> dict[str, object]:
    cfg = OSCFARConfig()
    rng = np.random.default_rng(2026)
    frames = []
    for frame_id in range(8):
        frame = rng.exponential(1.0, 4096).astype(np.float64)
        frame[400 + frame_id] = 80.0
        frame[1900:1904] += 40.0
        frames.append(frame)
    mismatch_count = 0
    with tempfile.TemporaryDirectory(prefix="p0-os-cfar-") as raw:
        library_path, compiler = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = library.p0_os_cfar_process
        function.restype = ctypes.c_int
        for frame_id, power in enumerate(frames):
            expected = OSCFARDetector(cfg).process(power, frame_id=frame_id)
            detections = np.zeros(power.size, dtype=np.uint8)
            noise = np.empty(power.size, dtype=np.float64)
            threshold = np.empty(power.size, dtype=np.float64)
            candidates = (Candidate * 4096)()
            count = ctypes.c_size_t()
            c_cfg = Config(cfg.reference_cells_per_side, cfg.guard_cells_per_side, cfg.order_statistic_rank, cfg.threshold_coefficient, cfg.maximum_gap_bins)
            status = function(
                power.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), power.size, ctypes.byref(c_cfg),
                detections.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                noise.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                threshold.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                candidates, 4096, ctypes.byref(count),
            )
            if status != 0:
                raise RuntimeError(f"C detector returned {status}")
            mismatch_count += int(np.count_nonzero(detections.astype(bool) != expected.detections))
            observed = [(candidates[index].start, candidates[index].end, candidates[index].peak) for index in range(count.value)]
            wanted = [(item.start_bin, item.end_bin, item.peak_bin) for item in expected.candidates]
            mismatch_count += int(observed != wanted)
        handle = library._handle
        del function
        del library
        _ctypes.FreeLibrary(handle)
    return {"phase": "P0", "status": "passed" if mismatch_count == 0 else "failed", "compiler": compiler, "frames": len(frames), "cells": len(frames) * 4096, "mismatch_count": mismatch_count, "arm_execution": "not_exercised"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
