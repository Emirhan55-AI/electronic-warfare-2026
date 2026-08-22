"""Deterministic PHASE-06D vectors for the real AMD FFT IP boundary."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np

from .fft_model import FRAME_LENGTH, pack_sq1_15_word
from .fft_vectors import build_frames as build_phase06c_frames


ROOT = Path(__file__).resolve().parents[2]
PHASE06C_INPUT = ROOT / "datasets" / "fixtures" / "phase06c" / "axis-input.mem"


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _words_bytes(words: tuple[int, ...]) -> bytes:
    return b"".join(int(word).to_bytes(4, "little", signed=False) for word in words)


def _quantize(samples: np.ndarray) -> tuple[int, ...]:
    i_values = np.clip(np.rint(samples.real * (1 << 15)), -32768, 32767).astype(np.int64)
    q_values = np.clip(np.rint(samples.imag * (1 << 15)), -32768, 32767).astype(np.int64)
    return tuple(
        pack_sq1_15_word(int(i_value), int(q_value))
        for i_value, q_value in zip(i_values, q_values, strict=True)
    )


def _tone(bin_index: int, amplitude: float, phase: float = 0.0) -> np.ndarray:
    index = np.arange(FRAME_LENGTH, dtype=np.float64)
    return amplitude * np.exp(1j * (2.0 * np.pi * bin_index * index / FRAME_LENGTH + phase))


def build_frames() -> OrderedDict[str, tuple[int, ...]]:
    """Reuse every PHASE-06C frame and append one exact-bin negative tone."""
    frames = OrderedDict(build_phase06c_frames())
    frames["negative_frequency_tone"] = _quantize(_tone(-384, 0.625, 0.125))
    return frames


def build_vector_files() -> dict[str, bytes]:
    frames = build_frames()
    input_words = tuple(word for words in frames.values() for word in words)
    input_mem = "".join(f"{word:08x}\n" for word in input_words).encode("ascii")

    inherited_lines = PHASE06C_INPUT.read_bytes()
    inherited_length = len(inherited_lines)
    if input_mem[:inherited_length] != inherited_lines:
        raise AssertionError("PHASE-06C input vectors were not inherited byte-for-byte.")

    records = []
    for frame_index, (identifier, words) in enumerate(frames.items()):
        record: dict[str, object] = {
            "vector_id": identifier,
            "frame_index": frame_index,
            "sample_offset": frame_index * FRAME_LENGTH,
            "sample_count": FRAME_LENGTH,
            "input_sha256": _sha256(_words_bytes(words)),
        }
        if identifier == "negative_frequency_tone":
            record.update(
                {
                    "signed_bin": -384,
                    "natural_order_bin": FRAME_LENGTH - 384,
                    "amplitude": 0.625,
                    "phase_radians": 0.125,
                }
            )
        records.append(record)

    vectors = {
        "schema_version": 1,
        "phase": "PHASE-06D",
        "claim_boundary": "AMD FFT input vectors only; expected output is produced by the installed bit-accurate C model.",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(frames),
        "total_samples": len(input_words),
        "input_format": "signed SQ1.15 low-I/high-Q in a 32-bit AXI payload",
        "inherited_phase06c_frame_count": len(frames) - 1,
        "vectors": records,
    }
    files = {
        "axis-input.mem": input_mem,
        "golden-vectors.json": _canonical(vectors),
    }
    manifest = {
        "schema_version": 1,
        "phase": "PHASE-06D",
        "claim_boundary": "Fixture provenance only; C-model and XSim outputs are verified separately.",
        "source": {
            "file": "datasets/fixtures/phase06c/axis-input.mem",
            "sha256": _sha256(inherited_lines),
            "inherited_bytes": inherited_length,
            "inherited_frames": len(frames) - 1,
        },
        "files": [
            {"file": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in files.items()
        ],
    }
    files["fixture-manifest.json"] = _canonical(manifest)
    return files
