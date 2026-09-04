#!/usr/bin/env python3
"""Record the reproducible source/simulation gate for ADR-0040."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/evidence/phase08/persistent-weak-integration-v1.json"
MODEL_EVIDENCE = ROOT / "results/evidence/phase08/persistent-weak-model-v1.json"
REFERENCED_EVIDENCE = {
    "current_vivado_build": ROOT / "results/evidence/p0/vivado-50mhz-adr0040-p03.json",
    "full_rtl_hierarchy": ROOT / "results/evidence/p0/candidate-dsp-runtime-v2.json",
    "functional_reducer": ROOT / "results/evidence/p0/candidate-reducer-final-rtl-v2.json",
    "packetizer": ROOT / "results/evidence/p0/candidate-reducer-packetizer-v2.json",
    "pl_runtime_host": ROOT / "results/evidence/p0/os-cfar-pl-runtime-integration.json",
    "local_service_host": ROOT / "results/evidence/p0/ed-local-service-host-acceptance.json",
    "petalinux_arm_image": ROOT / "results/evidence/p0/ed-local-service-petalinux-build.json",
    "physical_board": ROOT / "results/evidence/p0/adr0040-physical-acceptance.json",
}
SOURCE_PATHS = (
    "algorithms/ps/persistent_weak_cfar.py",
    "algorithms/rtl/p0_os_cfar.py",
    "algorithms/rtl/p0_candidate_reducer.py",
    "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    "algorithms/fpga/p0/rtl/p0_weak_candidate_grouping.sv",
    "algorithms/fpga/p0/rtl/p0_weak_nomination_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
    "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv",
    "platforms/embedded/phase06i/include/phase06i_transport_abi.h",
    "platforms/embedded/p0/include/p0_persistent_weak.h",
    "platforms/embedded/p0/src/p0_persistent_weak.c",
    "platforms/embedded/p0/include/p0_ed_pipeline.h",
    "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    "app/operator_console/live_ed.py",
    "scripts/create_p0_vivado_project.tcl",
    "scripts/evaluate_p0_persistent_weak.py",
    "scripts/verify_p0_persistent_weak_integration.py",
)
PYTEST_TARGETS = (
    "tests/p0/test_p0_candidate_packet_classes_rtl.py",
    "tests/p0/test_p0_weak_nomination_rtl.py",
    "tests/p0/test_p0_weak_nomination_top_rtl.py",
    "tests/p0/test_p0_ed_pipeline_weak.py",
    "tests/p0/test_p0_persistent_weak_c.py",
    "tests/p0/test_p0_persistent_weak_cfar.py",
    "tests/p0/test_p0_persistent_weak_evaluation.py",
    "tests/test_live_ed_session.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_host_source(name: str) -> Path:
    if "/" in name:
        return ROOT / name
    candidates = (
        ROOT / "platforms/embedded/p0/src" / name,
        ROOT / "platforms/embedded/p0/include" / name,
        ROOT / "platforms/embedded/p0/petalinux" / name,
        ROOT / "platforms/embedded/phase06i/include" / name,
        ROOT / "platforms/embedded/phase06j/src" / name,
        ROOT / "platforms/embedded/phase06j/include" / name,
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def _evidence_hashes_current(path: Path) -> bool:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "passed":
        return False
    source_hashes = document.get("source_sha256", document.get("sources", {}))
    if not source_hashes:
        return False
    for name, digest in source_hashes.items():
        source = _resolve_host_source(name) if path.name.startswith("ed-local") else ROOT / name
        if not source.is_file() or _sha256(source) != digest:
            return False
    for name, digest in document.get("acceptance_source_sha256", {}).items():
        source = ROOT / name
        if not source.is_file() or _sha256(source) != digest:
            return False
    return True


def _model_gate() -> tuple[bool, dict[str, object]]:
    model = json.loads(MODEL_EVIDENCE.read_text(encoding="utf-8"))
    noise = model.get("noise_scenarios", [])
    invariance = model.get("frequency_invariance", [])
    passed = (
        model.get("implementation_status")
        == "top8_reference_model_passed"
        and len(noise) == 3
        and all(item.get("false_confirmed_windows") == 0 for item in noise)
        and len(invariance) == 5
        and all(item.get("confirmed") is True for item in invariance)
    )
    return passed, {
        "trials_per_noise_profile": noise[0]["window_trials"] if noise else 0,
        "noise_profiles": len(noise),
        "false_confirmed_windows": sum(
            int(item.get("false_confirmed_windows", 0)) for item in noise
        ),
        "frequency_positions": len(invariance),
        "confirmed_frequency_positions": sum(
            int(item.get("confirmed") is True) for item in invariance
        ),
    }


def _run_pytest() -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", *PYTEST_TARGETS, "-q"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip().splitlines()
    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "summary": output[-1] if output else "no output",
        "targets": list(PYTEST_TARGETS),
    }


def evaluate() -> dict[str, object]:
    reference_status = {
        name: {
            "path": path.relative_to(ROOT).as_posix(),
            "source_hashes_current": _evidence_hashes_current(path),
        }
        for name, path in REFERENCED_EVIDENCE.items()
    }
    model_passed, model_summary = _model_gate()
    pytest_result = _run_pytest()
    source_hashes = {name: _sha256(ROOT / name) for name in SOURCE_PATHS}
    source_gate = all(item["source_hashes_current"] for item in reference_status.values())
    passed = source_gate and model_passed and pytest_result["status"] == "passed"
    return {
        "schema": "p0-persistent-weak-integration-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "digital_physical_passed_live_rf_open" if passed else "failed",
        "profile": {
            "weak_threshold_db": 6.0,
            "window_frames": 32,
            "required_frames": 24,
            "peak_tolerance_bins": 2,
            "maximum_weak_nominations_per_frame": 1352,
            "maximum_tracked_weak_nominations_per_frame": 8,
        },
        "reference_evidence": reference_status,
        "model": model_summary,
        "pytest": pytest_result,
        "source_sha256": source_hashes,
        "deployment_gates": {
            "vivado_available_on_this_host": shutil.which("vivado") is not None,
            "vivado_synthesis_and_route_passed": reference_status[
                "current_vivado_build"
            ]["source_hashes_current"],
            "current_bitstream_generated": reference_status[
                "current_vivado_build"
            ]["source_hashes_current"],
            "petalinux_build_available_on_this_host": shutil.which("petalinux-build") is not None,
            "petalinux_build_available_in_vm": True,
            "current_petalinux_image_built": reference_status["petalinux_arm_image"][
                "source_hashes_current"
            ],
            "current_sources_run_on_arm_board": reference_status["physical_board"][
                "source_hashes_current"
            ],
            "current_sources_live_rf_acceptance": False,
        },
        "current_physical_evidence": "results/evidence/p0/adr0040-physical-acceptance.json",
        "historical_physical_evidence": [
            "results/evidence/p0/vivado-50mhz.json",
            "results/evidence/p0/ed-throughput-physical-acceptance.json",
            "results/evidence/p0/ed-service-v3-cold-boot-acceptance.json",
        ],
        "claim_boundary": (
            "Current ADR-0040 sources pass the top-8 reference model, RTL, packet, host C, "
            "PetaLinux packaging and persistent-image ZedBoard digital function/throughput "
            "acceptance. Blind live-RF detection probability, field false-alarm rate and "
            "calibrated RF accuracy remain open."
        ),
    }


def check() -> bool:
    try:
        document = json.loads(OUTPUT.read_text(encoding="utf-8"))
        return (
            document.get("status") == "digital_physical_passed_live_rf_open"
            and all(
                _sha256(ROOT / name) == digest
                for name, digest in document.get("source_sha256", {}).items()
            )
            and all(
                item.get("source_hashes_current") is True
                for item in document.get("reference_evidence", {}).values()
            )
            and document.get("deployment_gates", {}).get(
                "vivado_synthesis_and_route_passed"
            ) is True
            and document.get("deployment_gates", {}).get(
                "current_bitstream_generated"
            ) is True
            and document.get("deployment_gates", {}).get(
                "current_sources_run_on_arm_board"
            ) is True
            and document.get("deployment_gates", {}).get(
                "current_sources_live_rf_acceptance"
            ) is False
            and document.get("deployment_gates", {}).get(
                "current_petalinux_image_built"
            ) is True
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        document = evaluate()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    passed = check()
    print(f"ADR-0040 kaynak/simülasyon kapısı: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
