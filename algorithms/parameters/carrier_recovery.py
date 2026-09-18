"""16 özgün karede bastırılmış taşıyıcının koşullu frekans kestirimi.

Bu sonuç doğrudan gözlenen spektral çizgi değildir; modülasyon etiketi de
üretmez. İkinci/dördüncü kuvvet çizgisi ve dört ayrı zaman grubunun tutarlılığı
birlikte aranır. Kapsam dışı yayınlarda sonuç vermekten kaçınır.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


METHOD_ID = "frequency.suppressed-carrier-power-consensus-v1"


@dataclass(frozen=True)
class CarrierRecovery:
    frequency_hz: float | None
    order: int | None
    concentration: float | None
    group_concentrations: tuple[float, ...]
    group_frequency_range_hz: float | None
    reason: str


def _channel(frames: np.ndarray, lower: int, upper: int) -> np.ndarray:
    mask = np.zeros(4096, dtype=float)
    mask[lower:upper + 1] = 1.0
    transition = min(4, (upper - lower + 1) // 4)
    for edge in range(transition):
        taper = math.sin(math.pi * 0.5 * (edge + 1) / transition) ** 2
        mask[lower + edge] = mask[upper - edge] = taper
    spectrum = np.fft.fftshift(np.fft.fft(frames, axis=1), axes=1)
    return np.fft.ifft(np.fft.ifftshift(spectrum * mask, axes=1), axis=1).reshape(-1)


def _estimate(channel: np.ndarray, rate: float, middle: float, order: int):
    powered = channel ** order
    count = len(channel)
    power = abs(np.fft.fft(powered * np.hanning(count))) ** 2
    peak = int(np.argmax(power))
    logs = np.log(np.maximum(power[np.array([(peak - 1) % count, peak,
                                            (peak + 1) % count])], np.finfo(float).tiny))
    denominator = logs[0] - 2 * logs[1] + logs[2]
    delta = float(np.clip(0.5 * (logs[0] - logs[2]) / denominator, -0.5, 0.5)) if abs(denominator) > 1e-15 else 0.0
    signed = peak if peak < count // 2 else peak - count
    powered_frequency = (signed + delta) * rate / count
    branches = [(powered_frequency + alias * rate) / order
                for alias in range(-order, order + 1)
                if -rate / 2 <= (powered_frequency + alias * rate) / order < rate / 2]
    frequency = min(branches, key=lambda candidate: abs(candidate - middle))
    oscillator = np.exp(-2j * math.pi * order * frequency * np.arange(count) / rate)
    denominator = float(np.sum(abs(channel) ** order))
    concentration = float(abs(np.sum(powered * oscillator)) / denominator) if denominator > 0 else 0.0
    return float(frequency), concentration


def recover_carrier(
    samples, *, sample_rate_hz: float, center_frequency_hz: float,
    lower_shifted_bin: int, upper_shifted_bin: int,
    lower_band_edge_hz: float, upper_band_edge_hz: float, snr_db: float,
) -> CarrierRecovery:
    """Yalnız izole, kesintisiz ve kırpılmamış 16 kare bağını çağıran doğrular."""
    frames = np.asarray(samples, dtype=np.complex128)
    scalars = (sample_rate_hz, center_frequency_hz, lower_band_edge_hz,
               upper_band_edge_hz, snr_db)
    if (frames.shape != (16, 4096) or not np.all(np.isfinite(frames))
            or not all(math.isfinite(value) for value in scalars)
            or not 0 < sample_rate_hz <= 20_000_000
            or not 56 <= lower_shifted_bin < upper_shifted_bin <= 4039
            or not lower_band_edge_hz < upper_band_edge_hz):
        raise ValueError("Taşıyıcı kestirimi geçerli 16 kare ve bant bağlamı gerektirir.")
    empty = CarrierRecovery(None, None, None, (), None, "power_line_not_supported")
    if snr_db < 6.0:
        return CarrierRecovery(None, None, None, (), None, "low_snr")
    spacing = sample_rate_hz / 4096
    middle = 0.5 * (lower_band_edge_hz + upper_band_edge_hz) - center_frequency_hz
    width = upper_band_edge_hz - lower_band_edge_hz
    if width >= sample_rate_hz / 2:
        return CarrierRecovery(None, None, None, (), None, "alias_ambiguity")
    # Reject ambiguous alias branches rather than assuming a known TX setting.
    if width >= sample_rate_hz / 4:
        # The 2nd-order path can still be unique; the 4th-order path cannot.
        orders = (2,)
    else:
        orders = (2, 4)
    channel = _channel(frames, lower_shifted_bin, upper_shifted_bin)
    candidates = []
    for order in orders:
        frequency, concentration = _estimate(channel, sample_rate_hz, middle, order)
        gate = 0.35 if order == 2 else 0.25
        group_gate = 0.25 if order == 2 else 0.15
        if (concentration < gate
                or abs(frequency - middle) > max(2 * spacing, 0.075 * width)):
            continue
        groups = [_estimate(group, sample_rate_hz, middle, order)
                  for group in channel.reshape(4, -1)]
        group_range = max(value[0] for value in groups) - min(value[0] for value in groups)
        if (min(value[1] for value in groups) < group_gate
                or group_range > 0.25 * spacing
                or max(abs(value[0] - frequency) for value in groups) > 0.25 * spacing):
            continue
        candidates.append(CarrierRecovery(
            center_frequency_hz + frequency, order, concentration,
            tuple(value[1] for value in groups), group_range,
            "recovered_from_modulation",
        ))
    if not candidates:
        return empty
    if len(candidates) == 2 and abs(candidates[0].frequency_hz - candidates[1].frequency_hz) > 0.25 * spacing:
        return CarrierRecovery(None, None, None, (), None, "power_orders_disagree")
    return candidates[0]
