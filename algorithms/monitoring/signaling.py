"""Conservative decoders for unencrypted analog audio signalling."""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


DTMF_LOW_HZ = (697.0, 770.0, 852.0, 941.0)
DTMF_HIGH_HZ = (1209.0, 1336.0, 1477.0, 1633.0)
DTMF_KEYS = (
    ("1", "2", "3", "A"),
    ("4", "5", "6", "B"),
    ("7", "8", "9", "C"),
    ("*", "0", "#", "D"),
)


def _tone_amplitude(values: npt.NDArray[np.float64], frequency_hz: float, sample_rate_hz: int) -> float:
    index = np.arange(values.size, dtype=np.float64)
    reference = np.exp(-2j * np.pi * frequency_hz * index / sample_rate_hz)
    return float(2.0 * abs(np.vdot(reference, values)) / values.size)


def decode_dtmf(audio: npt.ArrayLike, sample_rate_hz: int = 48_000) -> tuple[str, ...]:
    """Decode sustained DTMF symbols with dominance, twist and duration gates.

    This intentionally covers only standard, unencrypted dual-tone signalling;
    it is not a speech codec, scrambler decoder or generic analog-data decoder.
    """
    values = np.asarray(audio, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)) or sample_rate_hz < 8_000:
        return ()
    window_size = max(320, int(round(0.040 * sample_rate_hz)))
    hop = max(160, int(round(0.020 * sample_rate_hz)))
    if values.size < window_size:
        return ()
    window = np.hanning(window_size)
    stable_key: str | None = None
    stable_windows = 0
    released_windows = 2
    decoded: list[str] = []

    for start in range(0, values.size - window_size + 1, hop):
        segment = values[start:start + window_size]
        segment = (segment - float(np.mean(segment))) * window
        rms = float(np.sqrt(np.mean(segment * segment)))
        candidate: str | None = None
        if rms >= 0.005:
            low = tuple(_tone_amplitude(segment, frequency, sample_rate_hz) for frequency in DTMF_LOW_HZ)
            high = tuple(_tone_amplitude(segment, frequency, sample_rate_hz) for frequency in DTMF_HIGH_HZ)
            low_order = np.argsort(low)
            high_order = np.argsort(high)
            low_index, high_index = int(low_order[-1]), int(high_order[-1])
            low_peak, high_peak = low[low_index], high[high_index]
            low_ratio = low_peak / max(low[int(low_order[-2])], 1e-12)
            high_ratio = high_peak / max(high[int(high_order[-2])], 1e-12)
            twist_db = 20.0 * math.log10(max(high_peak, 1e-12) / max(low_peak, 1e-12))
            if (
                low_peak >= 0.20 * rms
                and high_peak >= 0.20 * rms
                and low_ratio >= 2.5
                and high_ratio >= 2.5
                and -8.0 <= twist_db <= 6.0
            ):
                candidate = DTMF_KEYS[low_index][high_index]

        if candidate is None:
            released_windows += 1
            stable_key = None
            stable_windows = 0
            continue
        if candidate == stable_key:
            stable_windows += 1
        else:
            stable_key = candidate
            stable_windows = 1
        if stable_windows >= 2 and released_windows >= 2:
            decoded.append(candidate)
            released_windows = 0
        elif stable_windows >= 2 and decoded and decoded[-1] != candidate:
            decoded.append(candidate)
            released_windows = 0
    return tuple(decoded)
