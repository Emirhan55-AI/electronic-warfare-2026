#!/usr/bin/env python3
"""Verify the already-running P0DF-v1 service without deploying board files."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.direction_client import estimate_on_board
from app.operator_console.quick_direction_actions import _direction_source_token
from scripts.verify_phase09_amplitude_df_arm import _cases

DEFAULT_OUTPUT = (
    ROOT / "results/evidence/phase09/amplitude-df-live-service-20260918.json"
)
EXPECTED = {
    "lob-ready": "LOB HAZIR",
    "adaptive-lob-ready": "LOB HAZIR",
    "coverage-gate": "ÖN/ARKA BELİRSİZ",
    "front-back-gate": "ÖN/ARKA BELİRSİZ",
    "receiver-gate": "ALICI AYARI DEĞİŞTİ",
    "target-gate": "HEDEF FREKANSI DEĞİŞTİ",
    "prominence-gate": "BELİRSİZ MAKSİMUM",
    "linear-repeat-average": "YETERSİZ AÇI",
}


def verify(host: str, port: int) -> dict[str, object]:
    cases = []
    for name, measurements in _cases().items():
        remapped = tuple(
            replace(
                item,
                frame_id=_direction_source_token(
                    index, int(item.frame_id or 0) % 1_000_000
                ),
            )
            for index, item in enumerate(measurements)
        )
        estimate = estimate_on_board(host, port, remapped).estimate
        cases.append(
            {
                "case": name,
                "status": estimate.status,
                "angle_deg": estimate.estimated_angle_deg,
                "measurement_count": estimate.measurement_count,
                "distinct_angle_count": estimate.distinct_angle_count,
                "maximum_gap_deg": estimate.maximum_angular_gap_deg,
                "prominence_db": estimate.peak_prominence_db,
                "front_to_back_db": estimate.front_to_back_db,
                "sampling_rms_deg": estimate.angular_sampling_rms_deg,
            }
        )
    actual = {item["case"]: item["status"] for item in cases}
    if actual != EXPECTED:
        raise AssertionError("Çalışan kart hizmeti kilitli yön profiliyle eşleşmedi.")
    sources = (
        ROOT / "algorithms/p0/direction_client.py",
        ROOT / "app/operator_console/quick_direction_actions.py",
        ROOT / "platforms/embedded/p0/src/p0_amplitude_df.c",
        ROOT / "scripts/verify_phase09_direction_live_service.py",
    )
    return {
        "schema": "phase09-amplitude-df-live-service-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed",
        "requirements": ["KTR-4.4"],
        "board": {"host": host, "port": port},
        "protocol": {
            "request": "P0DF-v1",
            "response": "P0FR-v1",
            "source_frame_identity": "scan-local uint32 measurement-index plus RX frame",
        },
        "cases": cases,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources
        },
        "claim_boundary": (
            "Connected running-service ARM/network numeric verification only; no deployment, "
            "antenna, live RF, geographic bearing or degree-RMS accuracy acceptance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = verify(args.host, args.port)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], "cases": len(result["cases"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
