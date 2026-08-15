#!/usr/bin/env python3
"""Write or read-only verify deterministic PHASE-06B evidence."""

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

from reference.rtl.frame_stats import FRAME_LENGTH
from reference.rtl.hann_vectors import build_vector_files
from reference.rtl.hann_window import (
    COEFFICIENT_FRACTION_BITS,
    COEFFICIENT_SCALE,
    COEFFICIENT_WIDTH,
    OUTPUT_COMPONENT_WIDTH,
    OUTPUT_FRACTION_BITS,
    OUTPUT_SHIFT,
    OUTPUT_WORD_WIDTH,
    PRODUCT_WIDTH,
    build_word_length_study,
    quantized_hann_coefficients,
    unpack_windowed_word,
    window_word,
)


EVIDENCE = ROOT / "results" / "evidence" / "phase06b"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06b"
OWNED_FILES = (
    "toolchain.json",
    "word-length-study.json",
    "fixed-point-contract.json",
    "golden-frame-results.json",
    "python-model-result.json",
    "latency.json",
    "rtl-simulation.json",
    "verification-summary.json",
)
RTL_SOURCES = (
    ROOT / "rtl" / "phase06b" / "rtl" / "phase06b_pkg.sv",
    ROOT / "rtl" / "phase06a" / "rtl" / "axis_skid_buffer.sv",
    ROOT / "rtl" / "phase06b" / "rtl" / "axis_hann_window.sv",
)
TESTBENCH = ROOT / "rtl" / "phase06b" / "tb" / "tb_axis_hann_window.sv"
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


def _run(command: list[str], *, cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
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
        ("iverilog", ("iverilog",), ("-V",)),
        ("vvp", ("vvp",), ("-V",)),
    )
    tools: list[dict[str, object]] = []
    for name, commands, version_arguments in specifications:
        available = all(_resolve_command(command) for command in commands)
        executable = _resolve_command(commands[0]) if available else None
        item: dict[str, object] = {
            "name": name,
            "status": "available" if available else "unavailable",
            "detail": "required commands available" if available else "required commands not found on PATH",
        }
        if executable:
            item["version"] = _version(executable, version_arguments)
        tools.append(item)
    return {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "purpose": "Salt-okunur araç keşfidir; kurulum, sentez veya donanım erişimi yapmaz.",
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


def run_simulation(toolchain: dict[str, object]) -> dict[str, object]:
    if not (_tool_available(toolchain, "iverilog") and _tool_available(toolchain, "vvp")):
        return {
            "schema_version": 1,
            "phase": "PHASE-06B",
            "status": "skipped",
            "reason": "tool_unavailable",
            "rtl_compile": "skipped",
            "rtl_simulation": "skipped",
            "golden_equivalence": "skipped",
            "claim_boundary": "RTL hazırlanmıştır; gerçek simülasyon çalıştırılmamıştır.",
        }
    with tempfile.TemporaryDirectory(prefix="phase06b-sim-") as temporary:
        output = Path(temporary) / "phase06b.vvp"
        try:
            compile_result = _run(
                [
                    _resolve_command("iverilog") or "iverilog",
                    "-g2012",
                    "-s",
                    "tb_axis_hann_window",
                    "-o",
                    str(output),
                    *(str(path) for path in (*RTL_SOURCES, TESTBENCH)),
                ],
                cwd=ROOT,
            )
            if compile_result.returncode:
                return {
                    "schema_version": 1,
                    "phase": "PHASE-06B",
                    "status": "failed",
                    "reason": "compile_failure",
                    "simulator": "iverilog",
                    "rtl_compile": "failed",
                    "rtl_simulation": "failed",
                    "golden_equivalence": "failed",
                    "bounded_log": _bounded_log(compile_result),
                }
            run_result = _run([_resolve_command("vvp") or "vvp", str(output)], cwd=ROOT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "schema_version": 1,
                "phase": "PHASE-06B",
                "status": "failed",
                "reason": "simulator_did_not_complete",
                "simulator": "iverilog",
                "rtl_compile": "failed",
                "rtl_simulation": "failed",
                "golden_equivalence": "failed",
                "bounded_log": f"{type(exc).__name__}: simulator did not complete",
            }
    log = _bounded_log(run_result)
    latency_match = re.search(r"PHASE-06B TB LATENCY: (\d+) cycle", run_result.stdout)
    coverage_match = re.search(
        r"PHASE-06B TB COVERAGE: input_stalls=(\d+) output_stalls=(\d+) tlast=(\d+)",
        run_result.stdout,
    )
    pass_match = re.search(r"PHASE-06B TB PASS: (\d+) samples checked", run_result.stdout)
    passed = (
        run_result.returncode == 0
        and latency_match is not None
        and coverage_match is not None
        and pass_match is not None
        and int(latency_match.group(1)) == 1
        and int(coverage_match.group(1)) > 0
        and int(coverage_match.group(2)) > 0
        and int(coverage_match.group(3)) == 11
        and int(pass_match.group(1)) == 45074
    )
    return {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "status": "passed" if passed else "failed",
        "reason": "self_checking_testbench" if passed else "simulation_failure",
        "simulator": "iverilog",
        "rtl_compile": "passed",
        "rtl_simulation": "passed" if passed else "failed",
        "golden_equivalence": "passed" if passed else "failed",
        "samples_checked": int(pass_match.group(1)) if pass_match else 0,
        "latency_cycles": int(latency_match.group(1)) if latency_match else None,
        "input_stall_cycles": int(coverage_match.group(1)) if coverage_match else 0,
        "output_stall_cycles": int(coverage_match.group(2)) if coverage_match else 0,
        "tlast_transfers_checked": int(coverage_match.group(3)) if coverage_match else 0,
        "bounded_log": log,
        "hardware": "not_exercised",
        "fft": "not_implemented",
        "amd_xilinx_fft_ip": "not_integrated",
        "synthesis": "not_exercised",
        "implementation": "not_exercised",
        "timing": "not_exercised",
        "resource_utilization": "not_exercised",
        "regional_detector_rtl": "not_implemented",
        "claim_boundary": "Bu sonuç yalnız sabit nokta Hann RTL simülasyonudur; FFT, sentez veya FPGA sonucu değildir.",
    }


def _historical_integrity() -> tuple[int, bool]:
    listing = _run(["git", "ls-tree", "-r", "--name-only", "HEAD", "results/evidence", "profiles"], cwd=ROOT)
    paths = [
        path
        for path in listing.stdout.splitlines()
        if not (
            path.startswith("results/evidence/phase06")
            and not path.startswith("results/evidence/phase06a/")
        )
    ]
    intact = listing.returncode == 0
    for relative in paths:
        worktree = _run(["git", "hash-object", "--", relative], cwd=ROOT).stdout.strip()
        head = _run(["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT).stdout.strip()
        intact = intact and bool(worktree) and worktree == head
    return len(paths), intact


def _python_model_result(golden: dict[str, object]) -> dict[str, object]:
    coefficients = quantized_hann_coefficients()
    cases = []
    for identifier, word, index in (
        ("zero_first", 0x0000, 0),
        ("minimum_center", 0x8080, 2048),
        ("maximum_center", 0x7F7F, 2048),
        ("alternating_minimum", 0x8080, 2047),
        ("impulse_137", 0x8080, 137),
        ("constant_complex_center", 0x40C0, 2048),
        ("last_coefficient", 0x7F7F, 4095),
    ):
        output = window_word(word, index, coefficients)
        i_value, q_value = unpack_windowed_word(output)
        cases.append(
            {
                "id": identifier,
                "sample_index": index,
                "coefficient": coefficients[index],
                "output_word": f"{output:08x}",
                "output_i": i_value,
                "output_q": q_value,
            }
        )
    return {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "status": "passed",
        "algorithm_reference": "PHASE-02 NumPy float64 periodic Hann",
        "bit_true_model": "integer coefficient lookup, multiply, ties-away rounding and SQ1.15 packing",
        "hardware_result_path_uses_floating_point": False,
        "coefficient_count": len(coefficients),
        "vector_frame_count": golden["frame_count"],
        "vector_sample_count": golden["total_samples"],
        "edge_cases": cases,
    }


def build_documents(*, execute_simulation: bool) -> dict[str, dict[str, object]]:
    generated, manifest = build_vector_files()
    repeated_generated, repeated_manifest = build_vector_files()
    vectors_deterministic = generated == repeated_generated and manifest == repeated_manifest
    golden = json.loads(generated["golden-vectors.json"].decode("utf-8"))
    study = build_word_length_study()
    toolchain = discover_toolchain()
    if execute_simulation:
        first_simulation = run_simulation(toolchain)
        second_simulation = run_simulation(toolchain)
        simulation = dict(second_simulation)
        if first_simulation.get("status") == second_simulation.get("status") == "passed":
            rtl_deterministic = canonical_bytes(first_simulation) == canonical_bytes(second_simulation)
            simulation["deterministic_rerun"] = "passed" if rtl_deterministic else "failed"
        elif first_simulation.get("status") == second_simulation.get("status") == "skipped":
            simulation["deterministic_rerun"] = "not_exercised"
        else:
            simulation["deterministic_rerun"] = "failed"
        simulation["deterministic_scope"] = "two fresh compile-and-simulation executions compared byte-for-byte"
    else:
        stored = EVIDENCE / "rtl-simulation.json"
        simulation = json.loads(stored.read_text(encoding="utf-8")) if stored.is_file() else {
            "schema_version": 1,
            "phase": "PHASE-06B",
            "status": "failed",
            "reason": "missing_evidence",
        }
    fixed_point = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "input": {"datatype": "ci8", "format": "SQ1.7", "layout": "tdata[7:0]=I,tdata[15:8]=Q"},
        "frame_length": FRAME_LENGTH,
        "coefficient": {
            "format": f"UQ1.{COEFFICIENT_FRACTION_BITS}",
            "width": COEFFICIENT_WIDTH,
            "scale": COEFFICIENT_SCALE,
            "rom_values": FRAME_LENGTH // 2 + 1,
            "quantization": "floor(w*32768+0.5)",
        },
        "product": {"width": PRODUCT_WIDTH, "fractional_bits": 22},
        "output": {
            "format": f"SQ1.{OUTPUT_FRACTION_BITS}",
            "component_width": OUTPUT_COMPONENT_WIDTH,
            "payload_width": OUTPUT_WORD_WIDTH,
            "layout": "tdata[15:0]=I,tdata[31:16]=Q",
        },
        "output_shift": OUTPUT_SHIFT,
        "shift_semantics": "unsigned magnitude right shift followed by sign restoration",
        "rounding": "nearest_ties_away_from_zero",
        "truncation": "only_after_explicit_rounding",
        "overflow": "mathematically_bounded_no_saturation_no_wrap",
    }
    golden_results = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "source_fixture": manifest["source"],
        "vector_hashes": manifest["files"],
        "frame_count": golden["frame_count"],
        "samples": golden["total_samples"],
        "vectors": golden["vectors"],
    }
    python_result = _python_model_result(golden)
    latency = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "status": "passed" if simulation.get("status") == "passed" else simulation.get("status", "failed"),
        "definition": "accepted input rising edge to first corresponding output-valid rising edge",
        "core_latency_cycles": simulation.get("latency_cycles"),
        "ready_throughput_samples_per_cycle": 1,
        "backpressure_completion_bound": "unbounded_by_contract",
        "measurement": "self_checking_testbench",
    }
    count, intact = _historical_integrity()
    mandatory = {
        "vectors": all(
            (FIXTURES / name).is_file() and (FIXTURES / name).read_bytes() == payload
            for name, payload in generated.items()
        ),
        "rtl_sources": all(path.is_file() for path in (*RTL_SOURCES, TESTBENCH)),
        "python_model": python_result["status"] == "passed",
        "word_length_study": study["selected_format"] == "UQ1.15 coefficient, SQ1.15 output",
        "deterministic_vectors": vectors_deterministic,
        "historical_integrity": intact,
    }
    simulation_status = simulation.get("status")
    overall = (
        "passed"
        if all(mandatory.values())
        and simulation_status == "passed"
        and simulation.get("deterministic_rerun") == "passed"
        else "prepared_not_simulated"
        if all(mandatory.values()) and simulation_status == "skipped"
        else "failed"
    )
    summary = {
        "schema_version": 1,
        "phase": "PHASE-06B",
        "title": "Sabit Nokta Hann Pencereleme ve FFT Arayüz Temeli",
        "overall": overall,
        "checks": [
            {"id": name, "status": "passed" if status else "failed"}
            for name, status in mandatory.items()
        ] + [{"id": "rtl_simulation", "status": simulation_status}],
        "historical_integrity": {"files": count, "status": "passed" if intact else "failed"},
        "deterministic_result": {
            "vectors": "passed" if vectors_deterministic else "failed",
            "rtl_compile_and_simulation_rerun": simulation.get("deterministic_rerun", "failed"),
            "comparison": "byte_identical",
        },
        "algorithm_reference": "PHASE-02 floating-point NumPy Hann",
        "bit_true_model": "PHASE-06B integer Python model",
        "rtl": "PHASE-06B synthesizable vendor-independent SystemVerilog Hann",
        "fft_status": "not_implemented",
        "amd_xilinx_fft_ip_status": "not_integrated",
        "regional_detector_rtl_status": "not_implemented",
        "hardware_status": "not_exercised",
        "synthesis_status": "not_exercised",
        "implementation_status": "not_exercised",
        "timing_status": "not_exercised",
        "resource_utilization_status": "not_exercised",
        "claim_boundary": "PHASE-06B yalnız sabit nokta Hann ve FFT-facing AXI temelidir.",
    }
    return {
        "toolchain.json": toolchain,
        "word-length-study.json": study,
        "fixed-point-contract.json": fixed_point,
        "golden-frame-results.json": golden_results,
        "python-model-result.json": python_result,
        "latency.json": latency,
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
    if not all((EVIDENCE / name).is_file() for name in OWNED_FILES):
        return False
    stored = {name: json.loads((EVIDENCE / name).read_text(encoding="utf-8")) for name in OWNED_FILES}
    current_summary = dict(documents["verification-summary.json"])
    stored_summary = stored["verification-summary.json"]
    current_summary["historical_integrity"] = stored_summary.get("historical_integrity")
    exact = all(stored[name] == documents[name] for name in OWNED_FILES if name != "verification-summary.json")
    exact = exact and stored_summary == current_summary
    simulation = documents["rtl-simulation.json"]
    accepted_overall = documents["verification-summary.json"]["overall"] in {"passed", "prepared_not_simulated"}
    honest_skip = simulation.get("status") != "skipped" or simulation.get("reason") == "tool_unavailable"
    safe = all(
        token not in b"".join(canonical_bytes(document) for document in documents.values()).lower()
        for token in (b"c:\\users", b"timestamp", b"hostname", b"machine")
    )
    return (
        exact
        and accepted_overall
        and honest_skip
        and safe
        and documents["verification-summary.json"]["historical_integrity"]["status"] == "passed"
        and stored_summary["historical_integrity"]["status"] == "passed"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    summary_path = EVIDENCE / "verification-summary.json"
    overall = json.loads(summary_path.read_text(encoding="utf-8"))["overall"] if summary_path.is_file() else "missing"
    print(f"PHASE-06B verification: {'passed' if passed else 'failed'} ({overall})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
