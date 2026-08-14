"""Deterministic clean truth and hashing helpers for PHASE-04-E1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from reference.parameters.obw99_reference import build_clean_reference
from reference.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from reference.spectrum import SpectrumProcessor


ROOT = Path(__file__).resolve().parents[2]
E1_ROOT = ROOT / "datasets" / "fixtures" / "phase04e1"
SCENES_PATH = E1_ROOT / "operator-scenes.json"
ACCEPTANCE_PATH = E1_ROOT / "acceptance-gates.json"
METHOD_LOCK_PATH = E1_ROOT / "method-lock.json"
PHASE03_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def clean_truth_by_family() -> dict[str, dict[str, float]]:
    d1 = build_clean_reference()
    return {str(item["family_id"]): dict(item["truth"]) for item in d1["families"]}


def build_golden_reference() -> dict[str, Any]:
    catalog = load_json(SCENES_PATH)
    parameter_catalog = load_parameter_catalog()
    truth = clean_truth_by_family()
    processor = SpectrumProcessor()
    records: list[dict[str, Any]] = []
    for item in catalog["families"]:
        family_id = str(item["id"])
        source_scene_id = str(item["scene_id"])
        active = tuple(int(value) for value in item.get("active_frames", [0, 1, 2, 3]))
        clean_psd: list[np.ndarray] = []
        clean_bins: list[np.ndarray] = []
        clean_samples_power: list[float] = []
        for frame_index in active[:4]:
            frame = generate_parameter_scene(
                source_scene_id,
                trial_index=0,
                condition_index=0,
                frame_index=frame_index,
                clean_power_dbfs=-18.0,
                snr_db=12.0,
                catalog=parameter_catalog,
            )
            result = processor.process(frame.clean_samples, sample_rate_hz=8_000_000.0, center_frequency_hz=100_000_000.0)
            clean_psd.append(np.asarray(result.display.psd_fs2_per_hz))
            clean_bins.append(np.asarray(result.display.bin_power_fs2))
            clean_samples_power.append(float(np.mean(np.abs(frame.clean_samples) ** 2)))
        family_truth = truth[family_id]
        lower = float(family_truth["lower_shifted_native_bin"])
        upper = float(family_truth["upper_shifted_native_bin"])
        span_lower = max(56, int(np.floor(lower)) - 12)
        span_upper = min(4039, int(np.ceil(upper)) + 12)
        mean_psd = np.mean(np.stack(clean_psd), axis=0)
        mean_bin = np.mean(np.stack(clean_bins), axis=0)
        channel_power = float(np.sum(mean_psd[span_lower : span_upper + 1]) * (8_000_000.0 / 4096.0))
        bin_spacing = 8_000_000.0 / 4096.0
        emission_center_hz = 100_000_000.0 + (0.5 * (lower + upper) - 2048.0) * bin_spacing
        scene_definition = next(scene for scene in parameter_catalog["scenes"] if scene["id"] == source_scene_id)
        carrier_line_hz = 100_000_000.0 + float(scene_definition.get("signed_center_bin", 0.0)) * bin_spacing
        records.append({
            "family_id": family_id,
            "source_scene_id": source_scene_id,
            "carrier_line_applicable": bool(item["carrier_line_applicable"]),
            "expected_domain": str(item["domain"]),
            "operator_span": [span_lower, span_upper],
            "obw99": family_truth,
            "emission_center_frequency_hz": emission_center_hz,
            "carrier_line_frequency_hz": carrier_line_hz if bool(item["carrier_line_applicable"]) else None,
            "clean_channel_power_dbfs": float(10.0 * np.log10(max(channel_power, np.finfo(float).tiny))),
            "clean_peak_power_dbfs_per_bin": float(10.0 * np.log10(max(float(np.max(mean_bin[span_lower : span_upper + 1])), np.finfo(float).tiny))),
            "clean_time_power_dbfs": float(10.0 * np.log10(max(float(np.mean(clean_samples_power)), np.finfo(float).tiny))),
        })
    return {
        "schema_version": 1,
        "artifact_id": "phase04e1-golden-parameters-v1",
        "status": "passed",
        "sample_rate_hz": 8_000_000.0,
        "center_frequency_hz": 100_000_000.0,
        "fft_length": 4096,
        "families": records,
        "contracts": {
            "operator_scenes_sha256": sha256_file(SCENES_PATH),
            "acceptance_gates_sha256": sha256_file(ACCEPTANCE_PATH),
            "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
        },
    }


def implementation_manifest() -> dict[str, Any]:
    paths = [
        "reference/parameters/operator_assisted.py",
        "reference/parameters/operator_classification.py",
        "reference/parameters/operator_evaluation.py",
        "reference/parameters/operator_reference.py",
        "reference/pipeline/profile.py",
        "host/operator_console/controller.py",
    ]
    sources = [{"path": item, "sha256": sha256_file(ROOT / item)} for item in paths]
    digest = hashlib.sha256(canonical_json_bytes({"schema_version": 1, "sources": sources})).hexdigest()
    return {"schema_version": 1, "sources": sources, "sha256": digest}
