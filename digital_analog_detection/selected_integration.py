"""Seçili kanalı ortak eğitim önişlemesiyle sınıflandıran v2 ürün adaptörü."""
from dataclasses import replace
import hashlib
import math
from pathlib import Path

import numpy as np
from scipy.special import expit

from .channel_features import selected_channel_features, PREPROCESSING_ID
from .integration import AutomaticDomainResult, _validate_frames
from .selected_channel_model import MODEL

METHOD_ID = "domain.selected-channel-logreg-pc-v2"
MODEL_SHA256 = hashlib.sha256(Path(__file__).with_name("selected_channel_model.py").read_bytes()).hexdigest()


def classify_parameter_frames(frames, *, sample_rate_hz, lower_shifted_bin,
                              upper_shifted_bin, snr_db):
    stacked = _validate_frames(frames)
    result = AutomaticDomainResult("uncertain", None, "", None, None, (), None, None,
        method_id=METHOD_ID, profile_id=MODEL["profile_id"], model_sha256=MODEL_SHA256)
    if not math.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("Analog/Sayısal ayrımı için örnekleme hızı geçersiz.")
    if sample_rate_hz != 2_000_000.:
        return replace(result, reason="Model yalnız 2 MS/s örnekleme hızı için hazırlanmıştır.")
    if snr_db is None or not math.isfinite(snr_db) or snr_db < 4.:
        return replace(result, reason="Bant içi SNR otomatik ayrım için yetersizdir.")
    if MODEL["preprocessing_id"] != PREPROCESSING_ID:
        raise ValueError("Sınıflandırıcı ve kanal filtresi profili eşleşmiyor.")
    try:
        channel = selected_channel_features(stacked, lower_shifted_bin, upper_shifted_bin)
    except ValueError as exc:
        return replace(result, reason=str(exc))
    vector = np.asarray([channel.features[key] for key in MODEL["feature_order"]])
    scaled = (vector - MODEL["scaler_mean"]) / MODEL["scaler_scale"]
    p = float(expit(np.dot(MODEL["coefficients"], scaled) + MODEL["intercept"]))
    confidence = max(p, 1 - p)
    result = replace(result, probability_digital=p, confidence=confidence,
        feature_values=tuple(float(x) for x in vector), estimated_offset_hz=channel.offset_hz,
        filter_bandwidth_hz=channel.bandwidth_hz)
    if np.any(scaled < MODEL["feature_lower"]) or np.any(scaled > MODEL["feature_upper"]):
        return replace(result, reason="Sinyalin özellikleri modelin eğitim kapsamının dışında; tür belirlenemedi.")
    if confidence < MODEL["confidence_threshold"]:
        return replace(result, reason="Model skoru karar eşiğini geçmedi; tür belirlenemedi.")
    return replace(result, state="valid", value="Sayısal" if p >= .5 else "Analog",
        reason="Deneysel model tahmini; gerçek RF sinyal türü bağımsız olarak doğrulanmadı.")
