"""KTR-4.2: uzun gerçek I/Q gözlemi için ürün dışı ölçüm ön işlemesi.

Sınıf etiketi/model almaz. Sayısal güç ve spektral merkez, sınıflandırma
kalitesinden bağımsızdır. Taşıyıcı hipotezini gerçek taşıyıcı diye sunmaz.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.signal import fftconvolve, firwin, resample_poly, welch


@dataclass(frozen=True)
class RFObservation:
    duration_s: float
    analysis_band_hz: tuple[float, float]
    signal_power_dbfs: float | None
    noise_power_dbfs: float | None
    snr_db: float | None
    spectral_center_hz: float | None
    reference_difference_db: float | None
    quality_reason: str | None
    full_emission_obw99_hz: float | None
    bandwidth_reason: str
    carrier_frequency_hz: float | None
    carrier_reason: str
    signal_domain: str
    classification_reason: str
    features: dict[str, float]
    classification_diagnostics: dict | None = None

    def to_dict(self):
        return asdict(self)


def _db(value):
    return float(10 * np.log10(value)) if value > 0 else None


def _frequency_concentration(channel, rate, order):
    """M'inci kuvvet çizgisi: PSK/AM frekans hipotezi, taşıyıcı kabulü değil."""
    # Normalize amplitude before powers to avoid tiny physical ADC magnitudes.
    rms = math.sqrt(float(np.mean(abs(channel) ** 2)))
    z = channel / rms
    powered = z ** order
    window = np.hanning(len(z))
    nfft = 1 << (len(z) - 1).bit_length()
    spectral = abs(np.fft.fft(powered * window, n=nfft)) ** 2
    index = int(np.argmax(spectral))
    frequency = np.fft.fftfreq(nfft, 1 / rate)[index]
    delta = rate / nfft
    time = np.arange(len(z)) / rate

    def objective(f):
        return -float(abs(np.sum(powered * window * np.exp(-2j * np.pi * f * time))))

    fit = minimize_scalar(objective, bounds=(frequency-delta, frequency+delta),
        method='bounded', options={'xatol': .01})
    if not fit.success:
        raise ValueError('Kuvvet çizgisi frekans araması yakınsamadı.')
    offset = float(fit.x / order)
    rotated = z * np.exp(-2j * np.pi * offset * time)
    concentration = float(abs(np.mean(rotated ** order)) / np.mean(abs(rotated) ** order))
    return rotated, offset, concentration


def observe_rf(samples, *, sample_rate_hz, center_frequency_hz,
               lower_frequency_hz, upper_frequency_hz, classification_model=None):
    """İzole analiz aralığının 50–500 ms gözlemi; operatör/olay sahipliği dışarıda.

    Girdi normalize kompleks I/Q'dur; ADC clipping/USB bütünlüğü ham kayıt
    düzeyinde ayrıca doğrulanmalıdır. Bu işlev fiziksel kabul vermez.
    """
    x = np.asarray(samples, dtype=np.complex128)
    scalars = (sample_rate_hz, center_frequency_hz, lower_frequency_hz, upper_frequency_hz)
    if x.ndim != 1 or not np.all(np.isfinite(x)) or not all(math.isfinite(v) for v in scalars):
        raise ValueError('Sonlu tek boyutlu I/Q ve frekans bağlamı gerekli.')
    if not 100_000 <= sample_rate_hz <= 20_000_000:
        raise ValueError('Örnekleme hızı desteklenen aralık dışında.')
    duration = len(x) / sample_rate_hz
    if not .05 <= duration <= .5:
        raise ValueError('50–500 ms kesintisiz gözlem gerekli.')
    width = upper_frequency_hz - lower_frequency_hz
    middle = (lower_frequency_hz + upper_frequency_hz) / 2
    if not 4_000 <= width <= min(250_000, sample_rate_hz / 8):
        raise ValueError('İzole bant genişliği desteklenmiyor.')
    guard = max(10_000., width / 4)
    reference_width = max(20_000., width / 2)
    if lower_frequency_hz-guard-reference_width <= center_frequency_hz-sample_rate_hz/2 or upper_frequency_hz+guard+reference_width >= center_frequency_hz+sample_rate_hz/2:
        raise ValueError('İki taraflı gürültü referansı örnekleme bandı dışında.')
    if lower_frequency_hz <= center_frequency_hz <= upper_frequency_hz:
        raise ValueError('Alıcı DC çizgisini içeren bantta emisyon/DC ayrımı gerekli.')

    # The FFT length is bounded by the actual observation length. Resolution
    # is sample_rate/nperseg; zero padding is not extra resolution.
    nperseg = min(65_536, 1 << int(math.floor(math.log2(len(x) / 4))))
    freq, psd = welch(x, fs=sample_rate_hz, window='hann', nperseg=nperseg,
        noverlap=nperseg//2, detrend='constant', return_onesided=False,
        scaling='density', average='mean')
    freq = np.fft.fftshift(freq) + center_frequency_hz
    psd = np.fft.fftshift(psd)
    df = sample_rate_hz / nperseg
    inside = (freq >= lower_frequency_hz) & (freq <= upper_frequency_hz)
    left = (freq >= lower_frequency_hz-guard-reference_width) & (freq < lower_frequency_hz-guard)
    right = (freq > upper_frequency_hz+guard) & (freq <= upper_frequency_hz+guard+reference_width)
    nl, nr = float(np.mean(psd[left])), float(np.mean(psd[right]))
    noise = (nl+nr)/2
    signed = psd[inside] - noise
    excess = float(signed.sum()) * df
    noise_power = noise * np.count_nonzero(inside) * df
    side_difference = _db(nl / nr) if min(nl, nr) > 0 else None
    snr = _db(excess / noise_power) if noise_power > 0 else None
    quality = None
    if side_difference is None or abs(side_difference) > 6:
        quality = 'reference_mismatch'
    elif snr is None or snr < 6:
        quality = 'low_snr'
    # Signed first moment avoids positive-only noise mass; low quality is
    # explicit and the centroid is withheld if outside the selected interval.
    centroid = float(np.sum(freq[inside] * signed) * df / excess) if excess > 0 else None
    if centroid is not None and not lower_frequency_hz <= centroid <= upper_frequency_hz:
        centroid = None
    features = {}
    domain = 'Belirsiz'
    classification_reason = 'classifier_not_validated_for_rf_features'
    classification_diagnostics = None
    if quality is None:
        # Mix before decimation; anti-alias filtering is performed by the
        # polyphase resampler. Extra channel FIR isolates the requested band.
        time = np.arange(len(x)) / sample_rate_hz
        mixed = (x-x.mean()) * np.exp(-2j*np.pi*(middle-center_frequency_hz)*time)
        down = max(1, int(sample_rate_hz / (4 * width)))
        rate = sample_rate_hz / down
        coarse = resample_poly(mixed, 1, down)
        taps = firwin(257, width / 2, fs=rate, window=('kaiser', 8.6))
        filtered = fftconvolve(coarse, taps, mode='same')
        # More than half the FIR plus resampler edge support is discarded.
        channel = filtered[160:-160]
        if len(channel) < 1024 or np.mean(abs(channel) ** 2) <= 0:
            quality = 'insufficient_channel_samples'
        else:
            rms = math.sqrt(float(np.mean(abs(channel)**2)))
            z = channel/rms
            amplitude = abs(z)
            phase_step = np.angle(z[1:] * z[:-1].conj())
            phase_weight = np.minimum(amplitude[1:], amplitude[:-1])
            usable = phase_weight > .25
            second, offset2, concentration2 = _frequency_concentration(channel, rate, 2)
            _, offset4, concentration4 = _frequency_concentration(channel, rate, 4)
            coherent = float(abs(np.mean(second))**2/np.mean(abs(second)**2))
            features = {
                'channel_rate_hz': float(rate), 'channel_samples': float(len(channel)),
                'channel_duration_s': len(channel)/rate,
                'amplitude_cv': float(np.std(amplitude)/np.mean(amplitude)),
                'amplitude_fourth_moment': float(np.mean(amplitude**4)),
                'low_amplitude_fraction': float(np.mean(amplitude < .25)),
                'phase_step_std_rad': float(np.std(phase_step[usable])) if np.any(usable) else 0.,
                'squared_frequency_hypothesis_hz': middle+offset2,
                'fourth_frequency_hypothesis_hz': middle+offset4,
                'squared_concentration': concentration2, 'fourth_concentration': concentration4,
                'coherent_power_fraction_after_squared_correction': coherent,
                'uncorrected_squared_concentration': float(abs(np.mean(z*z))/np.mean(abs(z)**2)),
            }
            if classification_model is not None:
                from .rf_channel_classifier import classify_channel
                domain, classification_diagnostics = classify_channel(
                    z, second, np.maximum(signed - 3 * noise, 0), classification_model)
                classification_reason = 'development_candidate_requires_independent_rf'
    if classification_model is not None and quality is not None:
        classification_reason = quality
    return RFObservation(duration, (lower_frequency_hz, upper_frequency_hz),
        _db(excess) if side_difference is not None and abs(side_difference) <= 6 else None,
        _db(noise_power), snr, centroid, side_difference, quality,
        None, 'full_emission_containment_unverified', None, 'hypothesis_only',
        domain, classification_reason, features, classification_diagnostics)
