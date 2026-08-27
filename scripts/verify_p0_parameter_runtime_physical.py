#!/usr/bin/env python3
"""Verify one physical ZedBoard parameter run without post-hoc numeric gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


FIELDS = (
    "emission_center_frequency_hz",
    "lower_occupied_edge_hz",
    "upper_occupied_edge_hz",
    "occupied_bandwidth_hz",
    "channel_power_dbfs",
    "snr_estimate_db",
)
FREQUENCY_FIELDS = FIELDS[:4]
DB_FIELDS = FIELDS[4:]


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(
    manifest_path: Path,
    event_path: Path,
    parameter_paths: list[Path],
    host_physical_power_path: Path,
    physical_power_paths: list[Path],
) -> dict[str, object]:
    if len(parameter_paths) != 4 or len(physical_power_paths) != 4:
        raise AssertionError("exactly four parameter and four physical power files are required")
    manifest = _load(manifest_path)
    event_frame = _load(event_path)
    parameters = [_load(path) for path in parameter_paths]
    host = _load(host_physical_power_path)
    span = tuple(int(value) for value in manifest["span"])
    event_id = int(manifest["event_id"])
    intent_id = int(manifest["intent_id"])

    if event_frame["dma_status_flags"] != 7 or event_frame["frame_id"] != 0:
        raise AssertionError("event acquisition did not complete physical DMA frame zero")
    owners = [
        event
        for event in event_frame["active"]
        if event["event_id"] == event_id
        and event["state"] == "tentative"
        and event["observed_this_frame"]
        and span[0] <= event["peak_bin"] <= span[1]
    ]
    if len(owners) != 1:
        raise AssertionError("the requested event does not uniquely own the measurement span")
    protected = (span[0] - 36, span[1] + 36)
    interfering = [
        event
        for event in event_frame["active"]
        if event["event_id"] != event_id
        and event["start_bin"] <= protected[1]
        and event["end_bin"] >= protected[0]
    ]
    if interfering:
        raise AssertionError("another event intersects the protected measurement span")

    observations: list[int] = []
    candidate_counts: list[int] = []
    for index, document in enumerate(parameters, start=1):
        parameter = document["parameter"]
        if (
            document["frame_id"] != index
            or document["dma_status_flags"] != 7
            or parameter["intent_id"] != intent_id
            or parameter["event_id"] != event_id
            or parameter["observation_count"] != index
        ):
            raise AssertionError(f"parameter frame {index} lost its physical context")
        observations.append(int(parameter["observation_count"]))
        candidate_counts.append(int(document["raw_candidate_count"]))
        for name in FIELDS:
            field = parameter[name]
            if index < 4:
                if field != {"state": "not_available", "reason": "accumulating"}:
                    raise AssertionError(f"{name} published before four observations")
            elif (
                field.get("state") != "valid"
                or field.get("reason") != "none"
                or not math.isfinite(float(field.get("value")))
            ):
                raise AssertionError(f"final physical field is not valid: {name}")

    final = parameters[-1]["parameter"]
    exact_errors: dict[str, float] = {}
    ideal_characterization: dict[str, dict[str, float]] = {}
    for name in FIELDS:
        host_field = host[name]
        if host_field["state"] != 1 or host_field["reason"] != 0:
            raise AssertionError(f"host replay field is not valid: {name}")
        physical_value = float(final[name]["value"])
        host_value = float(host_field["value"])
        error = abs(physical_value - host_value)
        if error != 0.0:
            raise AssertionError(f"ARM and host C differ for {name}: {error}")
        exact_errors[name] = error
        ideal_value = float(manifest["expected_fields"][name]["value"])
        ideal_characterization[name] = {
            "ideal_host": ideal_value,
            "physical": physical_value,
            "absolute_error": abs(physical_value - ideal_value),
        }

    power_hashes: dict[str, str] = {}
    for path in physical_power_paths:
        if path.stat().st_size != 4096 * 8:
            raise AssertionError(f"physical power frame has the wrong size: {path}")
        power_hashes[path.name] = _sha256(path)
    maximum_frequency_error = max(
        ideal_characterization[name]["absolute_error"] for name in FREQUENCY_FIELDS
    )
    maximum_db_error = max(
        ideal_characterization[name]["absolute_error"] for name in DB_FIELDS
    )
    artifact_paths = [event_path, *parameter_paths, host_physical_power_path]
    return {
        "status": "passed",
        "scope": "physical ZedBoard PL-DMA-ARM parameter execution",
        "measurement": {
            "scene": manifest["scene"],
            "sample_rate_hz": manifest["sample_rate_hz"],
            "center_frequency_hz": manifest["center_frequency_hz"],
            "span": list(span),
            "intent_id": intent_id,
            "event_id": event_id,
            "observations": observations,
            "raw_candidate_counts": candidate_counts,
            "dma_status_flags": [int(item["dma_status_flags"]) for item in parameters],
        },
        "cross_architecture_equivalence": {
            "reference": "host C replay of captured physical PL UQ28.30 frames",
            "fields": len(FIELDS),
            "maximum_absolute_error": max(exact_errors.values()),
            "field_absolute_errors": exact_errors,
        },
        "ideal_fft_characterization": {
            "pass_fail_gate": None,
            "reason": "No physical ideal-FFT equivalence tolerance was declared before execution.",
            "maximum_frequency_field_error_hz": maximum_frequency_error,
            "maximum_db_field_error_db": maximum_db_error,
            "fields": ideal_characterization,
        },
        "physical_power_sha256": power_hashes,
        "artifact_sha256": {path.name: _sha256(path) for path in artifact_paths},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("event", type=Path)
    parser.add_argument("host_physical_power", type=Path)
    parser.add_argument("parameters", nargs=4, type=Path)
    parser.add_argument("--power", nargs=4, required=True, type=Path)
    arguments = parser.parse_args()
    result = verify(
        arguments.manifest,
        arguments.event,
        arguments.parameters,
        arguments.host_physical_power,
        arguments.power,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
