"""Deterministic small SigMF fixtures for recorded analog monitoring."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt


SAMPLE_RATE_HZ = 192_000
CENTER_FREQUENCY_HZ = 100_000_000
FRAME_LENGTH = 4096
FRAME_COUNT = 8
COMPLEX_SAMPLES = FRAME_LENGTH * FRAME_COUNT


@dataclass(frozen=True)
class FixtureSpec:
    fixture_id: str
    mode: Literal["am", "nfm", "noise"]
    carrier_offset_hz: float
    audio_tone_hz: float | None
    channel_bandwidth_hz: float
    modulation_index: float
    seed: int


FIXTURE_SPECS = (
    FixtureSpec("am-tone-ci8", "am", 24_000.0, 3_000.0, 16_000.0, 0.55, 20260501),
    FixtureSpec("nfm-tone-ci8", "nfm", -24_000.0, 2_000.0, 16_000.0, 2.5, 20260502),
    FixtureSpec("noise-only-ci8", "noise", 0.0, None, 16_000.0, 0.0, 20260503),
)


def generate_iq(spec: FixtureSpec, *, snr_db: float | None = None, trial: int = 0) -> npt.NDArray[np.complex128]:
    t = np.arange(COMPLEX_SAMPLES, dtype=np.float64) / SAMPLE_RATE_HZ
    if spec.mode == "am":
        audio = np.sin(2.0 * np.pi * float(spec.audio_tone_hz) * t)
        clean = 0.55 * (1.0 + spec.modulation_index * audio) * np.exp(2j * np.pi * spec.carrier_offset_hz * t)
    elif spec.mode == "nfm":
        audio_hz = float(spec.audio_tone_hz)
        deviation_hz = spec.modulation_index * audio_hz
        phase = 2.0 * np.pi * spec.carrier_offset_hz * t - (deviation_hz / audio_hz) * np.cos(2.0 * np.pi * audio_hz * t)
        clean = 0.70 * np.exp(1j * phase)
    else:
        rng = np.random.default_rng(np.random.SeedSequence([spec.seed, trial]))
        return np.asarray(0.025 * (rng.normal(size=t.size) + 1j * rng.normal(size=t.size)), dtype=np.complex128)
    if snr_db is None:
        return np.asarray(clean, dtype=np.complex128)
    rng = np.random.default_rng(np.random.SeedSequence([spec.seed, trial, int(round(snr_db * 10.0))]))
    signal_power = float(np.mean(np.abs(clean) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = math.sqrt(noise_power / 2.0) * (rng.normal(size=t.size) + 1j * rng.normal(size=t.size))
    return np.asarray(clean + noise, dtype=np.complex128)


def _ci8(iq: npt.NDArray[np.complex128]) -> bytes:
    interleaved = np.empty(iq.size * 2, dtype=np.int8)
    interleaved[0::2] = np.rint(np.clip(iq.real, -1.0, 127.0 / 128.0) * 128.0).astype(np.int8)
    interleaved[1::2] = np.rint(np.clip(iq.imag, -1.0, 127.0 / 128.0) * 128.0).astype(np.int8)
    return interleaved.tobytes()


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_fixture_files() -> tuple[dict[str, bytes], dict[str, object]]:
    files: dict[str, bytes] = {}
    manifest_rows: list[dict[str, object]] = []
    for spec in FIXTURE_SPECS:
        payload = _ci8(generate_iq(spec))
        metadata = {
            "global": {
                "core:version": "1.0.0",
                "core:datatype": "ci8",
                "core:sample_rate": SAMPLE_RATE_HZ,
                "core:num_channels": 1,
                "core:description": "Deterministik PHASE-05 sentetik test kaynağı; gerçek RF kaydı değildir.",
            },
            "captures": [{"core:sample_start": 0, "core:frequency": CENTER_FREQUENCY_HZ}],
            "annotations": [],
        }
        meta_payload = _canonical(metadata)
        files[f"{spec.fixture_id}.sigmf-data"] = payload
        files[f"{spec.fixture_id}.sigmf-meta"] = meta_payload
        manifest_rows.append(
            {
                "fixture_id": spec.fixture_id,
                "mode": spec.mode,
                "datatype": "ci8",
                "sample_rate_hz": SAMPLE_RATE_HZ,
                "center_frequency_hz": CENTER_FREQUENCY_HZ,
                "complex_samples": COMPLEX_SAMPLES,
                "frame_length": FRAME_LENGTH,
                "frame_count": FRAME_COUNT,
                "carrier_offset_hz": spec.carrier_offset_hz,
                "audio_tone_hz": spec.audio_tone_hz,
                "channel_bandwidth_hz": spec.channel_bandwidth_hz,
                "modulation_index": spec.modulation_index,
                "seed": spec.seed,
                "data_sha256": hashlib.sha256(payload).hexdigest(),
                "data_sha512": hashlib.sha512(payload).hexdigest(),
                "metadata_sha256": hashlib.sha256(meta_payload).hexdigest(),
            }
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "phase": "PHASE-05",
        "claim_boundary": "Deterministik sentetik I/Q; gerçek RF kaydı değildir.",
        "fixtures": manifest_rows,
    }
    files["fixture-manifest.json"] = _canonical(manifest)
    return files, manifest
