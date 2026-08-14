"""Lock PHASE-04-E1 methods and implementation inputs before evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.operator_assisted import OperatorMeasurementProcessor
from reference.parameters.operator_reference import (
    ACCEPTANCE_PATH,
    METHOD_LOCK_PATH,
    PHASE03_PROFILE_PATH,
    SCENES_PATH,
    canonical_json_bytes,
    implementation_manifest,
    sha256_file,
)


EVIDENCE = ROOT / "results" / "evidence" / "phase04e1"
INVALID_RUN = EVIDENCE / "invalid-protocol-run1"
INVALID_FILES = (
    "binding-results.json",
    "oos-results.json",
    "parameter-comparison.json",
    "golden-parameters.json",
    "verification-summary.json",
)


def _archive_invalid_run() -> None:
    """Preserve the first protocol-invalid run once, before the v2 lock replaces it."""
    manifest_path = INVALID_RUN / "invalid-run-manifest.json"
    if manifest_path.exists():
        return
    INVALID_RUN.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, str]] = []
    for name in INVALID_FILES:
        source = EVIDENCE / name
        target = INVALID_RUN / name
        target.write_bytes(source.read_bytes())
        files.append({"file": name, "sha256": sha256_file(source)})
    old_lock = METHOD_LOCK_PATH.read_bytes()
    (INVALID_RUN / "method-lock.json").write_bytes(old_lock)
    old_lock_document = json.loads(old_lock.decode("utf-8"))
    constants_sha256 = hashlib.sha256(canonical_json_bytes(old_lock_document["constants"])).hexdigest()
    files.append({"file": "method-lock.json", "sha256": hashlib.sha256(old_lock).hexdigest()})
    manifest = {
        "schema_version": 1,
        "status": "evaluation_protocol_invalid",
        "protocol_revision": "coupled-fields-v1",
        "invalid_reasons": [
            "automatic_span_was_a_global_manual_field_gate",
            "obw_edge_and_temporal_gates_were_applied_to_every_field",
        ],
        "capability_decision_allowed": False,
        "benchmark_used_for_retuning": False,
        "algorithm_constants_changed": False,
        "algorithm_constants_sha256": constants_sha256,
        "files": files,
    }
    manifest_path.write_bytes(canonical_json_bytes(manifest))


def build_lock() -> dict[str, object]:
    manifest = implementation_manifest()
    payload: dict[str, object] = {
        "schema_version": 1,
        "lock_id": "phase04e1-method-lock-v1",
        "status": "locked-pre-binding",
        "protocol_revision": "independent-fields-v2",
        "methods": {
            "automatic_span": "span.candidate-bounded-v1",
            **OperatorMeasurementProcessor.METHOD_IDS,
        },
        "constants": {
            "usable_shifted_bins": [20, 4075],
            "span_width_bins": [8, 512],
            "reference_cells_per_side": 32,
            "reference_guard_bins": 4,
            "reference_mismatch_db_maximum": 3.0,
            "required_consecutive_frames": 4,
            "minimum_integrated_snr_db": 6.0,
            "edge_excess_share_maximum": 0.005,
            "carrier_peak_to_noise_db_minimum": 10.0,
            "carrier_line_share_minimum": 0.35,
            "carrier_temporal_range_bins_maximum": 1.0,
            "domain_thresholds": {
                "off_fraction_minimum": 0.20,
                "two_level_minimum": 0.75,
                "constant_modulus_maximum": 0.20,
                "phase_jump_minimum": 0.005,
                "phase_jump_maximum": 0.25,
                "fsk_mode_separation_minimum": 4.0,
                "fsk_valley_ratio_maximum": 0.50,
                "confidence_minimum": 0.33,
                "score_margin_minimum": 2
            }
        },
        "contracts": {
            "acceptance_sha256": sha256_file(ACCEPTANCE_PATH),
            "operator_scenes_sha256": sha256_file(SCENES_PATH),
            "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
            "implementation_manifest_sha256": manifest["sha256"],
        },
    }
    identity = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return {**payload, "method_lock_sha256": identity}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = canonical_json_bytes(build_lock())
    if args.write:
        _archive_invalid_run()
        METHOD_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        METHOD_LOCK_PATH.write_bytes(expected)
        return 0
    return 0 if METHOD_LOCK_PATH.exists() and METHOD_LOCK_PATH.read_bytes() == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
