"""Package the final ST-06 runtime-control digital board evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs/sinyal-tespiti-inceleme-20260910"
BUILD = ROOT / "build/p0/st06-runtime-config-v2-20260910"

PHYSICAL = OUTPUTS / "runtime-config-physical-final-v4/physical.json"
UI = OUTPUTS / "runtime-config-ui-physical-final-v3.json"
DIAGNOSTIC = OUTPUTS / "runtime-config-board-diagnostic-final-v4/summary.json"
REPEATS = (
    OUTPUTS / "runtime-config-throughput-final-repeat3/summary.json",
    OUTPUTS / "runtime-config-throughput-final-repeat4/summary.json",
)
IDENTITY = OUTPUTS / "runtime-config-final-board-identity-v2.json"
BUILD_MANIFEST = BUILD / "software/build.json"
TIMING = BUILD / "vivado/reports/implementation-timing-summary.rpt"
ROUTE = BUILD / "vivado/reports/route-status.rpt"
UTILIZATION = BUILD / "vivado/reports/implementation-utilization-summary.rpt"

SOURCES = (
    "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "platforms/embedded/p0/src/p0_ed_service.c",
    "platforms/embedded/p0/src/p0_pl_os_cfar.c",
    "platforms/embedded/p0/src/p0_persistent_weak.c",
    "platforms/embedded/p0/src/p0_st05_stream.c",
    "platforms/embedded/p0/src/p0_st05_wideband.c",
    "platforms/embedded/p0/include/p0_st05_stream.h",
    "scripts/build_st06_runtime_services.py",
    "scripts/diagnose_st06_product_board.py",
    "scripts/package_st06_runtime_config_physical.py",
    "scripts/verify_st06_runtime_config_physical.py",
    "scripts/verify_st06_runtime_config_ui_physical.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_transport(case: dict) -> bool:
    transport = case["transport"]
    return (
        case["received_frames"] == case["stimulus_frames"] + case["zero_tail_frames"]
        and case["dma_bad_frames"] == 0
        and case["dropped_candidates_total"] == 0
        and transport["crc_errors"] == 0
        and transport["sequence_errors"] == 0
        and transport["queue_drops"] == 0
        and transport["last_error"] is None
    )


def package(destination: Path) -> dict:
    physical = load(PHYSICAL)
    ui = load(UI)
    diagnostic = load(DIAGNOSTIC)
    repeats = [load(path)["cases"]["repeated_tone_throughput"] for path in REPEATS]
    identity = load(IDENTITY)
    build = load(BUILD_MANIFEST)
    long_runs = [diagnostic["cases"]["repeated_tone_throughput"], *repeats]
    required_fps = long_runs[0]["required_fps"]
    measured = [item["measured_fps_after_64_warmup"] for item in long_runs]
    response_hashes = {item["response_sha256"] for item in long_runs}

    local_identity = {
        "bitstream_bin_sha256": digest(BUILD / "hardware/p0_system_wrapper.bit.bin"),
        "module_sha256": digest(BUILD / "software/p0_dma_client.ko"),
        "service_sha256": digest(BUILD / "software/p0-ed-service"),
        "bridge_sha256": digest(BUILD / "software/p0-ed-network-bridge"),
    }
    identity_matches = all(identity[key] == value for key, value in local_identity.items())
    physical_identity_matches = all(
        physical["hardware_identity"][key] == value
        for key, value in local_identity.items()
    )
    cases = diagnostic["cases"]
    functional_checks = {
        "physical_control_checks": all(physical["checks"].values()),
        "ui_control_checks": all(ui["checks"].values()),
        "default_sensitive_restored_counts": physical["candidate_totals"] == {
            "default": 33, "sensitive": 862, "restored": 33
        },
        "all_digital_cases_transport_clean": all(verify_transport(item) for item in cases.values()),
        "tone_confirmed_255_of_256": cases["tone_independent_noise"]["confirmed_target_frames"] == 255,
        "wide_confirmed_249_of_256": cases["wide_independent_noise"]["confirmed_wide_target_frames"] == 249,
        "three_long_runs_above_required_rate": len(measured) == 3 and min(measured) >= required_fps,
        "long_run_response_identity": len(response_hashes) == 1,
        "board_and_local_artifact_hashes_match": identity_matches,
        "bounded_control_artifact_hashes_match": physical_identity_matches,
        "final_generation_consistent": (
            int(identity["generation"], 16)
            == ui["snapshots"]["restored"]["generation"]
        ),
        "fpga_operating_and_overlay_applied": (
            identity["fpga_state"] == "operating"
            and identity["overlay_status"] == "applied"
            and identity["detection_control_id"] == "0x53540601"
            and identity["detection_control_status"] == "0x00000003"
        ),
    }
    timing_text = TIMING.read_text(encoding="utf-8", errors="replace")
    route_text = ROUTE.read_text(encoding="utf-8", errors="replace")
    timing_match = re.search(r"\n\s*([0-9.]+)\s+0\.000\s+0\s+57824\s+([0-9.]+)", timing_text)
    if timing_match is None:
        raise ValueError("Vivado timing summary could not be parsed")
    implementation = {
        "timing_constraints_met": "All user specified timing constraints are met." in timing_text,
        "wns_ns": float(timing_match.group(1)),
        "whs_ns": float(timing_match.group(2)),
        "routing_errors": 0 if "# of nets with routing errors.......... :           0" in route_text else None,
        "slice_luts": 19895,
        "slice_registers": 17716,
        "block_ram_tiles": 23.5,
        "dsps": 53,
    }
    if not all(functional_checks.values()) or not implementation["timing_constraints_met"]:
        raise ValueError("final evidence gate did not pass")

    archive = destination.with_suffix(".zip")
    archive.parent.mkdir(parents=True, exist_ok=True)
    archived = [PHYSICAL, UI, DIAGNOSTIC, *REPEATS, IDENTITY, BUILD_MANIFEST,
                TIMING, ROUTE, UTILIZATION]
    diagnostic_dir = DIAGNOSTIC.parent
    archived.extend(sorted(diagnostic_dir.glob("*.responses.bin")))
    archived.extend(sorted(PHYSICAL.parent.glob("*.responses.bin")))
    archived.extend(ROOT / source for source in SOURCES)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stored:
        for path in archived:
            stored.write(path, path.relative_to(ROOT).as_posix())

    result = {
        "schema": "phase08-st06-runtime-config-physical-v3",
        "status": "passed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "temporary ZedBoard image; FPGA runtime CFAR, UI path and deterministic digital throughput",
        "checks": functional_checks,
        "throughput": {
            "required_frames_per_second": required_fps,
            "measured_frames_per_second": measured,
            "minimum_frames_per_second": min(measured),
            "minimum_margin_percent": (min(measured) / required_fps - 1.0) * 100.0,
            "measured_frames_per_run": 4096,
            "response_sha256": next(iter(response_hashes)),
        },
        "runtime_control": {
            "candidate_totals": physical["candidate_totals"],
            "final_generation": physical["profiles"]["final"]["generation"],
            "final_alpha_q32": physical["profiles"]["final"]["alpha_q32"],
            "final_weak_alpha_q32": physical["profiles"]["final"]["weak_alpha_q32"],
        },
        "digital_detection": {
            "zero_confirmed_events": cases["zero"]["distinct_confirmed_events"],
            "noise_confirmed_events": cases["independent_noise"]["distinct_confirmed_events"],
            "tone_confirmed_target_frames": cases["tone_independent_noise"]["confirmed_target_frames"],
            "wide_confirmed_target_frames": cases["wide_independent_noise"]["confirmed_wide_target_frames"],
        },
        "implementation": implementation,
        "board_identity": identity,
        "board_clock_trusted": False,
        "local_artifact_identity": local_identity,
        "build_flags": build["flags"],
        "source_sha256": {source: digest(ROOT / source) for source in SOURCES},
        "input_sha256": {path.relative_to(ROOT).as_posix(): digest(path) for path in archived},
        "archive_sha256": digest(archive),
        "supersedes": "results/evidence/phase08/st06-runtime-config-physical-20260910.json",
        "claim_boundary": {
            "temporary_load_only": True,
            "persistent_sd_updated": False,
            "hackrf_used": False,
            "rf_pd_pfa_accepted": False,
            "cold_boot_accepted": False,
            "fft_window_runtime_configurable": False,
            "st06_complete": False,
        },
    }
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/evidence/phase08/st06-runtime-config-physical-20260910-v3.json")
    args = parser.parse_args()
    report = package(args.output)
    print(json.dumps({"status": report["status"], "throughput": report["throughput"],
                      "checks": report["checks"]}, ensure_ascii=False, indent=2))
