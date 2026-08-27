#!/usr/bin/env python3
"""Compare physical P0 ED service results with the host temporal reference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


FRAME_FIELDS = (
    "frame_id",
    "raw_candidate_count",
    "active_count",
    "ended_count",
    "dropped_candidates",
)
EVENT_FIELDS = (
    "event_id",
    "state",
    "first_frame_id",
    "last_seen_frame_id",
    "seen_count",
    "observed_this_frame",
    "start_bin",
    "end_bin",
    "peak_bin",
    "peak_power_uq28_30",
    "noise_power_uq28_30",
    "threshold_power_uq32_30",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project(record: dict[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: record[field] for field in fields}


def verify(reference_path: Path, service_paths: list[Path]) -> dict[str, object]:
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    expected_frames = reference.get("frames")
    if reference.get("status") != "passed" or not isinstance(expected_frames, list):
        raise AssertionError("host reference is not a passed frame sequence")
    if len(service_paths) != len(expected_frames):
        raise AssertionError(
            f"expected {len(expected_frames)} physical frames, received {len(service_paths)}"
        )

    summaries: list[dict[str, object]] = []
    file_hashes: dict[str, str] = {}
    for index, (expected, service_path) in enumerate(zip(expected_frames, service_paths)):
        actual = json.loads(service_path.read_text(encoding="utf-8"))
        if _project(actual, FRAME_FIELDS) != _project(expected, FRAME_FIELDS):
            raise AssertionError(f"frame {index} summary differs from host reference")
        if actual.get("dma_status_flags") != 7:
            raise AssertionError(f"frame {index} DMA completion flags are not 0x7")
        for collection in ("active", "ended"):
            actual_events = [_project(event, EVENT_FIELDS) for event in actual[collection]]
            expected_events = [_project(event, EVENT_FIELDS) for event in expected[collection]]
            if actual_events != expected_events:
                raise AssertionError(
                    f"frame {index} {collection} events differ from host reference"
                )
        summaries.append(_project(actual, FRAME_FIELDS))
        file_hashes[service_path.name] = _sha256(service_path)

    return {
        "status": "passed",
        "frames": summaries,
        "dma_status_flags": 7,
        "event_field_equivalence": True,
        "host_reference_sha256": _sha256(reference_path),
        "physical_result_sha256": file_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("frames", nargs="+", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.reference, arguments.frames), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
