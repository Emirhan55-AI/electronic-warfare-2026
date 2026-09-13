"""Replay an unchanged local RF record through the portable wide-span C core.

This is a recorded-I/Q software check, not a physical PL/ARM or RF accuracy test.
"""
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from verify_p0_parameter_runtime import _build, _ci8, STATE
from algorithms.p0.parameter_client import BoardAnalysisSpan, measure_on_board
from algorithms.parameters import F5ParameterEstimator, MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from app.operator_console.measurement_record import read_measurement


def _field(field) -> dict:
    return {"state": field.state, "value": field.value, "unit": field.unit,
            "reason": field.reason}


def verify(path: Path, *, host: str | None = None, port: int = 47007) -> dict:
    document, frames = read_measurement(path)
    values = dict(document["intent"])
    context = dict(values["context"])
    context["candidates"] = tuple(MeasurementCandidate(**item) for item in context["candidates"])
    context["owner_observed_frames"] = tuple(context["owner_observed_frames"])
    values["context"] = MeasurementContext(**context)
    owner = next(item for item in context["candidates"] if item.event_id == values["event_id"])
    values["span"] = BoardAnalysisSpan(max(56, owner.lower_shifted_bin - 64),
                                      min(4039, owner.upper_shifted_bin + 64), "auto_suggested")
    intent = MeasurementIntent(**values)
    processor = SpectrumProcessor(SpectrumConfig(**document["spectrum_config"]))
    spectra, raw_frames = [], []
    with tempfile.TemporaryDirectory(prefix="parameter-wide-record-") as raw:
        directory = Path(raw)
        executable, _, compiler = _build(directory)
        paths = []
        for index, frame in enumerate(frames):
            iq, decoded = _ci8(frame)
            raw_frames.append(iq)
            if not np.array_equal(decoded, frame):
                raise ValueError("Kayıt özgün CI8 örnekleri içermiyor.")
            spectrum = processor.process(decoded, sample_rate_hz=document["sample_rate_hz"],
                                         center_frequency_hz=document["center_frequency_hz"])
            power = np.rint(np.asarray(spectrum.fft_power_unshifted) * (1 << 30)).astype("<u8")
            spectra.append(replace(spectrum, display=processor.display_from_power(spectrum, power.astype(float) / (1 << 30))))
            iq_path, power_path = directory / f"{index}.ci8", directory / f"{index}.u64"
            iq_path.write_bytes(iq)
            power_path.write_bytes(power.tobytes())
            paths.extend((iq_path, power_path))
        output = directory / "result.json"
        subprocess.run([str(executable), str(int(document["sample_rate_hz"])),
                        str(int(document["center_frequency_hz"])), str(intent.span.lower_shifted_bin),
                        str(intent.span.upper_shifted_bin), *map(str, paths), str(output)], check=True, capture_output=True)
        actual = json.loads(output.read_text(encoding="utf-8"))
        expected = F5ParameterEstimator().measure(intent, frames, tuple(spectra))
        mapping = {"carrier_line_frequency_hz": "carrier_line_frequency",
                   "emission_center_frequency_hz": "emission_center_frequency",
                   "lower_occupied_edge_hz": "lower_band_edge", "upper_occupied_edge_hz": "upper_band_edge",
                   "occupied_bandwidth_hz": "occupied_bandwidth", "channel_power_dbfs": "channel_power_dbfs",
                   "snr_estimate_db": "snr_estimate_db"}
        for c_name, py_name in mapping.items():
            reference = getattr(expected, py_name)
            assert actual[c_name]["state"] == STATE[reference.state], c_name
            if reference.state == "valid":
                assert abs(actual[c_name]["value"] - reference.value) < (0.02 if c_name.endswith("_hz") else 1e-8), c_name
    board_record = None
    if host is not None:
        measured = measure_on_board(host, port, intent, b"".join(raw_frames),
                                    sample_rate_hz=int(document["sample_rate_hz"]),
                                    center_frequency_hz=int(document["center_frequency_hz"]))
        board_record = {
            "protocol_version": int.from_bytes(measured.response[4:6], "little"),
            "response_sha256": hashlib.sha256(measured.response).hexdigest(),
            "elapsed_us": measured.elapsed_us,
            "profile_generation": measured.profile_generation,
            "fields": {py_name: _field(getattr(measured.result, py_name))
                       for py_name in mapping.values()},
        }
        if board_record["protocol_version"] != 2:
            raise AssertionError("Geniş kart ölçümü P0PR-v2 yanıtı üretmedi.")
        for py_name in mapping.values():
            reference = getattr(expected, py_name)
            observed = getattr(measured.result, py_name)
            if observed.state != reference.state:
                raise AssertionError(f"{py_name} kart durumu referansla eşleşmiyor.")
            if reference.state == "valid":
                tolerance = 2.0 if py_name.endswith("frequency") or "edge" in py_name else (
                    4.0 if py_name == "occupied_bandwidth" else 0.02)
                if abs(float(observed.value) - float(reference.value)) > tolerance:
                    raise AssertionError(f"{py_name} kart değeri referans toleransını aşıyor.")
    return {"status": "passed", "compiler": compiler,
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "original_span": document["intent"]["span"],
            "wide_span": [intent.span.lower_shifted_bin, intent.span.upper_shifted_bin],
            "original_fields": document["fields"], "portable_c_result": actual,
            "board_execution": board_record,
            "physical_execution": host is not None, "rf_accuracy_acceptance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int, default=47007)
    args = parser.parse_args()
    result = verify(args.record, host=args.host, port=args.port)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: result[key] for key in ("status", "wide_span", "portable_c_result")}, ensure_ascii=False))
