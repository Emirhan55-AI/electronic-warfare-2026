import struct
from pathlib import Path
import os
import subprocess
import zlib

from algorithms.p0.detection_config import (
    DetectionProfile,
    decode_response,
    encode_request,
)

MESSAGE = struct.Struct("<4sHHIIIIQQII")
ROOT = Path(__file__).resolve().parents[1]


def response(version: int, operation: int, token: int, profile: DetectionProfile) -> bytes:
    payload = MESSAGE.pack(
        b"P0DR", version, 48, operation, token, 0, profile.generation,
        profile.alpha_q32, profile.weak_alpha_q32,
        profile.fft_size if version == 2 else 0, 0,
    )
    return payload[:44] + struct.pack("<I", zlib.crc32(payload[:44]))


def test_v2_profile_carries_fft_size_and_verified_readback() -> None:
    profile = DetectionProfile(7, 36_851_433_755, 17_098_572_778, 16384, True)
    request = encode_request(2, 99, profile, protocol_version=2)
    fields = MESSAGE.unpack(request)
    assert fields[1] == 2
    assert fields[9] == 16384
    assert fields[10] == zlib.crc32(request[:44])
    assert decode_response(response(2, 2, 99, profile), 2, 99,
                           protocol_version=2) == profile


def test_v1_profile_remains_fixed_4096() -> None:
    profile = DetectionProfile(3, 36_851_433_755, 17_098_572_778)
    request = encode_request(2, 5, profile)
    assert MESSAGE.unpack(request)[1] == 1
    assert MESSAGE.unpack(request)[9] == 0
    assert decode_response(response(1, 2, 5, profile), 2, 5) == profile


def test_c_service_protocol_v1_v2_roundtrip(tmp_path: Path) -> None:
    prefix = ["wsl.exe"] if os.name == "nt" else []
    executable = "/tmp/p0_detection_profile_protocol_test" if prefix else str(tmp_path / "profile")
    build = subprocess.run(
        [*prefix, "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-Iplatforms/embedded/p0/include", "-Iplatforms/embedded/phase06j/include",
         "-Iplatforms/embedded/phase06i/include",
         "platforms/embedded/p0/src/p0_ed_service_protocol.c",
         "tests/p0/p0_detection_profile_protocol_run.c", "-lm", "-o", executable],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([*prefix, executable], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "DETECTION_PROFILE_PROTOCOL_PASS" in run.stdout
