"""Offline/loopback-only P0 ET mathematical acceptance."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.et import AnalogDeceptionConfig, AnalogDeceptionEngine, ContinuousJammingConfig, ContinuousJammingEngine, ETMissionController, SafetyMode


def evaluate() -> dict[str, object]:
    engine = ContinuousJammingEngine()
    waveform_results = []
    configs = (
        ContinuousJammingConfig("single", 48_000, 0.25, (4_000.0,)),
        ContinuousJammingConfig("multiple", 48_000, 0.25, (-8_000.0, 0.0, 8_000.0)),
        ContinuousJammingConfig("barrage", 48_000, 0.25),
    )
    overall = True
    for config in configs:
        result = engine.generate(config)
        frequencies, power = engine.spectrum(result.samples, result.sample_rate_hz)
        if config.family == "single":
            measured = [float(frequencies[int(np.argmax(power))])]
            spectral_pass = abs(measured[0] - config.offsets_hz[0]) <= result.sample_rate_hz / result.samples.size
            flatness = None
        elif config.family == "multiple":
            strongest = np.argpartition(power, -len(config.offsets_hz))[-len(config.offsets_hz):]
            measured = sorted(float(frequencies[index]) for index in strongest)
            spectral_pass = all(abs(actual - expected) <= result.sample_rate_hz / result.samples.size for actual, expected in zip(measured, sorted(config.offsets_hz)))
            flatness = None
        else:
            positive = power[power > 0]
            flatness = float(np.exp(np.mean(np.log(positive))) / np.mean(positive))
            measured = []
            spectral_pass = flatness >= 0.50
        passed = spectral_pass and result.peak_magnitude <= 0.7000000001
        overall = overall and passed
        waveform_results.append({"family": config.family, "expected_offsets_hz": config.offsets_hz if config.family != "barrage" else None, "measured_offsets_hz": measured, "spectral_flatness": flatness, "peak_magnitude": result.peak_magnitude, "rms_magnitude": result.rms_magnitude, "status": "passed" if passed else "failed"})

    audio_rate = 48_000
    time = np.arange(audio_rate, dtype=np.float64) / audio_rate
    audio = np.sin(2.0 * np.pi * 1_000.0 * time)
    deception_results = []
    deception_engine = AnalogDeceptionEngine()
    for mode in ("FM", "NFM"):
        result = deception_engine.generate(audio, AnalogDeceptionConfig(mode=mode, duration_seconds=0.25))
        passed = result.loopback_correlation >= 0.999 and result.peak_magnitude <= 0.7000000001
        overall = overall and passed
        deception_results.append({"mode": mode, "loopback_correlation": result.loopback_correlation, "peak_magnitude": result.peak_magnitude, "duration_seconds": result.duration_seconds, "status": "passed" if passed else "failed"})

    safety = ETMissionController(SafetyMode.HARDWARE_TX_LOCKED)
    locked = False
    try:
        safety.start(duration_seconds=1.0, detail="acceptance")
    except PermissionError:
        locked = True
    safety.set_mode(SafetyMode.LOOPBACK)
    safety.start(duration_seconds=1.0, detail="acceptance")
    safety.emergency_stop()
    latched = False
    try:
        safety.start(duration_seconds=1.0, detail="acceptance")
    except RuntimeError:
        latched = True
    safety_pass = locked and latched and safety.state == "ACİL DURDURMA"
    overall = overall and safety_pass
    return {"schema_version": 1, "status": "passed" if overall else "failed", "waveforms": waveform_results, "analog_deception": deception_results, "safety": {"hardware_tx_locked": locked, "emergency_stop_latched": latched, "real_tx_backend": "not_implemented", "status": "passed" if safety_pass else "failed"}, "claim_boundary": "Offline complex baseband and local loopback only; no RF transmission or RF power claim."}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
