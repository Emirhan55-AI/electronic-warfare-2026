#!/usr/bin/env python3
"""Create or check the pre-binding PHASE-04-D1 OBW99 method lock."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.obw99 import OccupiedBandwidthEstimator
from reference.parameters.obw99_reference import (
    ACCEPTANCE_PATH,
    ADR_PATH,
    GENERATOR_PATH,
    PHASE03_PROFILE_PATH,
    REFERENCE_CONTRACT_PATH,
    SCENES_PATH,
    canonical_json_bytes,
    implementation_manifest,
    load_d1_catalog,
    load_json,
    noise_calibration,
    sha256_file,
)


OUTPUT = ROOT / "datasets" / "fixtures" / "phase04d1" / "method-lock.json"
CLEAN_REFERENCE = ROOT / "datasets" / "fixtures" / "phase04d1" / "clean-reference.json"
INTERFACE_CONTRACT = ROOT / "docs" / "interfaces" / "OCCUPIED_BANDWIDTH_CONTRACT.md"


def _lock_document() -> dict[str, Any]:
    calibration = noise_calibration()
    if calibration["status"] != "passed":
        raise ValueError("noise calibration must pass before method-lock creation")
    if not CLEAN_REFERENCE.is_file() or load_json(CLEAN_REFERENCE).get("status") != "passed":
        raise ValueError("clean reference must pass before method-lock creation")
    reference_contract = load_json(REFERENCE_CONTRACT_PATH)
    acceptance = load_json(ACCEPTANCE_PATH)
    catalog = load_d1_catalog()
    if reference_contract.get("status") != "accepted" or acceptance.get("status") != "accepted":
        raise ValueError("numeric contracts are not accepted")
    runtime = {
        "method_id": OccupiedBandwidthEstimator.METHOD_ID,
        "block_id": OccupiedBandwidthEstimator.BLOCK_ID,
        "output_type": OccupiedBandwidthEstimator.OUTPUT_TYPE,
        "temporal_depth": reference_contract["temporal_state"]["minimum_consecutive_confirmed_observed_frames"],
        "initial_margin_bins": reference_contract["analysis_span"]["initial_margin_bins_per_side"],
        "expansion_step_bins": reference_contract["analysis_span"]["expansion_step_bins_per_side"],
        "maximum_analysis_bins": reference_contract["analysis_span"]["maximum_analysis_width_bins"],
        "edge_guard_bins": reference_contract["analysis_span"]["analysis_edge_guard_bins"],
        "reference_cells_per_side": reference_contract["analysis_span"]["reference_cells_per_side"],
        "reference_guard_bins": reference_contract["analysis_span"]["reference_guard_bins"],
        "minimum_excess_to_noise_ratio": reference_contract["quality"]["minimum_integrated_excess_to_noise_ratio"],
        "maximum_active_events": reference_contract["bounded_memory"]["maximum_active_events"],
        "maximum_history_bytes": reference_contract["bounded_memory"]["total_bytes_for_64_events"],
    }
    document: dict[str, Any] = {
        "schema_version": 1,
        "phase": "PHASE-04-D1E",
        "status": "locked-pre-binding",
        "comparison_id": "phase04-d1-obw99-selection-v1",
        "method": runtime,
        "contracts": {
            "adr_0007_sha256": sha256_file(ADR_PATH),
            "interface_contract_sha256": sha256_file(INTERFACE_CONTRACT),
            "acceptance_gates_sha256": sha256_file(ACCEPTANCE_PATH),
            "reference_contract_sha256": sha256_file(REFERENCE_CONTRACT_PATH),
            "scene_catalog_sha256": sha256_file(SCENES_PATH),
            "clean_reference_sha256": sha256_file(CLEAN_REFERENCE),
            "clean_reference_generator_sha256": sha256_file(GENERATOR_PATH),
            "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
        },
        "noise_calibration": calibration,
        "implementation_manifest": implementation_manifest(),
        "statistics": {
            "q95_method": catalog["common"]["q95_method"],
            "q95_rank_formula": catalog["common"]["q95_rank_formula"],
            "invalid_expected_valid_result": "valid_rate_failure",
            "negative_populations_in_valid_rate": False,
        },
        "populations": {
            "supported_family_ids": [item["family_id"] for item in catalog["supported_families"]],
            "binding_snr_db": catalog["common"]["binding_snr_db"],
            "binding_trials_per_family": catalog["common"]["binding_trials_per_family"],
            "oos_trials_per_family": catalog["common"]["oos_trials_per_family"],
            "binding_base_seed": catalog["common"]["binding_base_seed"],
            "oos_base_seed": catalog["common"]["oos_base_seed"],
            "noise_sequences": catalog["common"]["noise_sequences"],
            "noise_frames_per_sequence": catalog["common"]["noise_frames_per_sequence"],
            "close_pair_trials": catalog["common"]["close_pair_trials"],
        },
        "binding_or_oos_executed": False,
    }
    document["identity_sha256"] = hashlib.sha256(canonical_json_bytes(document)).hexdigest()
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = canonical_json_bytes(_lock_document())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.write:
        if OUTPUT.is_file() and OUTPUT.read_bytes() != payload:
            print("existing method lock differs; refusing overwrite", file=sys.stderr)
            return 2
        if not OUTPUT.is_file():
            OUTPUT.write_bytes(payload)
        print("method lock established")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
        print("method lock is missing or differs", file=sys.stderr)
        return 1
    print("method lock check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
