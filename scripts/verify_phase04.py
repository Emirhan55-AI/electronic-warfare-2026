#!/usr/bin/env python3
"""Write or read-only verify deterministic PHASE-04 evidence."""

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

from reference.parameters import FEATURE_HISTORY_BYTES, compute_transient_guard, load_parameter_catalog  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes  # noqa: E402
from reference.pipeline import (  # noqa: E402
    RuntimePipeline,
    VerifiedProfileBinding,
    load_verified_phase04_profile,
)
from reference.spectrum import SigMFFrameSource  # noqa: E402


EVIDENCE = ROOT / "results" / "evidence" / "phase04"
COMPARISON = EVIDENCE / "parameter-comparison.json"
PROFILE = ROOT / "profiles" / "phase04" / "operation-default.json"
GOLDEN = EVIDENCE / "golden-parameters.json"
SUMMARY = EVIDENCE / "verification-summary.json"


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    data = canonical_json_bytes(payload)
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


def _selected_methods(profile: Any) -> dict[str, str] | None:
    block = profile.parameter_block
    if block is None:
        return None
    return {
        "analysis_window": str(block.parameters["analysis_window_method"]),
        "noise": str(block.parameters["noise_method"]),
        "bandwidth": str(block.parameters["bandwidth_method"]),
        "spectral_center": str(block.parameters["spectral_center_method"]),
        "carrier": str(block.parameters["carrier_method"]),
        "power_snr": str(block.parameters["power_snr_method"]),
        "signal_domain": str(block.parameters["signal_domain_method"]),
    }


def _external(
    profile: Any | None,
    binding: VerifiedProfileBinding | None,
    start: int,
    count: int,
) -> dict[str, Any]:
    metadata = os.environ.get("PHASE01_EXTERNAL_METADATA")
    data = os.environ.get("PHASE01_EXTERNAL_DATA")
    if not metadata and not data:
        return {"status": "skipped", "reason": "external paths are not configured"}
    if not metadata or not data:
        return {"status": "failed", "reason": "both external variables are required"}
    if profile is None:
        return {"status": "skipped", "reason": "validated PHASE-04 profile is unavailable"}
    if not 0 <= start or not 1 <= count <= 4:
        return {"status": "failed", "reason": "bounded frame range is invalid"}
    source = None
    try:
        source = SigMFFrameSource(Path(metadata), Path(data), mode="explicit", frame_length=4096)
        if start + count > source.frame_count:
            return {"status": "failed", "reason": "bounded frame range exceeds the recording"}
        passes: list[list[dict[str, Any]]] = []
        for _ in range(2):
            runtime = RuntimePipeline(profile, verified_binding=binding)
            records: list[dict[str, Any]] = []
            for index in range(start, start + count):
                frame = source.read_frame(index)
                result = runtime.process(
                    frame,
                    sample_rate_hz=source.sample_rate_hz,
                    center_frequency_hz=source.center_frequency_hz,
                    frame_index=index,
                )
                records.append(
                    {
                        "frame_index": index,
                        "event_count": 0 if result.parameters is None else len(result.parameters.events),
                        "region_count": len(result.detection.regions),
                    }
                )
            passes.append(records)
        return {
            "status": "passed" if passes[0] == passes[1] else "failed",
            "start_frame": start,
            "frame_count": count,
            "source_datatype": source.report.source_datatype,
            "sample_rate_hz": source.sample_rate_hz,
            "deterministic_replay": passes[0] == passes[1],
            "bounded_read_only": True,
            "annotation_ground_truth_used": False,
        }
    except Exception as exc:
        return {"status": "failed", "reason": str(getattr(exc, "code", type(exc).__name__))}
    finally:
        if source is not None:
            source.close()


def build(*, external_start: int = 0, external_count: int = 4) -> tuple[dict[str, Any], dict[str, Any], bool]:
    catalog = load_parameter_catalog()
    worst, width, rounded = compute_transient_guard()
    comparison: dict[str, Any] | None = None
    comparison_error = None
    if COMPARISON.is_file():
        try:
            comparison = json.loads(COMPARISON.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            comparison_error = "comparison_unreadable"
    profile = None
    binding = None
    binding_error = comparison_error
    if PROFILE.is_file():
        try:
            profile, binding = load_verified_phase04_profile(PROFILE, COMPARISON)
        except Exception as exc:
            binding_error = str(getattr(exc, "code", type(exc).__name__))
    elif binding_error is None:
        binding_error = "profile_not_established"
    selected = None if profile is None else _selected_methods(profile)
    compared = None if comparison is None else comparison.get("selected_methods")
    checks = [
        {
            "name": "catalog-contract",
            "status": "passed" if catalog["common"]["valid_feature_slice"] == [1152, 2944] else "failed",
        },
        {
            "name": "transient-guard",
            "status": "passed" if (worst, width, rounded) == (1106, 2, 1152) else "failed",
        },
        {
            "name": "feature-history-bound",
            "status": "passed" if FEATURE_HISTORY_BYTES == 67840 else "failed",
        },
        {
            "name": "comparison-profile-runtime",
            "status": "passed" if selected is not None and selected == compared and binding is not None else "failed",
        },
        {
            "name": "combined-pipeline",
            "status": "passed" if comparison is not None and comparison.get("combined_pipeline", {}).get("status") == "passed" else "failed",
        },
    ]
    external = _external(profile, binding, external_start, external_count)
    checks.append({"name": "external-ism-bounded", "status": external["status"]})
    required_failed = any(item["status"] == "failed" for item in checks if item["name"] != "external-ism-bounded")
    external_failed = external["status"] == "failed"
    passed = not required_failed and not external_failed
    catalog_bytes = (ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json").read_bytes()
    golden = {
        "schema_version": 1,
        "phase": "PHASE-04",
        "overall": "passed" if passed else "failed",
        "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        "comparison_sha256": hashlib.sha256(COMPARISON.read_bytes()).hexdigest() if COMPARISON.is_file() else None,
        "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest() if PROFILE.is_file() else None,
        "selected_methods": selected,
        "binding_status": "passed" if binding is not None else "failed",
        "binding_error_code": binding_error,
        "transient_guard": {
            "impulse_energy_fraction": 0.999,
            "worst_radius_samples": worst,
            "worst_mask_width_bins": width,
            "rounded_guard_samples_per_side": rounded,
            "feature_slice": [1152, 2944],
            "feature_sample_count": 1792,
        },
        "feature_history": {
            "maximum_tracks": 64,
            "records_per_track": 4,
            "float64_values_per_record": 32,
            "payload_bytes": FEATURE_HISTORY_BYTES,
            "raw_iq_retained": False,
        },
        "external_integration": external,
    }
    summary = {
        "schema_version": 1,
        "phase": "PHASE-04",
        "overall": "passed" if passed else "failed",
        "checks": checks,
    }
    return golden, summary, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--external-start-frame", type=int, default=0)
    parser.add_argument("--external-frame-count", type=int, default=4)
    args = parser.parse_args()
    golden, summary, passed = build(external_start=args.external_start_frame, external_count=args.external_frame_count)
    if args.write:
        _atomic(GOLDEN, golden)
        _atomic(SUMMARY, summary)
    else:
        if not GOLDEN.is_file() or not SUMMARY.is_file() or GOLDEN.read_bytes() != canonical_json_bytes(golden) or SUMMARY.read_bytes() != canonical_json_bytes(summary):
            print("PHASE-04 evidence differs; --check made no changes.")
            return 1
    print(f"PHASE-04 verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
