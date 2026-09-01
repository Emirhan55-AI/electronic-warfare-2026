"""Record operator-triggered real RX sessions; never substitutes IQ or board data."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CAPTURE_SOURCES = (
    "app/operator_console/detection_model.py",
    "app/operator_console/live_ed.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/quick_application.py",
    "app/operator_console/qml/Main.qml",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
    "scripts/capture_phase08_product.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CAPTURE_SOURCES}
    lock = threading.Lock()
    counter = max((int(path.stem.split("-")[1]) for path in output.glob("run-*.json")), default=0)

    from app.operator_console.live_ed import LiveEDSession
    from app.operator_console.quick_application import build_quick_application

    class ObservedSession(LiveEDSession):
        def run(self, snapshot_handler=None):
            nonlocal counter
            with lock:
                counter += 1
                index = counter
            snapshots = []
            started = time.perf_counter()
            report = {
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "configuration": asdict(self.configuration),
                "source_sha256": source_hashes,
                "backend": "real HackRFContinuousRX and TCPClientIQTransport",
                "transmit_enabled": False,
                "ui_triggered": True,
            }

            def observe(snapshot):
                snapshots.append({
                    "sequence_number": snapshot.sequence_number,
                    "iq_sha256": hashlib.sha256(snapshot.output_frame.payload).hexdigest(),
                    "response": asdict(snapshot.response),
                })
                if snapshot_handler:
                    snapshot_handler(snapshot)

            try:
                result = super().run(observe)
                report["status"] = "passed"
                report["result"] = asdict(result)
                return result
            except Exception as exc:
                report["status"] = "failed"
                report["error_code"] = getattr(exc, "code", type(exc).__name__)
                report["error"] = str(exc)
                raise
            finally:
                report["elapsed_seconds"] = time.perf_counter() - started
                report["snapshots"] = snapshots
                # Exclusive creation preserves evidence from earlier launches.
                with (output / f"run-{index:02d}.json").open("x", encoding="utf-8") as stream:
                    json.dump(report, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")

    app, engine, view_model = build_quick_application([sys.argv[0]])
    view_model._live_session_factory = ObservedSession
    last_state = None

    def selected_measurement_window():
        rows = []
        selected_id = view_model.selectedDetectionId
        for snapshot in getattr(view_model, "_selected_live_measurement_window", ()):
            owner = next(
                (
                    event
                    for event in snapshot.response.active
                    if event.event_id == selected_id
                    and event.state == "confirmed"
                    and event.observed_this_frame
                ),
                None,
            )
            rows.append(
                {
                    "sequence_number": snapshot.sequence_number,
                    "frame_id": snapshot.response.frame_id,
                    "iq_sha256": hashlib.sha256(snapshot.output_frame.payload).hexdigest(),
                    "sample_rate_hz": snapshot.output_frame.sample_rate_hz,
                    "center_frequency_hz": snapshot.output_frame.center_frequency_hz,
                    "event_id": owner.event_id if owner is not None else None,
                    "event_revision": owner.seen_count if owner is not None else None,
                    "confirmed_and_observed": owner is not None,
                }
            )
        return rows

    def save_ui_state():
        nonlocal last_state
        parameter_rows = view_model.parameterRows
        current = (
            view_model.busy,
            view_model.frameIndex,
            view_model.sourceState,
            view_model.selectedDetectionId,
            view_model.showLiveCandidates,
            view_model.analysisSpanConfirmed,
            view_model.measurementReady,
            json.dumps(parameter_rows, ensure_ascii=False, sort_keys=True),
        )
        if current == last_state:
            return
        last_state = current
        payload = {
            "source_state": view_model.sourceState,
            "source_ready": view_model.sourceReady,
            "busy": view_model.busy,
            "frame_index": view_model.frameIndex,
            "frame_count": view_model.frameCount,
            "status": view_model.statusMessage,
            "error": view_model.errorMessage,
            "detections": view_model.detections,
            "spectrum_points": len(view_model.spectrumValues),
            "selected_event_id": view_model.selectedDetectionId,
            "selected_state": view_model.selectedDetectionStateText,
            "selected_current": view_model.selectedDetectionCurrent,
            "analysis_span_confirmed": view_model.analysisSpanConfirmed,
            "measurement_selection_ready": view_model.measurementSelectionReady,
            "measurement_ready": view_model.measurementReady,
            "measurement_window": selected_measurement_window(),
            "parameter_rows": parameter_rows,
            "show_candidates": view_model.showLiveCandidates,
            "pipeline": view_model.pipelineBlocks,
        }
        (output / "ui-state.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    view_model.stateChanged.connect(save_ui_state)
    view_model.detectionsChanged.connect(save_ui_state)
    save_ui_state()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
