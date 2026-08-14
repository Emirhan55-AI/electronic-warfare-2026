"""Deterministic golden gates for PHASE-05 analog monitoring."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from reference.pipeline import RuntimePipeline, load_profile
from reference.spectrum import SigMFFrameSource

from .dsp import AUDIO_SAMPLE_RATE_HZ, AnalogMonitor, aligned_correlation, dominant_tone_hz
from .fixtures import FIXTURE_SPECS, FRAME_LENGTH, generate_iq
from .models import AnalogMonitorConfig


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "datasets" / "fixtures" / "phase05"
PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _reference_tone(length: int, frequency_hz: float) -> np.ndarray:
    return np.sin(2.0 * np.pi * frequency_hz * np.arange(length, dtype=np.float64) / AUDIO_SAMPLE_RATE_HZ)


def _measure(spec: object, iq: np.ndarray) -> tuple[dict[str, object], bytes]:
    frames = tuple(iq[index : index + FRAME_LENGTH] for index in range(0, FRAME_LENGTH * 4, FRAME_LENGTH))
    config = AnalogMonitorConfig(spec.mode, 192_000.0, spec.carrier_offset_hz, spec.channel_bandwidth_hz)  # type: ignore[attr-defined]
    result = AnalogMonitor().process(frames, config)
    reference = _reference_tone(result.audio.size, float(spec.audio_tone_hz))  # type: ignore[attr-defined]
    correlation = aligned_correlation(reference, result.audio)
    tone_bin_hz = AUDIO_SAMPLE_RATE_HZ / (1 << max(12, int(math.ceil(math.log2(result.audio.size)))))
    row = {
        "sample_rate_hz": result.sample_rate_hz,
        "finite": bool(np.all(np.isfinite(result.audio))),
        "pcm_clipping_count": result.clipping_count,
        "dominant_tone_hz": result.dominant_tone_hz,
        "tone_error_hz": abs(result.dominant_tone_hz - float(spec.audio_tone_hz)),  # type: ignore[attr-defined]
        "evaluation_fft_bin_hz": tone_bin_hz,
        "normalized_correlation": correlation,
        "audio_samples": int(result.audio.size),
        "pcm_sha256": hashlib.sha256(result.pcm16).hexdigest(),
    }
    return row, result.pcm16


def _event_gate(spec: object) -> bool:
    source = SigMFFrameSource(FIXTURE_DIR / f"{spec.fixture_id}.sigmf-meta")  # type: ignore[attr-defined]
    pipeline = RuntimePipeline(load_profile(PROFILE_PATH))
    confirmed = False
    for index in range(4):
        result = pipeline.process(
            source.read_frame(index),
            sample_rate_hz=source.sample_rate_hz,
            center_frequency_hz=source.center_frequency_hz,
            frame_index=index,
        )
        expected = float(spec.carrier_offset_hz)  # type: ignore[attr-defined]
        confirmed = confirmed or any(
            event.state == "confirmed"
            and abs(result.spectrum.display.frequency_offset_hz[event.region.peak_bin] - expected) <= 12_000.0
            for event in result.detection.active_events
        )
    return confirmed


def build_phase05_evidence() -> tuple[dict[str, object], dict[str, object]]:
    clean_rows: dict[str, dict[str, object]] = {}
    noisy_rows: dict[str, dict[str, object]] = {}
    all_passed = True
    for spec in FIXTURE_SPECS[:2]:
        source = SigMFFrameSource(FIXTURE_DIR / f"{spec.fixture_id}.sigmf-meta")
        clean_iq = np.concatenate(tuple(source.read_frame(i) for i in range(4)))
        clean, pcm_first = _measure(spec, clean_iq)
        _, pcm_second = _measure(spec, clean_iq)
        clean["deterministic_pcm"] = pcm_first == pcm_second
        clean["confirmed_event"] = _event_gate(spec)
        clean["passed"] = bool(
            clean["sample_rate_hz"] == 48_000
            and clean["finite"]
            and clean["pcm_clipping_count"] == 0
            and clean["tone_error_hz"] <= clean["evaluation_fft_bin_hz"]
            and clean["normalized_correlation"] >= 0.95
            and clean["deterministic_pcm"]
            and clean["confirmed_event"]
        )
        noisy, _ = _measure(spec, generate_iq(spec, snr_db=20.0, trial=0)[: FRAME_LENGTH * 4])
        noisy["snr_db"] = 20.0
        noisy["passed"] = bool(
            noisy["finite"]
            and noisy["pcm_clipping_count"] == 0
            and noisy["tone_error_hz"] <= 2.0 * noisy["evaluation_fft_bin_hz"]
            and noisy["normalized_correlation"] >= 0.80
        )
        clean_rows[spec.mode] = clean
        noisy_rows[spec.mode] = noisy
        all_passed = all_passed and bool(clean["passed"] and noisy["passed"])

    noise_source = SigMFFrameSource(FIXTURE_DIR / "noise-only-ci8.sigmf-meta")
    pipeline = RuntimePipeline(load_profile(PROFILE_PATH))
    confirmed_count = 0
    for index in range(4):
        result = pipeline.process(
            noise_source.read_frame(index),
            sample_rate_hz=noise_source.sample_rate_hz,
            center_frequency_hz=noise_source.center_frequency_hz,
            frame_index=index,
        )
        confirmed_count += sum(event.state == "confirmed" for event in result.detection.active_events)
    noise_gate = {"frames": 4, "confirmed_events": confirmed_count, "playback_enabled": False, "passed": confirmed_count == 0}
    all_passed = all_passed and bool(noise_gate["passed"])
    golden = {
        "schema_version": 1,
        "phase": "PHASE-05",
        "status": "passed" if all_passed else "failed",
        "clean": clean_rows,
        "snr_20_db": noisy_rows,
        "noise_only": noise_gate,
        "gates": {
            "audio_sample_rate_hz": 48_000,
            "clean_correlation_minimum": 0.95,
            "snr20_correlation_minimum": 0.80,
            "clean_tone_error_bins_maximum": 1,
            "snr20_tone_error_bins_maximum": 2,
            "pcm_clipping_count_maximum": 0,
        },
    }
    summary = {
        "schema_version": 1,
        "phase": "PHASE-05",
        "status": golden["status"],
        "hardware_status": "not_exercised",
        "live_rx_status": "not_exercised",
        "runtime_profile": "phase03-operation-default",
        "detector": "detector.regional",
        "checks": [
            {"id": "am-clean", "status": "passed" if clean_rows["am"]["passed"] else "failed"},
            {"id": "nfm-clean", "status": "passed" if clean_rows["nfm"]["passed"] else "failed"},
            {"id": "am-snr20", "status": "passed" if noisy_rows["am"]["passed"] else "failed"},
            {"id": "nfm-snr20", "status": "passed" if noisy_rows["nfm"]["passed"] else "failed"},
            {"id": "noise-only", "status": "passed" if noise_gate["passed"] else "failed"},
            {"id": "external-ism", "status": "skipped"},
            {"id": "live-hackrf-audio", "status": "skipped"},
        ],
        "claim_boundary": "Kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM; canlı HackRF ve otomatik modülasyon sınıflandırması değildir.",
    }
    return golden, summary


def canonical_bytes(document: object) -> bytes:
    return _canonical(document)
