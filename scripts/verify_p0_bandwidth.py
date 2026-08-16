"""Generate/check the P0 mandatory bandwidth ground-truth evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0.bandwidth import BandwidthProfile
from reference.p0.fixtures import FRAME_LENGTH, SAMPLE_RATE_HZ
from scripts.verify_p0_algorithms import evaluate as evaluate_algorithms


EVIDENCE_PATH = ROOT / "results" / "evidence" / "p0" / "bandwidth-ground-truth.json"


def evaluate() -> dict[str, object]:
    algorithms = evaluate_algorithms()
    records: list[dict[str, object]] = []
    for scene in algorithms["scenes"]:
        for index, measurement in enumerate(scene["measurements"]):
            records.append(
                {
                    "fixture": scene["fixture"],
                    "emitter_index": index,
                    "ground_truth_bandwidth_hz": measurement.get("expected_bandwidth_hz"),
                    "measured_bandwidth_hz": measurement.get("measured_bandwidth_hz"),
                    "absolute_error_hz": measurement.get("bandwidth_absolute_error_hz"),
                    "relative_error": measurement.get("bandwidth_relative_error"),
                    "tolerance_hz": measurement.get("bandwidth_tolerance_hz"),
                    "tolerance_bins": measurement.get("bandwidth_tolerance_bins"),
                    "canonical_method": measurement.get("bandwidth_method"),
                    "threshold_bandwidth_hz": measurement.get("threshold_bandwidth_hz"),
                    "occupied_bandwidth_hz": measurement.get("occupied_bandwidth_hz"),
                    "coarse_candidate_bandwidth_hz": measurement.get("coarse_candidate_bandwidth_hz"),
                    "failure_condition": measurement.get("failure_condition"),
                    "status": measurement.get("status"),
                }
            )
    passed = bool(records) and all(item["status"] == "passed" for item in records)
    profile = BandwidthProfile()
    return {
        "schema_version": 1,
        "checkpoint": "P0 Mandatory Closure Block A",
        "status": "passed" if passed else "failed",
        "canonical_output": "threshold edges when stable; explicitly labelled noise-referenced occupied-power fallback otherwise",
        "profile": {
            "edge_snr_db": profile.edge_snr_db,
            "occupied_power_fraction": profile.occupied_power_fraction,
            "smoothing_kernel": profile.smoothing_kernel,
            "maximum_bridge_gap_bins": profile.maximum_bridge_gap_bins,
            "threshold_to_occupied_maximum_ratio": profile.threshold_to_occupied_maximum_ratio,
            "fft_length": FRAME_LENGTH,
            "fixture_sample_rate_hz": SAMPLE_RATE_HZ,
            "fixture_bin_width_hz": SAMPLE_RATE_HZ / FRAME_LENGTH,
        },
        "records": records,
        "claim_boundary": "Deterministic host fixtures with bin-resolution tolerances; not calibrated RF or ZedBoard execution.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("bandwidth evidence is missing or stale", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
