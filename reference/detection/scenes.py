"""Deterministic PHASE-03 scene catalogue loader and I/Q generator."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt


ComplexArray = npt.NDArray[np.complex128]
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = ROOT / "datasets" / "fixtures" / "phase03" / "detection-scenes.json"


@dataclass(frozen=True)
class SceneFrame:
    """One generated complex frame plus its machine-readable ground truth."""

    scene_id: str
    trial_index: int
    condition_index: int
    samples: ComplexArray
    ground_truth: tuple[dict[str, Any], ...]


def load_scene_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported scene catalogue schema")
    if document.get("index_order") != "fftshift":
        raise ValueError("scene catalogue must use fftshift index order")
    return document


def _rng(
    scene_seed: int,
    condition_index: int,
    trial_index: int,
    stream_kind: int,
    component_index: int = 0,
) -> np.random.Generator:
    sequence = np.random.SeedSequence(
        [scene_seed, condition_index, trial_index, stream_kind, component_index]
    )
    return np.random.default_rng(sequence)


def _normalize_power(samples: ComplexArray, target_power: float) -> ComplexArray:
    measured = float(np.mean(np.square(samples.real) + np.square(samples.imag)))
    if measured <= 0.0:
        raise ValueError("cannot normalize a zero-power scene")
    return np.asarray(samples * math.sqrt(target_power / measured), dtype=np.complex128)


def _noise(
    scene: dict[str, Any],
    condition_index: int,
    trial_index: int,
    frame_length: int,
) -> ComplexArray:
    noise_power = float(scene["noise_power"])
    generator = _rng(int(scene["scene_seed"]), condition_index, trial_index, 0)
    result = math.sqrt(noise_power / 2.0) * (
        generator.normal(size=frame_length) + 1j * generator.normal(size=frame_length)
    )
    result = np.asarray(result, dtype=np.complex128)
    if bool(scene.get("normalize_noise", True)):
        result = _normalize_power(result, noise_power)
    return result


def _tone(
    scene: dict[str, Any],
    tone: dict[str, Any],
    condition_index: int,
    trial_index: int,
    component_index: int,
    frame_length: int,
    snr_db: float,
) -> ComplexArray:
    phase_rng = _rng(int(scene["scene_seed"]), condition_index, trial_index, 1, component_index)
    phase = float(phase_rng.uniform(0.0, 2.0 * math.pi))
    amplitude = math.sqrt(float(scene["noise_power"]) * 10.0 ** (snr_db / 10.0))
    index = np.arange(frame_length, dtype=np.float64)
    return np.asarray(
        amplitude
        * np.exp(1j * ((2.0 * math.pi * float(tone["signed_bin"]) * index / frame_length) + phase)),
        dtype=np.complex128,
    )


def generate_scene(
    scene_id: str,
    *,
    trial_index: int = 0,
    condition_index: int = 0,
    catalog: dict[str, Any] | None = None,
) -> SceneFrame:
    """Generate one catalogue-defined scene without hidden scenario constants."""
    document = catalog or load_scene_catalog()
    common = document["common"]
    frame_length = int(common["frame_length"])
    scene = next((item for item in document["scenes"] if item["id"] == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    conditions = scene.get("conditions", [None])
    if not 0 <= condition_index < len(conditions):
        raise IndexError("condition_index outside the scene catalogue")
    kind = scene["kind"]

    if kind in {"tone", "multi_tone"}:
        noise = _noise(scene, condition_index, trial_index, frame_length)
        samples = noise.copy()
        condition = conditions[condition_index] or {}
        tones = scene["tones"]
        for component_index, tone in enumerate(tones):
            snr_db = float(condition["snr_db"]) if "snr_db" in condition else float(tone["snr_db"])
            samples += _tone(
                scene,
                tone,
                condition_index,
                trial_index,
                component_index,
                frame_length,
                snr_db,
            )
        truth = tuple(dict(tone, snr_db=(float(condition["snr_db"]) if "snr_db" in condition else float(tone["snr_db"]))) for tone in tones)
    elif kind == "wideband":
        noise = _noise(scene, condition_index, trial_index, frame_length)
        coefficients = np.zeros(frame_length, dtype=np.complex128)
        start = int(scene["shifted_start_bin"])
        end = int(scene["shifted_end_bin"])
        generator = _rng(int(scene["scene_seed"]), condition_index, trial_index, 2)
        phases = generator.uniform(0.0, 2.0 * math.pi, end - start + 1)
        coefficients[start : end + 1] = np.exp(1j * phases)
        signal = np.asarray(np.fft.ifft(np.fft.ifftshift(coefficients)), dtype=np.complex128)
        target_power = float(np.mean(np.abs(noise) ** 2)) * 10.0 ** (float(scene["total_snr_db"]) / 10.0)
        signal = _normalize_power(signal, target_power)
        samples = noise + signal
        truth = (
            {
                "role": "wideband_target",
                "shifted_start_bin": start,
                "shifted_end_bin": end,
                "total_snr_db": float(scene["total_snr_db"]),
            },
        )
    elif kind in {"sloped_noise", "stepped_noise"}:
        generator = _rng(int(scene["scene_seed"]), condition_index, trial_index, 0)
        if kind == "sloped_noise":
            db_shape = np.linspace(float(scene["start_db"]), float(scene["end_db"]), frame_length)
        else:
            boundary = int(scene["boundary_shifted_bin"])
            db_shape = np.empty(frame_length, dtype=np.float64)
            db_shape[:boundary] = float(scene["left_db"])
            db_shape[boundary:] = float(scene["right_db"])
        variance = np.power(10.0, db_shape / 10.0)
        shifted = np.sqrt(variance / 2.0) * (
            generator.normal(size=frame_length) + 1j * generator.normal(size=frame_length)
        )
        samples = np.asarray(np.fft.ifft(np.fft.ifftshift(shifted)), dtype=np.complex128)
        samples = _normalize_power(samples, float(scene["noise_power"]))
        truth = ()
    elif kind == "awgn":
        samples = _noise(scene, condition_index, trial_index, frame_length)
        truth = ()
    else:
        raise ValueError(f"unsupported scene kind: {kind}")

    samples.setflags(write=False)
    return SceneFrame(
        scene_id=scene_id,
        trial_index=trial_index,
        condition_index=condition_index,
        samples=samples,
        ground_truth=truth,
    )


def generate_temporal_frame(
    scene_id: str,
    *,
    sequence_index: int,
    frame_index: int,
    catalog: dict[str, Any] | None = None,
) -> SceneFrame:
    """Generate an active or noise-only frame from a catalogue temporal scene."""
    document = catalog or load_scene_catalog()
    common = document["common"]
    scene = next((item for item in document["scenes"] if item["id"] == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    sequence_length = int(scene["sequence_length"])
    if not 0 <= frame_index < sequence_length:
        raise IndexError("frame_index outside the temporal scene")
    trial_index = sequence_index * sequence_length + frame_index
    if frame_index in scene["active_frames"]:
        return generate_scene(scene_id, trial_index=trial_index, catalog=document)
    samples = _noise(scene, frame_index, trial_index, int(common["frame_length"]))
    samples.setflags(write=False)
    return SceneFrame(
        scene_id=scene_id,
        trial_index=trial_index,
        condition_index=frame_index,
        samples=samples,
        ground_truth=(),
    )
