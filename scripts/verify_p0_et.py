"""KTR-5.1–5.4 offline/loopback ET mathematical acceptance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.et import (  # noqa: E402
    AnalogDeceptionConfig,
    AnalogDeceptionEngine,
    ContinuousJammingConfig,
    ContinuousJammingEngine,
    ETMissionController,
    GNSSScenario,
    GNSSScenarioValidator,
    InterleavedConfig,
    InterleavedTaskController,
    SafetyMode,
)


EVIDENCE = ROOT / "results" / "evidence" / "p0" / "et-golden.json"
REFERENCE_URLS = {
    "obw99": "https://www.etsi.org/deliver/etsi_ts/125100_125199/125141/11.06.00_60/ts_125141v110600p.pdf",
    "gps_l1_ca": "https://www.gps.gov/interface-control-documents-icds-interface-specifications-iss",
    "gps_prn_assignments": "https://www.gps.gov/pseudorandom-noise-code-assignments",
    "time_shared_sensing": "https://www.mdpi.com/2072-4292/13/15/3043",
    "reactive_response_delay": "https://www.mdpi.com/1999-5903/17/10/474",
}


def _continuous_acceptance() -> list[dict[str, object]]:
    engine = ContinuousJammingEngine()
    configs = (
        ContinuousJammingConfig("single", 48_000, 0.25, (4_000.0,)),
        ContinuousJammingConfig("multiple", 48_000, 0.25, (-8_000.0, 0.0, 8_000.0)),
        ContinuousJammingConfig("barrage", 48_000, 0.25, barrage_bandwidth_hz=16_000.0),
        ContinuousJammingConfig("sweep", 48_000, 0.50, sweep_start_hz=-9_000.0, sweep_stop_hz=9_000.0),
    )
    records: list[dict[str, object]] = []
    for config in configs:
        result = engine.generate(config)
        frequencies, power = engine.spectrum(result.samples, result.sample_rate_hz)
        record: dict[str, object] = {
            "family": config.family,
            "sample_count": int(result.samples.size),
            "peak_magnitude": result.peak_magnitude,
            "rms_magnitude": result.rms_magnitude,
            "obw99_hz": result.occupied_bandwidth_hz,
            "finite": bool(np.all(np.isfinite(result.samples))),
        }
        if config.family in {"single", "multiple"}:
            strongest = np.argpartition(power, -len(config.offsets_hz))[-len(config.offsets_hz) :]
            measured = sorted(float(frequencies[index]) for index in strongest)
            expected = sorted(config.offsets_hz)
            resolution = result.sample_rate_hz / result.samples.size
            spectral_pass = all(abs(actual - target) <= resolution for actual, target in zip(measured, expected))
            record.update(expected_offsets_hz=expected, measured_offsets_hz=measured)
        elif config.family == "barrage":
            support = np.abs(frequencies) <= config.barrage_bandwidth_hz / 2.0
            in_band_ratio = float(np.sum(power[support]) / np.sum(power))
            positive = power[support & (power > 0)]
            flatness = float(np.exp(np.mean(np.log(positive))) / np.mean(positive))
            spectral_pass = (
                in_band_ratio >= 0.999999
                and flatness >= 0.50
                and config.barrage_bandwidth_hz * 0.95 <= result.occupied_bandwidth_hz <= config.barrage_bandwidth_hz
            )
            record.update(in_band_power_ratio=in_band_ratio, spectral_flatness=flatness)
        else:
            instantaneous = (
                np.angle(result.samples[1:] * np.conj(result.samples[:-1]))
                * result.sample_rate_hz
                / (2.0 * np.pi)
            )
            start_hz = float(np.mean(instantaneous[:100]))
            stop_hz = float(np.mean(instantaneous[-100:]))
            progression = float(np.corrcoef(np.arange(instantaneous.size), instantaneous)[0, 1])
            spectral_pass = (
                abs(start_hz - config.sweep_start_hz) <= 50.0
                and abs(stop_hz - config.sweep_stop_hz) <= 50.0
                and progression >= 0.999999
                and len(result.sweep_sub_bands_hz) == 8
            )
            record.update(start_hz=start_hz, stop_hz=stop_hz, progression_correlation=progression)
        passed = (
            spectral_pass
            and bool(record["finite"])
            and result.peak_magnitude <= config.output_peak + 1e-12
            and not result.samples.flags.writeable
        )
        record["status"] = "passed" if passed else "failed"
        records.append(record)
    return records


def _interleaved_acceptance() -> list[dict[str, object]]:
    engine = InterleavedTaskController()
    records: list[dict[str, object]] = []
    for scenario in ("absent", "present", "intermittent", "edge"):
        config = InterleavedConfig(scenario=scenario)
        first = engine.run(config)
        second = engine.run(config)
        activations = [window.index for window in first.windows if window.task_active]
        starts = [
            window.index
            for window in first.windows
            if window.task_active and (window.index == 0 or not first.windows[window.index - 1].task_active)
        ]
        deterministic = (
            first.timeline == second.timeline
            and np.array_equal(first.analysis_samples, second.analysis_samples)
            and np.array_equal(first.task_output_samples, second.task_output_samples)
            and np.array_equal(first.task_gate, second.task_gate)
        )
        mutually_exclusive = all(
            (window.state == "DİNLE" and window.measured_band_power is not None and not window.task_active)
            or (window.state == "GÖREV" and window.measured_band_power is None and window.task_active)
            or (window.state in {"GECİKME", "KORUMA"} and window.measured_band_power is None and not window.task_active)
            for window in first.windows
        )
        gate_valid = (
            int(np.count_nonzero(first.task_gate)) == first.task_window_count * config.window_samples
            and np.all(first.task_output_samples[~first.task_gate] == 0.0)
            and first.task_output_samples.size == first.analysis_samples.size
        )
        schedule_valid = all(
            start >= config.response_delay_windows
            and first.timeline[start - config.response_delay_windows : start] == ("GECİKME",) * config.response_delay_windows
            and start + config.task_windows < len(first.timeline)
            and first.timeline[start + config.task_windows] == "KORUMA"
            for start in starts
        )
        if np.any(first.task_gate):
            active = first.task_output_samples[first.task_gate]
            measured_frequency_hz = float(
                np.median(np.angle(active[1:] * np.conj(active[:-1]))) * config.sample_rate_hz / (2.0 * np.pi)
            )
            spectral_valid = abs(measured_frequency_hz - config.target_offset_hz) <= 1e-9
            peak_valid = abs(float(np.max(np.abs(active))) - config.output_peak) <= 1e-12
        else:
            measured_frequency_hz = None
            spectral_valid = True
            peak_valid = float(np.max(np.abs(first.task_output_samples))) == 0.0
        if scenario == "absent":
            expected = not activations and all(window.decision == "PASİF" for window in first.windows)
            timeline_valid = first.timeline == ("DİNLE",) * config.windows
        else:
            expected = bool(starts)
            timeline_valid = all(state in first.timeline for state in ("DİNLE", "GECİKME", "GÖREV", "KORUMA"))
        passed = (
            expected
            and deterministic
            and timeline_valid
            and mutually_exclusive
            and gate_valid
            and schedule_valid
            and spectral_valid
            and peak_valid
            and first.final_state == "DİNLE"
            and not first.analysis_samples.flags.writeable
            and not first.task_output_samples.flags.writeable
            and not first.task_gate.flags.writeable
        )
        records.append(
            {
                "scenario": scenario,
                "analysis_input_samples": int(first.analysis_samples.size),
                "activation_indices": activations,
                "activation_starts": starts,
                "timeline": first.timeline,
                "final_state": first.final_state,
                "deterministic": deterministic,
                "listen_windows": first.listen_window_count,
                "response_delay_windows": first.response_delay_window_count,
                "task_windows": first.task_window_count,
                "guard_windows": first.guard_window_count,
                "task_duty_cycle": first.task_duty_cycle,
                "task_output_samples": int(first.task_output_samples.size),
                "active_output_samples": int(np.count_nonzero(first.task_gate)),
                "task_frequency_hz": measured_frequency_hz,
                "listen_task_mutually_exclusive": mutually_exclusive,
                "gate_valid": gate_valid,
                "schedule_valid": schedule_valid,
                "status": "passed" if passed else "failed",
            }
        )
    return records


def _interleaved_negative_acceptance() -> dict[str, object]:
    engine = InterleavedTaskController()
    bounded = engine.run(InterleavedConfig(scenario="present", windows=4))
    incomplete_cycle_rejected = (
        bounded.task_activation_count == 0
        and bounded.task_duty_cycle == 0.0
        and not np.any(bounded.task_gate)
        and np.all(bounded.task_output_samples == 0.0)
        and any(window.decision == "SÜRE YETERSİZ" for window in bounded.windows)
    )
    invalid_cases = (
        {"response_delay_windows": 0},
        {"task_windows": 0},
        {"guard_windows": 0},
        {"output_peak": 0.0},
        {"output_peak": 0.91},
    )
    rejected = 0
    for values in invalid_cases:
        try:
            InterleavedConfig(**values)
        except ValueError:
            rejected += 1
    passed = incomplete_cycle_rejected and rejected == len(invalid_cases)
    return {
        "incomplete_cycle_rejected": incomplete_cycle_rejected,
        "invalid_configurations_rejected": rejected,
        "invalid_configuration_count": len(invalid_cases),
        "status": "passed" if passed else "failed",
    }


def _analog_acceptance() -> list[dict[str, object]]:
    audio_rate = 48_000
    time = np.arange(audio_rate, dtype=np.float64) / audio_rate
    audio = np.sin(2.0 * np.pi * 1_000.0 * time) + 0.1 * np.sin(2.0 * np.pi * 10_000.0 * time)
    engine = AnalogDeceptionEngine()
    records: list[dict[str, object]] = []
    for mode in ("AM", "FM", "NFM"):
        config = AnalogDeceptionConfig(mode=mode, duration_seconds=0.25)
        result = engine.generate(audio, config)
        source_axis = np.arange(result.normalized_audio.size, dtype=np.float64) / config.audio_sample_rate_hz
        target_axis = np.arange(result.samples.size, dtype=np.float64) / config.sample_rate_hz
        reference = np.interp(target_axis, source_axis, result.normalized_audio, left=0.0, right=0.0)
        if mode == "AM":
            recovered = (np.abs(result.samples) / config.output_peak - 0.5) * 2.0
            correlation = float(np.corrcoef(reference, recovered)[0, 1])
        else:
            recovered = (
                np.angle(result.samples[1:] * np.conj(result.samples[:-1]))
                * config.sample_rate_hz
                / (2.0 * np.pi * config.deviation_hz)
            )
            correlation = float(np.corrcoef(reference[1:], recovered)[0, 1])
        audio_spectrum = np.abs(np.fft.rfft(result.normalized_audio)) ** 2
        audio_frequencies = np.fft.rfftfreq(result.normalized_audio.size, d=1.0 / config.audio_sample_rate_hz)
        out_of_band_ratio = float(
            np.sum(audio_spectrum[audio_frequencies > config.audio_bandwidth_hz * 1.5]) / np.sum(audio_spectrum)
        )
        passed = (
            correlation >= 0.999
            and result.loopback_correlation >= 0.999
            and result.peak_magnitude <= config.output_peak + 1e-12
            and out_of_band_ratio <= 1e-4
            and np.all(np.isfinite(result.samples))
        )
        records.append(
            {
                "mode": mode,
                "independent_loopback_correlation": correlation,
                "engine_loopback_correlation": result.loopback_correlation,
                "out_of_band_audio_power_ratio": out_of_band_ratio,
                "peak_magnitude": result.peak_magnitude,
                "sample_count": int(result.samples.size),
                "status": "passed" if passed else "failed",
            }
        )
    return records


def _gnss_acceptance() -> list[dict[str, object]]:
    validator = GNSSScenarioValidator()
    cases = (
        ("valid_metadata", GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (3, 8, 63)), True),
        ("non_utc_offset", GNSSScenario(39.9334, 32.8597, "2026-08-16T15:00:00+03:00", (3,)), False),
        ("prn_out_of_range", GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (64,)), False),
        ("missing_metadata_source", GNSSScenario(39.9334, 32.8597, "2026-08-16T12:00:00Z", (3,), metadata_source=""), False),
        ("invalid_position_time", GNSSScenario(91.0, 32.8597, "not-a-time", ()), False),
    )
    records: list[dict[str, object]] = []
    for name, scenario, expected_valid in cases:
        result = validator.validate(scenario)
        passed = (
            result.valid is expected_valid
            and result.metadata_contract_valid is expected_valid
            and not result.waveform_available
            and not result.waveform_source_contract_valid
            and result.tx_state == "KİLİTLİ"
        )
        records.append(
            {
                "case": name,
                "expected_valid": expected_valid,
                "valid": result.valid,
                "errors": result.errors,
                "metadata_contract_valid": result.metadata_contract_valid,
                "waveform_available": result.waveform_available,
                "sample_count": 0,
                "tx_state": result.tx_state,
                "status": "passed" if passed else "failed",
            }
        )
    return records


def _safety_acceptance() -> dict[str, object]:
    locked_modes: dict[str, bool] = {}
    cabled_lab_context_recorded = False
    for mode in (SafetyMode.CABLED_LAB, SafetyMode.HARDWARE_TX_LOCKED):
        controller = ETMissionController(mode)
        try:
            controller.start(duration_seconds=1.0, detail="acceptance")
        except PermissionError:
            locked_modes[mode.value] = True
        else:
            locked_modes[mode.value] = False
            if mode is SafetyMode.CABLED_LAB:
                cabled_lab_context_recorded = bool(
                    controller.log and "FARADAY LAB" in controller.log[-1].detail
                )
    controller = ETMissionController(SafetyMode.LOOPBACK)
    controller.start(duration_seconds=1.0, detail="acceptance")
    controller.emergency_stop()
    try:
        controller.start(duration_seconds=1.0, detail="acceptance")
    except RuntimeError:
        emergency_latched = True
    else:
        emergency_latched = False
    passed = (
        not locked_modes[SafetyMode.CABLED_LAB.value]
        and locked_modes[SafetyMode.HARDWARE_TX_LOCKED.value]
        and cabled_lab_context_recorded
        and emergency_latched
        and not hasattr(controller, "transmit")
    )
    return {
        "locked_modes": locked_modes,
        "cabled_lab_context_recorded": cabled_lab_context_recorded,
        "emergency_stop_latched": emergency_latched,
        "transmit_method_present": hasattr(controller, "transmit"),
        "real_tx_backend": "not_implemented",
        "status": "passed" if passed else "failed",
    }


def evaluate() -> dict[str, object]:
    continuous = _continuous_acceptance()
    interleaved = _interleaved_acceptance()
    interleaved_negative = _interleaved_negative_acceptance()
    analog = _analog_acceptance()
    gnss = _gnss_acceptance()
    safety = _safety_acceptance()
    gates = {
        "KTR-5.1_continuous_offline": all(item["status"] == "passed" for item in continuous),
        "KTR-5.2_interleaved_offline_schedule": (
            all(item["status"] == "passed" for item in interleaved)
            and interleaved_negative["status"] == "passed"
        ),
        "KTR-5.3_analog_loopback": all(item["status"] == "passed" for item in analog),
        "KTR-5.4_gnss_metadata_only": all(item["status"] == "passed" for item in gnss),
        "tx_fail_closed": safety["status"] == "passed",
    }
    return {
        "schema_version": 3,
        "work_package": "ET-B",
        "status": "passed" if all(gates.values()) else "failed",
        "gates": gates,
        "continuous_waveforms": continuous,
        "interleaved_controller": interleaved,
        "interleaved_negative_safety": interleaved_negative,
        "analog_loopback": analog,
        "gnss_metadata": gnss,
        "safety": safety,
        "references": REFERENCE_URLS,
        "claim_boundary": (
            "Yalnız deterministik offline kompleks taban bant, zaman paylaşımlı görev tamponu, yerel "
            "loopback ve GPS L1 C/A metadata doğrulaması; RF yayını, RF güç/etki, ephemeris işleme "
            "veya GNSS dalga şekli yoktur."
        ),
    }


def check() -> bool:
    if not EVIDENCE.exists():
        return False
    expected = json.loads(json.dumps(evaluate(), ensure_ascii=False))
    return json.loads(EVIDENCE.read_text(encoding="utf-8")) == expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate()
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    current = not args.check or check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" and current else 1


if __name__ == "__main__":
    raise SystemExit(main())
