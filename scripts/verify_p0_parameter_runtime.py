#!/usr/bin/env python3
"""Verify the portable ARM numeric parameter core against the locked F5 estimator."""

from __future__ import annotations

from dataclasses import replace
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f5_estimator import F5ParameterEstimator
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor


P0 = ROOT / "platforms" / "embedded" / "p0"
RUNTIME = P0 / "src" / "p0_parameter_runtime.c"
RUNNER = P0 / "src" / "p0_parameter_run.c"
STATE_HARNESS = ROOT / "tests" / "p0" / "p0_parameter_runtime_test.c"
SAMPLE_RATE_HZ = 8_000_000
CENTER_FREQUENCY_HZ = 100_000_000
STATE = {"not_available": 0, "valid": 1, "insufficient_quality": 2, "uncertain": 3, "not_observed": 4}


def _msvc_vcvars() -> Path | None:
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
    result = Path(query.stdout.strip()) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    return result if result.is_file() else None


def _build(directory: Path) -> tuple[Path, Path, str]:
    if os.name == "nt" and (vcvars := _msvc_vcvars()) is not None:
        executable = directory / "p0-parameter-run.exe"
        state_executable = directory / "p0-parameter-runtime-test.exe"
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX '
            f'/I"{P0 / "include"}" "{RUNTIME}" "{RUNNER}" /Fe:"{executable}" '
            f'&& cl /nologo /std:c11 /O2 /W4 /WX /I"{P0 / "include"}" '
            f'"{RUNTIME}" "{STATE_HARNESS}" /Fe:"{state_executable}"'
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
        executable = directory / "p0-parameter-run"
        state_executable = directory / "p0-parameter-runtime-test"
        runner_build = subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             f"-I{P0 / 'include'}", str(RUNTIME), str(RUNNER), "-lm",
             "-o", str(executable)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        state_build = subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             f"-I{P0 / 'include'}", str(RUNTIME), str(STATE_HARNESS), "-lm",
             "-o", str(state_executable)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        build = subprocess.CompletedProcess(
            args=(runner_build.args, state_build.args),
            returncode=runner_build.returncode or state_build.returncode,
            stdout=runner_build.stdout + state_build.stdout,
            stderr=runner_build.stderr + state_build.stderr,
        )
        compiler = Path(cc).name
    if build.returncode or not executable.is_file() or not state_executable.is_file():
        raise RuntimeError(f"parameter runtime build failed:\n{build.stdout}\n{build.stderr}")
    return executable, state_executable, compiler


def _ci8(samples: np.ndarray) -> tuple[bytes, np.ndarray]:
    interleaved = np.empty((4096, 2), dtype=np.int8)
    interleaved[:, 0] = np.clip(np.rint(samples.real * 128.0), -128, 127).astype(np.int8)
    interleaved[:, 1] = np.clip(np.rint(samples.imag * 128.0), -128, 127).astype(np.int8)
    decoded = interleaved[:, 0].astype(np.float64) / 128.0
    decoded = decoded + 1j * interleaved[:, 1].astype(np.float64) / 128.0
    return interleaved.tobytes(), np.asarray(decoded, dtype=np.complex128)


def _case(
    directory: Path,
    executable: Path,
    scene_id: str,
    seed: int,
    span_override: tuple[int, int] | None = None,
    snr_db: float = 12.0,
) -> dict[str, object]:
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    generated = tuple(
        generate_parameter_scene(
            scene_id, trial_index=0, condition_index=3, frame_index=index,
            clean_power_dbfs=-18.0, snr_db=snr_db, catalog=catalog,
            scene_seed_override=seed,
        )
        for index in range(4)
    )
    clean_spectra = tuple(
        processor.process(
            frame.clean_samples, sample_rate_hz=SAMPLE_RATE_HZ,
            center_frequency_hz=CENTER_FREQUENCY_HZ,
        )
        for frame in generated
    )
    span = span_override or tuple(int(value) for value in _truth(clean_spectra, 12)["span"])
    samples: list[np.ndarray] = []
    spectra = []
    paths: list[Path] = []
    for index, frame in enumerate(generated):
        raw_iq, decoded = _ci8(np.asarray(frame.samples, dtype=np.complex128))
        spectrum = processor.process(
            decoded, sample_rate_hz=SAMPLE_RATE_HZ,
            center_frequency_hz=CENTER_FREQUENCY_HZ,
        )
        quantized = np.rint(
            np.asarray(spectrum.fft_power_unshifted) * float(1 << 30)
        ).astype("<u8")
        display = processor.display_from_power(spectrum, quantized.astype(np.float64) / float(1 << 30))
        spectra.append(replace(spectrum, display=display))
        samples.append(decoded)
        iq_path = directory / f"{scene_id}-{index}.ci8"
        power_path = directory / f"{scene_id}-{index}.u64"
        iq_path.write_bytes(raw_iq)
        power_path.write_bytes(quantized.tobytes())
        paths.extend((iq_path, power_path))

    expected = F5ParameterEstimator().measure(
        _intent(span, 1, 1), tuple(samples), tuple(spectra)
    )
    output = directory / f"{scene_id}-result.json"
    command = [
        str(executable), str(SAMPLE_RATE_HZ), str(CENTER_FREQUENCY_HZ),
        str(span[0]), str(span[1]), *(str(path) for path in paths), str(output),
    ]
    run = subprocess.run(
        command, cwd=directory, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    if run.returncode or "P0_PARAMETER_RESULT=PASS" not in run.stdout:
        raise RuntimeError(f"parameter runtime failed:\n{run.stdout}\n{run.stderr}")
    actual = json.loads(output.read_text(encoding="utf-8"))
    fields = {
        "carrier_line_frequency_hz": expected.carrier_line_frequency,
        "emission_center_frequency_hz": expected.emission_center_frequency,
        "lower_occupied_edge_hz": expected.lower_band_edge,
        "upper_occupied_edge_hz": expected.upper_band_edge,
        "occupied_bandwidth_hz": expected.occupied_bandwidth,
        "channel_power_dbfs": expected.channel_power_dbfs,
        "snr_estimate_db": expected.snr_estimate_db,
    }
    maximum_error = 0.0
    comparisons: dict[str, object] = {}
    for name, reference in fields.items():
        if actual[name]["state"] != STATE[reference.state]:
            raise AssertionError(
                f"{scene_id} {name} state mismatch: {actual[name]['state']} != {reference.state}"
            )
        if reference.state == "valid":
            error = abs(float(actual[name]["value"]) - float(reference.value))
            tolerance = 0.02 if name.endswith("_hz") else 1.0e-8
            if error > tolerance:
                raise AssertionError(
                    f"{scene_id} {name} error {error} exceeds {tolerance}"
                )
            maximum_error = max(maximum_error, error)
            comparisons[name] = {"state": "valid", "absolute_error": error}
        else:
            comparisons[name] = {"state": reference.state}
    return {
        "scene": scene_id,
        "snr_db": snr_db,
        "span": list(span),
        "span_width_bins": span[1] - span[0] + 1,
        "maximum_absolute_error": maximum_error,
        "fields": comparisons,
    }


def verify(*, extended: bool = False) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="p0-parameter-runtime-") as raw:
        directory = Path(raw)
        executable, state_executable, compiler = _build(directory)
        state_run = subprocess.run(
            [str(state_executable)], cwd=directory, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if state_run.returncode or "P0_PARAMETER_RUNTIME_STATE_TEST=PASS" not in state_run.stdout:
            raise RuntimeError(
                f"parameter state test failed:\n{state_run.stdout}\n{state_run.stderr}"
            )
        cases = [
            _case(directory, executable, "am-carrier", 3502604761305543594),
            _case(directory, executable, "wideband-noise-like", 3502604761305543595),
            _case(
                directory, executable, "noise-only", 3502604761305633594,
                (1792, 2303),
            ),
        ]
        if extended:
            scenes = ("tone-bin-centered", "tone-off-bin", "am-carrier", "nfm",
                      "ook", "two-fsk", "bpsk", "qpsk", "wideband-noise-like", "dsb-sc")
            for snr in (-3.0, 3.0, 12.0):
                for index, scene in enumerate(scenes):
                    cases.append(_case(directory, executable, scene,
                                       3502604761305544000 + index, snr_db=snr))
    if not any(int(case["span_width_bins"]) >= 100 for case in cases):
        raise AssertionError("broad-span FFT path was not exercised")
    return {
        "status": "passed",
        "compiler": compiler,
        "state_machine_test": state_run.stdout.strip(),
        "persistent_payload_bytes": 56064,
        "carrier_peak_heap_workspace_bytes": 327680,
        "profile": "phase04f5-operator-assisted-parameters-v6",
        "ported_fields": [
            "carrier_line_frequency", "emission_center_frequency", "occupied_bandwidth",
            "uncalibrated_channel_power_dbfs", "snr_estimate_db",
        ],
        "not_ported": ["signal_domain"],
        "cases": cases,
        "scope": "software reference equivalence; not RF accuracy or deployed service acceptance",
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (RUNTIME, RUNNER, STATE_HARNESS, P0 / "include/p0_parameter_runtime.h", Path(__file__))
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(extended=args.extended)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
        with zipfile.ZipFile(args.output.with_suffix(".zip"), "x", zipfile.ZIP_STORED) as archive:
            archive.writestr(args.output.name, payload.encode("utf-8"))
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "ported_fields": result["ported_fields"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
