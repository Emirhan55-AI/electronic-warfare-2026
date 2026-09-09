"""Bounded, reproducible records of the input and output of one F5 measurement."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
from uuid import uuid4
import zipfile

import numpy as np

from algorithms.parameters import (
    AnalysisSpan, F1ParameterResult, F5ParameterEstimator,
    MeasurementCandidate, MeasurementContext, MeasurementIntent,
)
from algorithms.pipeline import PHASE04F5_PROFILE_PATH, load_phase04f5_capability
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor


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
    "app/operator_console/quick_scan_actions.py",
    "app/operator_console/quick_detection_state.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/live_ed.py",
    "algorithms/spectrum/dsp.py",
    "algorithms/spectrum/source.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/native_channelizer.py",
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
        "methods": dict(F5ParameterEstimator.METHOD_IDS),
    }


@dataclass(frozen=True)
class RecordedMeasurement:
    result: F1ParameterResult
    path: Path
    sha256: str
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


def measure_and_record(
    intent: MeasurementIntent, samples: tuple[np.ndarray, ...], *,
    sample_rate_hz: float, center_frequency_hz: float,
    spectrum_config: SpectrumConfig, source: dict, requested_utc: str,
    directory: Path,
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
    processor = SpectrumProcessor(spectrum_config)
    spectra = tuple(processor.process(frame, sample_rate_hz=sample_rate_hz,
                                      center_frequency_hz=center_frequency_hz) for frame in frames)
    result = F5ParameterEstimator().measure(intent, frames, spectra)
    if runtime_binding() != binding:
        raise ValueError("Ölçüm sırasında yöntem veya kaynak değişti; sonuç kaydedilmedi.")
    capability = load_phase04f5_capability()
    if capability is None or result.persistent_payload_bytes > capability.maximum_persistent_payload_bytes:
        raise ValueError("Ölçüm profili veya kalıcı bellek sınırı geçersiz.")
    fields = result_fields(result)
    record_id = uuid4().hex
    document = {
        "schema": SCHEMA, "record_id": record_id,
        "requirements": ["KTR-4.2", "KTR-4.2-F1"],
        "requested_utc": requested_utc, "completed_utc": utc_now(),
        "acquisition_utc": None, "time_reference": "host_request_and_completion_only",
        "processing_location": "host", "spectrum_origin": "host_recomputed_from_recorded_iq",
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
        "calibration": {"status": "unavailable", "profile_id": None, "profile_sha256": None,
                        "power_reference": "digital_full_scale", "dbm_available": False,
                        "frequency_calibration_available": False},
        "accuracy_proven": False,
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
    return RecordedMeasurement(result, path, digest(path.read_bytes()),
                               document["completed_utc"], document["observation_duration_s"])


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
        or document["processing_location"] != "host"
        or document["iq"]["encoding"] != "complex_float64_little_endian"
        or document["iq"]["bytes"] != IQ_BYTES
    ):
        raise ValueError("Ölçüm birim veya süre bağlamı geçersiz.")
    if document["runtime"] != runtime_binding():
        raise ValueError("Kayıt farklı kaynak veya çalışma zamanı sürümüne ait.")
    if document["calibration"]["dbm_available"] or document["accuracy_proven"]:
        raise ValueError("Kayıt doğrulanmamış kalibrasyon veya doğruluk iddiası içeriyor.")
    values = dict(document["intent"])
    values["span"] = AnalysisSpan(**values["span"])
    if values["context"] is not None:
        context = dict(values["context"])
        context["candidates"] = tuple(MeasurementCandidate(**item) for item in context["candidates"])
        context["owner_observed_frames"] = tuple(context["owner_observed_frames"])
        values["context"] = MeasurementContext(**context)
    intent = MeasurementIntent(**values)
    processor = SpectrumProcessor(SpectrumConfig(**document["spectrum_config"]))
    spectra = tuple(processor.process(
        frame, sample_rate_hz=document["sample_rate_hz"],
        center_frequency_hz=document["center_frequency_hz"],
    ) for frame in frames)
    result = F5ParameterEstimator().measure(intent, frames, spectra)
    if json_bytes(result_fields(result)) != json_bytes(document["fields"]) or json_bytes(asdict(result.quality)) != json_bytes(document["quality"]):
        raise ValueError("Kaydedilen alanlar veya kalite bilgisi aynı girdiden yeniden üretilemedi.")
    return result
