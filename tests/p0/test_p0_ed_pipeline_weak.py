from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from algorithms.ps.candidate_transport import encode_packet
from algorithms.rtl.candidate_grouping import CandidateRecord


ROOT = Path(__file__).resolve().parents[2]
P0 = ROOT / "platforms/embedded/p0"
P06I = ROOT / "platforms/embedded/phase06i"
P06J = ROOT / "platforms/embedded/phase06j"


def _compiler() -> tuple[str, bool] | None:
    found = shutil.which("gcc") or shutil.which("cc")
    if found:
        return found, False
    fallback = Path("C:/msys64/ucrt64/bin/gcc.exe")
    if fallback.exists():
        return str(fallback), False
    if shutil.which("wsl.exe"):
        return "gcc", True
    return None


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/" + "/".join(resolved.parts[1:])


def _candidate(
    *, strong: bool = False, peak: int = 2300, peak_to_noise: int = 5
) -> CandidateRecord:
    noise = 1 << 30
    return CandidateRecord(
        start_shifted_bin=peak,
        end_shifted_bin=peak,
        peak_shifted_bin=peak,
        peak_power=peak_to_noise * noise,
        regional_noise=noise,
        threshold=4 * noise,
        pfa_select=1,
        evaluate_center=False,
        weak_evidence=True,
        single_frame_confident=strong,
    )


def _compile(output: Path) -> bool:
    selected = _compiler()
    if selected is None:
        pytest.skip("C11 derleyicisi bulunamadı.")
    compiler, using_wsl = selected
    sources = [
        ROOT / "tests/p0/p0_ed_pipeline_weak_run.c",
        P0 / "src/p0_ed_pipeline.c",
        P0 / "src/p0_parameter_runtime.c",
        P0 / "src/p0_os_cfar.c",
        P0 / "src/p0_pl_os_cfar.c",
        P0 / "src/p0_multiscale_detector.c",
        P0 / "src/p0_candidate_packet.c",
        P0 / "src/p0_persistent_weak.c",
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
            "-I", str(P0 / "include"),
            "-I", str(P06I / "include"),
            "-I", str(P06J / "include"),
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
                _wsl_path(Path(value[2:])) if value.startswith("-IC:") else value
                for value in command[1:]
            ),
        ]
        for index, value in enumerate(command):
            if index != 0 and value.startswith("C:\\"):
                command[index] = _wsl_path(Path(value))
    subprocess.run(
        command,
        check=True,
        cwd=ROOT,
    )
    return using_wsl


def _run(tmp_path: Path, packets: list[bytes]) -> list[list[int]]:
    executable = tmp_path / "p0_ed_pipeline_weak_run"
    using_wsl = _compile(executable)
    stream = tmp_path / "packets.bin"
    stream.write_bytes(
        b"".join(struct.pack("<I", len(packet)) + packet for packet in packets)
    )
    completed = subprocess.run(
        ["wsl.exe", _wsl_path(executable), _wsl_path(stream)]
        if using_wsl else [str(executable), str(stream)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return [[int(value) for value in line.split(",")] for line in completed.stdout.splitlines()]


def test_weak_packet_path_requires_24_of_32_and_emits_end(tmp_path: Path) -> None:
    packets = [encode_packet(frame, [_candidate()]) for frame in range(32)]
    packets.extend(encode_packet(frame, []) for frame in range(32, 41))
    rows = _run(tmp_path, packets)

    assert all(row[2] == 0 for row in rows[:31])
    assert rows[31][2:11] == [1, 0, 0, 2, 0x05, 2300, 0, 0, 0]
    assert all(row[2] == 1 for row in rows[32:40])
    assert rows[40][2:11] == [0, 1, 0, 0, 0, 0, 3, 2300, 0]


def test_frame_gap_resets_weak_occupancy(tmp_path: Path) -> None:
    packets = [encode_packet(frame, [_candidate()]) for frame in range(23)]
    packets.append(encode_packet(24, [_candidate()]))
    packets.extend(encode_packet(frame, [_candidate()]) for frame in range(25, 56))
    rows = _run(tmp_path, packets)

    assert rows[23][4] == 1
    assert all(row[2] == 0 for row in rows[:54])
    assert rows[54][2] == 1


def test_single_frame_confident_candidate_keeps_normal_two_of_three_path(
    tmp_path: Path,
) -> None:
    rows = _run(
        tmp_path,
        [encode_packet(frame, [_candidate(strong=True)]) for frame in range(2)],
    )

    assert rows[0][2] == 1 and rows[0][5] == 1
    assert rows[1][2] == 1 and rows[1][5] == 2
    assert rows[1][6] == 0x0D


def test_persistent_weak_output_is_ranked_and_bounded_below_event_capacity(
    tmp_path: Path,
) -> None:
    strong = [_candidate(strong=True, peak=100 + index * 3) for index in range(50)]
    weak = [
        _candidate(peak=1000 + index * 10, peak_to_noise=index + 4)
        for index in range(54)
    ]
    packets = [encode_packet(frame, [*strong, *weak]) for frame in range(32)]

    rows = _run(tmp_path, packets)

    assert all(row[2] == 50 for row in rows[:31])
    assert rows[31][1] == 104
    assert rows[31][2] == 58
    assert rows[31][10] == 0
    assert rows[31][11] == 1460
