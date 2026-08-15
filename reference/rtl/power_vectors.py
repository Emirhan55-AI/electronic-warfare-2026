"""Deterministic PHASE-06F edge and real-AMD-FFT power vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .fft_power import COMPONENT_MAX, COMPONENT_MIN, pack_fft_word, power_from_fft_word, width_proof


ROOT = Path(__file__).resolve().parents[2]
REAL_FFT_SOURCE = ROOT / "datasets" / "fixtures" / "phase06d" / "cmodel-expected.mem"

EDGE_COMPONENTS = (
    ("zero", 0, 0),
    ("i_max_positive", COMPONENT_MAX, 0),
    ("i_min_negative", COMPONENT_MIN, 0),
    ("q_max_positive", 0, COMPONENT_MAX),
    ("q_min_negative", 0, COMPONENT_MIN),
    ("both_max_positive", COMPONENT_MAX, COMPONENT_MAX),
    ("both_min_negative", COMPONENT_MIN, COMPONENT_MIN),
    ("mixed_extrema", COMPONENT_MIN, COMPONENT_MAX),
    ("equal_positive", 1_234_567, 1_234_567),
    ("equal_negative", -1_234_567, -1_234_567),
    ("small_mixed", 1, -1),
    ("small_signed", -2, 3),
)


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _mem(words: tuple[int, ...], digits: int) -> bytes:
    return b"".join(f"{word:0{digits}x}\n".encode("ascii") for word in words)


def build_vector_files() -> dict[str, bytes]:
    real_words = tuple(int(line, 16) for line in REAL_FFT_SOURCE.read_text(encoding="ascii").splitlines() if line)
    if len(real_words) != 45_056:
        raise ValueError("PHASE-06D gerçek FFT fixture'ı 45.056 örnek içermelidir.")
    edge_words = tuple(pack_fft_word(i_value, q_value) for _, i_value, q_value in EDGE_COMPONENTS)
    edge_power = tuple(power_from_fft_word(word) for word in edge_words)
    real_power = tuple(power_from_fft_word(word) for word in real_words)
    edge_input = _mem(edge_words, 16)
    edge_expected = _mem(edge_power, 15)
    real_expected = _mem(real_power, 15)
    golden = {
        "phase": "PHASE-06F",
        "status": "passed",
        "equation": "P_int = I_int^2 + Q_int^2",
        "input_format": "signed 29-bit SQ14.15 per component in sign-extended 32-bit lanes",
        "output_format": "unsigned 58-bit UQ28.30",
        "edge_vectors": [
            {"id": identifier, "i_integer": i_value, "q_integer": q_value, "power_integer": power}
            for (identifier, i_value, q_value), power in zip(EDGE_COMPONENTS, edge_power, strict=True)
        ],
        "real_amd_fft": {
            "source": "datasets/fixtures/phase06d/cmodel-expected.mem",
            "source_sha256": hashlib.sha256(REAL_FFT_SOURCE.read_bytes()).hexdigest(),
            "frames": 11,
            "samples": len(real_words),
            "power_sha256": sha256_bytes(real_expected),
            "includes": ["zero", "impulse", "dc", "exact_bin_tone", "negative_frequency_tone", "two_tone", "representative_hann"],
        },
        "boundary_proof": width_proof(),
    }
    golden_bytes = canonical_bytes(golden)
    files = {
        "edge-input.mem": edge_input,
        "edge-expected.mem": edge_expected,
        "real-power-expected.mem": real_expected,
        "golden-vectors.json": golden_bytes,
    }
    manifest = {
        "phase": "PHASE-06F",
        "status": "passed",
        "files": {name: {"bytes": len(payload), "sha256": sha256_bytes(payload)} for name, payload in files.items()},
        "external_source": {
            "path": "datasets/fixtures/phase06d/cmodel-expected.mem",
            "sha256": hashlib.sha256(REAL_FFT_SOURCE.read_bytes()).hexdigest(),
        },
    }
    files["fixture-manifest.json"] = canonical_bytes(manifest)
    return files
