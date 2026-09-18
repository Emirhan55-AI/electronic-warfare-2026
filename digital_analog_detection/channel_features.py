"""Seçili kanalla sınırlı ortak eğitim/çalışma önişlemesi."""
from dataclasses import dataclass
import math

import numpy as np
from scipy.signal import firwin, lfilter

from .feature_extractor_v1 import extract_features, normalize_iq

SAMPLE_RATE_HZ = 2_000_000.0
SAMPLES = 16384
RESIDUAL_HZ = 2500.0
PREPROCESSING_ID = "selected-channel-fir-v2"


@dataclass(frozen=True)
class ChannelFeatures:
    features: dict[str, float]
    offset_hz: float
    bandwidth_hz: float
    filter_taps: int


def selected_channel_features(frames, lower: int, upper: int) -> ChannelFeatures:
    values = np.asarray(frames, dtype=np.complex128)
    if values.shape != (4, 4096) or not np.all(np.isfinite(values)):
        raise ValueError("Sınıflandırma dört sonlu 4096 örneklik kare gerektirir.")
    if type(lower) is not int or type(upper) is not int or not 56 <= lower <= upper <= 4039 or upper - lower + 1 < 8:
        raise ValueError("Sınıflandırma analiz aralığı geçersiz.")
    spectrum = np.fft.fftshift(np.fft.fft(values * np.hanning(4096), axis=1), axes=1)
    psd = np.mean(np.abs(spectrum) ** 2, axis=0)
    region = psd[lower:upper + 1]
    side = np.r_[psd[lower - 36:lower - 4], psd[upper + 5:upper + 37]]
    noise = float(np.median(side))
    weights = np.maximum(region - noise, 0.)
    if weights.sum() <= np.finfo(float).tiny:
        raise ValueError("Seçili kanalda sınıflandırılabilir enerji yok.")
    spacing = SAMPLE_RATE_HZ / 4096
    centroid = float(np.dot(np.arange(lower, upper + 1), weights) / weights.sum())
    offset = (centroid - 2048) * spacing
    # Asimetrik aralıkta her iki kenarı koru. Bant genişliği OBW ölçümü değildir.
    mixer_hz = offset - RESIDUAL_HZ
    edge_offsets = ((lower - .5 - 2048) * spacing - mixer_hz,
                    (upper + .5 - 2048) * spacing - mixer_hz)
    half_band = max(abs(value) for value in edge_offsets)
    transition = max(4000., min(20000., half_band * .15))
    cutoff = half_band + transition / 2
    if cutoff + transition / 2 >= SAMPLE_RATE_HZ / 2:
        raise ValueError("Seçili kanal sınıflandırma filtresinin kullanılabilir sınırını aşıyor.")
    # Hamming FIR yaklaşık geçiş genişliği; çalışma/bellek sonlu tutulur.
    taps_count = min(2049, max(127, int(math.ceil(3.3 * SAMPLE_RATE_HZ / transition)) | 1))
    taps = firwin(taps_count, cutoff, fs=SAMPLE_RATE_HZ)
    n = np.arange(SAMPLES)
    shifted = values.reshape(-1) * np.exp(-2j * np.pi * mixer_hz * n / SAMPLE_RATE_HZ)
    filtered = lfilter(taps, 1., shifted)[taps_count - 1:]
    features = extract_features(normalize_iq(filtered), SAMPLE_RATE_HZ)
    if not all(math.isfinite(v) for v in features.values()):
        raise ValueError("Sınıflandırma özellikleri sonlu değil.")
    return ChannelFeatures(features, offset, 2 * half_band, taps_count)
