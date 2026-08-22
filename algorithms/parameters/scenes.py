"""Deterministic, streaming PHASE-04 synthetic parameter scenes."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"


@dataclass(frozen=True)
class ParameterSceneFrame:
    scene_id: str
    trial_index: int
    condition_index: int
    frame_index: int
    samples: npt.NDArray[np.complex128]
    clean_samples: npt.NDArray[np.complex128]
    ground_truth: dict[str, Any]


def load_parameter_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or document.get("index_order") != "fftshift":
        raise ValueError("unsupported PHASE-04 scene catalogue")
    if document["common"]["transient_guard_samples_per_side"] != 1152:
        raise ValueError("PHASE-04 transient guard contract changed")
    return document


def _rng(scene_seed: int, condition: int, trial: int, frame: int, stream: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([scene_seed, condition, trial, frame, stream]))


def _normalize(samples: np.ndarray, power: float) -> np.ndarray:
    measured = float(np.mean(np.abs(samples) ** 2))
    if measured <= 0.0:
        return np.zeros_like(samples, dtype=np.complex128)
    return np.asarray(samples * math.sqrt(power / measured), dtype=np.complex128)


def _bits(scene: dict[str, Any], condition: int, trial: int, frame: int, count: int, levels: int = 2) -> np.ndarray:
    return _rng(int(scene["scene_seed"]), condition, trial, frame, 1).integers(0, levels, size=count)


def _rrc_taps(samples_per_symbol: int, rolloff: float = 0.35, span_symbols: int = 8) -> np.ndarray:
    half = span_symbols * samples_per_symbol // 2
    time = np.arange(-half, half + 1, dtype=np.float64) / samples_per_symbol
    taps = np.empty(time.size, dtype=np.float64)
    for index, value in enumerate(time):
        if abs(value) < 1e-12:
            taps[index] = 1.0 + rolloff * (4.0 / math.pi - 1.0)
        elif abs(abs(value) - 1.0 / (4.0 * rolloff)) < 1e-12:
            taps[index] = (rolloff / math.sqrt(2.0)) * (
                (1.0 + 2.0 / math.pi) * math.sin(math.pi / (4.0 * rolloff))
                + (1.0 - 2.0 / math.pi) * math.cos(math.pi / (4.0 * rolloff))
            )
        else:
            numerator = math.sin(math.pi * value * (1.0 - rolloff))
            numerator += 4.0 * rolloff * value * math.cos(math.pi * value * (1.0 + rolloff))
            denominator = math.pi * value * (1.0 - (4.0 * rolloff * value) ** 2)
            taps[index] = numerator / denominator
    taps /= math.sqrt(float(np.sum(taps**2)))
    return taps


def _fft_convolve_same(values: np.ndarray, taps: np.ndarray) -> np.ndarray:
    required = values.size + taps.size - 1
    fft_size = 1 << (required - 1).bit_length()
    full = np.fft.ifft(np.fft.fft(values, fft_size) * np.fft.fft(taps, fft_size))[:required]
    start = (taps.size - 1) // 2
    return np.asarray(full[start : start + values.size], dtype=np.complex128)


def _symbol_waveform(symbols: np.ndarray, samples_per_symbol: int, length: int) -> np.ndarray:
    span = 8
    upsampled = np.zeros(symbols.size * samples_per_symbol, dtype=np.complex128)
    upsampled[::samples_per_symbol] = symbols
    shaped = _fft_convolve_same(upsampled, _rrc_taps(samples_per_symbol, 0.35, span))
    start = (span // 2 + 1) * samples_per_symbol
    if start + length > shaped.size:
        raise ValueError("symbol sequence does not cover the requested frame")
    return shaped[start : start + length]


def _modulate(scene: dict[str, Any], condition: int, trial: int, frame: int, n: int) -> np.ndarray:
    family = scene["family"]
    index = np.arange(n, dtype=np.float64) + frame * n
    center = float(scene.get("signed_center_bin", 0.0))
    carrier = np.exp(1j * 2.0 * np.pi * center * index / n)
    phase = float(_rng(int(scene["scene_seed"]), condition, trial, frame, 2).uniform(0.0, 2.0 * np.pi))
    if family == "tone":
        return carrier * np.exp(1j * phase)
    if family in {"am", "dsb_sc"}:
        message = np.cos(2.0 * np.pi * float(scene["message_bins"]) * index / n + phase)
        envelope = 1.0 + float(scene.get("modulation_index", 1.0)) * message if family == "am" else message
        return np.asarray(envelope * carrier, dtype=np.complex128)
    if family == "nfm":
        message_bins = float(scene["message_bins"])
        deviation = float(scene["deviation_bins"])
        phase_mod = (deviation / message_bins) * np.sin(2.0 * np.pi * message_bins * index / n + phase)
        return np.exp(1j * (2.0 * np.pi * center * index / n + phase_mod))
    if family in {"ook", "bpsk", "qpsk", "burst_qpsk", "two_fsk"}:
        rate = int(scene["symbol_rate_bins"])
        sps = n // rate
        count = math.ceil(n / sps) + 12
        if family == "qpsk" or family == "burst_qpsk":
            values = _bits(scene, condition, trial, frame, count, 4)
            symbols = np.exp(1j * (np.pi / 4.0 + values * np.pi / 2.0))
            return _symbol_waveform(symbols, sps, n) * carrier
        bits = _bits(scene, condition, trial, frame, count)
        if family == "ook":
            return _symbol_waveform(bits.astype(np.float64), sps, n) * carrier
        if family == "bpsk":
            return _symbol_waveform(2.0 * bits - 1.0, sps, n) * carrier
        deviation = float(scene["deviation_bins"])
        # Keep the short eight-symbol frame energy-balanced while preserving the seeded order.
        active_count = math.ceil(n / sps)
        balanced = np.tile(np.asarray([0, 1], dtype=np.int64), math.ceil(active_count / 2))[:active_count]
        order = _rng(int(scene["scene_seed"]), condition, trial, frame, 4).permutation(active_count)
        balanced = balanced[order]
        frequency_symbols = np.where(balanced > 0, 1.0, -1.0)
        padded = np.resize(frequency_symbols, active_count + 12)
        shaped_frequency = _symbol_waveform(padded, sps, n).real
        shaped_frequency /= max(float(np.max(np.abs(shaped_frequency))), np.finfo(np.float64).tiny)
        inst = deviation * shaped_frequency
        phase_track = 2.0 * np.pi * np.cumsum(center + inst) / n
        return np.exp(1j * phase_track)
    if family == "wideband":
        shifted = np.zeros(n, dtype=np.complex128)
        start, end = int(scene["shifted_start_bin"]), int(scene["shifted_end_bin"])
        rng = _rng(int(scene["scene_seed"]), condition, trial, frame, 3)
        shifted[start : end + 1] = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, end - start + 1))
        return np.fft.ifft(np.fft.ifftshift(shifted)).astype(np.complex128)
    if family == "mixed":
        samples_per_symbol = 64
        symbol_count = math.ceil(n / samples_per_symbol) + 12
        bits = _bits(scene, condition, trial, frame, symbol_count)
        digital = _symbol_waveform(2.0 * bits - 1.0, samples_per_symbol, n)
        analog = 0.7 + 0.3 * np.cos(2.0 * np.pi * 6.0 * index / n)
        return np.asarray((analog + digital) * carrier, dtype=np.complex128)
    raise ValueError(f"unsupported parameter scene family: {family}")


def generate_parameter_scene(
    scene_id: str,
    *,
    trial_index: int = 0,
    condition_index: int = 0,
    frame_index: int = 0,
    clean_power_dbfs: float = -18.0,
    snr_db: float = 12.0,
    catalog: dict[str, Any] | None = None,
    scene_seed_override: int | None = None,
) -> ParameterSceneFrame:
    document = catalog or load_parameter_catalog()
    scene = next((item for item in document["scenes"] if item["id"] == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    if scene_seed_override is not None:
        scene = dict(scene)
        scene["scene_seed"] = int(scene_seed_override)
    n = int(document["common"]["frame_length"])
    active = scene.get("active_frames")
    if active is not None and frame_index not in active:
        clean = np.zeros(n, dtype=np.complex128)
    elif scene["family"] == "noise":
        clean = np.zeros(n, dtype=np.complex128)
    elif scene["family"] == "close_pair":
        first = dict(scene, family="am", signed_center_bin=scene["component_centers_bins"][0], message_bins=8.0, modulation_index=0.6)
        second = dict(scene, family="qpsk", signed_center_bin=scene["component_centers_bins"][1], symbol_rate_bins=32.0)
        clean = _normalize(_modulate(first, condition_index, trial_index, frame_index, n), 10.0 ** (clean_power_dbfs / 10.0))
        clean += _normalize(_modulate(second, condition_index, trial_index, frame_index, n), 10.0 ** ((clean_power_dbfs - 3.0) / 10.0))
    else:
        clean = _normalize(_modulate(scene, condition_index, trial_index, frame_index, n), 10.0 ** (clean_power_dbfs / 10.0))
    signal_power = float(np.mean(np.abs(clean) ** 2))
    band = scene.get("band_definition")
    if scene["family"] == "wideband":
        nominal_band_bins = float(scene["shifted_end_bin"] - scene["shifted_start_bin"] + 1)
    elif band is not None and "lower_offset_bins" in band:
        nominal_band_bins = float(band["upper_offset_bins"] - band["lower_offset_bins"])
    elif scene["family"] == "close_pair":
        nominal_band_bins = 160.0
    else:
        nominal_band_bins = 3.0
    in_band_noise_power = signal_power / (10.0 ** (snr_db / 10.0)) if signal_power > 0.0 else 10.0 ** (-6.0)
    noise_power = in_band_noise_power * n / max(nominal_band_bins, 1.0)
    rng = _rng(int(scene["scene_seed"]), condition_index, trial_index, frame_index, 0)
    noise = math.sqrt(noise_power / 2.0) * (rng.normal(size=n) + 1j * rng.normal(size=n))
    samples = np.asarray(clean + noise, dtype=np.complex128)
    samples.setflags(write=False)
    clean.setflags(write=False)
    ground_truth = {
        "nominal_center_frequency_hz": float(document["common"]["center_frequency_hz"] + float(scene.get("signed_center_bin", 0.0)) * document["common"]["bin_spacing_hz"]),
        "clean_power_fs2": signal_power,
        "snr_db": float(snr_db),
        "band_definition": scene.get("band_definition"),
        "validity": dict(zip(document["field_order"], scene["validity"])),
        "expected_domain": "Analog" if scene["family"] in {"am", "nfm"} else "Sayısal" if scene["family"] in {"ook", "two_fsk", "bpsk", "qpsk", "burst_qpsk"} else "Belirsiz",
    }
    return ParameterSceneFrame(scene_id, trial_index, condition_index, frame_index, samples, clean, ground_truth)
