#!/usr/bin/env python3
"""Compile-check the complete CI8-to-candidate PL boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "results/evidence/p0/candidate-dsp-runtime.json"
SOURCES = (
    ROOT / "algorithms/fpga/phase06a/rtl/axis_skid_buffer.sv",
    ROOT / "algorithms/fpga/phase06b/rtl/phase06b_pkg.sv",
    ROOT / "algorithms/fpga/phase06b/rtl/axis_hann_window.sv",
    ROOT / "algorithms/fpga/phase06c/rtl/phase06c_pkg.sv",
    ROOT / "algorithms/fpga/phase06c/rtl/axis_fft_wrapper.sv",
    ROOT / "algorithms/fpga/phase06d/rtl/amd_xfft_adapter.sv",
    ROOT / "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    ROOT / "algorithms/fpga/phase06i/rtl/phase06i_pkg.sv",
    ROOT / "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_region_bank.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_reducer_packetizer_top.sv",
    ROOT / "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_top.sv",
    ROOT / "algorithms/fpga/p0/tb/tb_p0_candidate_dsp_runtime.sv",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    fallback = Path(r"C:\msys64\ucrt64\bin") / f"{name}.exe"
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError(f"{name} bulunamadı")


def evaluate() -> dict[str, object]:
    iverilog = _tool("iverilog")
    with tempfile.TemporaryDirectory(prefix="p0-candidate-dsp-") as raw:
        executable = Path(raw) / "candidate_dsp_runtime.vvp"
        result = subprocess.run(
            [
                iverilog,
                "-g2012",
                "-Wall",
                "-t",
                "null",
                "-s",
                "p0_candidate_dsp_runtime_top",
                "-o",
                str(executable),
                *(str(path) for path in SOURCES),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout + result.stderr)

    return {
        "schema_version": 1,
        "status": "passed",
        "scope": "Complete CI8 input to PHASE-06I AXI64 candidate packet path compile boundary",
        "compiler": "Icarus Verilog SystemVerilog 2012",
        "top": "p0_candidate_dsp_runtime_top",
        "stages": [
            "CI8 AXI4-Stream input",
            "PHASE-06B Hann window",
            "PHASE-06D AMD 4096 FFT adapter",
            "PHASE-06F exact linear power",
            "P0 final candidate reducer",
            "PHASE-06I AXI64 packetizer",
        ],
        "functional_simulation": "not_run_in_compile_gate",
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in SOURCES
        },
        "claim_boundary": (
            "This evidence proves that the complete CI8-to-packetizer RTL hierarchy elaborates "
            "against the vendor FFT boundary. It does not claim vendor-IP functional simulation, "
            "Vivado timing, bitstream generation, DMA/driver integration, board execution or live HackRF processing."
        ),
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
        print("P0 tam aday DSP runtime derleme kanıtı eksik veya güncel değil.")
        return 1
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
