"""Build the source-bound ST-04 hierarchical detection architecture decision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "search_profile_baseline": "results/evidence/phase08/st04-search-profile-baseline-v1.json",
    "sweep_resolution": "results/evidence/phase08/st04-sweep-resolution-v1.json",
    "same_iq_resolution": "results/evidence/phase08/st04-same-iq-resolution-v1.json",
    "fpga_functional_capacity": "results/evidence/p0/candidate-reducer-final-rtl-v2.json",
    "fpga_post_route": "results/evidence/p0/vivado-50mhz-adr0040-p03.json",
}
SOURCES = (
    "scripts/evaluate_st04_architecture.py",
    "docs/decisions/ADR-0041-PHASE08-HIERARCHICAL-BLIND-DETECTION.md",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def build_report() -> dict[str, object]:
    baseline = _read_json(INPUTS["search_profile_baseline"])
    sweep = _read_json(INPUTS["sweep_resolution"])
    same_iq = _read_json(INPUTS["same_iq_resolution"])
    rtl = _read_json(INPUTS["fpga_functional_capacity"])
    vivado = _read_json(INPUTS["fpga_post_route"])

    sweep_profiles = {
        int(profile["requested_bin_width_hz"]): profile
        for profile in sweep["profiles"]  # type: ignore[index]
    }
    selected_sweep = sweep_profiles[25_000]
    same_iq_profiles = {
        int(profile["fft_size"]): profile
        for profile in same_iq["profiles"]  # type: ignore[index]
    }
    selected_same_iq = same_iq_profiles[16_384]
    capacity = rtl["capacity"]  # type: ignore[index]
    resources = vivado["post_route_resources"]  # type: ignore[index]
    timing = vivado["timing"]  # type: ignore[index]
    current_functional_fps = float(capacity["functional_frames_per_second"])  # type: ignore[index]
    direct_8msps_required_fps = 8_000_000 / 4_096
    direct_8msps_capacity_ratio = current_functional_fps / direct_8msps_required_fps
    slice_luts = resources["slice_luts"]  # type: ignore[index]

    return {
        "schema": "phase08-st04-hierarchical-detection-architecture-v1",
        "status": "architecture_selected",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase08_complete": False,
        "st04_complete": True,
        "transmit_enabled": False,
        "architecture": {
            "stage_0_full_band_discovery": {
                "owner": "host",
                "implementation": "official_hackrf_sweep",
                "range_hz": baseline["requested_range_hz"],
                "sample_rate_hz": 20_000_000,
                "requested_bin_width_hz": 25_000,
                "actual_bin_widths_hz": selected_sweep["actual_bin_widths_hz"],
                "median_full_sweep_seconds": selected_sweep["process_seconds_per_sweep"]["median"],
                "p95_full_sweep_seconds": selected_sweep["process_seconds_per_sweep"]["p95"],
                "validated_gap_free_sweeps": selected_sweep["validated_sweep_count"],
                "authority": "candidate_only",
            },
            "stage_1_candidate_refinement": {
                "owner": "host",
                "implementation": "8msps_hann_integrated_spectrum_two_lo",
                "sample_rate_hz": 8_000_000,
                "fft_size": 16_384,
                "bin_spacing_hz": selected_same_iq["bin_spacing_hz"],
                "same_recording_target_recovered": selected_same_iq["evaluation_truth"]["target_recovered_in_two_lo_on"],
                "same_recording_off_common_candidates": len(selected_same_iq["two_lo_off_matches"]),
                "authority": "rx_evidence_only",
            },
            "stage_2_detailed_confirmation": {
                "owner": "fpga_pl_and_arm_ps",
                "implementation": "2msps_hann_fft_os_cfar_multiscale_temporal",
                "sample_rate_hz": 2_000_000,
                "fft_size": 4_096,
                "bin_spacing_hz": 2_000_000 / 4_096,
                "functional_capacity_frames_per_second": current_functional_fps,
                "required_frames_per_second": float(capacity["required_frames_per_second"]),  # type: ignore[index]
                "functional_capacity_ratio": current_functional_fps / float(capacity["required_frames_per_second"]),  # type: ignore[index]
                "authority": "fpga_candidate_with_arm_temporal_state",
            },
        },
        "fpga_scaling_boundary": {
            "existing_4096_pipeline_direct_8msps_required_frames_per_second": direct_8msps_required_fps,
            "existing_pipeline_functional_capacity_frames_per_second": current_functional_fps,
            "direct_8msps_capacity_ratio": direct_8msps_capacity_ratio,
            "direct_8msps_existing_pipeline_meets_capacity": direct_8msps_capacity_ratio >= 1.0,
            "post_route_slice_luts_used": int(slice_luts["used"]),
            "post_route_slice_luts_available": int(slice_luts["available"]),
            "post_route_slice_lut_utilization_percent": float(slice_luts["utilization_percent"]),
            "post_route_slice_luts_free": int(slice_luts["available"]) - int(slice_luts["used"]),
            "setup_wns_ns": float(timing["setup_wns_ns"]),
            "hold_whs_ns": float(timing["hold_whs_ns"]),
            "decision": "do_not_reuse_existing_4096_pipeline_at_8msps",
            "claim_boundary": (
                "Bu hesap yalnız mevcut 4096-hücre RTL zincirinin doğrudan 8 MS/s tekrar kullanımını eler; "
                "başka bir FPGA mimarisinin yapılamayacağını kanıtlamaz."
            ),
        },
        "profile_decision": {
            "selected_for_controlled_blind_test": True,
            "selected_for_product": False,
            "stage_0_requested_bin_width_hz": 25_000,
            "stage_1_fft_size": 16_384,
            "stage_2_fft_size": 4_096,
            "reason": (
                "25 kHz tam bant sweep ölçümünde kaba profillerle aynı zaman sınıfında kalıp daha fazla frekans ayrıntısı verdi; "
                "16.384 aynı fiziksel kayıtta hedefi iki LO'da geri kazanıp kapalı kayıtta ortak aday üretmeyen tek profildi; "
                "mevcut 2 MS/s FPGA zinciri kapasiteyi karşılarken doğrudan 8 MS/s tekrar kullanım karşılamadı."
            ),
        },
        "open_acceptance_gates": [
            "Stage-0 sweep güçlerinden frekans-truth kullanmadan aday çıkarma ve adayları Stage-1'e otomatik aktarma.",
            "Farklı frekans, yayın ailesi, seviye ve sürelerde kontrollü kör RF matrisi.",
            "Sistem düzeyinde Pd, yanlış doğrulanmış olay/MHz-dakika ve p95 ilk tespit gecikmesi.",
            "Stage-1 RX adayının Stage-2 FPGA yeniden ayarı ve iki-LO yaşam döngüsüyle uçtan uca kabulü.",
        ],
        "input_evidence_sha256": {
            name: {"path": path, "sha256": _sha256(ROOT / path)}
            for name, path in INPUTS.items()
        },
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Önceki ST-04 mimari kanıtının üzerine yazılmaz.")
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "status": report["status"],
        "st04_complete": report["st04_complete"],
        "selected_for_product": report["profile_decision"]["selected_for_product"],
        "direct_8msps_capacity_ratio": report["fpga_scaling_boundary"]["direct_8msps_capacity_ratio"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
