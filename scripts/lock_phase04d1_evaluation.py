#!/usr/bin/env python3
"""Create or check the immutable PHASE-04-D1F pre-run evaluation lock."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.obw99_evaluation import (
    COMPARISON_ID,
    EVALUATION_LOCK_PATH,
    evaluation_input_hashes,
    verify_evaluation_lock,
)
from reference.parameters.obw99_reference import canonical_json_bytes, load_d1_catalog, load_json, sha256_file


SOURCES = (
    "reference/parameters/obw99_evaluation.py",
    "scripts/lock_phase04d1_evaluation.py",
    "scripts/run_phase04d1_evaluation.py",
    "scripts/verify_phase04d1.py",
)


def document() -> dict[str, object]:
    catalog = load_d1_catalog()
    method_lock = load_json(ROOT / "datasets/fixtures/phase04d1/method-lock.json")
    sources = [
        {"path": path, "sha256": sha256_file(ROOT / path)}
        for path in sorted(SOURCES)
    ]
    manifest = {"sources": sources}
    return {
        "schema_version": 1,
        "phase": "PHASE-04-D1F",
        "status": "locked-pre-run",
        "comparison_id": COMPARISON_ID,
        "inputs": evaluation_input_hashes(),
        "method_lock_identity": method_lock["identity_sha256"],
        "implementation_manifest": {
            "identity_sha256": hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
            "sources": sources,
        },
        "statistics": {
            "q95_method": catalog["common"]["q95_method"],
            "q95_rank_formula": catalog["common"]["q95_rank_formula"],
        },
        "populations": {
            "supported_family_ids": [item["family_id"] for item in catalog["supported_families"]],
            "binding_base_seed": catalog["common"]["binding_base_seed"],
            "binding_trials_per_family": catalog["common"]["binding_trials_per_family"],
            "binding_snr_db": catalog["common"]["binding_snr_db"],
            "oos_base_seed": catalog["common"]["oos_base_seed"],
            "oos_trials_per_family": catalog["common"]["oos_trials_per_family"],
            "close_pair_population": "close_am_qpsk",
            "negative_population": "noise_only",
            "noise_sequences_binding": catalog["common"]["noise_sequences"],
            "noise_frames_per_sequence": catalog["common"]["noise_frames_per_sequence"],
        },
        "dynamic_timing_used_for_decision": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = canonical_json_bytes(document())
    if args.write:
        if EVALUATION_LOCK_PATH.exists() and EVALUATION_LOCK_PATH.read_bytes() != payload:
            print("existing evaluation lock differs; refusing overwrite", file=sys.stderr)
            return 2
        if not EVALUATION_LOCK_PATH.exists():
            EVALUATION_LOCK_PATH.write_bytes(payload)
        print("evaluation lock established")
        return 0
    if not EVALUATION_LOCK_PATH.is_file() or EVALUATION_LOCK_PATH.read_bytes() != payload:
        print("evaluation lock is missing or differs", file=sys.stderr)
        return 1
    verify_evaluation_lock(load_json(EVALUATION_LOCK_PATH))
    print("evaluation lock check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
