"""Generate/check deterministic evidence for all three competition search modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0 import P0SearchEngine, SearchRequest
from reference.p0.fixtures import build_judge_demo_engine


EVIDENCE_PATH = ROOT / "results" / "evidence" / "p0" / "judge-workflow.json"


def _measurement(result: object) -> dict[str, object]:
    parameters = getattr(result, "parameters")
    if len(parameters) != 1:
        return {"detected_count": len(parameters), "status": "failed"}
    item = parameters[0]
    return {
        "detected_count": 1,
        "confirmed": item.confirmed,
        "carrier_frequency_hz": item.carrier_frequency_hz,
        "lower_frequency_hz": item.lower_frequency_hz,
        "upper_frequency_hz": item.upper_frequency_hz,
        "bandwidth_hz": item.bandwidth_hz,
        "bandwidth_method": item.bandwidth_method,
        "coarse_candidate_bandwidth_hz": item.coarse_candidate_bandwidth_hz,
        "relative_power_dbfs": item.relative_power_dbfs,
        "snr_db": item.snr_db,
        "signal_domain": item.signal_domain,
        "calibration_state": item.calibration_state,
        "provenance": item.provenance,
        "backend": item.backend,
        "status": "passed" if item.confirmed else "failed",
    }


def evaluate() -> dict[str, object]:
    engine = build_judge_demo_engine()
    assert isinstance(engine, P0SearchEngine)
    demonstrations = (
        ("DEMO-A", "BİLİNMEYEN FREKANS", SearchRequest.unknown()),
        ("DEMO-B", "HAKEM BANT BİLDİRDİ", SearchRequest.judge_band_mhz(100.080, 100.100)),
        ("DEMO-C", "HAKEM FREKANS BİLDİRDİ", SearchRequest.judge_frequency_mhz(100.090)),
    )
    records = []
    for demo_id, label, request in demonstrations:
        result = engine.execute(request)
        records.append(
            {
                "demo": demo_id,
                "ui_label": label,
                "request_mode": request.mode.value,
                "request_bounds_hz": request.analysis_bounds_hz(),
                "examined_windows": result.examined_window_ids,
                "execution_status": result.status,
                "measurement": _measurement(result),
            }
        )

    excluding_band = engine.execute(SearchRequest.judge_band_mhz(99.950, 99.960))
    wrong_frequency = engine.execute(SearchRequest.judge_frequency_mhz(100.200))
    invalid_cases = []
    for case, factory in (
        ("not-finite", lambda: SearchRequest.judge_band_mhz(float("nan"), 100.1)),
        ("reversed-band", lambda: SearchRequest.judge_band_mhz(100.1, 100.0)),
        ("out-of-range", lambda: SearchRequest.judge_frequency_mhz(7000.0)),
        ("excessive-span", lambda: SearchRequest.judge_band_mhz(100.0, 121.0)),
    ):
        try:
            factory()
        except ValueError as exc:
            invalid_cases.append({"case": case, "rejected": True, "message": str(exc)})
        else:
            invalid_cases.append({"case": case, "rejected": False, "message": None})
    negative = {
        "band_excluding_signal": {
            "status": excluding_band.status,
            "detected_count": len(excluding_band.parameters),
        },
        "wrong_exact_frequency": {
            "status": wrong_frequency.status,
            "detected_count": len(wrong_frequency.parameters),
        },
        "invalid_inputs": invalid_cases,
    }
    passed = (
        all(record["measurement"]["status"] == "passed" for record in records)
        and excluding_band.status == "COMPLETED_NO_SIGNAL"
        and wrong_frequency.status == "COMPLETED_NO_SIGNAL"
        and all(item["rejected"] for item in invalid_cases)
    )
    return {
        "schema_version": 1,
        "checkpoint": "P0 Mandatory Closure Block A",
        "status": "passed" if passed else "failed",
        "canonical_frequency_unit": "Hz",
        "ui_frequency_unit": "MHz with explicit x1,000,000 conversion",
        "fixture": {
            "id": "nfm-like",
            "source": "two-frame deterministic replay with independent second-frame noise",
            "live_hardware": False,
        },
        "demonstrations": records,
        "negative_cases": negative,
        "claim_boundary": "Replay/host competition workflow; HackRF scan/tune and live RF are not exercised.",
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
        print("judge-workflow evidence is missing or stale", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
