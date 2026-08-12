#!/usr/bin/env python3
"""Extract a deterministic source-native slice from an explicit external SigMF dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.sigmf.contract import inspect_sigmf  # noqa: E402


DEFAULT_SAMPLE_START = 0
DEFAULT_SAMPLE_COUNT = 16_384
OUTPUT_BASENAME = "ism-band-24-native-slice"


def read_source_slice(data_path: Path, byte_offset: int, byte_count: int) -> tuple[bytes, dict[str, int]]:
    """Read only the requested source bytes and confirm size/mtime stability."""
    before = data_path.stat()
    with data_path.open("rb") as source:
        source.seek(byte_offset)
        data = source.read(byte_count)
    after = data_path.stat()
    identity = {
        "size_before": before.st_size,
        "size_after": after.st_size,
        "mtime_ns_before": before.st_mtime_ns,
        "mtime_ns_after": after.st_mtime_ns,
    }
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise RuntimeError("external source size or mtime changed during the read")
    if len(data) != byte_count:
        raise RuntimeError("external source does not contain the requested sample range")
    return data, identity


def build_slice_metadata(source_metadata: dict[str, object], slice_sha512: str) -> dict[str, object]:
    global_object = dict(source_metadata["global"])
    global_object["core:sha512"] = slice_sha512
    return {
        "global": global_object,
        "captures": [
            {
                **dict(source_metadata["captures"][0]),
                "core:sample_start": 0,
            }
        ],
        "annotations": [],
    }


def extract_slice(
    metadata_path: Path,
    data_path: Path,
    output_directory: Path,
    sample_start: int = DEFAULT_SAMPLE_START,
    sample_count: int = DEFAULT_SAMPLE_COUNT,
) -> dict[str, object]:
    report = inspect_sigmf(metadata_path, data_path, mode="explicit")
    if not report.valid:
        codes = ", ".join(issue.code for issue in report.errors)
        raise RuntimeError(f"external dataset contract failed: {codes}")
    if report.source_datatype != "ci16_le":
        raise RuntimeError("external slice extraction requires source-native ci16_le data")
    if sample_start < 0 or sample_count <= 0:
        raise ValueError("sample_start must be non-negative and sample_count must be positive")
    if sample_start % report.frame_length or sample_count % report.frame_length:
        raise ValueError("external slice must align to complete PHASE-01 frames")

    bytes_per_sample = report.bytes_per_complex_sample
    assert bytes_per_sample is not None
    byte_offset = sample_start * bytes_per_sample
    byte_count = sample_count * bytes_per_sample
    slice_data, identity = read_source_slice(data_path, byte_offset, byte_count)
    sha256 = hashlib.sha256(slice_data).hexdigest()
    sha512 = hashlib.sha512(slice_data).hexdigest()
    source_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    slice_metadata = build_slice_metadata(source_metadata, sha512)

    data_output = output_directory / f"{OUTPUT_BASENAME}.sigmf-data"
    metadata_output = output_directory / f"{OUTPUT_BASENAME}.sigmf-meta"
    manifest_output = output_directory / f"{OUTPUT_BASENAME}.manifest.json"
    for output in (data_output, metadata_output, manifest_output):
        if output.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {output.name}")

    manifest = {
        "schema_version": 1,
        "phase": "PHASE-01",
        "source_metadata_filename": metadata_path.name,
        "source_data_filename": data_path.name,
        "source_size_bytes": identity["size_before"],
        "source_mtime_ns": identity["mtime_ns_before"],
        "source_identity_note": "size and mtime are non-cryptographic change indicators",
        "source_datatype": report.source_datatype,
        "source_sample_rate": report.sample_rate,
        "source_center_frequency": report.center_frequency,
        "source_sample_range": [sample_start, sample_start + sample_count],
        "complex_sample_count": sample_count,
        "frame_length": report.frame_length,
        "frame_count": sample_count // report.frame_length,
        "slice_size_bytes": len(slice_data),
        "slice_sha256": sha256,
        "slice_sha512": sha512,
        "source_author": source_metadata["global"].get("core:author"),
        "source_description": source_metadata["global"].get("core:description"),
        "source_hardware": source_metadata["global"].get("core:hw"),
        "source_recorder": source_metadata["global"].get("core:recorder"),
        "source_license_text": source_metadata["global"].get("core:license"),
        "license_status": "unverified",
        "warnings": ["nonstandard_metadata_extension", "license_unverified"],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    data_output.write_bytes(slice_data)
    metadata_output.write_text(
        json.dumps(slice_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest_output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-path", type=Path, required=True)
    parser.add_argument("--data-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-start", type=int, default=DEFAULT_SAMPLE_START)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    args = parser.parse_args()
    try:
        manifest = extract_slice(
            args.metadata_path,
            args.data_path,
            args.output_dir,
            args.sample_start,
            args.sample_count,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"FAILED: {exc}")
        return 1
    print(
        "Extracted source-native slice: "
        f"{manifest['complex_sample_count']} complex samples, {manifest['slice_size_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
