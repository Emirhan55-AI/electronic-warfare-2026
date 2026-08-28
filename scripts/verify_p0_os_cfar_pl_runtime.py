#!/usr/bin/env python3
"""Verify PL-tagged OS-CFAR DMA decoding and the reduced PS processing path."""

from __future__ import annotations

import argparse
import _ctypes
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.detection import P0_DETECTOR_PROFILE
from algorithms.rtl.p0_os_cfar import detect_frame
from algorithms.rtl.p0_os_cfar_vectors import p0_os_cfar_vectors


EVIDENCE = ROOT / "results/evidence/p0/os-cfar-pl-runtime-integration.json"
FRAME_LENGTH = 4096
CANDIDATE_CAPACITY = 1352


class CConfig(ctypes.Structure):
    _fields_ = [
        ("reference", ctypes.c_uint32),
        ("guard", ctypes.c_uint32),
        ("rank", ctypes.c_uint32),
        ("coefficient", ctypes.c_double),
        ("gap", ctypes.c_uint32),
    ]


class CCandidate(ctypes.Structure):
    _fields_ = [
        ("start", ctypes.c_uint32),
        ("end", ctypes.c_uint32),
        ("peak", ctypes.c_uint32),
        ("peak_power", ctypes.c_double),
        ("noise", ctypes.c_double),
        ("threshold", ctypes.c_double),
    ]


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _msvc() -> tuple[Path, Path] | None:
    finder = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not finder.is_file():
        return None
    query = subprocess.run(
        [
            str(finder),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if query.returncode or not query.stdout.strip():
        return None
    root = Path(query.stdout.strip())
    vcvars = root / "VC/Auxiliary/Build/vcvars64.bat"
    compilers = sorted((root / "VC/Tools/MSVC").glob("*/bin/Hostx64/x64/cl.exe"), reverse=True)
    return (vcvars, compilers[0]) if vcvars.is_file() and compilers else None


def _compile(directory: Path) -> tuple[Path, str]:
    include = ROOT / "platforms/embedded/p0/include"
    sources = (
        ROOT / "platforms/embedded/p0/src/p0_os_cfar.c",
        ROOT / "platforms/embedded/p0/src/p0_multiscale_detector.c",
        ROOT / "platforms/embedded/p0/src/p0_pl_os_cfar.c",
    )
    if (msvc := _msvc()) is not None:
        vcvars, _ = msvc
        output = directory / "p0_pl_os_cfar.dll"
        source_args = " ".join(f'"{source}"' for source in sources)
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX /LD '
            f'/I"{include}" {source_args} /link /OUT:"{output}"'
        )
        subprocess.run(command, check=True, cwd=directory, shell=True)
        return output, "MSVC C11"
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        raise FileNotFoundError("C11 host compiler is unavailable")
    output = directory / ("p0_pl_os_cfar.dll" if os.name == "nt" else "libp0_pl_os_cfar.so")
    subprocess.run(
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
            *(str(source) for source in sources),
            "-lm",
            "-o",
            str(output),
        ],
        check=True,
    )
    return output, Path(compiler).name


def _candidate_tuple(candidate: CCandidate) -> tuple[int, int, int, float, float, float]:
    return (
        candidate.start,
        candidate.end,
        candidate.peak,
        candidate.peak_power,
        candidate.noise,
        candidate.threshold,
    )


def _word_payload(words: tuple[int, ...]) -> bytes:
    return b"".join(word.to_bytes(8, "little") for word in words)


def evaluate() -> dict[str, object]:
    config = CConfig(
        P0_DETECTOR_PROFILE.reference_cells_per_side,
        P0_DETECTOR_PROFILE.guard_cells_per_side,
        P0_DETECTOR_PROFILE.order_statistic_rank,
        P0_DETECTOR_PROFILE.threshold_coefficient,
        P0_DETECTOR_PROFILE.maximum_gap_bins,
    )
    decode_mismatches = 0
    candidate_mismatches = 0
    recovery_mismatches = 0
    malformed_rejections = 0
    compiler = ""
    with tempfile.TemporaryDirectory(prefix="p0-pl-os-cfar-runtime-") as raw:
        library_path, compiler = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        decode = library.p0_pl_os_cfar_decode
        decode.restype = ctypes.c_int
        process = library.p0_multiscale_process
        process.restype = ctypes.c_int
        process_pl = library.p0_multiscale_process_pl
        process_pl.restype = ctypes.c_int

        first_payload: bytes | None = None
        for vector in p0_os_cfar_vectors():
            fixed = detect_frame(vector.natural_power)
            payload = _word_payload(fixed.dma_words_natural)
            if first_payload is None:
                first_payload = payload
            raw_frame = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
            shifted_raw = (ctypes.c_uint64 * FRAME_LENGTH)()
            shifted_power = (ctypes.c_double * FRAME_LENGTH)()
            decoded_detections = (ctypes.c_uint8 * FRAME_LENGTH)()
            decisions_present = ctypes.c_int()
            decode_status = decode(
                raw_frame,
                len(payload),
                shifted_raw,
                shifted_power,
                decoded_detections,
                ctypes.byref(decisions_present),
            )
            expected_shifted = tuple(vector.natural_power[index ^ 0x800] for index in range(FRAME_LENGTH))
            decode_mismatches += int(
                decode_status != 0
                or decisions_present.value != 1
                or tuple(shifted_raw) != expected_shifted
                or tuple(decoded_detections) != tuple(map(int, fixed.detected_shifted))
            )

            reference_detections = (ctypes.c_uint8 * FRAME_LENGTH)()
            reference_noise = (ctypes.c_double * FRAME_LENGTH)()
            reference_threshold = (ctypes.c_double * FRAME_LENGTH)()
            reference_candidates = (CCandidate * CANDIDATE_CAPACITY)()
            reference_count = ctypes.c_size_t()
            reference_recoveries = ctypes.c_size_t()
            reference_status = process(
                shifted_power,
                FRAME_LENGTH,
                ctypes.byref(config),
                reference_detections,
                reference_noise,
                reference_threshold,
                reference_candidates,
                CANDIDATE_CAPACITY,
                ctypes.byref(reference_count),
                ctypes.byref(reference_recoveries),
            )

            pl_detections = (ctypes.c_uint8 * FRAME_LENGTH)(*tuple(decoded_detections))
            pl_noise = (ctypes.c_double * FRAME_LENGTH)()
            pl_threshold = (ctypes.c_double * FRAME_LENGTH)()
            pl_candidates = (CCandidate * CANDIDATE_CAPACITY)()
            pl_count = ctypes.c_size_t()
            pl_recoveries = ctypes.c_size_t()
            pl_status = process_pl(
                shifted_power,
                FRAME_LENGTH,
                ctypes.byref(config),
                pl_detections,
                pl_noise,
                pl_threshold,
                pl_candidates,
                CANDIDATE_CAPACITY,
                ctypes.byref(pl_count),
                ctypes.byref(pl_recoveries),
            )
            reference_rows = [_candidate_tuple(reference_candidates[index]) for index in range(reference_count.value)]
            pl_rows = [_candidate_tuple(pl_candidates[index]) for index in range(pl_count.value)]
            candidate_mismatches += int(
                reference_status != 0
                or pl_status != 0
                or reference_count.value != pl_count.value
                or reference_rows != pl_rows
            )
            recovery_mismatches += int(reference_recoveries.value != pl_recoveries.value)

        assert first_payload is not None
        malformed = []
        mixed = bytearray(first_payload)
        mixed[7] &= 0x0F
        malformed.append(mixed)
        missing_evaluated = bytearray(first_payload)
        word = int.from_bytes(missing_evaluated[0:8], "little") & ~(1 << 58)
        missing_evaluated[0:8] = word.to_bytes(8, "little")
        malformed.append(missing_evaluated)
        detected_outside = bytearray(first_payload)
        natural_edge = 2048
        offset = natural_edge * 8
        word = int.from_bytes(detected_outside[offset : offset + 8], "little") | (1 << 59)
        detected_outside[offset : offset + 8] = word.to_bytes(8, "little")
        malformed.append(detected_outside)
        for payload in malformed:
            raw_frame = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
            shifted_raw = (ctypes.c_uint64 * FRAME_LENGTH)()
            shifted_power = (ctypes.c_double * FRAME_LENGTH)()
            decoded_detections = (ctypes.c_uint8 * FRAME_LENGTH)()
            decisions_present = ctypes.c_int()
            malformed_rejections += int(
                decode(
                    raw_frame,
                    len(payload),
                    shifted_raw,
                    shifted_power,
                    decoded_detections,
                    ctypes.byref(decisions_present),
                )
                == -2
            )

        legacy_words = tuple(word & ((1 << 58) - 1) for word in detect_frame([0] * FRAME_LENGTH).dma_words_natural)
        legacy_payload = _word_payload(legacy_words)
        raw_frame = (ctypes.c_uint8 * len(legacy_payload)).from_buffer_copy(legacy_payload)
        shifted_raw = (ctypes.c_uint64 * FRAME_LENGTH)()
        shifted_power = (ctypes.c_double * FRAME_LENGTH)()
        decoded_detections = (ctypes.c_uint8 * FRAME_LENGTH)()
        decisions_present = ctypes.c_int(-1)
        legacy_status = decode(
            raw_frame,
            len(legacy_payload),
            shifted_raw,
            shifted_power,
            decoded_detections,
            ctypes.byref(decisions_present),
        )
        legacy_compatibility = legacy_status == 0 and decisions_present.value == 0 and not any(decoded_detections)

        handle = library._handle
        del decode
        del process
        del process_pl
        del library
        if os.name == "nt":
            _ctypes.FreeLibrary(handle)

    passed = (
        decode_mismatches == 0
        and candidate_mismatches == 0
        and recovery_mismatches == 0
        and malformed_rejections == 3
        and legacy_compatibility
    )
    sources = (
        "platforms/embedded/p0/include/p0_pl_os_cfar.h",
        "platforms/embedded/p0/src/p0_pl_os_cfar.c",
        "platforms/embedded/p0/include/p0_os_cfar.h",
        "platforms/embedded/p0/src/p0_os_cfar.c",
        "platforms/embedded/p0/include/p0_multiscale_detector.h",
        "platforms/embedded/p0/src/p0_multiscale_detector.c",
        "platforms/embedded/p0/src/p0_ed_pipeline.c",
        "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
        "scripts/verify_p0_os_cfar_pl_runtime.py",
        "tests/p0/test_p0_os_cfar_pl_runtime.py",
    )
    return {
        "status": "passed" if passed else "failed",
        "compiler": compiler,
        "frames": len(p0_os_cfar_vectors()),
        "dma_words": len(p0_os_cfar_vectors()) * FRAME_LENGTH,
        "decode_mismatches": decode_mismatches,
        "combined_candidate_mismatches": candidate_mismatches,
        "recovery_count_mismatches": recovery_mismatches,
        "malformed_frames_rejected": malformed_rejections,
        "legacy_power_only_frame_compatibility": "passed" if legacy_compatibility else "failed",
        "runtime_path": {
            "pl_owned": "OS-CFAR cell decisions",
            "ps_owned": "candidate grouping, wideband recovery, temporal confirmation and parameters",
            "full_frame_marker_validation": "required before PL decisions are used",
            "mixed_or_malformed_frame_policy": "reject without temporal-state advancement",
        },
        "claim_limit": "host C integration; PetaLinux ARM and physical FPGA are not exercised",
        "sources": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sources
        },
    }


def write() -> None:
    document = evaluate()
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_bytes(canonical_bytes(document))
    print("P0 PL OS-CFAR çalışma zamanı entegrasyon kanıtı yazıldı.")


def check() -> bool:
    try:
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        expected_sources = evaluate_source_hashes(stored.get("sources", {}))
        return stored.get("status") == "passed" and expected_sources
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def evaluate_source_hashes(stored: object) -> bool:
    if not isinstance(stored, dict):
        return False
    return all(
        isinstance(name, str)
        and isinstance(digest, str)
        and (ROOT / name).is_file()
        and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        for name, digest in stored.items()
    ) and bool(stored)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"P0 PL OS-CFAR çalışma zamanı entegrasyonu: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
