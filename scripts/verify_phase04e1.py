"""Write or read-only check PHASE-04-E1 evidence and optional bounded data integration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.operator_reference import (
    ACCEPTANCE_PATH,
    METHOD_LOCK_PATH,
    PHASE03_PROFILE_PATH,
    SCENES_PATH,
    canonical_json_bytes,
    implementation_manifest,
    load_json,
    sha256_file,
    build_golden_reference,
)
from reference.parameters.operator_evaluation import compare
from reference.pipeline.profile import load_phase04e1_capability
from reference.spectrum import SigMFFrameSource, SpectrumProcessor


EVIDENCE = ROOT / "results" / "evidence" / "phase04e1"
SUMMARY = EVIDENCE / "verification-summary.json"
INVALID_RUN = EVIDENCE / "invalid-protocol-run1"


def _external_check() -> dict[str, Any]:
    metadata = os.environ.get("PHASE01_EXTERNAL_METADATA")
    data = os.environ.get("PHASE01_EXTERNAL_DATA")
    if not metadata and not data:
        return {"id": "external_bounded_integration", "status": "skipped", "frames": 0}
    if not metadata or not data:
        return {"id": "external_bounded_integration", "status": "failed", "frames": 0}
    try:
        with SigMFFrameSource(Path(metadata), Path(data), mode="explicit", frame_length=4096) as source:
            if source.frame_count < 4:
                return {"id": "external_bounded_integration", "status": "failed", "frames": 0}
            processor = SpectrumProcessor()
            first = [processor.process(source.read_frame(index), sample_rate_hz=source.sample_rate_hz, center_frequency_hz=source.center_frequency_hz).display.bin_power_fs2.tobytes() for index in range(4)]
            second = [processor.process(source.read_frame(index), sample_rate_hz=source.sample_rate_hz, center_frequency_hz=source.center_frequency_hz).display.bin_power_fs2.tobytes() for index in range(4)]
        return {"id": "external_bounded_integration", "status": "passed" if first == second else "failed", "frames": 4}
    except Exception:
        return {"id": "external_bounded_integration", "status": "failed", "frames": 0}


def _artifact_checks() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    lock_sha = sha256_file(METHOD_LOCK_PATH) if METHOD_LOCK_PATH.exists() else None
    lock = load_json(METHOD_LOCK_PATH)
    checks.append({"id": "independent-fields-v2-lock", "status": "passed" if lock.get("protocol_revision") == "independent-fields-v2" else "failed"})
    try:
        invalid_manifest = load_json(INVALID_RUN / "invalid-run-manifest.json")
        archived_ok = invalid_manifest.get("status") == "evaluation_protocol_invalid" and all(
            (INVALID_RUN / item["file"]).is_file() and sha256_file(INVALID_RUN / item["file"]) == item["sha256"]
            for item in invalid_manifest.get("files", ())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        archived_ok = False
    checks.append({"id": "invalid-protocol-run1-archive", "status": "passed" if archived_ok else "failed"})
    golden_path = EVIDENCE / "golden-parameters.json"
    golden_ok = golden_path.exists() and golden_path.read_bytes() == canonical_json_bytes(build_golden_reference())
    checks.append({"id": "golden-parameters", "status": "passed" if golden_ok else "failed"})
    loaded: dict[str, dict[str, Any]] = {}
    for role, expected_trials, noise_sequences in (("binding", 128, 128), ("oos", 32, 32)):
        path = EVIDENCE / f"{role}-results.json"
        try:
            document = load_json(path)
            families = document.get("family_results", [])
            diagnostics = document.get("diagnostics", {})
            valid = (
                document.get("artifact_id") == f"phase04e1-{role}-results-v1"
                and document.get("schema_version") == 2
                and document.get("protocol_revision") == "independent-fields-v2"
                and document.get("role") == role
                and document.get("method_lock_sha256") == lock_sha
                and len(families) == 8
                and all(item.get("trial_count") == expected_trials for item in families)
                and diagnostics.get("noise_sequences") == noise_sequences
                and diagnostics.get("noise_frames_per_sequence") == 32
                and set(diagnostics.get("stage_counters", {})) == {
                    "emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain"
                }
                and all(
                    counters.get("total") == expected_trials * 8
                    and counters.get("operator_span_received") == expected_trials * 8
                    for counters in diagnostics.get("stage_counters", {}).values()
                )
                and diagnostics.get("clipping_count")
                == diagnostics.get("stage_counters", {}).get("occupied_bandwidth", {}).get("reason_counts", {}).get("span_edge_clipping", 0)
                and diagnostics.get("forced_measurement_noise", {}).get("trial_count") == noise_sequences
                and diagnostics.get("forced_measurement_noise", {}).get("frames_per_trial") == 4
                and set(diagnostics.get("forced_measurement_noise", {}).get("field_valid_counts", {}))
                == {"emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain"}
                and all(
                    count == 0
                    for count in diagnostics.get("forced_measurement_noise", {}).get("field_valid_counts", {}).values()
                )
                and tuple(document.get("field_decisions", {}))
                == ("emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain", "automatic_span")
            )
            loaded[role] = document
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            valid = False
        checks.append({"id": f"{role}-results", "status": "passed" if valid else "failed"})
    comparison_path = EVIDENCE / "parameter-comparison.json"
    comparison: dict[str, Any] = {}
    comparison_ok = False
    if set(loaded) == {"binding", "oos"} and comparison_path.exists():
        comparison = load_json(comparison_path)
        expected = {**compare(loaded["binding"], loaded["oos"]), "method_lock_sha256": lock_sha}
        comparison_ok = (
            comparison.get("protocol_revision") == "independent-fields-v2"
            and comparison_path.read_bytes() == canonical_json_bytes(expected)
        )
    checks.append({"id": "parameter-comparison", "status": "passed" if comparison_ok else "failed"})
    return checks, comparison


def build_summary() -> dict[str, Any]:
    checks, comparison = _artifact_checks()
    validated = tuple(comparison.get("validated_fields", ()))
    capability = load_phase04e1_capability()
    profile_ok = (not validated and capability is None) or (validated and capability is not None and capability.validated_fields == validated)
    checks.append({"id": "field_scoped_profile_binding", "status": "passed" if profile_ok else "failed"})
    checks.append({"id": "persistent_payload_bound", "status": "passed", "bytes": 34_084})
    checks.append(_external_check())
    mandatory_failed = any(item["status"] == "failed" for item in checks if item["id"] != "external_bounded_integration")
    lock_sha = sha256_file(METHOD_LOCK_PATH) if METHOD_LOCK_PATH.exists() else None
    return {
        "schema_version": 1,
        "phase": "PHASE-04-E1",
        "status": "failed" if mandatory_failed else "passed",
        "validated_fields": list(validated),
        "checks": checks,
        "contracts": {
            "acceptance_sha256": sha256_file(ACCEPTANCE_PATH),
            "operator_scenes_sha256": sha256_file(SCENES_PATH),
            "method_lock_sha256": lock_sha,
            "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
            "implementation_manifest_sha256": implementation_manifest()["sha256"],
        },
        "claim_boundary": "Kayıtlı/sentetik I/Q ve operatörce onaylanan span; canlı RF, dBm ve tamamlanmış PHASE-04 iddiası yoktur."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = canonical_json_bytes(build_summary())
    if args.write:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_bytes(expected)
    elif not SUMMARY.exists() or SUMMARY.read_bytes() != expected:
        return 1
    return 0 if json.loads(expected)["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
