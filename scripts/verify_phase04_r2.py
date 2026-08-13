#!/usr/bin/env python3
"""Establish or read-only verify deterministic PHASE-04-R2 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters import R2_BAND_HISTORY_BYTES, R2_PARAMETER_HISTORY_BYTES  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes, phase04_implementation_manifest  # noqa: E402
from reference.parameters.r2 import R2_COMPARISON_ID  # noqa: E402
from reference.pipeline import RuntimePipeline, load_verified_phase04_profile  # noqa: E402
from reference.spectrum import SigMFFrameSource  # noqa: E402


EVIDENCE = ROOT / "results" / "evidence" / "phase04"
LOCK = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"
COMPARISON = EVIDENCE / "r2-parameter-comparison.json"
DIAGNOSTIC = EVIDENCE / "r2-family-diagnostic.json"
OOS = EVIDENCE / "r2-out-of-sample.json"
GOLDEN = EVIDENCE / "r2-golden-parameters.json"
SUMMARY = EVIDENCE / "r2-verification-summary.json"
PROFILE = ROOT / "profiles" / "phase04" / "operation-default.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _document(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    document = json.loads(data.decode("utf-8"))
    if not isinstance(document, dict) or canonical_json_bytes(document) != data:
        raise ValueError(f"{path.name} is not canonical JSON")
    return document, data


def _validate_inputs(
    comparison_path: Path,
    diagnostic_path: Path,
    oos_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    comparison, _ = _document(comparison_path)
    diagnostic, _ = _document(diagnostic_path)
    oos, _ = _document(oos_path)
    manifest = phase04_implementation_manifest()
    if comparison.get("schema_version") != 3 or comparison.get("comparison_id") != R2_COMPARISON_ID:
        raise ValueError("R2 comparison identity is invalid")
    if comparison.get("method_lock_sha256") != _sha(LOCK):
        raise ValueError("R2 comparison method-lock digest is stale")
    for field in ("catalog_sha256", "implementation_manifest_sha256", "phase03_profile_sha256"):
        if comparison.get(field) != manifest[field]:
            raise ValueError(f"R2 comparison {field} is stale")
    if diagnostic.get("phase") != "PHASE-04-R2" or diagnostic.get("status") != "passed":
        raise ValueError("R2 diagnostic evidence is invalid")
    for key in ("noise_calibration", "noise_end_to_end_validation", "morphology_calibration"):
        if diagnostic.get(key, {}).get("status") != "passed":
            raise ValueError(f"R2 diagnostic {key} did not pass")
    if (
        oos.get("phase") != "PHASE-04-R2"
        or oos.get("status") != "passed"
        or oos.get("used_for_selection") is not False
        or oos.get("used_for_gate_changes") is not False
        or oos.get("base_seed") != 20260423
        or oos.get("trials_per_family") != 32
        or oos.get("snr_db_order") != [12.0, -6.0, 0.0, 6.0]
        or not isinstance(oos.get("rows"), list)
        or len(oos["rows"]) != 40
        or any(row.get("binding") is not False for row in oos["rows"])
    ):
        raise ValueError("R2 OOS isolation contract is invalid")
    return comparison, diagnostic, oos


def _external(start: int, count: int) -> dict[str, Any]:
    metadata = os.environ.get("PHASE01_EXTERNAL_METADATA")
    data = os.environ.get("PHASE01_EXTERNAL_DATA")
    if not metadata and not data:
        return {"status": "skipped", "reason": "external paths are not configured"}
    if not metadata or not data:
        return {"status": "failed", "reason": "both external variables are required"}
    if not PROFILE.is_file():
        return {"status": "skipped", "reason": "validated PHASE-04-R2 profile is unavailable"}
    if start < 0 or not 1 <= count <= 4:
        return {"status": "failed", "reason": "bounded frame range is invalid"}
    source = None
    try:
        profile, binding = load_verified_phase04_profile(PROFILE, COMPARISON)
        source = SigMFFrameSource(Path(metadata), Path(data), mode="explicit", frame_length=4096)
        if start + count > source.frame_count:
            return {"status": "failed", "reason": "bounded frame range exceeds the recording"}
        replays: list[list[dict[str, int]]] = []
        for _ in range(2):
            runtime = RuntimePipeline(profile, verified_binding=binding)
            records: list[dict[str, int]] = []
            for index in range(start, start + count):
                result = runtime.process(
                    source.read_frame(index),
                    sample_rate_hz=source.sample_rate_hz,
                    center_frequency_hz=source.center_frequency_hz,
                    frame_index=index,
                )
                records.append({
                    "frame_index": index,
                    "region_count": len(result.detection.regions),
                    "parameter_event_count": 0 if result.parameters is None else len(result.parameters.events),
                })
            replays.append(records)
        return {
            "status": "passed" if replays[0] == replays[1] else "failed",
            "start_frame": start,
            "frame_count": count,
            "source_datatype": source.report.source_datatype,
            "sample_rate_hz": source.sample_rate_hz,
            "deterministic_replay": replays[0] == replays[1],
            "bounded_read_only": True,
            "annotation_ground_truth_used": False,
            "bandwidth_accuracy_claimed": False,
        }
    except Exception as exc:
        return {"status": "failed", "reason": str(getattr(exc, "code", type(exc).__name__))}
    finally:
        if source is not None:
            source.close()


def build(
    comparison_path: Path = COMPARISON,
    diagnostic_path: Path = DIAGNOSTIC,
    oos_path: Path = OOS,
    *,
    external_start: int = 0,
    external_count: int = 4,
) -> tuple[dict[str, Any], dict[str, Any]]:
    comparison, diagnostic, oos = _validate_inputs(comparison_path, diagnostic_path, oos_path)
    band_status = str(comparison.get("noise_bandwidth_decision", {}).get("status"))
    algorithm_status = str(comparison.get("overall"))
    profile_required = algorithm_status == "passed"
    binding_status = "skipped"
    binding_error = None
    profile_sha256 = None
    if profile_required:
        try:
            load_verified_phase04_profile(PROFILE, COMPARISON)
            binding_status = "passed"
            profile_sha256 = _sha(PROFILE)
        except Exception as exc:
            binding_status = "failed"
            binding_error = str(getattr(exc, "code", type(exc).__name__))
    elif PROFILE.exists():
        binding_status = "failed"
        binding_error = "profile_must_be_absent_for_failed_comparison"
    external = _external(external_start, external_count)
    checks = [
        {"name": "method-lock-and-calibration", "status": "passed"},
        {"name": "comparison-integrity", "status": "passed"},
        {"name": "oos-isolation", "status": "passed"},
        {"name": "binding-band", "status": "passed" if band_status == "passed" else "failed"},
        {
            "name": "validated-profile-binding",
            "status": binding_status,
        },
        {"name": "external-ism-bounded", "status": external["status"]},
    ]
    infrastructure_ok = binding_status != "failed" and external["status"] != "failed"
    golden = {
        "schema_version": 1,
        "phase": "PHASE-04-R2",
        "evidence_status": "passed" if infrastructure_ok else "failed",
        "algorithm_status": algorithm_status,
        "binding_band_status": band_status,
        "method_lock_sha256": _sha(LOCK),
        "comparison_sha256": _sha(comparison_path),
        "family_diagnostic_sha256": _sha(diagnostic_path),
        "out_of_sample_sha256": _sha(oos_path),
        "profile_sha256": profile_sha256,
        "selected_methods": comparison.get("selected_methods"),
        "profile_binding_status": binding_status,
        "profile_binding_error_code": binding_error,
        "locked_calibration": {
            "iid_correction": 1.2775478205746595,
            "hann_correction": 1.2601468855166762,
            "nominal_seed_ratio": 6.907755278982137,
            "nominal_grow_ratio": 2.995732273553991,
            "exact_pfa_claimed": False,
            "morphology_moment_threshold_bins2": 2.7005873918882553,
        },
        "history_bounds": {
            "band_history_payload_bytes": R2_BAND_HISTORY_BYTES,
            "combined_parameter_history_payload_bytes": R2_PARAMETER_HISTORY_BYTES,
            "raw_iq_retained": False,
        },
        "out_of_sample": {
            "status": oos["status"],
            "base_seed": oos["base_seed"],
            "trials_per_family": oos["trials_per_family"],
            "used_for_selection": False,
            "used_for_gate_changes": False,
        },
        "external_integration": external,
    }
    summary = {
        "schema_version": 1,
        "phase": "PHASE-04-R2",
        "evidence_status": "passed" if infrastructure_ok else "failed",
        "algorithm_status": algorithm_status,
        "checks": checks,
    }
    return golden, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", action="store_true")
    actions.add_argument("--check", action="store_true")
    parser.add_argument("--comparison-source", type=Path)
    parser.add_argument("--diagnostic-source", type=Path)
    parser.add_argument("--oos-source", type=Path)
    parser.add_argument("--external-start-frame", type=int, default=0)
    parser.add_argument("--external-frame-count", type=int, default=4)
    args = parser.parse_args()
    if args.write:
        if args.comparison_source is None or args.diagnostic_source is None or args.oos_source is None:
            parser.error("--write requires all three temporary source paths")
        if not COMPARISON.is_file() or COMPARISON.read_bytes() != args.comparison_source.read_bytes():
            parser.error("established comparison must match the temporary binding result")
        comparison_path = args.comparison_source
        diagnostic_path = args.diagnostic_source
        oos_path = args.oos_source
    else:
        comparison_path, diagnostic_path, oos_path = COMPARISON, DIAGNOSTIC, OOS
    try:
        golden, summary = build(
            comparison_path,
            diagnostic_path,
            oos_path,
            external_start=args.external_start_frame,
            external_count=args.external_frame_count,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"PHASE-04-R2 evidence invalid: {type(exc).__name__}")
        return 2
    if args.write:
        _atomic(DIAGNOSTIC, diagnostic_path.read_bytes())
        _atomic(OOS, oos_path.read_bytes())
        # Rebuild hashes against their final repository-owned paths.
        golden, summary = build(external_start=args.external_start_frame, external_count=args.external_frame_count)
        _atomic(GOLDEN, canonical_json_bytes(golden))
        _atomic(SUMMARY, canonical_json_bytes(summary))
    else:
        expected_golden = canonical_json_bytes(golden)
        expected_summary = canonical_json_bytes(summary)
        if not GOLDEN.is_file() or not SUMMARY.is_file() or GOLDEN.read_bytes() != expected_golden or SUMMARY.read_bytes() != expected_summary:
            print("PHASE-04-R2 evidence differs; --check made no changes.")
            return 2
    print(f"PHASE-04-R2 evidence integrity: {summary['evidence_status']}")
    print(f"PHASE-04-R2 algorithm status: {summary['algorithm_status']}")
    return 0 if summary["evidence_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
