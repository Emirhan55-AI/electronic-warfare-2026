#!/usr/bin/env python3
"""Verify the locked P0 OS-CFAR plus qualified regional recovery profile."""

from __future__ import annotations

import argparse
import _ctypes
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.detection.scenes import generate_scene, generate_temporal_frame, load_scene_catalog
from algorithms.p0 import (
    MultiscaleDetector,
    P0_DETECTOR_PROFILE,
    P0_WIDEBAND_RECOVERY_PROFILE,
    TemporalConfirmation,
)
from algorithms.spectrum import SpectrumProcessor
from scripts.verify_p0_detector_profile import evaluate as evaluate_os_profile


EVIDENCE_PATH = ROOT / "results/evidence/p0/multiscale-detector-host-acceptance.json"
WIDEBAND_TRIALS = 256
TEMPORAL_SEQUENCES = 128


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


def _spectrum(samples: np.ndarray, catalog: dict[str, object]) -> np.ndarray:
    common = catalog["common"]
    result = SpectrumProcessor().process(
        samples,
        sample_rate_hz=float(common["sample_rate_hz"]),
        center_frequency_hz=float(common["center_frequency_hz"]),
    )
    return result.display.bin_power_fs2


def _metrics(candidates: tuple[object, ...], start: int, end: int) -> tuple[float, float, float]:
    predicted = np.zeros(4096, dtype=np.bool_)
    truth = np.zeros(4096, dtype=np.bool_)
    for candidate in candidates:
        predicted[candidate.start_bin : candidate.end_bin + 1] = True
    truth[start : end + 1] = True
    intersection = int(np.count_nonzero(predicted & truth))
    union = int(np.count_nonzero(predicted | truth))
    predicted_count = int(np.count_nonzero(predicted))
    return (
        intersection / (end - start + 1),
        intersection / union if union else 0.0,
        int(np.count_nonzero(predicted & ~truth)) / predicted_count if predicted_count else 1.0,
    )


def _wideband_gate(catalog: dict[str, object]) -> tuple[dict[str, object], list[np.ndarray]]:
    detector = MultiscaleDetector()
    metrics: list[tuple[float, float, float]] = []
    frames: list[np.ndarray] = []
    recovery_counts: list[int] = []
    candidate_counts: list[int] = []
    successful = 0
    for trial_index in range(WIDEBAND_TRIALS):
        frame = generate_scene("wideband-noise-like", trial_index=trial_index, catalog=catalog)
        power = _spectrum(frame.samples, catalog)
        result = detector.process(power, frame_id=trial_index)
        truth = frame.ground_truth[0]
        values = _metrics(
            result.candidates,
            int(truth["shifted_start_bin"]),
            int(truth["shifted_end_bin"]),
        )
        successful += int(values[0] >= 0.60 and values[1] >= 0.50 and values[2] <= 0.25)
        metrics.append(values)
        recovery_counts.append(len(result.recovery_candidates))
        candidate_counts.append(len(result.candidates))
        if trial_index < 32:
            frames.append(np.ascontiguousarray(power, dtype=np.float64))
    rate = successful / WIDEBAND_TRIALS
    payload = {
        "status": "passed" if rate >= 0.90 else "failed",
        "trials": WIDEBAND_TRIALS,
        "successful_frames": successful,
        "successful_frame_rate": rate,
        "minimum_coverage": 0.60,
        "minimum_iou": 0.50,
        "maximum_overreach": 0.25,
        "mean_coverage": float(np.mean([item[0] for item in metrics])),
        "mean_iou": float(np.mean([item[1] for item in metrics])),
        "mean_overreach": float(np.mean([item[2] for item in metrics])),
        "minimum_recovery_candidates": min(recovery_counts),
        "maximum_recovery_candidates": max(recovery_counts),
        "maximum_combined_candidates": max(candidate_counts),
    }
    return payload, frames


def _regional_addition_gate(catalog: dict[str, object]) -> tuple[dict[str, object], list[np.ndarray]]:
    detector = MultiscaleDetector()
    records: list[dict[str, object]] = []
    parity_frames: list[np.ndarray] = []
    scene_counts = (
        ("awgn-low", 1024),
        ("awgn-medium", 4096),
        ("awgn-high", 1024),
        ("sloped-noise", 512),
        ("stepped-noise", 512),
    )
    for scene_id, count in scene_counts:
        additions = 0
        for trial_index in range(count):
            frame = generate_scene(scene_id, trial_index=trial_index, catalog=catalog)
            power = _spectrum(frame.samples, catalog)
            additions += len(detector.recovery_candidates(power))
            if scene_id == "awgn-medium" and trial_index < 32:
                parity_frames.append(np.ascontiguousarray(power, dtype=np.float64))
        records.append({"scene": scene_id, "frames": count, "recovery_candidates": additions})

    local_additions = 0
    local_frames = 0
    for scene_id in ("tone-bin-centered", "tone-off-bin"):
        for condition_index in range(5):
            for trial_index in range(256):
                frame = generate_scene(
                    scene_id,
                    trial_index=trial_index,
                    condition_index=condition_index,
                    catalog=catalog,
                )
                local_additions += len(detector.recovery_candidates(_spectrum(frame.samples, catalog)))
                local_frames += 1
    for scene_id in ("two-equal-tones", "two-unequal-tones"):
        for trial_index in range(256):
            frame = generate_scene(scene_id, trial_index=trial_index, catalog=catalog)
            local_additions += len(detector.recovery_candidates(_spectrum(frame.samples, catalog)))
            local_frames += 1
    for scene_id in ("center-tone", "first-valid-edge-tone", "unevaluated-edge-tone"):
        for trial_index in range(128):
            frame = generate_scene(scene_id, trial_index=trial_index, catalog=catalog)
            local_additions += len(detector.recovery_candidates(_spectrum(frame.samples, catalog)))
            local_frames += 1
    for scene_id, frame_count in (("transient-tone", 5), ("persistent-tone", 7)):
        for sequence_index in range(TEMPORAL_SEQUENCES):
            for frame_index in range(frame_count):
                frame = generate_temporal_frame(
                    scene_id,
                    sequence_index=sequence_index,
                    frame_index=frame_index,
                    catalog=catalog,
                )
                local_additions += len(detector.recovery_candidates(_spectrum(frame.samples, catalog)))
                local_frames += 1
    all_zero = all(record["recovery_candidates"] == 0 for record in records) and local_additions == 0
    return {
        "status": "passed" if all_zero else "failed",
        "noise_records": records,
        "local_signal_frames": local_frames,
        "local_signal_recovery_candidates": local_additions,
        "acceptance": "no added >=41-bin recovery candidate",
    }, parity_frames


def _wideband_temporal_gate(catalog: dict[str, object]) -> dict[str, object]:
    detector = MultiscaleDetector()
    passed = 0
    for sequence_index in range(TEMPORAL_SEQUENCES):
        temporal = TemporalConfirmation()
        valid = True
        for frame_index in range(4):
            trial_index = sequence_index * 4 + frame_index
            frame = generate_scene("wideband-noise-like", trial_index=trial_index, catalog=catalog)
            truth = frame.ground_truth[0]
            start = int(truth["shifted_start_bin"])
            end = int(truth["shifted_end_bin"])
            detection = detector.process(_spectrum(frame.samples, catalog), frame_id=frame_index)
            tracked = temporal.update(detection.candidates, frame_id=frame_index)
            if frame_index >= 1:
                owners = [
                    item for item in tracked
                    if item.state == "confirmed"
                    and item.observed_this_frame
                    and item.candidate.start_bin <= end
                    and item.candidate.end_bin >= start
                ]
                valid = valid and len(owners) == 1
        passed += int(valid)
    rate = passed / TEMPORAL_SEQUENCES
    return {
        "status": "passed" if rate >= 0.99 else "failed",
        "sequences": TEMPORAL_SEQUENCES,
        "four_frame_single_owner_sequences": passed,
        "success_rate": rate,
        "minimum_rate": 0.99,
    }


def _msvc() -> tuple[Path, Path] | None:
    finder = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not finder.is_file():
        return None
    query = subprocess.run(
        [str(finder), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        capture_output=True, text=True, encoding="utf-8", check=False,
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
    )
    if (msvc := _msvc()) is not None:
        vcvars, _ = msvc
        output = directory / "p0_multiscale_detector.dll"
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
    output = directory / ("p0_multiscale_detector.dll" if os.name == "nt" else "libp0_multiscale_detector.so")
    subprocess.run(
        [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
         f"-I{include}", *(str(source) for source in sources), "-lm", "-o", str(output)],
        check=True,
    )
    return output, Path(compiler).name


def _c_python_gate(frames: list[np.ndarray]) -> dict[str, object]:
    detector = MultiscaleDetector()
    mismatches = 0
    with tempfile.TemporaryDirectory(prefix="p0-multiscale-") as raw:
        library_path, compiler = _compile(Path(raw))
        library = ctypes.CDLL(str(library_path))
        function = library.p0_multiscale_process
        function.restype = ctypes.c_int
        config = CConfig(
            P0_DETECTOR_PROFILE.reference_cells_per_side,
            P0_DETECTOR_PROFILE.guard_cells_per_side,
            P0_DETECTOR_PROFILE.order_statistic_rank,
            P0_DETECTOR_PROFILE.threshold_coefficient,
            P0_DETECTOR_PROFILE.maximum_gap_bins,
        )
        for frame_id, power in enumerate(frames):
            expected = detector.process(power, frame_id=frame_id)
            detections = np.zeros(4096, dtype=np.uint8)
            noise = np.empty(4096, dtype=np.float64)
            threshold = np.empty(4096, dtype=np.float64)
            candidates = (CCandidate * 1352)()
            candidate_count = ctypes.c_size_t()
            recovery_count = ctypes.c_size_t()
            status = function(
                power.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                power.size,
                ctypes.byref(config),
                detections.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                noise.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                threshold.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                candidates,
                1352,
                ctypes.byref(candidate_count),
                ctypes.byref(recovery_count),
            )
            observed = [
                (candidates[index].start, candidates[index].end, candidates[index].peak)
                for index in range(candidate_count.value)
            ]
            wanted = [
                (candidate.start_bin, candidate.end_bin, candidate.peak_bin)
                for candidate in expected.candidates
            ]
            mismatches += int(
                status != 0
                or observed != wanted
                or recovery_count.value != len(expected.recovery_candidates)
            )
        handle = library._handle
        del function
        del library
        if os.name == "nt":
            _ctypes.FreeLibrary(handle)
    return {
        "status": "passed" if mismatches == 0 else "failed",
        "compiler": compiler,
        "frames": len(frames),
        "candidate_boundary_mismatches": mismatches,
    }


def evaluate() -> dict[str, object]:
    catalog = load_scene_catalog()
    wideband, wide_frames = _wideband_gate(catalog)
    additions, noise_frames = _regional_addition_gate(catalog)
    temporal = _wideband_temporal_gate(catalog)
    c_python = _c_python_gate([*wide_frames, *noise_frames])
    os_profile = evaluate_os_profile()
    bounded = (
        wideband["maximum_combined_candidates"] <= 1352
        and P0_WIDEBAND_RECOVERY_PROFILE.integration_bins == 32
        and P0_WIDEBAND_RECOVERY_PROFILE.noise_multiplier == 2.5
        and P0_WIDEBAND_RECOVERY_PROFILE.minimum_span_bins == 41
    )
    sections = (wideband, additions, temporal, c_python)
    passed = all(section["status"] == "passed" for section in sections) and os_profile["status"] == "passed" and bounded
    return {
        "schema_version": 1,
        "checkpoint": "P0 ED wideband recovery correction",
        "status": "passed" if passed else "failed",
        "method": {
            "local_detector": P0_DETECTOR_PROFILE.name,
            "region_bins": P0_WIDEBAND_RECOVERY_PROFILE.region_size,
            "integration_bins": P0_WIDEBAND_RECOVERY_PROFILE.integration_bins,
            "noise_multiplier": P0_WIDEBAND_RECOVERY_PROFILE.noise_multiplier,
            "support_erosion_bins": [15, 16],
            "minimum_recovery_span_bins": P0_WIDEBAND_RECOVERY_PROFILE.minimum_span_bins,
            "fusion": "qualified integrated-energy owner suppresses overlapping OS-CFAR fragments",
        },
        "wideband": wideband,
        "no_added_broad_false_candidates": additions,
        "wideband_temporal": temporal,
        "portable_c_equivalence": c_python,
        "existing_os_false_alarm": os_profile["empirical_false_alarm"],
        "bounded_contract": {
            "status": "passed" if bounded else "failed",
            "maximum_candidates": 1352,
            "maximum_active_events": 64,
            "abi_version": 1,
        },
        "claim_boundary": "Host reference and portable C evidence; not ARM, FPGA execution, throughput, or live RF.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("multiscale detector evidence is missing or stale", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
