"""Kayıtlı özgün CI8 parametre penceresini çalışan P0 kart hizmetinde yeniden ölç."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.parameters import MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.p0.parameter_client import BoardAnalysisSpan, measure_on_board
from app.operator_console.measurement_record import read_measurement, result_fields


def _intent(document: dict) -> MeasurementIntent:
    values = dict(document["intent"])
    values["span"] = BoardAnalysisSpan(**values["span"])
    context = dict(values["context"])
    context["candidates"] = tuple(
        MeasurementCandidate(**item) for item in context["candidates"]
    )
    context["owner_observed_frames"] = tuple(context["owner_observed_frames"])
    values["context"] = MeasurementContext(**context)
    return MeasurementIntent(**values)


def replay(path: Path, host: str, port: int, *, recover_carrier: bool = False) -> dict:
    document, frames = read_measurement(path)
    if len(frames) != 16:
        raise ValueError("Kartın genişletilmiş ölçümü için kayıt tam 16 kare olmalıdır.")
    interleaved = np.stack((np.stack(frames).real, np.stack(frames).imag), axis=-1) * 128.0
    if (
        np.any(interleaved != np.rint(interleaved))
        or np.any(interleaved < -128)
        or np.any(interleaved > 127)
    ):
        raise ValueError("Kayıttaki özgün CI8 örnekleri geri üretilemiyor.")
    raw_ci8 = interleaved.astype(np.int8).tobytes()
    measurement = measure_on_board(
        host,
        port,
        _intent(document),
        raw_ci8,
        sample_rate_hz=int(document["sample_rate_hz"]),
        center_frequency_hz=int(document["center_frequency_hz"]),
        recover_carrier=recover_carrier,
    )
    return {
        "status": "passed",
        "record_path": str(path.resolve()),
        "record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "input_ci8_sha256": hashlib.sha256(raw_ci8).hexdigest(),
        "board_endpoint": {"host": host, "port": port},
        "protocol": f"P0PM-v{int.from_bytes(measurement.response[4:6], 'little')}",
        "elapsed_us": measurement.elapsed_us,
        "profile_generation": measurement.profile_generation,
        "fields": result_fields(measurement.result),
        "quality": asdict(measurement.result.quality),
        "response_sha256": hashlib.sha256(measurement.response).hexdigest(),
        "source_measurement_fields": document["fields"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recover-carrier", action="store_true")
    args = parser.parse_args()
    report = replay(args.record, args.host, args.port, recover_carrier=args.recover_carrier)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({
        "status": report["status"],
        "protocol": report["protocol"],
        "elapsed_us": report["elapsed_us"],
        "fields": report["fields"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
