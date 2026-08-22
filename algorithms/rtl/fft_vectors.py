"""Deterministic PHASE-06C numerical and transport-stub vector construction."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np

from .fft_model import (
    FRAME_LENGTH,
    OUTPUT_WORD_WIDTH,
    build_numerical_study,
    pack_sq1_15_word,
    quantized_unscaled_fft,
    sign_extend_input_word,
    unpack_fft_word,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE06B_EXPECTED = ROOT / "datasets" / "fixtures" / "phase06b" / "axis-expected.mem"
SELECTED_BINS = (0, 1, 64, 128, 256, 512, 1024, 2048, 4095)


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _words_bytes(words: tuple[int, ...], width: int) -> bytes:
    return b"".join(int(word).to_bytes(width, "little", signed=False) for word in words)


def _quantize(samples: np.ndarray) -> tuple[int, ...]:
    i_values = np.clip(np.rint(samples.real * (1 << 15)), -32768, 32767).astype(np.int64)
    q_values = np.clip(np.rint(samples.imag * (1 << 15)), -32768, 32767).astype(np.int64)
    return tuple(pack_sq1_15_word(int(i_value), int(q_value)) for i_value, q_value in zip(i_values, q_values, strict=True))


def _tone(bin_index: int, amplitude: float, phase: float = 0.0) -> np.ndarray:
    index = np.arange(FRAME_LENGTH, dtype=np.float64)
    return amplitude * np.exp(1j * (2.0 * np.pi * bin_index * index / FRAME_LENGTH + phase))


def build_frames() -> OrderedDict[str, tuple[int, ...]]:
    representative_lines = PHASE06B_EXPECTED.read_text(encoding="ascii").splitlines()
    if len(representative_lines) < FRAME_LENGTH:
        raise ValueError("PHASE-06B representative Hann frame eksik.")
    representative = tuple(int(line, 16) for line in representative_lines[:FRAME_LENGTH])
    frames: OrderedDict[str, tuple[int, ...]] = OrderedDict()
    frames["zero"] = (0,) * FRAME_LENGTH
    frames["impulse"] = (pack_sq1_15_word(32767, 0),) + (0,) * (FRAME_LENGTH - 1)
    frames["positive_dc"] = (pack_sq1_15_word(16384, 0),) * FRAME_LENGTH
    frames["negative_dc"] = (pack_sq1_15_word(-16384, 0),) * FRAME_LENGTH
    frames["single_tone"] = _quantize(_tone(256, 0.75))
    frames["two_tone"] = _quantize(_tone(128, 0.50) + _tone(512, 0.25, 0.3))
    frames["multiple_tones"] = _quantize(
        _tone(64, 0.30) + _tone(333, 0.25, 0.2) + _tone(1024, 0.20, -0.4)
    )
    frames["alternating_extrema"] = tuple(
        pack_sq1_15_word(-32768, 32767) if index % 2 == 0 else pack_sq1_15_word(32767, -32768)
        for index in range(FRAME_LENGTH)
    )
    frames["complex_extrema"] = (pack_sq1_15_word(32767, -32768),) * FRAME_LENGTH
    frames["representative_hann"] = representative
    return frames


def build_vector_files() -> tuple[dict[str, bytes], dict[str, object], dict[str, object]]:
    frames = build_frames()
    numerical_study = build_numerical_study(frames)
    input_words = tuple(word for words in frames.values() for word in words)
    fft_frames = {identifier: quantized_unscaled_fft(words) for identifier, words in frames.items()}
    fft_words = tuple(word for words in fft_frames.values() for word in words)
    stub_words = tuple(sign_extend_input_word(word) for word in input_words)

    records = []
    for frame_index, (identifier, words) in enumerate(frames.items()):
        outputs = fft_frames[identifier]
        magnitudes = [i_value * i_value + q_value * q_value for i_value, q_value in map(unpack_fft_word, outputs)]
        peak_index = int(np.argmax(np.asarray(magnitudes, dtype=object)))
        records.append(
            {
                "vector_id": identifier,
                "frame_index": frame_index,
                "sample_offset": frame_index * FRAME_LENGTH,
                "sample_count": FRAME_LENGTH,
                "input_sha256": _sha256(_words_bytes(words, 4)),
                "fft_output_sha256": _sha256(_words_bytes(outputs, 8)),
                "peak_index_unshifted": peak_index,
                "selected_outputs": [
                    {"bin": index, "word": f"{outputs[index]:016x}"} for index in SELECTED_BINS
                ],
            }
        )

    golden = {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "claim_boundary": "Idealized numerical FFT vectors and non-FFT transport-stub vectors; not AMD IP output.",
        "frame_length": FRAME_LENGTH,
        "frame_count": len(frames),
        "total_samples": len(input_words),
        "input_format": "signed SQ1.15 I/Q in 32-bit low-I/high-Q AXI payload",
        "fft_output_format": "signed 29-bit Q15 I/Q sign-extended into 32-bit lanes, 64-bit payload",
        "fft_output_order": "natural unshifted k=0..4095",
        "vectors": records,
    }
    input_mem = "".join(f"{word:08x}\n" for word in input_words).encode("ascii")
    fft_mem = "".join(f"{word:016x}\n" for word in fft_words).encode("ascii")
    stub_mem = "".join(f"{word:016x}\n" for word in stub_words).encode("ascii")
    golden_bytes = _canonical(golden)
    files = {
        "axis-input.mem": input_mem,
        "fft-expected.mem": fft_mem,
        "stub-expected.mem": stub_mem,
        "golden-vectors.json": golden_bytes,
    }
    source = PHASE06B_EXPECTED.read_bytes()
    manifest = {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "claim_boundary": "Wrapper transport stub is not an FFT; real AMD FFT IP is not exercised.",
        "source": {
            "file": "datasets/fixtures/phase06b/axis-expected.mem",
            "sha256": _sha256(source),
            "representative_samples": FRAME_LENGTH,
        },
        "files": [
            {"file": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in files.items()
        ],
    }
    files["fixture-manifest.json"] = _canonical(manifest)
    return files, manifest, numerical_study
