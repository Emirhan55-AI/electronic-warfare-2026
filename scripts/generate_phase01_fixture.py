#!/usr/bin/env python3
"""Generate or verify the deterministic PHASE-01 ci8 golden fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIRECTORY = ROOT / "datasets" / "fixtures" / "phase01"
DATA_PATH = FIXTURE_DIRECTORY / "known-tone-ci8.sigmf-data"
METADATA_PATH = FIXTURE_DIRECTORY / "known-tone-ci8.sigmf-meta"
MANIFEST_PATH = ROOT / "results" / "evidence" / "phase01" / "fixture-manifest.json"

SAMPLE_RATE = 8_000_000
CENTER_FREQUENCY = 100_000_000
COMPLEX_SAMPLE_COUNT = 16_384
FRAME_LENGTH = 4096
TONE_OFFSET_HZ = 500_000
SIGNED_FFT_BIN = 256
UNSHIFTED_FFT_INDEX = 256
PEAK_AMPLITUDE_COUNTS = 100
TONE_TABLE = (
    (100, 0),
    (92, 38),
    (71, 71),
    (38, 92),
    (0, 100),
    (-38, 92),
    (-71, 71),
    (-92, 38),
    (-100, 0),
    (-92, -38),
    (-71, -71),
    (-38, -92),
    (0, -100),
    (38, -92),
    (71, -71),
    (92, -38),
)


def fixture_data() -> bytes:
    pattern = bytes(component & 0xFF for pair in TONE_TABLE for component in pair)
    return pattern * (COMPLEX_SAMPLE_COUNT // len(TONE_TABLE))


def fixture_metadata(data_sha512: str) -> dict[str, object]:
    return {
        "global": {
            "core:version": "1.0.0",
            "core:datatype": "ci8",
            "core:sample_rate": SAMPLE_RATE,
            "core:num_channels": 1,
            "core:sha512": data_sha512,
            "core:description": "Deterministic PHASE-01 complex tone fixture",
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": CENTER_FREQUENCY,
            }
        ],
        "annotations": [],
    }


def fixture_manifest(data: bytes) -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-01",
        "fixture": "known-tone-ci8",
        "datatype": "ci8",
        "layout": "[I0,Q0,I1,Q1,...]",
        "sample_rate": SAMPLE_RATE,
        "center_frequency": CENTER_FREQUENCY,
        "complex_sample_count": COMPLEX_SAMPLE_COUNT,
        "frame_length": FRAME_LENGTH,
        "frame_count": COMPLEX_SAMPLE_COUNT // FRAME_LENGTH,
        "data_size_bytes": len(data),
        "tone_offset_hz": TONE_OFFSET_HZ,
        "peak_amplitude_counts": PEAK_AMPLITUDE_COUNTS,
        "expected_signed_fft_bin": SIGNED_FFT_BIN,
        "expected_unshifted_fft_index": UNSHIFTED_FFT_INDEX,
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
    }


def serialized_outputs() -> dict[Path, bytes]:
    data = fixture_data()
    manifest = fixture_manifest(data)
    metadata = fixture_metadata(str(manifest["sha512"]))
    return {
        DATA_PATH: data,
        METADATA_PATH: (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        MANIFEST_PATH: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }


def check_outputs(outputs: dict[Path, bytes]) -> list[str]:
    failures: list[str] = []
    for path, expected in outputs.items():
        if not path.is_file():
            failures.append(f"missing: {path.relative_to(ROOT).as_posix()}")
        elif path.read_bytes() != expected:
            failures.append(f"content mismatch: {path.relative_to(ROOT).as_posix()}")
    return failures


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify tracked outputs without writing")
    args = parser.parse_args()
    outputs = serialized_outputs()
    if args.check:
        failures = check_outputs(outputs)
        if failures:
            for failure in failures:
                print(f"FAILED: {failure}")
            return 1
        print("PHASE-01 golden fixture is deterministic and current")
        return 0
    write_outputs(outputs)
    print("Generated deterministic PHASE-01 golden fixture and manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
