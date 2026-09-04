from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from app.operator_console.integrated_spectrum import integrated_spectrum_candidates


ROOT = Path(__file__).resolve().parents[2]


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/" + "/".join(resolved.parts[1:])


def test_portable_c_matches_python_multiframe_candidate_fields(tmp_path):
    if shutil.which("wsl.exe") is None:
        pytest.skip("Portable C eşdeğerliği için WSL bulunamadı.")
    rng = np.random.default_rng(4040)
    frame_count = 96
    bin_count = 4096
    sample_rate_hz = 2_000_000.0
    frequencies = np.arange(bin_count, dtype=np.float64) * sample_rate_hz / bin_count
    power = rng.exponential(1.0, size=(frame_count, bin_count)).astype("<f8")
    for offset, added in [(-24, 12.0), (-22, 2.0), (-20, 2.0), (-18, 2.0),
                          (-16, 2.0), (-14, 2.0), (-12, 2.0), (-10, 2.0),
                          (-8, 2.0), (-6, 2.0), (-4, 2.0), (-2, 2.0),
                          (0, 2.0), (2, 2.0), (4, 2.0), (6, 2.0),
                          (8, 2.0), (10, 2.0), (12, 2.0), (14, 2.0),
                          (16, 2.0), (18, 2.0), (20, 2.0), (22, 2.0),
                          (24, 12.0)]:
        power[:, 2300 + offset] += added
    power[:, 2700] += 11.0

    expected = integrated_spectrum_candidates(
        frequencies, power, lower_hz=300_000.0, upper_hz=1_600_000.0
    )
    input_path = tmp_path / "power.f64"
    power.tofile(input_path)
    executable = tmp_path / "p0-multiframe-narrowband-run"
    include = ROOT / "platforms/embedded/p0/include"
    source = ROOT / "platforms/embedded/p0/src/p0_multiframe_narrowband.c"
    runner = ROOT / "platforms/embedded/p0/src/p0_multiframe_narrowband_run.c"
    subprocess.run([
        "wsl.exe", "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", _wsl_path(include), _wsl_path(source), _wsl_path(runner), "-lm",
        "-o", _wsl_path(executable),
    ], check=True)
    completed = subprocess.run([
        "wsl.exe", _wsl_path(executable), _wsl_path(input_path), str(frame_count),
        str(bin_count), str(sample_rate_hz), "615", "3276",
    ], check=True, capture_output=True, text=True)
    actual = [line.split(",") for line in completed.stdout.splitlines() if line]

    assert len(actual) == len(expected)
    spacing = sample_rate_hz / bin_count
    for row, reference in zip(actual, expected):
        center_bin, peak_bin, lower_bin, upper_bin, pnr, observed, total, components = row
        assert float(center_bin) == pytest.approx(reference.frequency_hz / spacing, abs=1e-8)
        assert int(peak_bin) == round(reference.peak_frequency_hz / spacing)
        assert int(lower_bin) == round(reference.lower_frequency_hz / spacing + 0.5)
        assert int(upper_bin) == round(reference.upper_frequency_hz / spacing - 0.5)
        assert float(pnr) == pytest.approx(reference.peak_to_noise_db, abs=1e-9)
        assert int(observed) == reference.observed_frames
        assert int(total) == reference.total_frames
        assert int(components) == reference.component_count


def test_petalinux_recipe_builds_and_installs_arm_diagnostic():
    recipe = (ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb").read_text(
        encoding="utf-8"
    )

    for name in (
        "p0_multiframe_narrowband.c",
        "p0_multiframe_narrowband.h",
        "p0_multiframe_narrowband_run.c",
    ):
        assert f"file://{name}" in recipe
    assert "-o ${S}/p0-multiframe-narrowband-run" in recipe
    assert "install -m 0755 ${S}/p0-multiframe-narrowband-run" in recipe
    assert "${bindir}/p0-multiframe-narrowband-run" in recipe
