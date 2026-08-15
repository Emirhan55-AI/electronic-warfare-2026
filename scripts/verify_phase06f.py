#!/usr/bin/env python3
"""Verify and record PHASE-06F exact FFT linear-power evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.rtl.fft_power import POWER_MAX_REACHABLE, power_from_fft_word, width_proof
from reference.rtl.power_vectors import REAL_FFT_SOURCE, build_vector_files


EVIDENCE = ROOT / "results" / "evidence" / "phase06f"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06f"
OWNED_FILES = (
    "fixed-point-contract.json",
    "integration.json",
    "latency.json",
    "python-model-result.json",
    "rtl-simulation.json",
    "source-manifest.json",
    "toolchain.json",
    "verification-summary.json",
)
SOURCE_FILES = (
    "docs/decisions/ADR-0016-PHASE06F-FFT-LINEAR-POWER.md",
    "docs/interfaces/RTL_FFT_POWER_CONTRACT.md",
    "reference/rtl/fft_power.py",
    "reference/rtl/power_vectors.py",
    "rtl/phase06f/rtl/axis_fft_linear_power.sv",
    "rtl/phase06f/tb/tb_axis_fft_linear_power.sv",
    "scripts/generate_phase06f_vectors.py",
    "datasets/fixtures/phase06f/edge-input.mem",
    "datasets/fixtures/phase06f/edge-expected.mem",
    "datasets/fixtures/phase06f/real-power-expected.mem",
    "datasets/fixtures/phase06f/golden-vectors.json",
    "datasets/fixtures/phase06f/fixture-manifest.json",
)
EXPECTED_PASS_LINE = "PHASE-06F TB PASS: 45068 power results checked"
EXPECTED_METRICS = {"latency_cycles": 2, "input_stalls": 11520, "output_stalls": 11520}


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commands() -> tuple[str, str]:
    iverilog = shutil.which("iverilog") or r"C:\msys64\ucrt64\bin\iverilog.exe"
    vvp = shutil.which("vvp") or r"C:\msys64\ucrt64\bin\vvp.exe"
    if not Path(iverilog).is_file() or not Path(vvp).is_file():
        raise FileNotFoundError("Icarus Verilog 13.0 executable was not found")
    return iverilog, vvp


def _normalized_output(stdout: str) -> bytes:
    lines = [line.strip() for line in stdout.splitlines() if line.startswith("PHASE06F_METRIC") or line.startswith("PHASE-06F TB PASS")]
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_rtl_once() -> dict[str, object]:
    iverilog, vvp = _commands()
    environment = os.environ.copy()
    environment["PATH"] = str(Path(iverilog).parent) + os.pathsep + environment.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="TEKNOFEST-phase06f-power-") as temporary:
        executable = Path(temporary) / "phase06f-power.vvp"
        compiled = subprocess.run(
            [iverilog, "-g2012", "-s", "tb_axis_fft_linear_power", "-o", str(executable),
             str(ROOT / "rtl/phase06f/rtl/axis_fft_linear_power.sv"),
             str(ROOT / "rtl/phase06f/tb/tb_axis_fft_linear_power.sv")],
            cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
        )
        if compiled.returncode != 0:
            raise RuntimeError(compiled.stdout + compiled.stderr)
        simulated = subprocess.run([vvp, str(executable)], cwd=ROOT, env=environment, capture_output=True, text=True, check=False)
        if simulated.returncode != 0 or EXPECTED_PASS_LINE not in simulated.stdout:
            raise RuntimeError(simulated.stdout + simulated.stderr)
    latency = re.search(r"PHASE06F_METRIC latency_cycles=(\d+)", simulated.stdout)
    stalls = re.search(r"PHASE06F_METRIC input_stalls=(\d+) output_stalls=(\d+)", simulated.stdout)
    if latency is None or stalls is None:
        raise ValueError("PHASE-06F RTL metrics missing")
    metrics = {"latency_cycles": int(latency.group(1)), "input_stalls": int(stalls.group(1)), "output_stalls": int(stalls.group(2))}
    if metrics != EXPECTED_METRICS:
        raise AssertionError(f"unexpected PHASE-06F RTL metrics: {metrics}")
    normalized = _normalized_output(simulated.stdout)
    return {"metrics": metrics, "normalized_output": normalized, "normalized_sha256": hashlib.sha256(normalized).hexdigest()}


def _stored_simulation_shape() -> dict[str, object]:
    normalized = (
        "PHASE06F_METRIC latency_cycles=2\n"
        "PHASE06F_METRIC input_stalls=11520 output_stalls=11520\n"
        "PHASE-06F TB PASS: 45068 power results checked\n"
    ).encode("utf-8")
    return {"metrics": dict(EXPECTED_METRICS), "normalized_output": normalized, "normalized_sha256": hashlib.sha256(normalized).hexdigest()}


def _python_results() -> tuple[dict[str, object], dict[str, object]]:
    files = build_vector_files()
    mismatched_files = [name for name, payload in files.items() if not (FIXTURES / name).is_file() or (FIXTURES / name).read_bytes() != payload]
    if mismatched_files:
        raise AssertionError("fixture mismatch: " + ", ".join(mismatched_files))
    real_words = tuple(int(line, 16) for line in REAL_FFT_SOURCE.read_text(encoding="ascii").splitlines() if line)
    stored_power = tuple(int(line, 16) for line in (FIXTURES / "real-power-expected.mem").read_text(encoding="ascii").splitlines() if line)
    computed_power = tuple(power_from_fft_word(word) for word in real_words)
    mismatches = sum(left != right for left, right in zip(computed_power, stored_power, strict=True))
    edge_count = len((FIXTURES / "edge-input.mem").read_text(encoding="ascii").splitlines())
    python_result = {
        "phase": "PHASE-06F", "status": "passed" if mismatches == 0 else "failed",
        "model": "independent Python arbitrary-precision integer square-and-sum",
        "edge_samples": edge_count, "real_amd_fft_samples": len(real_words),
        "total_samples": edge_count + len(real_words), "mismatch_count": mismatches,
        "maximum_result": max(computed_power), "reachable_contract_maximum": POWER_MAX_REACHABLE,
    }
    integration = {
        "phase": "PHASE-06F", "status": "passed" if mismatches == 0 else "failed",
        "input": "canonical normalized real PHASE-06D AMD FFT C-model/XSim-equivalent output",
        "input_path": "datasets/fixtures/phase06d/cmodel-expected.mem",
        "input_sha256": sha256(REAL_FFT_SOURCE), "frames": 11, "samples": len(real_words),
        "power_output_sha256": sha256(FIXTURES / "real-power-expected.mem"), "mismatch_count": mismatches,
    }
    return python_result, integration


def build_documents(*, execute_simulation: bool) -> dict[str, object]:
    python_result, integration = _python_results()
    first = run_rtl_once() if execute_simulation else _stored_simulation_shape()
    second = run_rtl_once() if execute_simulation else _stored_simulation_shape()
    deterministic = first["normalized_output"] == second["normalized_output"]
    proof = width_proof()
    simulation = {
        "phase": "PHASE-06F", "status": "passed", "compile": "passed", "simulation": "passed",
        "simulator": "Icarus Verilog 13.0 stable", "checked_results": 45068, "mismatch_count": 0,
        "edge_results": 12, "real_amd_fft_results": 45056,
        "latency_cycles": first["metrics"]["latency_cycles"],
        "input_stall_cycles": first["metrics"]["input_stalls"],
        "output_stall_cycles": first["metrics"]["output_stalls"],
        "deterministic_rerun": "passed" if deterministic else "failed",
        "normalized_output_sha256": first["normalized_sha256"],
        "coverage": ["exact_integer", "extrema", "reset", "backpressure", "payload_stability", "tlast", "xk_index", "consecutive_frames", "no_drop", "no_duplication"],
        "build_location": "external_temporary_directory",
    }
    summary_passed = python_result["status"] == integration["status"] == "passed" and simulation["deterministic_rerun"] == "passed"
    return {
        "fixed-point-contract.json": {"phase": "PHASE-06F", "status": "passed", **proof, "square_width": 57, "sum_width": 58, "fractional_bits": 30, "reachable_output_integer_range": [0, POWER_MAX_REACHABLE]},
        "integration.json": integration,
        "latency.json": {"phase": "PHASE-06F", "status": "passed", "registered_stages": ["operand", "square", "sum_output"], "unstalled_input_accept_to_output_valid_clock_intervals": 2, "steady_state_samples_per_cycle": 1, "post_power_timing": "not_reverified"},
        "python-model-result.json": python_result,
        "rtl-simulation.json": simulation,
        "source-manifest.json": {"phase": "PHASE-06F", "status": "passed", "files": {name: sha256(ROOT / name) for name in SOURCE_FILES}},
        "toolchain.json": {"phase": "PHASE-06F", "status": "passed", "rtl_language": "SystemVerilog", "simulator": "Icarus Verilog 13.0 stable", "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", "vivado": "not_run_for_phase06f", "hardware": "not_exercised"},
        "verification-summary.json": {"phase": "PHASE-06F", "overall": "passed" if summary_passed else "failed", "python_model": python_result["status"], "rtl_compile": "passed", "rtl_simulation": "passed", "golden_equivalence": "passed", "deterministic_rerun": "passed" if deterministic else "failed", "psd": "not_implemented", "regional_detector_rtl": "not_implemented", "post_power_synthesis": "not_exercised", "post_power_timing_100mhz": "not_reverified", "bitstream": "not_generated", "hardware": "not_exercised", "live_hackrf": "not_exercised"},
    }


def write() -> None:
    documents = build_documents(execute_simulation=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))
    print(f"PHASE-06F evidence written: {len(OWNED_FILES)} files")


def check() -> bool:
    try:
        documents = build_documents(execute_simulation=False)
        exact = all((EVIDENCE / name).is_file() and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name]) for name in OWNED_FILES)
        payload = b"".join((EVIDENCE / name).read_bytes() for name in OWNED_FILES).decode("utf-8", errors="replace").casefold()
        safe = not any(token in payload for token in ("c:\\users", "hostname", "timestamp", "onedrive"))
        return exact and safe and documents["verification-summary.json"]["overall"] == "passed"
    except (OSError, ValueError, AssertionError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"PHASE-06F verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
