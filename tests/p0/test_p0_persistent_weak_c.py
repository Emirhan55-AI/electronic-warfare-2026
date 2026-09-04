from pathlib import Path
import shutil
import subprocess

import pytest

from algorithms.ps.persistent_weak_cfar import (
    PERSISTENCE_WINDOW,
    PersistentWeakTracker,
    WeakNomination,
)


ROOT = Path(__file__).resolve().parents[2]


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/" + "/".join(resolved.parts[1:])


def test_portable_arm_c_tracker_matches_python_target_model(tmp_path: Path) -> None:
    if shutil.which("wsl.exe") is None:
        pytest.skip("Portable C eşdeğerliği için WSL bulunamadı.")
    frames: list[tuple[WeakNomination, ...]] = []
    tracker = PersistentWeakTracker()
    expected = ()
    for frame in range(PERSISTENCE_WINDOW):
        rows = []
        if frame not in {4, 11, 19, 27}:
            peak = 1700 + (frame % 3) - 1
            rows.append(WeakNomination(peak, peak, peak, 5 << 30, 1 << 30))
        rows.append(WeakNomination(2600, 2600, 2600, 4 << 30, 1 << 30))
        frame_rows = tuple(rows)
        frames.append(frame_rows)
        expected = tracker.update(frame_rows)

    executable = tmp_path / "p0-persistent-weak-run"
    include = ROOT / "platforms/embedded/p0/include"
    source = ROOT / "platforms/embedded/p0/src/p0_persistent_weak.c"
    runner = ROOT / "platforms/embedded/p0/src/p0_persistent_weak_run.c"
    subprocess.run([
        "wsl.exe", "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", _wsl_path(include), _wsl_path(source), _wsl_path(runner),
        "-o", _wsl_path(executable),
    ], check=True)
    lines = [str(len(frames))]
    for rows in frames:
        lines.append(str(len(rows)))
        lines.extend(
            f"{row.start_shifted_bin} {row.end_shifted_bin} {row.peak_shifted_bin} "
            f"{row.peak_power} {row.order_statistic}"
            for row in rows
        )
    completed = subprocess.run(
        ["wsl.exe", _wsl_path(executable)], input="\n".join(lines) + "\n",
        check=True, capture_output=True, text=True,
    )
    actual = [tuple(map(int, line.split(","))) for line in completed.stdout.splitlines()]
    reference = [(
        row.start_shifted_bin, row.end_shifted_bin, row.peak_shifted_bin,
        row.observed_frames, row.total_frames,
        round((10 ** (row.mean_peak_to_os_db / 10.0)) * 256),
    ) for row in expected]
    assert actual == reference


def test_petalinux_recipe_builds_the_arm_target_model() -> None:
    recipe = (ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb").read_text(
        encoding="utf-8"
    )
    for name in (
        "p0_persistent_weak.c",
        "p0_persistent_weak.h",
        "p0_persistent_weak_run.c",
    ):
        assert f"file://{name}" in recipe
    assert "-o ${S}/p0-persistent-weak-run" in recipe
    assert "install -m 0755 ${S}/p0-persistent-weak-run" in recipe
