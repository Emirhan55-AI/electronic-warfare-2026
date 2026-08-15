#!/usr/bin/env python3
"""Write or read-only verify deterministic PHASE-06C wrapper-foundation evidence."""

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

from reference.rtl.fft_model import (
    CONFIG_FORWARD_FIXED,
    FRAME_LENGTH,
    INPUT_COMPONENT_WIDTH,
    INPUT_FRACTION_BITS,
    INPUT_WORD_WIDTH,
    OUTPUT_COMPONENT_WIDTH,
    OUTPUT_CONTAINER_WIDTH,
    OUTPUT_FRACTION_BITS,
    OUTPUT_WORD_WIDTH,
    PHASE_FACTOR_WIDTH,
    THEORETICAL_GROWTH_BITS,
    architecture_decision_study,
    selected_ip_configuration,
)
from reference.rtl.fft_vectors import build_vector_files


EVIDENCE = ROOT / "results" / "evidence" / "phase06c"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase06c"
OWNED_FILES = (
    "architecture-decision-study.json",
    "numerical-study.json",
    "fixed-point-contract.json",
    "python-model-result.json",
    "latency.json",
    "wrapper-simulation.json",
    "toolchain.json",
    "verification-summary.json",
)
RTL_SOURCES = (
    ROOT / "rtl" / "phase06a" / "rtl" / "axis_skid_buffer.sv",
    ROOT / "rtl" / "phase06c" / "rtl" / "phase06c_pkg.sv",
    ROOT / "rtl" / "phase06c" / "rtl" / "axis_fft_wrapper.sv",
    ROOT / "rtl" / "phase06c" / "tb" / "fft_ip_transport_stub.sv",
    ROOT / "rtl" / "phase06c" / "tb" / "tb_axis_fft_wrapper.sv",
)
TESTBENCH = RTL_SOURCES[-1]
MSYS2_UCRT64_BIN = Path("C:/msys64/ucrt64/bin")
FIXED_COMMANDS = {
    "iverilog": MSYS2_UCRT64_BIN / "iverilog.exe",
    "vvp": MSYS2_UCRT64_BIN / "vvp.exe",
}


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


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
        "phase": "PHASE-06C",
        "purpose": "Read-only discovery; no installation, AMD IP generation, synthesis or hardware access.",
        "tools": tools,
        "product_guide_assumption": "AMD PG109 v9.1 / Vivado 2026.1; no local guide copy or installed Vivado",
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


def run_wrapper_simulation(toolchain: dict[str, object]) -> dict[str, object]:
    if not (_tool_available(toolchain, "iverilog") and _tool_available(toolchain, "vvp")):
        return {
            "schema_version": 1,
            "phase": "PHASE-06C",
            "status": "skipped",
            "reason": "tool_unavailable",
            "wrapper_compile": "skipped",
            "wrapper_simulation": "skipped",
            "real_amd_fft_ip_simulation": "not_exercised",
        }
    with tempfile.TemporaryDirectory(prefix="phase06c-wrapper-") as temporary:
        output = Path(temporary) / "phase06c.vvp"
        try:
            compile_result = _run(
                [
                    _resolve_command("iverilog") or "iverilog",
                    "-g2012",
                    "-s",
                    "tb_axis_fft_wrapper",
                    "-o",
                    str(output),
                    *(str(path) for path in RTL_SOURCES),
                ],
                cwd=ROOT,
            )
            if compile_result.returncode:
                return {
                    "schema_version": 1,
                    "phase": "PHASE-06C",
                    "status": "failed",
                    "reason": "compile_failure",
                    "wrapper_compile": "failed",
                    "wrapper_simulation": "failed",
                    "real_amd_fft_ip_simulation": "not_exercised",
                    "bounded_log": _bounded_log(compile_result),
                }
            run_result = _run([_resolve_command("vvp") or "vvp", str(output)], cwd=ROOT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "schema_version": 1,
                "phase": "PHASE-06C",
                "status": "failed",
                "reason": "simulator_did_not_complete",
                "wrapper_compile": "failed",
                "wrapper_simulation": "failed",
                "real_amd_fft_ip_simulation": "not_exercised",
                "bounded_log": f"{type(exc).__name__}: simulator did not complete",
            }
    latency_match = re.search(r"PHASE-06C TB LATENCY: wrapper_boundary=(\d+) cycles", run_result.stdout)
    coverage_match = re.search(
        r"PHASE-06C TB COVERAGE: input_stalls=(\d+) output_stalls=(\d+) tlast=(\d+) configs=(\d+) events=(\d+)",
        run_result.stdout,
    )
    pass_match = re.search(r"PHASE-06C TB PASS: (\d+) samples checked", run_result.stdout)
    passed = (
        run_result.returncode == 0
        and latency_match is not None
        and coverage_match is not None
        and pass_match is not None
        and int(latency_match.group(1)) == 2
        and int(coverage_match.group(1)) > 0
        and int(coverage_match.group(2)) > 0
        and int(coverage_match.group(3)) == 11
        and int(coverage_match.group(4)) == 3
        and int(coverage_match.group(5)) == 63
        and int(pass_match.group(1)) == 45074
    )
    return {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "status": "passed" if passed else "failed",
        "reason": "self_checking_wrapper_transport_testbench" if passed else "simulation_failure",
        "simulator": "iverilog",
        "wrapper_compile": "passed",
        "wrapper_simulation": "passed" if passed else "failed",
        "transport_stub_equivalence": "passed" if passed else "failed",
        "transport_stub_is_fft": False,
        "samples_checked": int(pass_match.group(1)) if pass_match else 0,
        "wrapper_boundary_latency_cycles": int(latency_match.group(1)) if latency_match else None,
        "input_stall_cycles": int(coverage_match.group(1)) if coverage_match else 0,
        "output_stall_cycles": int(coverage_match.group(2)) if coverage_match else 0,
        "tlast_transfers_checked": int(coverage_match.group(3)) if coverage_match else 0,
        "configuration_transfers_checked": int(coverage_match.group(4)) if coverage_match else 0,
        "event_bitmap_checked": int(coverage_match.group(5)) if coverage_match else 0,
        "testbench_accounting": {
            "samples": "1 latency probe + 40960 ten-frame samples + 17 partial-frame samples + 4096 post-reset samples = 45074",
            "tlast": "10 main-frame TLAST transfers + 1 post-reset frame TLAST transfer = 11",
            "config": "one handshake after each of three resets: initial startup, post-latency-probe reset, and mid-frame reset",
            "input_stalls": "cycles where external s_axis_tvalid=1 and s_axis_tready=0",
            "output_stalls": "cycles where external m_axis_tvalid=1 and m_axis_tready=0",
            "events": "all six stub event inputs asserted together for one cycle while external output is stalled; sticky result 0x3f",
        },
        "malformed_tlast_scope": (
            "wrapper forwards input TLAST to the abstract IP and captures injected event pins; "
            "real AMD malformed-TLAST timing/output behavior is not modeled by the transport stub"
        ),
        "bounded_log": _bounded_log(run_result),
        "real_amd_fft_ip_simulation": "not_exercised",
        "amd_ip_generation": "not_exercised",
        "xci": "not_created",
        "synthesis": "not_exercised",
        "implementation": "not_exercised",
        "timing": "not_exercised",
        "resource_utilization": "not_exercised",
        "hardware": "not_exercised",
        "claim_boundary": "Wrapper/control simulation only; the transport stub does not calculate an FFT.",
    }


def _historical_integrity() -> tuple[int, bool]:
    listing = _run(["git", "ls-tree", "-r", "--name-only", "HEAD", "results/evidence", "profiles"], cwd=ROOT)
    paths = [path for path in listing.stdout.splitlines() if not path.startswith("results/evidence/phase06c/")]
    intact = listing.returncode == 0
    for relative in paths:
        worktree = _run(["git", "hash-object", "--", relative], cwd=ROOT).stdout.strip()
        head = _run(["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT).stdout.strip()
        intact = intact and bool(worktree) and worktree == head
    return len(paths), intact


def build_documents(*, execute_simulation: bool) -> dict[str, dict[str, object]]:
    generated, manifest, numerical = build_vector_files()
    repeated, repeated_manifest, repeated_numerical = build_vector_files()
    vector_deterministic = (
        generated == repeated and manifest == repeated_manifest and numerical == repeated_numerical
    )
    golden = json.loads(generated["golden-vectors.json"].decode("utf-8"))
    architecture = architecture_decision_study()
    configuration = selected_ip_configuration()
    toolchain = discover_toolchain()
    if execute_simulation:
        first = run_wrapper_simulation(toolchain)
        second = run_wrapper_simulation(toolchain)
        simulation = dict(second)
        if first.get("status") == second.get("status") == "passed":
            simulation["deterministic_rerun"] = "passed" if canonical_bytes(first) == canonical_bytes(second) else "failed"
        elif first.get("status") == second.get("status") == "skipped":
            simulation["deterministic_rerun"] = "not_exercised"
        else:
            simulation["deterministic_rerun"] = "failed"
        simulation["deterministic_scope"] = "two fresh wrapper compile/simulation executions compared byte-for-byte"
    else:
        stored = EVIDENCE / "wrapper-simulation.json"
        simulation = json.loads(stored.read_text(encoding="utf-8")) if stored.is_file() else {
            "schema_version": 1,
            "phase": "PHASE-06C",
            "status": "failed",
            "reason": "missing_evidence",
        }

    fixed_point = {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "input": {
            "payload_width": INPUT_WORD_WIDTH,
            "component_width": INPUT_COMPONENT_WIDTH,
            "fractional_bits": INPUT_FRACTION_BITS,
            "format": "signed SQ1.15",
            "layout": "tdata[15:0]=I,tdata[31:16]=Q",
        },
        "transform": {
            "length": FRAME_LENGTH,
            "direction": "forward",
            "normalization": "unscaled",
            "input_order": "natural n=0..4095",
            "output_order": "natural unshifted k=0..4095",
        },
        "output": {
            "component_width": OUTPUT_COMPONENT_WIDTH,
            "container_width": OUTPUT_CONTAINER_WIDTH,
            "fractional_bits": OUTPUT_FRACTION_BITS,
            "format": "signed 29-bit two's-complement, 15 fractional bits; repository notation SQ14.15",
            "numeric_range": "[-8192, 8192 - 2^-15]",
            "payload_width": OUTPUT_WORD_WIDTH,
            "layout": "tdata[31:0]=I,tdata[63:32]=Q",
            "lane_padding": "bits[31:29] equal bit[28] for each lane",
        },
        "theoretical_growth_bits": THEORETICAL_GROWTH_BITS,
        "growth_definition": {
            "dft_accumulation_bits": 12,
            "complex_rotation_guard_bits": 1,
            "vendor_width_increase_bits": 13,
            "vendor_rule": "16 + log2(4096) + 1 = 29",
        },
        "phase_factor_width": PHASE_FACTOR_WIDTH,
        "rounding": "convergent",
        "configuration": {
            "expected_logical_word": f"0x{CONFIG_FORWARD_FIXED:02x}",
            "meaning": "channel 0 FWD_INV bit 0 = 1 (forward)",
            "wrapper_logical_bus_width": 8,
            "generated_ip_bus_width": "not_verified",
            "generated_ip_port_map": "not_verified",
        },
        "xk_index": {
            "logical_width": 12,
            "range": "0..4095",
            "wrapper_port_width": 12,
            "generated_tuser_width": "not_verified; PG109 requires zero-padding to a byte boundary",
        },
        "power_width": "not_frozen",
        "vendor_accuracy": "not_exercised",
    }
    python_result = {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "status": "passed",
        "algorithmic_reference": "PHASE-02 NumPy unscaled forward FFT",
        "quantized_model": "idealized convergent-rounded 29-bit Q15 external contract",
        "amd_c_model": "not_exercised",
        "frame_count": golden["frame_count"],
        "sample_count": golden["total_samples"],
        "vector_ids": [item["vector_id"] for item in golden["vectors"]],
        "selected_peak_indices": {
            item["vector_id"]: item["peak_index_unshifted"] for item in golden["vectors"]
        },
        "fixture_hashes": manifest["files"],
    }
    latency = {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "status": "passed" if simulation.get("status") == "passed" else simulation.get("status", "failed"),
        "definition": "external accepted input edge to external output-valid observation with immediate-response non-FFT stub",
        "wrapper_boundary_cycles": simulation.get("wrapper_boundary_latency_cycles"),
        "real_amd_fft_latency": "not_exercised",
        "complete_frame_latency": "not_exercised",
    }
    historical_count, historical_intact = _historical_integrity()
    mandatory = {
        "vectors": all(
            (FIXTURES / name).is_file() and (FIXTURES / name).read_bytes() == payload
            for name, payload in generated.items()
        ),
        "deterministic_vectors": vector_deterministic,
        "rtl_sources": all(path.is_file() for path in RTL_SOURCES),
        "architecture_decision": architecture["selection"] == "amd_xilinx_fft_logicore",
        "numerical_contract": numerical["selected_phase_factor_width"] == PHASE_FACTOR_WIDTH,
        "python_model": python_result["status"] == "passed",
        "historical_integrity": historical_intact,
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
        "phase": "PHASE-06C",
        "title": "4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli",
        "overall": overall,
        "checks": [
            {"id": name, "status": "passed" if status else "failed"}
            for name, status in mandatory.items()
        ] + [{"id": "wrapper_simulation", "status": simulation_status}],
        "historical_integrity": {
            "files": historical_count,
            "status": "passed" if historical_intact else "failed",
        },
        "deterministic_result": {
            "vectors": "passed" if vector_deterministic else "failed",
            "wrapper_compile_and_simulation_rerun": simulation.get("deterministic_rerun", "failed"),
            "comparison": "byte_identical",
        },
        "proven": [
            "architecture decision",
            "external numerical/scaling/ordering contract",
            "Python numerical characterization",
            "vendor-independent wrapper AXI/config/reset/TLAST/index/event behavior",
        ],
        "real_amd_fft_ip": "not_exercised",
        "vivado": "not_exercised_unavailable",
        "xsim": "not_exercised_unavailable",
        "amd_ip_generation": "not_exercised",
        "xci": "not_created",
        "synthesis": "not_exercised",
        "implementation": "not_exercised",
        "timing": "not_exercised",
        "resource_utilization": "not_exercised",
        "hardware": "not_exercised",
        "linear_power": "not_implemented",
        "psd": "not_implemented",
        "regional_detector_rtl": "not_implemented",
        "ui_capability_change": False,
        "phase04e1_behavior_change": False,
        "claim_boundary": "PHASE-06C is an architecture/contract/wrapper foundation, not functional AMD FFT RTL.",
    }
    architecture_document = dict(architecture)
    architecture_document["selected_configuration"] = configuration
    return {
        "architecture-decision-study.json": architecture_document,
        "numerical-study.json": numerical,
        "fixed-point-contract.json": fixed_point,
        "python-model-result.json": python_result,
        "latency.json": latency,
        "wrapper-simulation.json": simulation,
        "toolchain.json": toolchain,
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
    payload = b"".join(canonical_bytes(document) for document in documents.values()).lower()
    safe = all(token not in payload for token in (b"c:\\users", b"timestamp", b"hostname", b"machine"))
    summary = documents["verification-summary.json"]
    return (
        exact
        and safe
        and summary["overall"] in {"passed", "prepared_not_simulated"}
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
    print(f"PHASE-06C verification: {'passed' if passed else 'failed'} ({overall})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
