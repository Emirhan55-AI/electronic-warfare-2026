from pathlib import Path
import os
import shutil
import subprocess

from algorithms.p0.runtime_fft_bridge import POWER_MAX, collapse_runtime_cells

ROOT = Path(__file__).resolve().parents[1]


def test_reference_collapses_all_supported_lengths_and_saturates() -> None:
    for count in (4096, 8192, 16384):
        factor = count // 4096
        power, decisions = collapse_runtime_cells(
            [index % 101 + 1 for index in range(count)],
            [2 if index % 257 == 0 else 0 for index in range(count)],
        )
        assert len(power) == len(decisions) == 4096
        assert power[0] == sum(range(1, factor + 1))
        assert decisions[0] == 2
    power, _ = collapse_runtime_cells([POWER_MAX] * 8192, [0] * 8192)
    assert power == [POWER_MAX] * 4096


def test_arm_bridge_matches_reference(tmp_path: Path) -> None:
    compiler = shutil.which("gcc") or shutil.which("clang")
    prefix: list[str] = []
    if compiler is None and os.name == "nt":
        prefix = ["wsl.exe"]
        compiler = "gcc"
        executable: str | Path = "/tmp/p0_runtime_fft_bridge_test"
    else:
        assert compiler is not None
        executable = tmp_path / ("bridge.exe" if Path(compiler).suffix.lower() == ".exe" else "bridge")
    build = subprocess.run(
        [*prefix, compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-Iplatforms/embedded/p0/include", "platforms/embedded/p0/src/p0_runtime_fft_bridge.c",
         "tests/p0/p0_runtime_fft_bridge_run.c", "-o", str(executable)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([*prefix, str(executable)], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_FFT_BRIDGE_PASS" in run.stdout


def test_arm_runtime_decoder_validates_and_collapses(tmp_path: Path) -> None:
    prefix = ["wsl.exe"] if os.name == "nt" else []
    compiler = "gcc" if prefix else (shutil.which("gcc") or shutil.which("clang"))
    assert compiler is not None
    executable = "/tmp/p0_runtime_fft_decode_test" if prefix else str(tmp_path / "decode")
    build = subprocess.run(
        [*prefix, compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-Iplatforms/embedded/p0/include", "platforms/embedded/p0/src/p0_pl_os_cfar.c",
         "tests/p0/p0_runtime_fft_decode_run.c", "-o", executable],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([*prefix, executable], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_FFT_DECODE_PASS" in run.stdout
