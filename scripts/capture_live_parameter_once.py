"""Gerçek HackRF → FPGA → ARM yolunda tek bir canlı parametre ölçümü al."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication

from app.operator_console.measurement_record import read_measurement
from app.operator_console.quick_view_model import OperatorViewModel


def _pump(app: QGuiApplication, seconds: float) -> None:
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(0.002)


def _wait(app: QGuiApplication, predicate, timeout: float) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.002)
    app.processEvents()
    return bool(predicate())


def _row_summary(rows: list[dict]) -> list[dict]:
    keys = (
        "eventId", "frequencyHz", "lowerFrequencyHz", "upperFrequencyHz",
        "startBin", "peakBin", "endBin", "stateKey", "observed",
        "verificationKey", "snr",
    )
    return [{key: row.get(key) for key in keys if key in row} for row in rows]


def capture(args: argparse.Namespace) -> dict:
    app = QGuiApplication.instance() or QGuiApplication(["live-parameter-once"])
    view = OperatorViewModel(measurement_record_directory=args.record_directory)
    report = {
        "schema": "live-parameter-once-v1",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "requested": {
            "output_center_frequency_hz": args.center_hz,
            "target_frequency_hz": args.target_hz,
            "lna_gain_db": args.lna,
            "vga_gain_db": args.vga,
            "frame_count": args.frame_count,
        },
    }
    try:
        view.setSourceMode("hackrf")
        view.probeHackrf()
        _wait(app, lambda: not view.busy, args.probe_timeout)
        report["probe"] = {
            "hackrf_ready": view.hackrfReady,
            "source_state": view.sourceState,
            "status": view.statusMessage,
            "error": view.errorMessage,
        }
        if not view.hackrfReady or view.errorMessage:
            report["status"] = "inconclusive"
            report["reason"] = "receiver_or_board_probe_failed"
            return report

        view.startLiveEDSession(
            float(args.center_hz), args.lna, args.vga, args.frame_count
        )
        if not _wait(app, lambda: view.liveSessionActive or bool(view.errorMessage), 8.0):
            report["status"] = "inconclusive"
            report["reason"] = "live_session_did_not_start"
            return report
        if view.errorMessage:
            report["status"] = "inconclusive"
            report["reason"] = "live_session_failed"
            return report

        selection_deadline = time.perf_counter() + args.detection_timeout
        selected = None
        seen_rows: list[dict] = []
        while time.perf_counter() < selection_deadline and not view.errorMessage:
            app.processEvents()
            rows = list(view.detections)
            seen_rows = _row_summary(rows)
            candidates = [
                row for row in rows
                if row.get("stateKey") == "confirmed" and bool(row.get("observed", True))
                and abs(float(row["frequencyHz"]) - args.target_hz) <= args.tolerance_hz
            ]
            if candidates:
                selected = min(
                    candidates,
                    key=lambda row: abs(float(row["frequencyHz"]) - args.target_hz),
                )
                if view.selectedDetectionId != int(selected["eventId"]):
                    view.selectDetection(int(selected["eventId"]))
                if view.measurementSelectionReady:
                    break
            time.sleep(0.003)

        report["live_before_measurement"] = {
            "source_state": view.sourceState,
            "status": view.statusMessage,
            "error": view.errorMessage,
            "frame_index": view.frameIndex,
            "center_frequency_hz": view.centerFrequencyHz,
            "sample_rate_hz": view.sampleRateHz,
            "detections": seen_rows,
            "selected_event_id": view.selectedDetectionId,
            "measurement_selection_ready": view.measurementSelectionReady,
        }
        if selected is None or not view.measurementSelectionReady:
            report["status"] = "inconclusive"
            report["reason"] = "target_not_confirmed_in_current_rf"
            return report

        lower = float(view.analysisLowerMHzText)
        upper = float(view.analysisUpperMHzText)
        view.confirmAnalysisSpan(lower, upper)
        _pump(app, 0.1)
        report["selection"] = {
            "event_id": int(selected["eventId"]),
            "frequency_hz": float(selected["frequencyHz"]),
            "analysis_lower_mhz": lower,
            "analysis_upper_mhz": upper,
            "analysis_span_confirmed": view.analysisSpanConfirmed,
        }
        if not view.analysisSpanConfirmed:
            report["status"] = "failed"
            report["reason"] = "analysis_span_confirmation_failed"
            return report

        view.requestMeasurement()
        completed = _wait(
            app,
            lambda: bool(view.parameterRows) or bool(view.errorMessage),
            args.measurement_timeout,
        )
        report["measurement"] = {
            "completed": completed,
            "status": view.statusMessage,
            "error": view.errorMessage,
            "rows": list(view.parameterRows),
            "record_path": view.measurementRecordPath,
            "info": dict(view.measurementInfo),
        }
        if not completed or view.errorMessage or not view.parameterRows:
            report["status"] = "failed" if view.errorMessage else "inconclusive"
            report["reason"] = "live_measurement_not_completed"
            return report

        record_path = Path(view.measurementRecordPath)
        document, _ = read_measurement(record_path)
        report["measurement"]["record_sha256"] = hashlib.sha256(
            record_path.read_bytes()
        ).hexdigest()
        report["measurement"]["record_fields"] = document["fields"]
        report["measurement"]["board_measurement"] = document.get("board_measurement")
        report["measurement"]["source"] = document["source"]
        required = ("emission_center_frequency", "occupied_bandwidth", "channel_power_dbfs", "snr_estimate_db")
        invalid = [key for key in required if document["fields"][key]["state"] != "valid"]
        report["status"] = "inconclusive" if invalid else "passed"
        if invalid:
            report["reason"] = "live_measurement_quality_gate_rejected"
            report["invalid_fields"] = invalid
        return report
    finally:
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report["final_status_message"] = view.statusMessage
        report["final_error_message"] = view.errorMessage
        view.shutdown()
        _pump(app, 0.1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-directory", type=Path, required=True)
    parser.add_argument("--center-hz", type=int, default=819_953_044)
    parser.add_argument("--target-hz", type=float, default=820_012_126.03125)
    parser.add_argument("--tolerance-hz", type=float, default=1_000_000.0)
    parser.add_argument("--lna", type=int, default=16)
    parser.add_argument("--vga", type=int, default=16)
    parser.add_argument("--frame-count", type=int, default=8_192)
    parser.add_argument("--probe-timeout", type=float, default=20.0)
    parser.add_argument("--detection-timeout", type=float, default=30.0)
    parser.add_argument("--measurement-timeout", type=float, default=45.0)
    args = parser.parse_args()
    report = capture(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
    print(json.dumps({
        "status": report.get("status"),
        "reason": report.get("reason"),
        "measurement": report.get("measurement", {}).get("rows", []),
    }, ensure_ascii=False))
    return 0 if report.get("status") in {"passed", "inconclusive"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
