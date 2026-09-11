#!/usr/bin/env python3
"""Verify the portable ARM amplitude-DF core against the Python reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE, ManualAmplitudeDF

P0 = ROOT / "platforms" / "embedded" / "p0"
HEADER = P0 / "include" / "p0_amplitude_df.h"
CORE = P0 / "src" / "p0_amplitude_df.c"
RUNNER = P0 / "src" / "p0_amplitude_df_run.c"
EVIDENCE = ROOT / "results" / "evidence" / "phase09" / "amplitude-df-arm-equivalence-v1.json"

STATUS = {
    "YETERSİZ AÇI": "INSUFFICIENT_ANGLES",
    "YETERSİZ AÇI KAPSAMI": "INSUFFICIENT_COVERAGE",
    "YETERSİZ TEKRAR": "INSUFFICIENT_REPEATS",
    "ALICI AYARI DEĞİŞTİ": "RECEIVER_CHANGED",
    "HEDEF FREKANSI DEĞİŞTİ": "TARGET_CHANGED",
    "ÖN/ARKA BELİRSİZ": "FRONT_BACK_AMBIGUOUS",
    "BELİRSİZ MAKSİMUM": "AMBIGUOUS_MAXIMUM",
    "LOB HAZIR": "LOB_READY",
}


def _vcvars() -> Path | None:
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
    candidate = Path(query.stdout.strip()) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    return candidate if candidate.is_file() else None


def _build(directory: Path) -> tuple[Path, str]:
    executable = directory / ("p0-amplitude-df-run.exe" if os.name == "nt" else "p0-amplitude-df-run")
    if os.name == "nt" and (vcvars := _vcvars()) is not None:
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX '
            f'/I"{P0 / "include"}" "{CORE}" "{RUNNER}" /Fe:"{executable}"'
        )
        build = subprocess.run(
            command, cwd=directory, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        compiler = "MSVC C11"
    else:
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            raise FileNotFoundError("C11 compiler is unavailable")
        build = subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             f"-I{P0 / 'include'}", str(CORE), str(RUNNER), "-lm", "-o", str(executable)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        compiler = Path(cc).name
    if build.returncode or not executable.is_file():
        raise RuntimeError(f"amplitude DF build failed:\n{build.stdout}\n{build.stderr}")
    return executable, compiler


def _measurement(
    angle: float,
    power: float,
    frame: int,
    *,
    frequency_hz: float = 145_000_000.0,
    binding: str = "rx-a",
    confidence: float = 0.95,
    spread_db: float = 0.0,
    observations: int = 1,
) -> DFMeasurement:
    return DFMeasurement.create(
        angle_deg=angle,
        relative_power_db=power,
        frequency_hz=frequency_hz,
        confidence=confidence,
        power_spread_db=spread_db,
        observation_count=observations,
        channel_bandwidth_hz=12_500.0,
        receiver_binding=binding,
        frame_id=frame,
        source="NUMERIC_FIXTURE",
        timestamp_utc=f"2026-09-11T00:00:{frame % 60:02d}Z",
    )


def _bindings(measurements: list[DFMeasurement]) -> dict[str, int]:
    return {name: index + 1 for index, name in enumerate(sorted({m.receiver_binding for m in measurements if m.receiver_binding}))}


def _write_measurements(path: Path, measurements: list[DFMeasurement]) -> None:
    bindings = _bindings(measurements)
    rows = [str(len(measurements))]
    for item in measurements:
        rows.append(
            " ".join((
                f"{item.angle_deg:.17g}", f"{item.relative_power_db:.17g}",
                f"{item.frequency_hz:.17g}", f"{item.confidence:.17g}",
                f"{item.power_spread_db:.17g}", str(item.observation_count),
                f"{(item.channel_bandwidth_hz or 0.0):.17g}",
                "1" if item.channel_bandwidth_hz is not None else "0",
                str(bindings.get(item.receiver_binding, 0)), "1" if item.receiver_binding else "0",
                str(item.frame_id or 0), "1" if item.frame_id is not None else "0",
            ))
        )
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def _run_case(directory: Path, executable: Path, name: str,
              measurements: list[DFMeasurement]) -> dict[str, object]:
    model = ManualAmplitudeDF(FIELD_AMPLITUDE_DF_PROFILE)
    for item in measurements:
        model.add(item)
    expected = model.estimate()
    fixture = directory / f"{name}.txt"
    _write_measurements(fixture, measurements)
    run = subprocess.run(
        [str(executable), str(fixture)], cwd=directory, capture_output=True,
        text=True, encoding="utf-8", errors="replace", check=False,
    )
    if run.returncode:
        raise RuntimeError(f"{name}: portable core failed:\n{run.stdout}\n{run.stderr}")
    fields = run.stdout.strip().split()
    if len(fields) != 15 or fields[0] != "RESULT":
        raise AssertionError(f"{name}: unexpected runner output {run.stdout!r}")
    actual = {
        "status": fields[2], "raw": float(fields[3]), "estimated": float(fields[4]),
        "peak": float(fields[5]), "confidence": float(fields[6]),
        "measurement_count": int(fields[7]), "distinct_count": int(fields[8]),
        "maximum_gap": float(fields[9]), "prominence": float(fields[10]),
        "front_back_valid": bool(int(fields[11])), "front_back": float(fields[12]),
        "sampling_rms_valid": bool(int(fields[13])), "sampling_rms": float(fields[14]),
    }
    expected_values = {
        "raw": expected.raw_maximum_angle_deg,
        "estimated": expected.estimated_angle_deg,
        "peak": expected.peak_power_db,
        "confidence": expected.confidence,
        "maximum_gap": expected.maximum_angular_gap_deg,
        "prominence": expected.peak_prominence_db,
    }
    maximum_error = 0.0
    if actual["status"] != STATUS[expected.status]:
        raise AssertionError(f"{name}: status {actual['status']} != {expected.status}")
    if actual["measurement_count"] != expected.measurement_count or actual["distinct_count"] != expected.distinct_angle_count:
        raise AssertionError(f"{name}: count mismatch")
    for field, value in expected_values.items():
        error = abs(float(actual[field]) - float(value))
        maximum_error = max(maximum_error, error)
        if error > 1.0e-10:
            raise AssertionError(f"{name}: {field} error {error}")
    if actual["front_back_valid"] != (expected.front_to_back_db is not None):
        raise AssertionError(f"{name}: front/back validity mismatch")
    if expected.front_to_back_db is not None:
        maximum_error = max(maximum_error, abs(float(actual["front_back"]) - expected.front_to_back_db))
    if actual["sampling_rms_valid"] != (expected.angular_sampling_rms_deg is not None):
        raise AssertionError(f"{name}: sampling RMS validity mismatch")
    if expected.angular_sampling_rms_deg is not None:
        maximum_error = max(maximum_error, abs(float(actual["sampling_rms"]) - expected.angular_sampling_rms_deg))
    if maximum_error > 1.0e-10:
        raise AssertionError(f"{name}: maximum error {maximum_error}")
    return {
        "case": name,
        "status": expected.status,
        "measurements": len(measurements),
        "distinct_angles": expected.distinct_angle_count,
        "maximum_absolute_error": maximum_error,
    }


def _cases() -> dict[str, list[DFMeasurement]]:
    ready = [
        _measurement(angle, -38.0 + 25.0 * max(math.cos(math.radians(angle - 45.0)), 0.0) ** 4
                     + 3.0 * max(-math.cos(math.radians(angle - 45.0)), 0.0) ** 2, index)
        for index, angle in enumerate(range(0, 360, 15))
    ]
    coverage = [
        _measurement(float(angle), -10.0 - abs(angle - 40.0) / 4.0, index)
        for index, angle in enumerate(range(0, 120, 5))
    ]
    front_back = []
    for index, angle in enumerate(range(0, 360, 15)):
        distance = min(angle, 360 - angle)
        back_distance = abs(angle - 180)
        front_back.append(_measurement(float(angle), max(-9.0 - distance / 8.0,
                                                          -9.5 - back_distance / 8.0), index))
    receiver = [
        _measurement(float(angle), -10.0 - angle / 20.0, index,
                     binding="rx-b" if angle == 345 else "rx-a")
        for index, angle in enumerate(range(0, 360, 15))
    ]
    target = [
        _measurement(float(angle), -10.0 - angle / 20.0, index,
                     frequency_hz=145_010_000.0 if angle == 345 else 145_000_000.0)
        for index, angle in enumerate(range(0, 360, 15))
    ]
    ambiguous = [
        _measurement(float(angle), -10.0 if angle == 0 else (-20.0 if angle == 180 else -11.0), index)
        for index, angle in enumerate(range(0, 360, 15))
    ]
    repeated = [_measurement(0.0, -10.0, 1), _measurement(0.0, -20.0, 2)]
    return {
        "lob-ready": ready,
        "coverage-gate": coverage,
        "front-back-gate": front_back,
        "receiver-gate": receiver,
        "target-gate": target,
        "prominence-gate": ambiguous,
        "linear-repeat-average": repeated,
    }


def verify() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="p0-amplitude-df-") as raw:
        directory = Path(raw)
        executable, compiler = _build(directory)
        cases = [_run_case(directory, executable, name, values) for name, values in _cases().items()]

        duplicate = [_measurement(0.0, -10.0, 7), _measurement(15.0, -12.0, 7)]
        duplicate_file = directory / "duplicate.txt"
        _write_measurements(duplicate_file, duplicate)
        duplicate_run = subprocess.run([str(executable), str(duplicate_file)], capture_output=True,
                                       text=True, encoding="utf-8", errors="replace", check=False)
        if duplicate_run.returncode != 3 or duplicate_run.stdout.strip() != "ERROR -2":
            raise AssertionError("duplicate-frame gate did not fail closed")

        rms_file = directory / "rms.txt"
        estimates = [358.0, 2.0, 90.0, 270.0]
        truths = [2.0, 358.0, 100.0, 260.0]
        rms_file.write_text("4\n" + "\n".join(f"{a} {b}" for a, b in zip(estimates, truths)) + "\n", encoding="ascii")
        rms_run = subprocess.run([str(executable), "--rms", str(rms_file)], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", check=False)
        if rms_run.returncode or not rms_run.stdout.startswith("RMS "):
            raise AssertionError("portable RMS runner failed")
        actual_rms = float(rms_run.stdout.split()[1])
        expected_rms = ManualAmplitudeDF.rms_error_deg(estimates, truths)
        if abs(actual_rms - expected_rms) > 1.0e-12:
            raise AssertionError("circular RMS mismatch")

    return {
        "schema": "phase09-amplitude-df-arm-equivalence-v1",
        "status": "passed",
        "compiler": compiler,
        "profile": FIELD_AMPLITUDE_DF_PROFILE.profile_id,
        "cases": cases,
        "duplicate_frame_gate": "passed",
        "circular_rms_deg": actual_rms,
        "maximum_equivalence_error": max(float(case["maximum_absolute_error"]) for case in cases),
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (HEADER, CORE, RUNNER, Path(__file__), ROOT / "algorithms" / "p0" / "df.py")
        },
        "claim_boundary": (
            "Portable C/ARM software-reference equivalence only; no deployed-board, antenna, "
            "multipath, bearing-accuracy or field RMS acceptance claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    output = args.output or EVIDENCE
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"FAIL: stale or missing evidence: {output}")
        print(f"PASS: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "max_error": result["maximum_equivalence_error"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
