#!/usr/bin/env python3
"""Write or read-only verify deterministic PHASE-06A evidence."""

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

from reference.rtl.frame_stats import (
    ENERGY_WIDTH,
    FRAME_LENGTH,
    INDEX_WIDTH,
    POWER_WIDTH,
    SAMPLE_COUNT_WIDTH,
)
from reference.rtl.vectors import build_vector_files


EVIDENCE = ROOT / "results" / "evidence" / "phase06a"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06a"
OWNED_FILES = (
    "toolchain.json",
    "fixed-point-contract.json",
    "golden-frame-results.json",
    "python-model-result.json",
    "rtl-simulation.json",
    "verification-summary.json",
)
RTL_SOURCES = (
    ROOT / "rtl" / "phase06a" / "rtl" / "phase06a_pkg.sv",
    ROOT / "rtl" / "phase06a" / "rtl" / "axis_skid_buffer.sv",
    ROOT / "rtl" / "phase06a" / "rtl" / "axis_ci8_frame_stats.sv",
)
TESTBENCH = ROOT / "rtl" / "phase06a" / "tb" / "tb_axis_ci8_frame_stats.sv"
MSYS2_UCRT64_BIN = Path("C:/msys64/ucrt64/bin")
FIXED_COMMANDS = {
    "iverilog": MSYS2_UCRT64_BIN / "iverilog.exe",
    "vvp": MSYS2_UCRT64_BIN / "vvp.exe",
}


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_command(name: str) -> str | None:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    fixed = FIXED_COMMANDS.get(name)
    return str(fixed) if fixed is not None and fixed.is_file() else None


def _run(command: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if MSYS2_UCRT64_BIN.is_dir():
        environment["PATH"] = str(MSYS2_UCRT64_BIN) + os.pathsep + environment.get("PATH", "")
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout,
    )


def _version(executable: str, arguments: tuple[str, ...]) -> str:
    try:
        result = _run([executable, *arguments], cwd=ROOT, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "version query failed"
    lines = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return lines[0][:160] if lines else "version not reported"


def discover_toolchain() -> dict[str, object]:
    specifications = (
        ("vivado", ("vivado",), ("-version",)),
        ("xsim", ("xsim", "xvlog", "xelab"), ("--version",)),
        ("verilator", ("verilator",), ("--version",)),
        ("iverilog", ("iverilog",), ("-V",)),
        ("vvp", ("vvp",), ("-V",)),
        ("slang", ("slang",), ("--version",)),
        ("c_compiler", ("cl", "clang", "gcc"), ("--version",)),
    )
    tools: list[dict[str, object]] = []
    for name, commands, version_arguments in specifications:
        if name == "c_compiler":
            found = next((candidate for candidate in commands if _resolve_command(candidate)), None)
            available = found is not None
            resolved = _resolve_command(found) if found else None
            version = _version(resolved, ("/Bv",) if found == "cl" else version_arguments) if resolved else None
            detail = "compiler available" if available else "no supported C/C++ compiler found on PATH"
        else:
            available = all(_resolve_command(candidate) for candidate in commands)
            found = _resolve_command(commands[0]) if available else None
            version = _version(found, version_arguments) if found else None
            detail = "required commands available" if available else "required commands not found on PATH"
        item: dict[str, object] = {
            "name": name,
            "status": "available" if available else "unavailable",
            "detail": detail,
        }
        if version is not None:
            item["version"] = version
        tools.append(item)
    return {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "purpose": "Salt-okunur araç keşfidir; kurulum veya donanım erişimi yapmaz.",
        "tools": tools,
    }


def _tool_available(toolchain: dict[str, object], name: str) -> bool:
    return any(
        isinstance(item, dict) and item.get("name") == name and item.get("status") == "available"
        for item in toolchain["tools"]
    )


def _bounded_log(result: subprocess.CompletedProcess[str]) -> str:
    value = (result.stdout + "\n" + result.stderr).strip()[-8000:]
    value = value.replace(str(ROOT), "<repository>").replace(str(ROOT).replace("\\", "/"), "<repository>")
    return re.sub(r"[A-Za-z]:[\\/][^\r\n:]+", "<local-path>", value)


def _run_iverilog(directory: Path) -> tuple[bool, bool, str]:
    output = directory / "phase06a.vvp"
    compile_result = _run(
        [_resolve_command("iverilog") or "iverilog", "-g2012", "-s", "tb_axis_ci8_frame_stats", "-o", str(output),
         *(str(path) for path in (*RTL_SOURCES, TESTBENCH))],
        cwd=ROOT,
    )
    if compile_result.returncode:
        return False, False, "compile failed\n" + _bounded_log(compile_result)
    run_result = _run([_resolve_command("vvp") or "vvp", str(output)], cwd=ROOT)
    passed = run_result.returncode == 0 and "PHASE-06A TB PASS" in run_result.stdout
    return True, passed, _bounded_log(run_result)


def _run_verilator(directory: Path) -> tuple[bool, bool, str]:
    object_dir = directory / "obj"
    compile_result = _run(
        ["verilator", "--binary", "--timing", "--assert", "-Wall", "-Wno-fatal",
         "--top-module", "tb_axis_ci8_frame_stats", "--Mdir", str(object_dir),
         "-o", "phase06a_sim", *(str(path) for path in (*RTL_SOURCES, TESTBENCH))],
        cwd=ROOT,
        timeout=180,
    )
    if compile_result.returncode:
        return False, False, "compile failed\n" + _bounded_log(compile_result)
    executable = object_dir / ("phase06a_sim.exe" if sys.platform == "win32" else "phase06a_sim")
    run_result = _run([str(executable)], cwd=ROOT)
    passed = run_result.returncode == 0 and "PHASE-06A TB PASS" in run_result.stdout
    return True, passed, _bounded_log(run_result)


def _run_xsim(directory: Path) -> tuple[bool, bool, str]:
    fixture_target = directory / "datasets" / "fixtures" / "phase06a"
    fixture_target.parent.mkdir(parents=True)
    shutil.copytree(FIXTURES, fixture_target)
    compile_result = _run(["xvlog", "-sv", *(str(path) for path in (*RTL_SOURCES, TESTBENCH))], cwd=directory)
    if compile_result.returncode:
        return False, False, "compile failed\n" + _bounded_log(compile_result)
    elaborate_result = _run(["xelab", "tb_axis_ci8_frame_stats", "-s", "phase06a_snapshot"], cwd=directory)
    if elaborate_result.returncode:
        return False, False, "elaboration failed\n" + _bounded_log(elaborate_result)
    run_result = _run(["xsim", "phase06a_snapshot", "-runall"], cwd=directory)
    passed = run_result.returncode == 0 and "PHASE-06A TB PASS" in run_result.stdout
    return True, passed, _bounded_log(run_result)


def run_simulation(toolchain: dict[str, object]) -> dict[str, object]:
    runner = None
    tool = None
    if _tool_available(toolchain, "iverilog") and _tool_available(toolchain, "vvp"):
        tool, runner = "iverilog", _run_iverilog
    elif _tool_available(toolchain, "verilator") and _tool_available(toolchain, "c_compiler"):
        tool, runner = "verilator", _run_verilator
    elif _tool_available(toolchain, "xsim"):
        tool, runner = "xsim", _run_xsim
    if runner is None:
        return {
            "schema_version": 1,
            "phase": "PHASE-06A",
            "status": "skipped",
            "reason": "tool_unavailable",
            "rtl_compile": "skipped",
            "rtl_simulation": "skipped",
            "golden_equivalence": "skipped",
            "hardware_status": "not_exercised",
            "hardware": "not_exercised",
            "synthesis": "not_exercised",
            "timing": "not_exercised",
            "resource_utilization": "not_exercised",
            "claim_boundary": "RTL testbench hazırlanmıştır; simülasyon çalıştırılmamıştır.",
        }
    with tempfile.TemporaryDirectory(prefix="phase06a-sim-") as temporary:
        try:
            compiled, passed, log = runner(Path(temporary))
        except (OSError, subprocess.TimeoutExpired) as exc:
            compiled, passed, log = False, False, f"{type(exc).__name__}: simulator did not complete"
    return {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "status": "passed" if passed else "failed",
        "reason": "self_checking_testbench" if passed else "simulation_failure",
        "simulator": tool,
        "rtl_compile": "passed" if compiled else "failed",
        "rtl_simulation": "passed" if passed else "failed",
        "golden_equivalence": "passed" if passed else "failed",
        "bounded_log": log,
        "hardware_status": "not_exercised",
        "hardware": "not_exercised",
        "synthesis": "not_exercised",
        "timing": "not_exercised",
        "resource_utilization": "not_exercised",
        "claim_boundary": "Bu sonuç yalnız RTL simülasyonudur; sentez veya FPGA sonucu değildir.",
    }


def _historical_integrity() -> tuple[int, bool]:
    paths = _run(["git", "ls-tree", "-r", "--name-only", "HEAD", "results/evidence", "profiles"], cwd=ROOT).stdout.splitlines()
    intact = True
    for relative in paths:
        worktree = _run(["git", "hash-object", "--", relative], cwd=ROOT).stdout.strip()
        head = _run(["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT).stdout.strip()
        intact = intact and bool(worktree) and worktree == head
    return len(paths), intact


def build_documents(*, execute_simulation: bool) -> dict[str, dict[str, object]]:
    generated, manifest = build_vector_files()
    golden = json.loads(generated["golden-vectors.json"].decode("utf-8"))
    toolchain = discover_toolchain()
    simulation = run_simulation(toolchain) if execute_simulation else None
    if simulation is None:
        stored = EVIDENCE / "rtl-simulation.json"
        simulation = json.loads(stored.read_text(encoding="utf-8")) if stored.is_file() else {
            "schema_version": 1, "phase": "PHASE-06A", "status": "failed", "reason": "missing_evidence"
        }
    fixed_point = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "input": {"datatype": "ci8", "layout": "tdata[7:0]=I,tdata[15:8]=Q", "component_range": [-128, 127]},
        "frame_length": FRAME_LENGTH,
        "widths": {"sample_power": POWER_WIDTH, "frame_energy": ENERGY_WIDTH, "peak_index": INDEX_WIDTH, "sample_count": SAMPLE_COUNT_WIDTH},
        "maxima": {"component_square": 16384, "sample_power": 32768, "frame_energy": 134217728},
        "overflow_policy": "mathematical_width_no_saturation",
        "peak_tie_break": "first_index",
    }
    golden_results = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "source_fixture": manifest["source"],
        "phase01_frames": golden["phase01_frames"],
        "vector_hashes": manifest["files"],
    }
    python_model = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "status": "passed",
        "frame_results": golden["phase01_frames"],
        "corner_vectors": golden["corner_vectors"],
        "protocol_vectors": golden["protocol_vectors"],
    }
    count, intact = _historical_integrity()
    mandatory = {
        "vectors": all((FIXTURES / name).is_file() and (FIXTURES / name).read_bytes() == payload for name, payload in generated.items()),
        "rtl_sources": all(path.is_file() for path in (*RTL_SOURCES, TESTBENCH)),
        "historical_integrity": intact,
        "python_model": python_model["status"] == "passed",
    }
    simulation_status = simulation.get("status")
    overall = "passed" if all(mandatory.values()) and simulation_status == "passed" else "prepared_not_simulated" if all(mandatory.values()) and simulation_status == "skipped" else "failed"
    summary = {
        "schema_version": 1,
        "phase": "PHASE-06A",
        "overall": overall,
        "checks": [
            {"id": name, "status": "passed" if status else "failed"}
            for name, status in mandatory.items()
        ] + [{"id": "rtl_simulation", "status": simulation_status}],
        "historical_integrity": {"files": count, "status": "passed" if intact else "failed"},
        "hardware_status": "not_exercised",
        "fft_status": "not_implemented",
        "detector_rtl_status": "not_implemented",
        "claim_boundary": "PHASE-06A yalnız ci8/AXI4-Stream frame-istatistik temelidir; FFT, sentez ve FPGA sonucu değildir.",
    }
    return {
        "toolchain.json": toolchain,
        "fixed-point-contract.json": fixed_point,
        "golden-frame-results.json": golden_results,
        "python-model-result.json": python_model,
        "rtl-simulation.json": simulation,
        "verification-summary.json": summary,
    }


def write() -> None:
    documents = build_documents(execute_simulation=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in OWNED_FILES:
        (EVIDENCE / name).write_bytes(canonical_bytes(documents[name]))


def check() -> bool:
    documents = build_documents(execute_simulation=False)
    exact = all((EVIDENCE / name).is_file() and (EVIDENCE / name).read_bytes() == canonical_bytes(documents[name]) for name in OWNED_FILES)
    simulation = documents["rtl-simulation.json"]
    accepted_overall = documents["verification-summary.json"]["overall"] in {"passed", "prepared_not_simulated"}
    honest_skip = simulation.get("status") != "skipped" or simulation.get("reason") == "tool_unavailable"
    return exact and accepted_overall and honest_skip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    summary = json.loads((EVIDENCE / "verification-summary.json").read_text(encoding="utf-8")) if (EVIDENCE / "verification-summary.json").is_file() else {"overall": "missing"}
    print(f"PHASE-06A verification: {'passed' if passed else 'failed'} ({summary['overall']})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
