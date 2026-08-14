"""Deterministic clean-reference and noise-calibration tools for PHASE-04-D1."""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from reference.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from reference.spectrum import SpectrumProcessor, periodic_hann


ROOT = Path(__file__).resolve().parents[2]
D1_ROOT = ROOT / "datasets" / "fixtures" / "phase04d1"
SCENES_PATH = D1_ROOT / "obw99-scenes.json"
ACCEPTANCE_PATH = D1_ROOT / "acceptance-gates.json"
REFERENCE_CONTRACT_PATH = D1_ROOT / "reference-contract.json"
ADR_PATH = ROOT / "docs" / "decisions" / "ADR-0007-OCCUPIED-BANDWIDTH-SEMANTICS.md"
PHASE03_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
GENERATOR_PATH = ROOT / "scripts" / "generate_phase04d1_reference.py"
ESTIMATOR_PATH = ROOT / "reference" / "parameters" / "obw99.py"
MODULE_PATH = Path(__file__)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize deterministic JSON without timestamps or platform paths."""
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return document


def load_d1_catalog(path: Path = SCENES_PATH) -> dict[str, Any]:
    document = load_json(path)
    if document.get("schema_version") != 1 or document.get("measurement") != "occupied_bandwidth_99":
        raise ValueError("unsupported PHASE-04-D1 scene catalog")
    if document["common"]["q95_method"] != "nearest_rank":
        raise ValueError("PHASE-04-D1 requires deterministic nearest-rank q95")
    return document


def _active_clean_frames(
    family: dict[str, Any],
    *,
    count: int,
    d1_catalog: dict[str, Any],
    parameter_catalog: dict[str, Any],
) -> Iterator[np.ndarray]:
    scene_id = str(family["source_scene_id"])
    policy = str(family["active_policy"])
    pattern = tuple(bool(item) for item in d1_catalog["clean_reference"]["burst_pattern"])
    produced = 0
    timeline = 0
    while produced < count:
        if policy == "continuous":
            frame_index = timeline
            trial_index = 0
            active = True
        elif policy == "burst_pattern_active_only":
            position = timeline % len(pattern)
            frame_index = position
            trial_index = timeline // len(pattern)
            active = pattern[position]
        else:
            raise ValueError(f"unsupported active policy: {policy}")
        timeline += 1
        if not active:
            continue
        frame = generate_parameter_scene(
            scene_id,
            trial_index=trial_index,
            condition_index=0,
            frame_index=frame_index,
            clean_power_dbfs=float(d1_catalog["common"]["clean_power_dbfs"]),
            snr_db=float(d1_catalog["common"]["binding_snr_db"]),
            catalog=parameter_catalog,
        )
        if not np.any(frame.clean_samples):
            raise ValueError(f"active clean-reference frame is empty: {scene_id}")
        produced += 1
        yield np.asarray(frame.clean_samples, dtype=np.complex128)


def fractional_power_edge(power: np.ndarray, fraction: float) -> float:
    """Return one cumulative-power edge using uniform-cell interpolation."""
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in the open interval (0, 1)")
    total = float(np.sum(power))
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("clean reference has no finite positive power")
    target = fraction * total
    cumulative = np.cumsum(power)
    index = min(int(np.searchsorted(cumulative, target, side="left")), power.size - 1)
    before = 0.0 if index == 0 else float(cumulative[index - 1])
    cell = float(power[index])
    position = index - 0.5 + (target - before) / max(cell, np.finfo(np.float64).tiny)
    return float(position)


def nearest_rank_q95(values: np.ndarray) -> float:
    """Return deterministic one-based ceil(0.95*N) empirical q95."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("q95 values must be a finite non-empty vector")
    rank = int(math.ceil(0.95 * array.size))
    return float(np.sort(array)[rank - 1])


def _edge_record(
    averaged_power: np.ndarray,
    *,
    sample_rate_hz: float,
    center_frequency_hz: float,
    native_length: int,
) -> dict[str, float]:
    grid_length = averaged_power.size
    lower_grid = fractional_power_edge(averaged_power, 0.005)
    upper_grid = fractional_power_edge(averaged_power, 0.995)
    grid_spacing = sample_rate_hz / grid_length
    lower_offset_hz = (lower_grid - grid_length / 2.0) * grid_spacing
    upper_offset_hz = (upper_grid - grid_length / 2.0) * grid_spacing
    lower_native = native_length / 2.0 + lower_offset_hz / (sample_rate_hz / native_length)
    upper_native = native_length / 2.0 + upper_offset_hz / (sample_rate_hz / native_length)
    return {
        "lower_shifted_native_bin": round(lower_native, 12),
        "upper_shifted_native_bin": round(upper_native, 12),
        "lower_offset_hz": round(lower_offset_hz, 9),
        "upper_offset_hz": round(upper_offset_hz, 9),
        "lower_frequency_hz": round(center_frequency_hz + lower_offset_hz, 9),
        "upper_frequency_hz": round(center_frequency_hz + upper_offset_hz, 9),
        "occupied_bandwidth_hz": round(upper_offset_hz - lower_offset_hz, 9),
    }


@lru_cache(maxsize=1)
def build_clean_reference() -> dict[str, Any]:
    """Build the fixed clean OBW99 reference without consulting estimator output."""
    d1 = load_d1_catalog()
    parameter_catalog = load_parameter_catalog()
    contract = load_json(REFERENCE_CONTRACT_PATH)
    n = int(contract["clean_reference"]["fft_length"])
    frames = int(contract["clean_reference"]["active_frames"])
    checkpoints = tuple(int(item) for item in contract["clean_reference"]["convergence_checkpoints_frames"])
    factor = int(contract["clean_reference"]["zero_padding_factor"])
    padded = n * factor
    sample_rate = float(d1["common"]["sample_rate_hz"])
    center = float(d1["common"]["center_frequency_hz"])
    window = periodic_hann(n)
    window_power = float(np.sum(window * window))
    families: list[dict[str, Any]] = []
    for family in d1["supported_families"]:
        native_sum = np.zeros(n, dtype=np.float64)
        padded_sum = np.zeros(padded, dtype=np.float64)
        checkpoint_edges: dict[int, dict[str, float]] = {}
        maximum_power_error = 0.0
        for index, samples in enumerate(
            _active_clean_frames(
                family,
                count=frames,
                d1_catalog=d1,
                parameter_catalog=parameter_catalog,
            ),
            start=1,
        ):
            windowed = samples * window
            native_power = np.abs(np.fft.fftshift(np.fft.fft(windowed, n))) ** 2
            padded_power = np.abs(np.fft.fftshift(np.fft.fft(windowed, padded))) ** 2
            native_integral = float(np.sum(native_power) / (sample_rate * window_power) * (sample_rate / n))
            padded_integral = float(np.sum(padded_power) / (sample_rate * window_power) * (sample_rate / padded))
            if native_integral >= 1e-12:
                maximum_power_error = max(
                    maximum_power_error,
                    abs(padded_integral - native_integral) / native_integral,
                )
            else:
                maximum_power_error = max(maximum_power_error, abs(padded_integral - native_integral))
            native_sum += native_power
            padded_sum += padded_power
            if index in checkpoints:
                checkpoint_edges[index] = _edge_record(
                    padded_sum / index,
                    sample_rate_hz=sample_rate,
                    center_frequency_hz=center,
                    native_length=n,
                )
        edge128 = checkpoint_edges[128]
        edge256 = checkpoint_edges[256]
        convergence = max(
            abs(edge128["lower_shifted_native_bin"] - edge256["lower_shifted_native_bin"]),
            abs(edge128["upper_shifted_native_bin"] - edge256["upper_shifted_native_bin"]),
        )
        if convergence > float(contract["clean_reference"]["edge_convergence_max_native_bins"]):
            raise ValueError(f"clean reference did not converge for {family['family_id']}")
        if maximum_power_error > float(contract["clean_reference"]["power_conservation_relative_tolerance"]):
            raise ValueError(f"zero-padding power conservation failed for {family['family_id']}")
        families.append(
            {
                "family_id": family["family_id"],
                "source_scene_id": family["source_scene_id"],
                "active_policy": family["active_policy"],
                "active_frames": frames,
                "checkpoints": [
                    {"active_frames": checkpoint, **checkpoint_edges[checkpoint]}
                    for checkpoint in checkpoints
                ],
                "truth": edge256,
                "edge_convergence_native_bins": round(convergence, 12),
                "maximum_zero_padding_power_error": float(f"{maximum_power_error:.15g}"),
            }
        )
    return {
        "schema_version": 1,
        "artifact_id": "phase04d1-clean-obw99-reference-v1",
        "status": "passed",
        "measurement": "occupied_bandwidth_99",
        "sample_rate_hz": sample_rate,
        "center_frequency_hz": center,
        "fft_length": n,
        "zero_padding_factor": factor,
        "occupied_power_fraction": 0.99,
        "families": families,
        "contracts": {
            "scenes_sha256": sha256_file(SCENES_PATH),
            "reference_contract_sha256": sha256_file(REFERENCE_CONTRACT_PATH),
        },
    }


def _noise_estimates(seed: int, frames: int, batch_size: int, contract: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    n = int(contract["clean_reference"]["fft_length"])
    window = periodic_hann(n)
    power_sum = float(np.sum(window * window))
    blocks = contract["noise_calibration_contract"]["reference_blocks_shifted_inclusive"]
    rng = np.random.default_rng(seed)
    all_values: list[np.ndarray] = []
    batch_means: list[float] = []
    for start in range(0, frames, batch_size):
        size = min(batch_size, frames - start)
        samples = (rng.normal(size=(size, n)) + 1j * rng.normal(size=(size, n))) / math.sqrt(2.0)
        normalized = np.abs(np.fft.fftshift(np.fft.fft(samples * window, axis=1), axes=1)) ** 2 / power_sum
        references = np.concatenate(
            [normalized[:, int(lower) : int(upper) + 1] for lower, upper in blocks],
            axis=1,
        )
        estimates = np.median(references, axis=1) / math.log(2.0)
        all_values.append(estimates)
        batch_means.append(float(np.mean(estimates)))
    return np.concatenate(all_values), np.asarray(batch_means, dtype=np.float64)


@lru_cache(maxsize=1)
def noise_calibration() -> dict[str, Any]:
    """Calibrate median/ln(2) only on fixed, independent PHASE-02 noise streams."""
    contract = load_json(REFERENCE_CONTRACT_PATH)
    settings = contract["noise_calibration_contract"]
    calibration, calibration_batches = _noise_estimates(
        int(settings["calibration_seed"]),
        int(settings["calibration_frames"]),
        int(settings["batch_size"]),
        contract,
    )
    correction = 1.0 / float(np.mean(calibration))
    validation, validation_batches = _noise_estimates(
        int(settings["validation_seed"]),
        int(settings["validation_frames"]),
        int(settings["batch_size"]),
        contract,
    )
    corrected = validation * correction
    mean = float(np.mean(corrected))
    variance = float(np.var(corrected, ddof=1))
    batch_corrected = validation_batches * correction
    half_width = 1.96 * float(np.std(batch_corrected, ddof=1)) / math.sqrt(batch_corrected.size)
    interval = (mean - half_width, mean + half_width)
    passed = (
        abs(mean - 1.0) <= float(settings["validation_corrected_mean_bias_absolute_maximum"])
        and half_width <= float(settings["validation_ci95_half_width_maximum"])
        and interval[0] <= 1.0 <= interval[1]
    )
    return {
        "status": "passed" if passed else "failed",
        "pipeline": "phase02-periodic-hann-fft-psd",
        "estimator": "median_reference_psd_div_ln2",
        "calibration_seed": int(settings["calibration_seed"]),
        "validation_seed": int(settings["validation_seed"]),
        "calibration_frames": int(settings["calibration_frames"]),
        "validation_frames": int(settings["validation_frames"]),
        "batch_size": int(settings["batch_size"]),
        "ci_method": settings["ci_method"],
        "reference_blocks_shifted_inclusive": settings["reference_blocks_shifted_inclusive"],
        "reference_guard_bins": int(settings["reference_guard_bins"]),
        "uncorrected_calibration_mean_ratio": float(np.mean(calibration)),
        "uncorrected_calibration_variance": float(np.var(calibration, ddof=1)),
        "correction_factor": correction,
        "corrected_validation_mean_ratio": mean,
        "corrected_validation_variance": variance,
        "corrected_validation_ci95": [interval[0], interval[1]],
        "corrected_validation_ci95_half_width": half_width,
        "corrected_validation_bias": mean - 1.0,
        "exact_pfa_claimed": False,
        "binding_or_oos_inputs_used": False,
    }


def phase02_noise_equivalence(samples: np.ndarray, *, sample_rate_hz: float) -> float:
    """Return maximum absolute PSD difference against SpectrumProcessor for one frame."""
    processor = SpectrumProcessor()
    result = processor.process(samples, sample_rate_hz=sample_rate_hz, center_frequency_hz=0.0)
    window = periodic_hann(samples.size)
    direct = np.fft.fftshift(np.abs(np.fft.fft(samples * window)) ** 2) / (
        sample_rate_hz * float(np.sum(window * window))
    )
    return float(np.max(np.abs(direct - result.display.psd_fs2_per_hz)))


def implementation_manifest() -> dict[str, Any]:
    sources = [MODULE_PATH, ESTIMATOR_PATH, GENERATOR_PATH]
    records = [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
        for path in sorted(sources, key=lambda item: item.as_posix())
    ]
    identity = hashlib.sha256(canonical_json_bytes({"sources": records})).hexdigest()
    return {"identity_sha256": identity, "sources": records}
