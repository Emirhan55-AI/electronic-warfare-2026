#!/usr/bin/env python3
"""Build and exercise the P0 multiscale detector to temporal runtime bridge."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
P0_INCLUDE = ROOT / "platforms" / "embedded" / "p0" / "include"
PHASE06I_INCLUDE = ROOT / "platforms" / "embedded" / "phase06i" / "include"
PHASE06J_INCLUDE = ROOT / "platforms" / "embedded" / "phase06j" / "include"
SOURCES = (
    ROOT / "platforms" / "embedded" / "p0" / "src" / "p0_os_cfar.c",
    ROOT / "platforms" / "embedded" / "p0" / "src" / "p0_multiscale_detector.c",
    ROOT / "platforms" / "embedded" / "p0" / "src" / "p0_candidate_packet.c",
    ROOT / "platforms" / "embedded" / "phase06j" / "src" / "phase06j_temporal.c",
    ROOT / "platforms" / "embedded" / "p0" / "src" / "p0_ed_runtime_run.c",
)


def _msvc_vcvars() -> Path | None:
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
    path = Path(query.stdout.strip()) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    return path if path.is_file() else None


def _compile(directory: Path) -> tuple[Path, str]:
    if os.name == "nt" and (vcvars := _msvc_vcvars()) is not None:
        output = directory / "p0-ed-runtime-run.exe"
        sources = " ".join(f'"{path}"' for path in SOURCES)
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX '
            f'/I"{P0_INCLUDE}" /I"{PHASE06I_INCLUDE}" /I"{PHASE06J_INCLUDE}" '
            f'{sources} /Fe:"{output}"'
        )
        build = subprocess.run(
            command, cwd=directory, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        family = "MSVC C11"
    else:
        compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if compiler is None:
            raise FileNotFoundError("C11 host compiler is unavailable")
        output = directory / "p0-ed-runtime-run"
        build = subprocess.run(
            [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             f"-I{P0_INCLUDE}", f"-I{PHASE06I_INCLUDE}", f"-I{PHASE06J_INCLUDE}",
             *(str(path) for path in SOURCES), "-lm", "-o", str(output)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        family = Path(compiler).name
    if build.returncode or not output.is_file():
        raise RuntimeError(f"C11 build failed ({build.returncode}):\n{build.stdout}\n{build.stderr}")
    return output, family


def _write_single_tone_power(path: Path) -> None:
    natural_power = [100] * 4096
    natural_power[256] = 1_000_000
    path.write_bytes(struct.pack("<4096Q", *natural_power))


def verify() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="p0-temporal-runtime-") as raw:
        directory = Path(raw)
        executable, compiler = _compile(directory)
        power = directory / "single-tone.u64"
        output = directory / "result.json"
        _write_single_tone_power(power)
        run = subprocess.run(
            [str(executable), str(output), str(power), str(power), str(power), "-", "-"],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        if run.returncode:
            raise RuntimeError(f"runtime failed ({run.returncode}):\n{run.stdout}\n{run.stderr}")
        payload = json.loads(output.read_text(encoding="utf-8"))
        sentinel = b"previous-valid-result\n"
        output.write_bytes(sentinel)
        rejected = subprocess.run(
            [str(executable), str(output), str(directory / "missing.u64")],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        if rejected.returncode == 0 or output.read_bytes() != sentinel or output.with_suffix(".json.tmp").exists():
            raise AssertionError("failed runtime replaced a prior result or left a partial temporary file")
    frames = payload["frames"]
    if len(frames) != 5:
        raise AssertionError("five-frame acceptance sequence was not produced")
    expected_counts = (
        (1, 1, 0, "tentative"),
        (1, 1, 0, "confirmed"),
        (1, 1, 0, "confirmed"),
        (0, 1, 0, "confirmed"),
        (0, 0, 1, "ended"),
    )
    for frame, (raw_count, active_count, ended_count, state) in zip(frames, expected_counts, strict=True):
        if (frame["raw_candidate_count"], frame["active_count"], frame["ended_count"]) != (
            raw_count, active_count, ended_count,
        ):
            raise AssertionError("temporal count sequence differs from the 2-of-3 contract")
        event = (frame["active"] or frame["ended"])[0]
        if event["state"] != state or event["peak_bin"] != 2304:
            raise AssertionError("event state or fftshift peak bin is incorrect")
    if frames[0]["active"][0]["peak_power_uq28_30"] != 1_000_000:
        raise AssertionError("FPGA peak power was not preserved exactly")
    return {
        "status": "passed",
        "compiler": compiler,
        "frames": len(frames),
        "first_confirmation_frame": 1,
        "expiry_frame": 4,
        "peak_shifted_bin": 2304,
        "packet_decoder": "phase06j strict ABI v1",
        "dropped_candidates": sum(frame["dropped_candidates"] for frame in frames),
        "failure_preserves_previous_result": True,
    }


def main() -> int:
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
