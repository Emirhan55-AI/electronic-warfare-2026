"""Verify the PHASE-10 one-band offline model and locked hardware boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.transmission import SingleBandNoiseEngine, SingleBandNoisePlan
from platforms.transmission import ETTransmitError, load_tx_safety_profile


DEFAULT_REPORT = ROOT / "build" / "acceptance" / "phase10-single-et" / "report.json"
PROFILE = ROOT / "config" / "p0" / "hackrf_et_tx.json"


def evaluate() -> dict[str, object]:
    plan = SingleBandNoisePlan(853_500_000, 854_500_000, 0.25, seed=2026)
    engine = SingleBandNoiseEngine()
    tile = engine.generate_tile(plan)
    summary = engine.summarize(plan, tile)
    ci8 = engine.encode_ci8(tile)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(tile))) ** 2
    frequencies = np.fft.fftshift(np.fft.fftfreq(tile.size, d=1.0 / plan.sample_rate_hz))
    outside = np.abs(frequencies) > plan.bandwidth_hz / 2.0
    outside_ratio = float(np.sum(spectrum[outside]) / np.sum(spectrum))
    profile = load_tx_safety_profile(PROFILE)
    try:
        profile.authorize(plan, txvga_db=0)
    except ETTransmitError as exc:
        locked = True
        lock_code = exc.code
    else:
        locked = False
        lock_code = ""
    gates = {
        "deterministic_finite_ci8": bool(np.all(np.isfinite(tile))) and len(ci8) == tile.size * 2,
        "single_band_spectral_support": outside_ratio <= 1e-12,
        "bounded_peak": summary.peak_magnitude <= plan.output_peak + 1e-12,
        "hardware_tx_fail_closed": locked and lock_code == "tx_gate_locked",
        "repository_profile_disabled": not profile.enabled and not profile.physical_gate_approved,
    }
    return {
        "schema_version": 1,
        "phase": "PHASE-10",
        "work_package": "TEKLI-GOREV-01",
        "software_status": "passed" if all(gates.values()) else "failed",
        "phase_status": "open_physical_gate",
        "gates": gates,
        "plan": {
            "lower_frequency_hz": plan.lower_frequency_hz,
            "upper_frequency_hz": plan.upper_frequency_hz,
            "center_frequency_hz": plan.center_frequency_hz,
            "bandwidth_hz": plan.bandwidth_hz,
            "duration_seconds": plan.duration_seconds,
            "sample_rate_hz": plan.sample_rate_hz,
            "mission_sample_count": plan.sample_count,
        },
        "waveform": {
            "tile_sample_count": tile.size,
            "tile_ci8_sha256": hashlib.sha256(ci8).hexdigest(),
            "peak_magnitude": summary.peak_magnitude,
            "rms_magnitude": summary.rms_magnitude,
            "measured_obw99_hz": summary.measured_obw99_hz,
            "outside_requested_band_power_ratio": outside_ratio,
        },
        "hardware": {
            "profile": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
            "enabled": profile.enabled,
            "physical_gate_approved": profile.physical_gate_approved,
            "device_serial_assigned": bool(profile.device_serial),
            "allowed_range_count": len(profile.allowed_frequency_ranges_hz),
            "observed_device": "not_connected",
            "tx_executed": False,
        },
        "claim_boundary": "İletimsiz CI8 ve fail-closed HackRF süreç sınırı doğrulandı; fiziksel RF çıkışı uygulanmış veya kabul edilmiş sayılmaz.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["software_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
