from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess

from algorithms.p0 import decode_df_response, encode_df_request
from scripts.verify_phase09_amplitude_df_arm import _cases

ROOT = Path(__file__).resolve().parents[1]


def _wsl_path(path: Path) -> str:
    resolved = str(path.resolve())
    return f"/mnt/{resolved[0].lower()}/{resolved[3:].replace(chr(92), '/')}"


def _build(tmp_path: Path) -> tuple[list[str], str]:
    prefix = ["wsl.exe"] if os.name == "nt" else []
    executable = "/tmp/p0-df-protocol-run" if prefix else str(tmp_path / "p0-df-protocol-run")
    build = subprocess.run(
        [*prefix, "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-Iplatforms/embedded/p0/include", "-Iplatforms/embedded/phase06i/include",
         "-Iplatforms/embedded/phase06j/include",
         "platforms/embedded/p0/src/p0_amplitude_df.c",
         "platforms/embedded/p0/src/p0_ed_service_protocol.c",
         "tests/p0/p0_df_protocol_run.c", "-lm", "-o", executable],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    return prefix, executable


def test_direction_batch_round_trip_through_c_arm_protocol(tmp_path: Path) -> None:
    prefix, executable = _build(tmp_path)
    measurements = tuple(_cases()["lob-ready"])
    token = 0x12345678
    request = encode_df_request(measurements, token)
    request_path = tmp_path / "request.bin"
    response_path = tmp_path / "response.bin"
    request_path.write_bytes(request)
    if prefix:
        request_arg = _wsl_path(request_path)
        response_arg = _wsl_path(response_path)
    else:
        request_arg, response_arg = str(request_path), str(response_path)
    run = subprocess.run([*prefix, executable, request_arg, response_arg], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "P0_DF_PROTOCOL=PASS" in run.stdout
    estimate = decode_df_response(response_path.read_bytes(), token).estimate
    assert estimate.status == "LOB HAZIR"
    assert estimate.estimated_angle_deg == 45.0
    assert estimate.distinct_angle_count == 24
    assert math.isclose(estimate.angular_sampling_rms_deg or 0.0,
                        15.0 / math.sqrt(12.0), rel_tol=0.0, abs_tol=1.0e-12)


def test_direction_request_crc_corruption_is_rejected(tmp_path: Path) -> None:
    prefix, executable = _build(tmp_path)
    request = bytearray(encode_df_request(tuple(_cases()["lob-ready"]), 17))
    request[55] ^= 1
    request_path = tmp_path / "bad.bin"
    response_path = tmp_path / "bad-response.bin"
    request_path.write_bytes(request)
    if prefix:
        request_arg = _wsl_path(request_path)
        response_arg = _wsl_path(response_path)
    else:
        request_arg, response_arg = str(request_path), str(response_path)
    run = subprocess.run([*prefix, executable, request_arg, response_arg], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 3
    assert not response_path.exists()
