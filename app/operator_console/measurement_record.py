"""Bounded, reproducible records of the input and output of one F5 measurement."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
from uuid import uuid4
import zipfile

import numpy as np

from algorithms.parameters import (
    AnalysisSpan, F1ParameterResult, F5ParameterEstimator,
    FieldMeasurement, MeasurementCandidate, MeasurementContext, MeasurementIntent,
)
from algorithms.pipeline import PHASE04F5_PROFILE_PATH, load_phase04f5_capability
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from algorithms.p0.parameter_client import decode_response as decode_board_response, measure_on_board
from algorithms.p0.parameter_client import BoardAnalysisSpan, BOARD_PERSISTENT_PAYLOAD_BYTES
from digital_analog_detection import METHOD_ID as AUTOMATIC_DOMAIN_METHOD_ID
from digital_analog_detection import classify_parameter_frames


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "parameter-measurement-v1"
IQ_BYTES = 4 * 4096 * 16
MAX_DOCUMENT_BYTES = 131_072
FIELD_SPECS = {
    "emission_center_frequency": ("emission_center_frequency", "Hz"),
    "carrier_line_frequency": ("carrier_line_frequency", "Hz"),
    "lower_band_edge": ("occupied_bandwidth", "Hz"),
    "upper_band_edge": ("occupied_bandwidth", "Hz"),
    "occupied_bandwidth": ("occupied_bandwidth", "Hz"),
    "channel_power_dbfs": ("uncalibrated_channel_power_dbfs", "dBFS"),
    "snr_estimate_db": ("snr_estimate_db", "dB"),
    "signal_domain": ("signal_domain", None),
}
PROVENANCE_SOURCES = (
    "app/operator_console/measurement_record.py",
    "app/operator_console/quick_measurement_actions.py",
    "app/operator_console/quick_direction_actions.py",
    "app/operator_console/quick_scan_actions.py",
    "app/operator_console/quick_detection_state.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/live_ed.py",
    "algorithms/spectrum/dsp.py",
    "algorithms/spectrum/source.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/native_channelizer.py",
    "algorithms/p0/parameter_client.py",
    "platforms/embedded/p0/include/p0_parameter_runtime.h",
    "platforms/embedded/p0/include/p0_ed_service_protocol.h",
    "platforms/embedded/p0/src/p0_parameter_runtime.c",
    "platforms/embedded/p0/src/p0_ed_service_protocol.c",
    "platforms/embedded/p0/src/p0_ed_service.c",
    "platforms/embedded/p0/src/p0_ed_network_bridge.c",
    "digital_analog_detection/classifier_model.py",
    "digital_analog_detection/feature_extractor_v1.py",
    "digital_analog_detection/integration.py",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_binding() -> dict:
    if load_phase04f5_capability() is None:
        raise ValueError("Ölçüm profili bütünlük denetiminden geçmedi.")
    profile_bytes = PHASE04F5_PROFILE_PATH.read_bytes()
    profile = json.loads(profile_bytes)
    paths = set(PROVENANCE_SOURCES)
    paths.update(item["path"] for item in profile["runtime_implementation"]["sources"])
    paths.update(item["package_path"] for item in profile["runtime_implementation"]["runtime_models"])
    return {
        "profile_id": profile["profile_id"],
        "profile_sha256": digest(profile_bytes),
        "sources_sha256": {name: digest((ROOT / name).read_bytes()) for name in sorted(paths)},
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "platform": platform.system() + "-" + platform.machine(),
        "methods": {
            **F5ParameterEstimator.METHOD_IDS,
            "automatic_signal_domain": AUTOMATIC_DOMAIN_METHOD_ID,
        },
    }


@dataclass(frozen=True)
class RecordedMeasurement:
    result: F1ParameterResult
    path: Path
    sha256: str
    persistent_payload_limit: int
    completed_utc: str = ""
    observation_duration_s: float = 0.0


def result_fields(result: F1ParameterResult) -> dict:
    fields = {}
    for name, (method, unit) in FIELD_SPECS.items():
        field = getattr(result, name)
        if field.state not in {"valid", "uncertain", "insufficient_quality", "not_observed", "not_applicable"}:
            raise ValueError("Ölçüm alanı durumu geçersiz.")
        if field.state == "valid":
            if name == "signal_domain":
                if field.value not in {"Analog", "Sayısal"}:
                    raise ValueError("Sinyal türü geçersiz.")
            elif not isinstance(field.value, (float, int)) or not math.isfinite(field.value):
                raise ValueError("Ölçüm alanında sonlu sayı yok.")
        fields[name] = {
            "state": field.state, "value": field.value if field.state == "valid" else None,
            "unit": unit, "reason": field.reason,
            "method_id": F5ParameterEstimator.METHOD_IDS[method],
        }
    return fields


def _automatic_signal_domain(
    result: F1ParameterResult,
    frames: tuple[np.ndarray, ...],
    intent: MeasurementIntent,
    sample_rate_hz: float,
):
    snr = (
        float(result.snr_estimate_db.value)
        if result.snr_estimate_db.state == "valid"
        and isinstance(result.snr_estimate_db.value, (float, int))
        else None
    )
    classification = classify_parameter_frames(
        frames,
        sample_rate_hz=sample_rate_hz,
        lower_shifted_bin=intent.span.lower_shifted_bin,
        upper_shifted_bin=intent.span.upper_shifted_bin,
        snr_db=snr,
    )
    if snr is None:
        classification = replace(classification, reason="SNR ölçümü geçersiz olduğu için sinyal türü hesaplanamadı.")
    field = FieldMeasurement(
        classification.state,
        classification.value,
        reason=classification.reason,
    )
    return replace(result, signal_domain=field), classification


def validate_measurement_ownership(intent: MeasurementIntent, source: dict) -> None:
    from algorithms.parameters.f1_estimator import _context_reason
    direction_capture = source.get("direction_capture")
    channel_capture = source.get("channel_capture")
    if direction_capture is not None and channel_capture is not None:
        raise ValueError("Ölçüm kaynağında birden fazla kanal sahipliği bağı var.")
    capture = direction_capture if direction_capture is not None else channel_capture
    if capture is None:
        if _context_reason(intent) is not None:
            raise ValueError("Seçilen tespitin ölçüm sahipliği veya analiz aralığı geçersiz.")
        owner = next(item for item in intent.context.candidates if item.event_id == intent.event_id)
        if (owner.lower_shifted_bin < intent.span.lower_shifted_bin
                or owner.upper_shifted_bin > intent.span.upper_shifted_bin):
            raise ValueError("Analiz aralığı seçili adayın tamamını kapsamıyor; aralığı genişletin.")
        for candidate in intent.context.candidates:
            if (candidate.event_id != intent.event_id and candidate.confirmed
                    and candidate.lower_shifted_bin <= intent.span.upper_shifted_bin + 36
                    and candidate.upper_shifted_bin >= intent.span.lower_shifted_bin - 36):
                raise ValueError("Gürültü referansında komşu sinyal var; izole bir analiz aralığı seçin.")
        return
    # P0PM's event_id labels the final observation; it does not claim that
    # this ID was present in earlier channel-bound frames. Both parameter and
    # direction capture keep the same isolated-channel ownership contract.
    context = intent.context
    events = source.get("owner_observations", [])
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    sequences = list(range(intent.start_frame, intent.start_frame + 4))
    valid = (
        context is not None and capture.get("binding") == "operator_selected_channel_v1"
        and capture.get("span") == [lower, upper]
        and capture.get("emitter_identity_verified") is False
        and capture.get("fresh_after_operator_request") is True
        and source.get("sequence_numbers") == sequences
        and sequences[0] > capture.get("host_capture_sequence_floor", sequences[0])
        and len(events) == 4
        and capture.get("event_ids") == [event["event_id"] for event in events]
        and events[-1]["event_id"] == intent.event_id
        and events[-1]["seen_count"] == intent.event_revision
        and all(event["state"] == "confirmed" and event["observed_this_frame"]
                and lower <= event["start_shifted_bin"] <= event["peak_shifted_bin"]
                <= event["end_shifted_bin"] <= upper for event in events)
        and context.owner_observed_frames == tuple(event["event_id"] == intent.event_id for event in events)
    )
    if not valid:
        raise ValueError("Ölçümün kanal veya yeni kare bağı geçersiz.")
    # Check generation, final owner and final-frame neighbours using the same
    # contract. Only the explicit channel observation booleans differ.
    from dataclasses import replace
    final_context = replace(context, owner_observed_frames=(True, True, True, True))
    if _context_reason(replace(intent, context=final_context)) is not None:
        raise ValueError("Ölçümün son gözlem bağlamı geçersiz.")


def measure_and_record(
    intent: MeasurementIntent, samples: tuple[np.ndarray, ...], *,
    sample_rate_hz: float, center_frequency_hz: float,
    spectrum_config: SpectrumConfig, source: dict, requested_utc: str,
    directory: Path,
    board_endpoint: tuple[str, int] | None = None,
) -> RecordedMeasurement:
    """Run in the measurement worker; no full recording is read or hashed."""
    if len(samples) != 4 or any(np.shape(frame) != (4096,) for frame in samples):
        raise ValueError("Ölçüm kaydı dört adet 4096 örnekli kare gerektirir.")
    if not all(np.all(np.isfinite(frame)) for frame in samples):
        raise ValueError("Ölçüm girdisinde sonlu olmayan örnek var.")
    if not math.isfinite(sample_rate_hz) or sample_rate_hz <= 0 or not math.isfinite(center_frequency_hz):
        raise ValueError("Ölçüm frekans bağlamı geçersiz.")
    # Explicit little-endian normalized estimator input, not an RF-voltage claim.
    iq = b"".join(np.asarray(frame, dtype="<c16").tobytes() for frame in samples)
    frames = tuple(np.frombuffer(iq, dtype="<c16").reshape(4, 4096))
    binding = runtime_binding()
    source = json.loads(json_bytes(source))
    board = None
    if board_endpoint is not None:
        validate_measurement_ownership(intent, source)
        if not float(sample_rate_hz).is_integer() or not float(center_frequency_hz).is_integer():
            raise ValueError("Kart ölçümünün frekans bağlamı tam Hz olmalıdır.")
        interleaved = np.stack((np.stack(frames).real, np.stack(frames).imag), axis=-1) * 128.0
        if np.any(interleaved != np.rint(interleaved)) or np.any(interleaved < -128) or np.any(interleaved > 127):
            raise ValueError("Kart ölçümü özgün CI8 örneklerini gerektirir.")
        raw_ci8 = interleaved.astype(np.int8).tobytes()
        expected_hashes = source.get("transport_iq_sha256")
        if expected_hashes is not None and expected_hashes != [digest(raw_ci8[i*8192:(i+1)*8192]) for i in range(4)]:
            raise ValueError("Ölçüm girdisi kartta gözlenen karelerle eşleşmiyor.")
        board = measure_on_board(*board_endpoint, intent, raw_ci8,
            sample_rate_hz=int(sample_rate_hz), center_frequency_hz=int(center_frequency_hz))
        result = board.result
    else:
        if intent.span.width_bins > 512:
            raise ValueError("Geniş analiz aralığı PL/ARM kart ölçümü gerektirir; PC sayısal geri dönüşü yoktur.")
        processor = SpectrumProcessor(spectrum_config)
        spectra = tuple(processor.process(frame, sample_rate_hz=sample_rate_hz,
                                          center_frequency_hz=center_frequency_hz) for frame in frames)
        result = F5ParameterEstimator().measure(intent, frames, spectra)
    result, automatic_domain = _automatic_signal_domain(
        result, frames, intent, sample_rate_hz
    )
    if runtime_binding() != binding:
        raise ValueError("Ölçüm sırasında yöntem veya kaynak değişti; sonuç kaydedilmedi.")
    capability = load_phase04f5_capability()
    memory_limit = BOARD_PERSISTENT_PAYLOAD_BYTES if board else (capability.maximum_persistent_payload_bytes if capability else 0)
    if capability is None or result.persistent_payload_bytes > memory_limit:
        raise ValueError("Ölçüm profili veya kalıcı bellek sınırı geçersiz.")
    fields = result_fields(result)
    fields["signal_domain"]["method_id"] = AUTOMATIC_DOMAIN_METHOD_ID
    record_id = uuid4().hex
    document = {
        "schema": SCHEMA, "record_id": record_id,
        "requirements": (["KTR-4.4", "KTR-4.2", "KTR-4.2-F1"]
                         if "direction_capture" in source else ["KTR-4.2", "KTR-4.2-F1"]),
        "requested_utc": requested_utc, "completed_utc": utc_now(),
        "acquisition_utc": None, "time_reference": "host_request_and_completion_only",
        "processing_location": "hybrid_zedboard_arm_host" if board else "host",
        "spectrum_origin": "physical_pl_replay_of_recorded_ci8" if board else "host_recomputed_from_recorded_iq",
        "source": source, "intent": asdict(intent), "runtime": binding,
        "sample_rate_hz": sample_rate_hz, "center_frequency_hz": center_frequency_hz,
        "spectrum_config": asdict(spectrum_config),
        "observation_duration_s": 4 * 4096 / sample_rate_hz,
        "bin_spacing_hz": sample_rate_hz / 4096,
        "iq": {"entry": "iq.cf64_le", "encoding": "complex_float64_little_endian",
               "reference": "normalized_estimator_input", "frames": 4, "samples_per_frame": 4096,
               "bytes": len(iq), "sha256": digest(iq),
               "frame_sha256": [digest(iq[i * 65536:(i + 1) * 65536]) for i in range(4)]},
        "fields": fields, "quality": asdict(result.quality),
        "automatic_signal_domain": automatic_domain.as_record(),
        "calibration": {"status": "unavailable", "profile_id": None, "profile_sha256": None,
                        "power_reference": "digital_full_scale", "dbm_available": False,
                        "frequency_calibration_available": False},
        "accuracy_proven": False,
    }
    if board:
        document["board_measurement"] = {
            "protocol": f"P0PM-v{struct.unpack_from('<H', board.response, 4)[0]}", "response_hex": board.response.hex(),
            "persistent_payload_bytes": result.persistent_payload_bytes,
            "span_contract": "board-full-span-v2" if struct.unpack_from('<H', board.response, 4)[0] == 2 else "legacy-512-v1",
            "elapsed_us": board.elapsed_us, "profile_generation": board.profile_generation,
            "fft_size": 4096, "classification_performed": False,
            "live_detection_revalidated": False,
            "input_ci8_sha256": digest(raw_ci8),
            "execution": "reprocess_operator_selected_record_on_pl_and_arm",
            "executed_methods": [
                name for name in F5ParameterEstimator.METHOD_IDS if name != "signal_domain"
            ],
            "service_binary_sha256": None,
            "service_identity_reason": "running_service_hash_not_exposed_by_protocol",
        }
    payload = json_bytes(document)
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Ölçüm kaydı boyut sınırını aştı.")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record_id}.zip"
    # Exclusive creation protects previous records, including a UUID collision.
    with path.open("xb") as stream:
        try:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("measurement.json", payload)
                archive.writestr("iq.cf64_le", iq)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            path.unlink(missing_ok=True)
            raise
    return RecordedMeasurement(
        result,
        path,
        digest(path.read_bytes()),
        memory_limit,
        document["completed_utc"],
        document["observation_duration_s"],
    )


def read_measurement(path: Path) -> tuple[dict, tuple[np.ndarray, ...]]:
    """Check bounded archive members and input hashes without extracting files."""
    if path.stat().st_size > IQ_BYTES + MAX_DOCUMENT_BYTES + 4096:
        raise ValueError("Ölçüm arşivi boyut sınırını aştı.")
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ["measurement.json", "iq.cf64_le"]:
            raise ValueError("Ölçüm arşivi girdileri geçersiz.")
        if archive.getinfo("measurement.json").file_size > MAX_DOCUMENT_BYTES or archive.getinfo("iq.cf64_le").file_size != IQ_BYTES:
            raise ValueError("Ölçüm arşivi açılmış boyutları geçersiz.")
        document = json.loads(archive.read("measurement.json"))
        iq = archive.read("iq.cf64_le")
    if document["schema"] != SCHEMA or document["iq"]["sha256"] != digest(iq):
        raise ValueError("Ölçüm girdisi bütünlük denetiminden geçmedi.")
    if document["iq"]["frame_sha256"] != [digest(iq[i * 65536:(i + 1) * 65536]) for i in range(4)]:
        raise ValueError("Ölçüm kare özetleri uyuşmuyor.")
    frames = tuple(np.frombuffer(iq, dtype="<c16").reshape(4, 4096))
    if not all(np.all(np.isfinite(frame)) for frame in frames):
        raise ValueError("Ölçüm girdisi sonlu değil.")
    return document, frames


def replay_measurement(path: Path, *, expected_sha256: str | None = None) -> F1ParameterResult:
    """Require the same runtime and reproduce field values/states exactly."""
    document, frames = read_measurement(path)
    if expected_sha256 is not None and digest(path.read_bytes()) != expected_sha256:
        raise ValueError("Ölçüm arşivinin dış özeti uyuşmuyor.")
    sample_rate = document["sample_rate_hz"]
    if not math.isfinite(sample_rate) or sample_rate <= 0 or (
        document["observation_duration_s"] != 4 * 4096 / sample_rate
        or document["bin_spacing_hz"] != sample_rate / 4096
        or document["processing_location"] not in {
            "host", "zedboard_arm", "hybrid_zedboard_arm_host"
        }
        or document["iq"]["encoding"] != "complex_float64_little_endian"
        or document["iq"]["bytes"] != IQ_BYTES
    ):
        raise ValueError("Ölçüm birim veya süre bağlamı geçersiz.")
    if document["runtime"] != runtime_binding():
        raise ValueError("Kayıt farklı kaynak veya çalışma zamanı sürümüne ait.")
    if document["calibration"]["dbm_available"] or document["accuracy_proven"]:
        raise ValueError("Kayıt doğrulanmamış kalibrasyon veya doğruluk iddiası içeriyor.")
    values = dict(document["intent"])
    span_type = BoardAnalysisSpan if document["processing_location"] != "host" else AnalysisSpan
    values["span"] = span_type(**values["span"])
    if values["context"] is not None:
        context = dict(values["context"])
        context["candidates"] = tuple(MeasurementCandidate(**item) for item in context["candidates"])
        context["owner_observed_frames"] = tuple(context["owner_observed_frames"])
        values["context"] = MeasurementContext(**context)
    intent = MeasurementIntent(**values)
    if "direction_capture" in document["source"]:
        validate_measurement_ownership(intent, document["source"])
    if document["processing_location"] in {"zedboard_arm", "hybrid_zedboard_arm_host"}:
        board = document.get("board_measurement")
        if not isinstance(board, dict) or board.get("protocol") not in {"P0PM-v1", "P0PM-v2"}:
            raise ValueError("Kart ölçüm kaydı eksik veya geçersiz.")
        interleaved = np.stack((np.stack(frames).real, np.stack(frames).imag), axis=-1) * 128.0
        if np.any(interleaved != np.rint(interleaved)) or np.any(interleaved < -128) or np.any(interleaved > 127):
            raise ValueError("Kart ölçüm kaydındaki CI8 örnekleri geri üretilemiyor.")
        raw_ci8 = interleaved.astype(np.int8).tobytes()
        try:
            response = bytes.fromhex(board["response_hex"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Kart ölçüm yanıtı geçersiz.") from exc
        token = struct.unpack_from("<I", response, 8)[0] if len(response) >= 12 else 0
        measured = decode_board_response(response, intent, raw_ci8, token)
        if board["protocol"] != f"P0PM-v{struct.unpack_from('<H', response, 4)[0]}":
            raise ValueError("Kart protokol sürümü kaydedilen yanıtla eşleşmiyor.")
        if (board.get("input_ci8_sha256") != digest(raw_ci8)
                or board.get("elapsed_us") != measured.elapsed_us
                or board.get("profile_generation") != measured.profile_generation
                or board.get("classification_performed") is not False):
            raise ValueError("Kart ölçüm üstverisi yanıtla eşleşmiyor.")
        result = measured.result
        if document["processing_location"] == "hybrid_zedboard_arm_host":
            result, automatic_domain = _automatic_signal_domain(
                result, frames, intent, sample_rate
            )
            if json_bytes(automatic_domain.as_record()) != json_bytes(
                document.get("automatic_signal_domain")
            ):
                raise ValueError("Otomatik Analog/Sayısal sonucu aynı girdiden üretilemedi.")
        fields = result_fields(result)
        fields["signal_domain"]["method_id"] = (
            AUTOMATIC_DOMAIN_METHOD_ID
            if document["processing_location"] == "hybrid_zedboard_arm_host"
            else None
        )
        if (json_bytes(fields) != json_bytes(document["fields"])
                or json_bytes(asdict(result.quality)) != json_bytes(document["quality"])):
            raise ValueError("Kart ölçüm yanıtı kaydedilen alanlarla eşleşmiyor.")
        return result
    processor = SpectrumProcessor(SpectrumConfig(**document["spectrum_config"]))
    spectra = tuple(processor.process(
        frame, sample_rate_hz=document["sample_rate_hz"],
        center_frequency_hz=document["center_frequency_hz"],
    ) for frame in frames)
    result = F5ParameterEstimator().measure(intent, frames, spectra)
    if "automatic_signal_domain" in document:
        result, automatic_domain = _automatic_signal_domain(
            result, frames, intent, sample_rate
        )
        if json_bytes(automatic_domain.as_record()) != json_bytes(
            document["automatic_signal_domain"]
        ):
            raise ValueError("Otomatik Analog/Sayısal sonucu aynı girdiden üretilemedi.")
    fields = result_fields(result)
    if "automatic_signal_domain" in document:
        fields["signal_domain"]["method_id"] = AUTOMATIC_DOMAIN_METHOD_ID
    if json_bytes(fields) != json_bytes(document["fields"]) or json_bytes(asdict(result.quality)) != json_bytes(document["quality"]):
        raise ValueError("Kaydedilen alanlar veya kalite bilgisi aynı girdiden yeniden üretilemedi.")
    return result
