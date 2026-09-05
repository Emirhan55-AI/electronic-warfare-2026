from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
P0 = ROOT / "platforms/embedded/p0"
P06I = ROOT / "platforms/embedded/phase06i"
P06J = ROOT / "platforms/embedded/phase06j"


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/" + "/".join(resolved.parts[1:])


def test_st06_product_pipeline_unifies_narrow_and_wideband(tmp_path: Path) -> None:
    compiler = shutil.which("gcc") or shutil.which("cc")
    using_wsl = False
    if compiler is None:
        fallback = Path("C:/msys64/ucrt64/bin/gcc.exe")
        if fallback.is_file():
            compiler = str(fallback)
        elif shutil.which("wsl.exe"):
            compiler = "gcc"
            using_wsl = True
        else:
            pytest.skip("C11 derleyicisi bulunamadı.")

    output = tmp_path / "p0-st06-product-pipeline-run"
    sources = [
        ROOT / "tests/p0/p0_st06_product_pipeline_run.c",
        P0 / "src/p0_parameter_runtime.c",
        P0 / "src/p0_ed_pipeline.c",
        P0 / "src/p0_os_cfar.c",
        P0 / "src/p0_pl_os_cfar.c",
        P0 / "src/p0_multiscale_detector.c",
        P0 / "src/p0_candidate_packet.c",
        P0 / "src/p0_persistent_weak.c",
        P0 / "src/p0_st05_wideband.c",
        P0 / "src/p0_st05_stream.c",
        P06J / "src/phase06j_temporal.c",
    ]
    command = [
        compiler,
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        "-I",
        str(P0 / "include"),
        "-I",
        str(P06I / "include"),
        "-I",
        str(P06J / "include"),
        *(str(source) for source in sources),
        "-lm",
        "-o",
        str(output),
    ]
    if using_wsl:
        command = [
            "wsl.exe",
            compiler,
            *(
                _wsl_path(Path(value)) if value.startswith("C:\\") else value
                for value in command[1:]
            ),
        ]
    subprocess.run(command, check=True, cwd=ROOT)
    completed = subprocess.run(
        ["wsl.exe", _wsl_path(output)] if using_wsl else [str(output)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "ST06_PRODUCT_PIPELINE=PASS"
