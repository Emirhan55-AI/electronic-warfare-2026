"""Dört ürün ölçüm karesini PC sınıflandırıcısına bağlayan sınırlı adaptör."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path

import numpy as np
from scipy.signal import firwin, lfilter

from . import classifier_model
from .feature_extractor_v1 import extract_features, normalize_iq


METHOD_ID = "domain.digital-analog-logreg-pc-v1"
PROFILE_ID = "digital-analog-synthetic-logreg-v1"
EXPECTED_SAMPLE_RATE_HZ = 2_000_000.0
FRAME_COUNT = 4
FRAME_SAMPLES = 4096
CONFIDENCE_THRESHOLD = 0.90
FILTER_TAPS = 127
FILTER_BANDWIDTH_HZ = 800_000.0
# Eğitim verisi ±5 kHz artık taşıyıcı içerir. Tam sıfıra karıştırmak özellikle
# AM'in C42 özelliğini eğitim alanının dışına taşır; sabit küçük artık korunur.
CLASSIFIER_RESIDUAL_HZ = 2_500.0
MODEL_PATH = Path(classifier_model.__file__).resolve()
MODEL_SHA256 = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()


@dataclass(frozen=True)
class AutomaticDomainResult:
    state: str
    value: str | None
    reason: str
    probability_digital: float | None
    confidence: float | None
    feature_values: tuple[float, ...]
    estimated_offset_hz: float | None
    filter_bandwidth_hz: float | None
    classifier_residual_hz: float = CLASSIFIER_RESIDUAL_HZ
    method_id: str = METHOD_ID
    profile_id: str = PROFILE_ID
    model_sha256: str = MODEL_SHA256
    physical_acceptance: bool = False
    product_acceptance: bool = False

    def as_record(self) -> dict[str, object]:
        document = asdict(self)
        document["feature_order"] = list(classifier_model.FEATURE_ORDER)
        document["feature_values"] = list(self.feature_values)
        document["confidence_threshold"] = CONFIDENCE_THRESHOLD
        document["input_frame_count"] = FRAME_COUNT
        document["input_samples_per_frame"] = FRAME_SAMPLES
        return document


def _uncertain(reason: str) -> AutomaticDomainResult:
    return AutomaticDomainResult(
        state="uncertain",
        value=None,
        reason=reason,
        probability_digital=None,
        confidence=None,
        feature_values=(),
        estimated_offset_hz=None,
        filter_bandwidth_hz=None,
    )


def _validate_frames(frames: tuple[np.ndarray, ...]) -> np.ndarray:
    if len(frames) != FRAME_COUNT:
        raise ValueError("Analog/Sayısal ayrımı dört ölçüm karesi gerektirir.")
    arrays = tuple(np.asarray(frame, dtype=np.complex128) for frame in frames)
    if any(frame.shape != (FRAME_SAMPLES,) for frame in arrays):
        raise ValueError("Analog/Sayısal ölçüm karesi 4096 kompleks örnek olmalıdır.")
    if not all(np.all(np.isfinite(frame)) for frame in arrays):
        raise ValueError("Analog/Sayısal ölçüm girdisi sonlu değil.")
    return np.stack(arrays)


def _channelize(
    stacked: np.ndarray,
    sample_rate_hz: float,
    lower_shifted_bin: int,
    upper_shifted_bin: int,
) -> tuple[np.ndarray, float, float]:
    window = np.hanning(FRAME_SAMPLES)
    spectra = np.fft.fftshift(np.fft.fft(stacked * window, axis=1), axes=1)
    power = np.mean(np.abs(spectra) ** 2, axis=0)
    region = power[lower_shifted_bin : upper_shifted_bin + 1]
    if region.size < 8 or not np.any(region > 0.0):
        raise ValueError("Seçili analiz aralığında sınıflandırılabilir enerji yok.")

    side = np.concatenate(
        (
            power[max(0, lower_shifted_bin - 32) : lower_shifted_bin],
            power[upper_shifted_bin + 1 : min(FRAME_SAMPLES, upper_shifted_bin + 33)],
        )
    )
    noise = float(np.median(side)) if side.size else 0.0
    weights = np.maximum(region - noise, 0.0)
    if float(np.sum(weights)) <= np.finfo(float).tiny:
        weights = region
    indices = np.arange(lower_shifted_bin, upper_shifted_bin + 1, dtype=np.float64)
    centroid = float(np.sum(indices * weights) / np.sum(weights))
    offset_hz = (centroid - FRAME_SAMPLES / 2.0) * sample_rate_hz / FRAME_SAMPLES

    joined = stacked.reshape(-1)
    time_index = np.arange(joined.size, dtype=np.float64)
    mixer_hz = offset_hz - CLASSIFIER_RESIDUAL_HZ
    shifted = joined * np.exp(-2j * np.pi * mixer_hz * time_index / sample_rate_hz)
    # Eğitim ailesi 500 ksym/s ve 0,5 excess bandwidth değerine kadar uzanır.
    # Klasördeki eski 400 kHz runtime filtresi eğitimde yoktu ve AM özelliklerini
    # bozuyordu; 800 kHz bant bu aileyi kesmeden 2 MS/s kanalını sınırlar.
    filter_bandwidth = FILTER_BANDWIDTH_HZ
    taps = firwin(FILTER_TAPS, filter_bandwidth / 2.0, fs=sample_rate_hz)
    filtered = lfilter(taps, 1.0, shifted)
    settled = filtered[FILTER_TAPS - 1 :]
    return normalize_iq(settled), offset_hz, filter_bandwidth


def classify_parameter_frames(
    frames: tuple[np.ndarray, ...],
    *,
    sample_rate_hz: float,
    lower_shifted_bin: int,
    upper_shifted_bin: int,
    snr_db: float | None,
) -> AutomaticDomainResult:
    """Aynı dört ölçüm karesinden yüksek güvenli PC kararı üret."""
    stacked = _validate_frames(frames)
    if not math.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("Analog/Sayısal ayrımı için örnekleme hızı geçersiz.")
    if sample_rate_hz != EXPECTED_SAMPLE_RATE_HZ:
        return _uncertain("Model yalnız 2 MS/s örnekleme hızı için hazırlanmıştır.")
    if not 56 <= lower_shifted_bin <= upper_shifted_bin <= 4039:
        raise ValueError("Analog/Sayısal analiz aralığı kullanılabilir FFT bandı dışında.")
    width = upper_shifted_bin - lower_shifted_bin + 1
    if not 8 <= width <= 3984:
        raise ValueError("Analog/Sayısal analiz aralığı 8–3984 FFT hücresi olmalıdır.")
    if snr_db is None or not math.isfinite(snr_db) or snr_db < 4.0:
        return _uncertain("Bant içi SNR otomatik ayrım için yetersizdir.")

    try:
        channel, offset_hz, filter_bandwidth = _channelize(
            stacked, sample_rate_hz, lower_shifted_bin, upper_shifted_bin
        )
    except ValueError as exc:
        return _uncertain(str(exc))
    features = extract_features(channel, sample_rate_hz)
    label, probability_digital, vector = classifier_model.classify(features)
    if not math.isfinite(probability_digital) or not all(math.isfinite(value) for value in vector):
        raise ValueError("Analog/Sayısal sınıflandırıcı sonlu sonuç üretmedi.")
    confidence = max(probability_digital, 1.0 - probability_digital)
    if confidence < CONFIDENCE_THRESHOLD:
        return AutomaticDomainResult(
            state="uncertain",
            value=None,
            reason="Model oyları güven eşiğini geçmedi.",
            probability_digital=probability_digital,
            confidence=confidence,
            feature_values=tuple(float(value) for value in vector),
            estimated_offset_hz=offset_hz,
            filter_bandwidth_hz=filter_bandwidth,
        )
    value = "Sayısal" if label == "DIGITAL" else "Analog"
    return AutomaticDomainResult(
        state="valid",
        value=value,
        reason="Yüksek güvenli deneysel PC sınıflandırıcı kararı.",
        probability_digital=probability_digital,
        confidence=confidence,
        feature_values=tuple(float(item) for item in vector),
        estimated_offset_hz=offset_hz,
        filter_bandwidth_hz=filter_bandwidth,
    )
