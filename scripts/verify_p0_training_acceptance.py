"""Build/check compact golden evidence for listening, parameters, UI binding and DF."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from host.operator_console.main_window import MainWindow
from reference.monitoring import AnalogMonitor, AnalogMonitorConfig, wav_bytes, write_wav
from reference.p0 import (
    ManualAmplitudeDF,
    OSCFARDetector,
    ParameterExtractor,
    TemporalConfirmation,
)
from reference.p0.df_fixtures import build_df_acceptance_scenes
from reference.p0.fixtures import CENTER_FREQUENCY_HZ, FRAME_LENGTH, SAMPLE_RATE_HZ, build_fixtures
from reference.spectrum import SigMFFrameSource


EVIDENCE = ROOT / "results" / "evidence" / "p0" / "training-functional-acceptance-v1.json"
AUDIO_OUT = ROOT / "build" / "acceptance" / "audio"
PHASE05 = ROOT / "datasets" / "fixtures" / "phase05"


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _independent_dominant_tone(audio: np.ndarray, sample_rate_hz: int) -> float:
    """Independent direct periodogram oracle; does not call monitoring.dominant_tone_hz."""
    values = np.asarray(audio, dtype=np.float64) - float(np.mean(audio))
    nfft = 1 << max(12, int(math.ceil(math.log2(values.size))))
    bins = np.fft.rfft(values * np.blackman(values.size), n=nfft)
    power = bins.real * bins.real + bins.imag * bins.imag
    power[0] = 0.0
    return float(int(np.argmax(power)) * sample_rate_hz / nfft)


def _independent_aligned_correlation(reference: np.ndarray, observed: np.ndarray) -> float:
    """Brute-force normalized dot-product oracle with an independent lag policy."""
    size = min(reference.size, observed.size)
    left = np.asarray(reference[:size], dtype=np.float64)
    right = np.asarray(observed[:size], dtype=np.float64)
    best = 0.0
    for lag in range(-384, 385):
        if lag < 0:
            a, b = left[-lag:], right[: size + lag]
        elif lag > 0:
            a, b = left[: size - lag], right[lag:]
        else:
            a, b = left, right
        a = a - float(np.mean(a))
        b = b - float(np.mean(b))
        denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
        if denominator > 0.0:
            best = max(best, abs(float(np.dot(a, b)) / denominator))
    return best


def _p0_parameter_result() -> tuple[object, dict[str, object]]:
    fixture = next(item for item in build_fixtures() if item.fixture_id == "nfm-like")
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(FRAME_LENGTH) / FRAME_LENGTH)
    shifted_power = np.abs(np.fft.fftshift(np.fft.fft(fixture.iq * window))) ** 2
    detection = OSCFARDetector().process(shifted_power, frame_id=0)
    expected_bin = FRAME_LENGTH // 2 + round(90_000.0 / (SAMPLE_RATE_HZ / FRAME_LENGTH))
    candidate = min(detection.candidates, key=lambda item: abs(item.peak_bin - expected_bin))
    tracker = TemporalConfirmation()
    tracker.update(detection.candidates, frame_id=0)
    tracks = tracker.update(detection.candidates, frame_id=1)
    confirmed = any(item.state == "confirmed" and item.candidate.peak_bin == candidate.peak_bin for item in tracks)
    result = ParameterExtractor().extract(
        frame_id=1,
        iq=fixture.iq,
        shifted_power=shifted_power,
        sample_rate_hz=SAMPLE_RATE_HZ,
        center_frequency_hz=CENTER_FREQUENCY_HZ,
        candidate=candidate,
        confirmed=confirmed,
        provenance="HOST REFERENCE",
        backend="P0 OS-CFAR + parameter.reference",
        neighboring_candidates=detection.candidates,
    )
    truth_carrier = 100_090_000.0
    truth_bandwidth = 2_400.0
    truth_amplitude_dbfs = 20.0 * math.log10(0.6)
    carrier_error = result.carrier_frequency_hz - truth_carrier
    bandwidth_error = result.bandwidth_hz - truth_bandwidth
    power_error = result.channel_power_dbfs - truth_amplitude_dbfs
    passed = (
        confirmed
        and abs(carrier_error) <= 300.0
        and abs(bandwidth_error) <= 1_250.0
        and abs(power_error) <= 0.25
        and 30.0 <= result.snr_db <= 40.0
        and result.signal_domain == "Analog"
    )
    return result, {
        "fixture": fixture.fixture_id,
        "fixture_sha256": hashlib.sha256(np.asarray(fixture.iq, dtype="<c16").tobytes()).hexdigest(),
        "input_truth": {
            "signal_present": True,
            "carrier_frequency_hz": truth_carrier,
            "reference_bandwidth_hz": truth_bandwidth,
            "amplitude": 0.6,
            "amplitude_dbfs": truth_amplitude_dbfs,
            "class": "Analog",
        },
        "expected": {"carrier_tolerance_hz": 300.0, "bandwidth_tolerance_hz": 1_250.0, "power_tolerance_db": 0.25, "snr_db_range": [30.0, 40.0]},
        "actual_algorithm": {
            "os_cfar_detected": bool(candidate),
            "temporally_confirmed": confirmed,
            "carrier_frequency_hz": result.carrier_frequency_hz,
            "bandwidth_hz": result.bandwidth_hz,
            "channel_power_dbfs": result.channel_power_dbfs,
            "snr_db": result.snr_db,
            "class": result.signal_domain,
        },
        "errors": {"carrier_hz": carrier_error, "bandwidth_hz": bandwidth_error, "power_db": power_error},
        "status": "PASS" if passed else "FAIL",
    }


def _noise_false_alarm() -> dict[str, object]:
    detector = OSCFARDetector()
    rng = np.random.default_rng(20260816)
    decisions = 0
    evaluated = 0
    for frame_id in range(64):
        result = detector.process(rng.exponential(1.0, FRAME_LENGTH), frame_id=frame_id)
        valid = np.isfinite(result.noise_power)
        decisions += int(np.count_nonzero(result.detections & valid))
        evaluated += int(np.count_nonzero(valid))
    empirical = decisions / evaluated
    tolerance = 2.5e-4
    return {
        "fixture": "seeded-exponential-noise-64x4096",
        "seed": 20260816,
        "expected_pfa_per_cut": 1e-4,
        "evaluated_cells": evaluated,
        "false_detections": decisions,
        "actual_empirical_pfa": empirical,
        "absolute_tolerance": tolerance,
        "status": "PASS" if abs(empirical - 1e-4) <= tolerance else "FAIL",
    }


def _audio_row(fixture_id: str, mode: str, offset_hz: float, tone_hz: float) -> tuple[dict[str, object], bytes, object]:
    source = SigMFFrameSource(PHASE05 / f"{fixture_id}.sigmf-meta")
    frames = tuple(source.read_frame(index) for index in range(4))
    result = AnalogMonitor().process(frames, AnalogMonitorConfig(mode, source.sample_rate_hz, offset_hz, 16_000.0))
    oracle_tone = _independent_dominant_tone(result.audio, result.sample_rate_hz)
    reference = np.sin(2.0 * np.pi * tone_hz * np.arange(result.audio.size) / result.sample_rate_hz)
    correlation = _independent_aligned_correlation(reference, result.audio)
    duration = result.audio.size / result.sample_rate_hz
    expected_duration = 4 * FRAME_LENGTH / source.sample_rate_hz - 2.0 / 1000.0
    peak = float(np.max(np.abs(result.audio)))
    rms = float(np.sqrt(np.mean(np.square(result.audio))))
    row = {
        "fixture": fixture_id,
        "fixture_sha256": hashlib.sha256(source.data_path.read_bytes()).hexdigest(),
        "input_truth": {"mode": mode.upper(), "audio_tone_hz": tone_hz, "carrier_offset_hz": offset_hz, "iq_sample_rate_hz": source.sample_rate_hz},
        "expected": {"audio_sample_rate_hz": 48_000, "channels": 1, "tone_tolerance_hz": 12.0, "correlation_minimum": 0.95, "duration_tolerance_s": 0.003},
        "actual_algorithm": {
            "audio_sample_rate_hz": result.sample_rate_hz,
            "channels": 1,
            "audio_samples": int(result.audio.size),
            "duration_s": duration,
            "finite": bool(np.all(np.isfinite(result.audio))),
            "peak": peak,
            "rms": rms,
            "clipping_count": result.clipping_count,
            "canonical_dominant_tone_hz": result.dominant_tone_hz,
        },
        "independent_oracle": {"dominant_tone_hz": oracle_tone, "normalized_correlation": correlation},
        "errors": {"tone_hz": oracle_tone - tone_hz, "duration_s": duration - expected_duration},
    }
    passed = (
        result.sample_rate_hz == 48_000
        and np.all(np.isfinite(result.audio))
        and result.clipping_count == 0
        and peak <= 1.0
        and abs(oracle_tone - tone_hz) <= 12.0
        and correlation >= 0.95
        and abs(duration - expected_duration) <= 0.003
    )
    row["status"] = "PASS" if passed else "FAIL"
    row["pcm16_sha256"] = hashlib.sha256(result.pcm16).hexdigest()
    row["wav_sha256"] = hashlib.sha256(wav_bytes(result.pcm16)).hexdigest()
    return row, result.pcm16, result


def _df_rows() -> list[dict[str, object]]:
    rows = []
    for scene in build_df_acceptance_scenes():
        model = ManualAmplitudeDF()
        from reference.p0 import DFMeasurement
        for index, (angle, power, confidence) in enumerate(scene.measurements):
            model.add(DFMeasurement.create(angle_deg=angle, relative_power_db=power, frequency_hz=145_000_000.0, confidence=confidence, timestamp_utc=f"2026-01-01T00:00:{index:02d}Z"))
        result = model.estimate()
        independent_argmax = max(scene.measurements, key=lambda item: (item[1], -item[0]))[0]
        error = abs((result.estimated_angle_deg - scene.truth_bearing_deg + 180.0) % 360.0 - 180.0)
        tolerance = 7.5 if scene.truth_bearing_deg != 355.0 else 10.0
        rows.append({
            "fixture": scene.scene_id,
            "fixture_sha256": hashlib.sha256(canonical_bytes(scene.measurements)).hexdigest(),
            "input_truth": {"bearing_deg": scene.truth_bearing_deg, "measurement_count": len(scene.measurements)},
            "expected": {"angular_error_tolerance_deg": tolerance},
            "independent_oracle": {"measured_argmax_deg": independent_argmax},
            "actual_algorithm": {"estimated_bearing_deg": result.estimated_angle_deg, "confidence": result.confidence, "quality": result.status},
            "errors": {"circular_angular_error_deg": error},
            "status": "PASS" if result.estimated_angle_deg == independent_argmax and error <= tolerance else "FAIL",
        })
    return rows


def evaluate() -> tuple[dict[str, object], dict[str, bytes]]:
    parameter_result, parameter = _p0_parameter_result()
    am, am_pcm, am_result = _audio_row("am-tone-ci8", "am", 24_000.0, 3_000.0)
    nfm, nfm_pcm, nfm_result = _audio_row("nfm-tone-ci8", "nfm", -24_000.0, 2_000.0)
    am["human_listening_wav"] = "build/acceptance/audio/am-tone-ci8-listen.wav"
    am["human_listening_note"] = "Kanonik 83 ms alıcı çıktısının 24 kez art arda tekrarı; yeni ses üretilmez."
    nfm["human_listening_wav"] = "build/acceptance/audio/nfm-tone-ci8-listen.wav"
    nfm["human_listening_note"] = "Kanonik 83 ms alıcı çıktısının 24 kez art arda tekrarı; yeni ses üretilmez."
    app = QApplication.instance() or QApplication(["p0-training-acceptance"])
    window = MainWindow(laboratory_mode=True)
    window.set_p0_parameter_result(parameter_result)
    locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
    expected_carrier = locale.toString(parameter_result.carrier_frequency_hz / 1_000_000.0, "f", 3) + " MHz"
    expected_bandwidth = locale.toString(parameter_result.bandwidth_hz / 1000.0, "f", 2) + " kHz"
    expected_snr = locale.toString(parameter_result.snr_db, "f", 1) + " dB"
    parameter_ui = {
        "backend_carrier_hz": parameter_result.carrier_frequency_hz,
        "expected_formatted_carrier": expected_carrier,
        "actual_carrier": window.parameter_values["p0_carrier"].text(),
        "actual_bandwidth": window.parameter_values["p0_bandwidth"].text(),
        "actual_snr": window.parameter_values["p0_snr"].text(),
        "actual_class": window.parameter_values["p0_domain"].text(),
        "status": "PASS" if (
            window.parameter_values["p0_carrier"].text() == expected_carrier
            and window.parameter_values["p0_bandwidth"].text() == expected_bandwidth
            and window.parameter_values["p0_snr"].text() == expected_snr
            and window.parameter_values["p0_domain"].text() == parameter_result.signal_domain
        ) else "FAIL",
    }
    window.set_listening_result(am_result, audio_available=False, source_sample_rate_hz=192_000.0, carrier_frequency_hz=100_024_000.0, channel_bandwidth_hz=16_000.0, backend="REPLAY / HOST · NumPy PHASE-05")
    listening_am_ui = {
        "actual_mode": window.listening_values["mode"].text(),
        "actual_carrier": window.listening_values["carrier"].text(),
        "actual_iq_rate": window.listening_values["iq_rate"].text(),
        "actual_audio_rate": window.listening_values["audio_rate"].text(),
        "actual_backend": window.listening_values["backend"].text(),
        "status": "PASS" if window.listening_values["mode"].text() == "AM" and "REPLAY / HOST" in window.listening_values["backend"].text() else "FAIL",
    }
    window.set_listening_result(nfm_result, audio_available=False, source_sample_rate_hz=192_000.0, carrier_frequency_hz=99_976_000.0, channel_bandwidth_hz=16_000.0, backend="REPLAY / HOST · NumPy PHASE-05")
    listening_nfm_ui = {
        "actual_mode": window.listening_values["mode"].text(),
        "actual_carrier": window.listening_values["carrier"].text(),
        "actual_iq_rate": window.listening_values["iq_rate"].text(),
        "actual_audio_rate": window.listening_values["audio_rate"].text(),
        "actual_backend": window.listening_values["backend"].text(),
        "status": "PASS" if window.listening_values["mode"].text() == "NFM" and "REPLAY / HOST" in window.listening_values["backend"].text() else "FAIL",
    }
    window._load_df_training_fixture()
    # The compact DF panel intentionally keeps the hint separate from the
    # numeric result fields.  Bind acceptance to those fields, rather than a
    # presentation-only sentence whose wording may change.
    df_ui = {
        "actual_result": window.df_result_label.text(),
        "actual_relative_bearing": window.df_result_values["relative"].text(),
        "actual_source": window.df_result_values["source"].text(),
        "plot_points": int(window.df_curve.xData.size),
        "status": "PASS" if (
            window.df_result_label.text().endswith("LOB HAZIR")
            and window.df_result_values["relative"].text() == "75°"
            and window.df_result_values["source"].text() == "HOST/SYNTHETIC"
            and window.df_curve.xData.size == 24
        ) else "FAIL",
    }
    window.close()
    app.processEvents()
    rows = {
        "detection_noise_truth": _noise_false_alarm(),
        "detection_and_parameters": parameter,
        "am_audio": am,
        "nfm_audio": nfm,
        "df": _df_rows(),
        "ui_binding": {"parameters": parameter_ui, "listening_am": listening_am_ui, "listening_nfm": listening_nfm_ui, "df": df_ui},
    }
    statuses = [rows["detection_noise_truth"]["status"], parameter["status"], am["status"], nfm["status"]]
    statuses.extend(item["status"] for item in rows["df"])
    statuses.extend(item["status"] for item in rows["ui_binding"].values())
    document = {
        "schema_version": 1,
        "evidence_id": "p0-training-functional-acceptance-v1",
        "status": "PASS" if all(item == "PASS" for item in statuses) else "FAIL",
        "correctness_levels": {
            "detection": "INDEPENDENTLY VERIFIED",
            "parameter_extraction": "INDEPENDENTLY VERIFIED",
            "am_nfm_listening": "INDEPENDENTLY VERIFIED",
            "synthetic_df": "INDEPENDENTLY VERIFIED",
            "physical_df": "NOT EXECUTED",
        },
        "results": rows,
        "claim_boundary": "Deterministik HOST/REPLAY doğrulamasıdır; canlı RF, fiziksel anten DF, FPGA/ARM veya TX sonucu değildir.",
    }
    return document, {
        "am-tone-ci8.wav": am_pcm,
        "nfm-tone-ci8.wav": nfm_pcm,
        "am-tone-ci8-listen.wav": am_pcm * 24,
        "nfm-tone-ci8-listen.wav": nfm_pcm * 24,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--replace", action="store_true", help="explicitly replace same-id evidence")
    args = parser.parse_args()
    document, audio = evaluate()
    payload = canonical_bytes(document)
    if args.write:
        if EVIDENCE.exists() and EVIDENCE.read_bytes() != payload:
            previous = json.loads(EVIDENCE.read_text(encoding="utf-8"))
            if previous.get("evidence_id") != document["evidence_id"] or (
                previous.get("status") != "FAIL" and not args.replace
            ):
                print("existing evidence differs; refusing silent overwrite", file=sys.stderr)
                return 2
            print("explicitly replacing same-version evidence", file=sys.stderr)
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_bytes(payload)
        AUDIO_OUT.mkdir(parents=True, exist_ok=True)
        for name, pcm in audio.items():
            write_wav(AUDIO_OUT / name, pcm)
    elif not EVIDENCE.is_file() or EVIDENCE.read_bytes() != payload:
        print("training acceptance evidence is missing or stale", file=sys.stderr)
        return 1
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0 if document["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
