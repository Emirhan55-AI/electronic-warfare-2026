#!/usr/bin/env python3
"""Render or read-only validate the seven PHASE-04 operator evidence images."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402

from host.operator_console.application import build_application  # noqa: E402
from reference.parameters import generate_parameter_scene, load_parameter_catalog  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes  # noqa: E402
from reference.pipeline import RuntimePipeline, VerifiedProfileBinding, load_verified_phase04_profile  # noqa: E402
from reference.sigmf import inspect_sigmf  # noqa: E402


PROFILE = ROOT / "profiles" / "phase04" / "operation-default.json"
EVIDENCE = ROOT / "results" / "evidence" / "phase04"
SUMMARY = EVIDENCE / "visual-summary.json"
IMAGES = (
    "empty-1366x768-scale100.png",
    "parameters-valid-1366x768-scale100.png",
    "carrier-unavailable-1366x768-scale100.png",
    "classification-uncertain-1366x768-scale100.png",
    "warning-1366x768-scale100.png",
    "error-1366x768-scale100.png",
    "parameters-valid-1920x1080-scale150.png",
)
IMAGE_STATES = (
    "empty",
    "parameters-valid",
    "carrier-not-observed",
    "classification-uncertain",
    "metadata-warning",
    "invalid-json-error",
    "parameters-valid",
)


def _remove_owned_visuals() -> None:
    """Invalidate only PHASE-04 visual artifacts after a failed write attempt."""
    SUMMARY.unlink(missing_ok=True)
    for filename in IMAGES:
        (EVIDENCE / filename).unlink(missing_ok=True)


def _metadata_fixture(directory: Path, *, include_channel: bool = True) -> Any:
    metadata = directory / "render.sigmf-meta"
    data = directory / "render.sigmf-data"
    global_object: dict[str, Any] = {
        "core:version": "1.0.0",
        "core:datatype": "ci8",
        "core:sample_rate": 8000000,
    }
    if include_channel:
        global_object["core:num_channels"] = 1
    metadata.write_text(
        json.dumps(
            {
                "global": global_object,
                "captures": [{"core:sample_start": 0, "core:frequency": 100000000}],
                "annotations": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    data.write_bytes(bytes(8192 * 4))
    return inspect_sigmf(metadata, data, mode="standard", frame_length=4096)


def _process_scene(profile: Any, binding: VerifiedProfileBinding, scene_id: str) -> Any:
    catalog = load_parameter_catalog()
    runtime = RuntimePipeline(profile, verified_binding=binding)
    result = None
    for frame_index in range(4):
        scene = generate_parameter_scene(
            scene_id,
            trial_index=0,
            frame_index=frame_index,
            clean_power_dbfs=-18.0,
            snr_db=12.0,
            catalog=catalog,
        )
        result = runtime.process(
            scene.samples,
            sample_rate_hz=8000000.0,
            center_frequency_hz=100000000.0,
            frame_index=frame_index,
        )
    return result


def _assert_scene_state(result: Any, expected: str) -> None:
    parameters = result.parameters
    if parameters is None or not parameters.events:
        raise RuntimeError(f"{expected} scene produced no parameter result")
    estimate = parameters.events[0]
    if expected == "parameters-valid":
        valid = (
            estimate.frequency.spectral_center_state == "valid"
            and estimate.frequency.observed_carrier_state == "valid"
            and estimate.bandwidth.lower_edge_state == "valid"
            and estimate.bandwidth.upper_edge_state == "valid"
            and estimate.bandwidth.bandwidth_state == "valid"
            and estimate.power.relative_power_state == "valid"
            and estimate.power.snr_state == "valid"
            and estimate.signal_domain.state == "valid"
        )
    elif expected == "carrier-not-observed":
        valid = (
            estimate.frequency.spectral_center_state == "valid"
            and estimate.frequency.observed_carrier_state == "not_observed"
            and estimate.frequency.observed_carrier_frequency_hz is None
        )
    elif expected == "classification-uncertain":
        valid = estimate.signal_domain.state == "uncertain" and estimate.signal_domain.value == "Belirsiz"
    else:
        raise ValueError(f"unknown PHASE-04 render state: {expected}")
    if not valid:
        raise RuntimeError(f"real pipeline did not produce the required {expected} state")


def _apply_result(window: Any, result: Any, report: Any) -> None:
    window.set_source("render.sigmf-meta", report)
    window.spectrum_view.update_spectrum(
        result.spectrum.display,
        result.spectrum.display,
        append_waterfall=True,
        detection_result=result.detection,
        spectrum_result=result.spectrum,
        parameter_result=result.parameters,
    )
    window.set_detection_result(result.detection)
    window.set_parameter_result(result.parameters)
    window.set_frame_position(3, 4)


def _capture(window: Any, path: Path, *, physical: tuple[int, int], scale: float) -> None:
    logical = (round(physical[0] / scale), round(physical[1] / scale))
    window.resize(*logical)
    window.show()
    window.repaint()
    image = QImage(physical[0], physical[1], QImage.Format.Format_ARGB32)
    image.setDevicePixelRatio(scale)
    image.fill(0)
    painter = QPainter(image)
    window.render(painter, targetOffset=image.rect().topLeft(), sourceRegion=QRect(0, 0, logical[0], logical[1]))
    painter.end()
    if not image.save(str(path), "PNG"):
        raise RuntimeError("PNG could not be saved")


def render() -> dict[str, Any]:
    if not PROFILE.is_file():
        raise RuntimeError("validated PHASE-04 profile is unavailable")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    profile, binding = load_verified_phase04_profile(PROFILE, EVIDENCE / "parameter-comparison.json")
    app, window, controller = build_application([], profile=profile, verified_binding=binding)
    del app
    with tempfile.TemporaryDirectory(prefix="phase04-render-") as temporary:
        directory = Path(temporary)
        normal_report = _metadata_fixture(directory)
        warning_report = _metadata_fixture(directory / "warning", include_channel=False) if (directory / "warning").mkdir() is None else None

        window.show_empty()
        _capture(window, EVIDENCE / IMAGES[0], physical=(1366, 768), scale=1.0)

        valid = _process_scene(profile, binding, "am-carrier")
        _assert_scene_state(valid, "parameters-valid")
        _apply_result(window, valid, normal_report)
        _capture(window, EVIDENCE / IMAGES[1], physical=(1366, 768), scale=1.0)

        carrier_unavailable = _process_scene(profile, binding, "qpsk")
        _assert_scene_state(carrier_unavailable, "carrier-not-observed")
        _apply_result(window, carrier_unavailable, normal_report)
        _capture(window, EVIDENCE / IMAGES[2], physical=(1366, 768), scale=1.0)

        uncertain = _process_scene(profile, binding, "dsb-sc")
        _assert_scene_state(uncertain, "classification-uncertain")
        _apply_result(window, uncertain, normal_report)
        _capture(window, EVIDENCE / IMAGES[3], physical=(1366, 768), scale=1.0)

        if not any(issue.code == "channel_count_defaulted" for issue in warning_report.warnings):
            raise RuntimeError("real missing-channel metadata path did not warn")
        _apply_result(window, valid, warning_report)
        window.show_warning("Kanal sayısı metadata'da yok; SigMF varsayılanı olan tek kanal kullanılıyor.")
        _capture(window, EVIDENCE / IMAGES[4], physical=(1366, 768), scale=1.0)

        broken = directory / "broken.sigmf-meta"
        broken.write_text("{bozuk", encoding="utf-8")
        error_report = inspect_sigmf(broken, directory / "render.sigmf-data", mode="standard", frame_length=4096)
        if not any(issue.code == "metadata_invalid_json" for issue in error_report.errors):
            raise RuntimeError("real invalid JSON path did not fail")
        window.show_empty()
        window.show_error("Metadata geçerli JSON değil.")
        _capture(window, EVIDENCE / IMAGES[5], physical=(1366, 768), scale=1.0)

        _apply_result(window, valid, normal_report)
        _capture(window, EVIDENCE / IMAGES[6], physical=(1920, 1080), scale=1.5)
    controller.close()
    records = []
    for filename, state in zip(IMAGES, IMAGE_STATES, strict=True):
        data = (EVIDENCE / filename).read_bytes()
        image = QImage(str(EVIDENCE / filename))
        records.append(
            {
                "filename": filename,
                "width": image.width(),
                "height": image.height(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "state": state,
                "status": "passed",
            }
        )
    return {
        "schema_version": 1,
        "phase": "PHASE-04",
        "overall": "passed",
        "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        "comparison_sha256": binding.comparison_sha256,
        "platform_byte_equality_required": False,
        "real_pipeline_outputs": True,
        "images": records,
    }


def check() -> bool:
    if not SUMMARY.is_file():
        return False
    try:
        _, binding = load_verified_phase04_profile(PROFILE, EVIDENCE / "parameter-comparison.json")
        payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except Exception:
        return False
    if (
        payload.get("overall") != "passed"
        or [item.get("filename") for item in payload.get("images", [])] != list(IMAGES)
        or [item.get("state") for item in payload.get("images", [])] != list(IMAGE_STATES)
    ):
        return False
    if (
        payload.get("profile_sha256") != hashlib.sha256(PROFILE.read_bytes()).hexdigest()
        or payload.get("comparison_sha256") != binding.comparison_sha256
    ):
        return False
    for item in payload["images"]:
        path = EVIDENCE / item["filename"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            return False
        image = QImage(str(path))
        if [image.width(), image.height()] != [item["width"], item["height"]]:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        passed = check()
    else:
        try:
            payload = render()
        except Exception as exc:
            _remove_owned_visuals()
            print(f"PHASE-04 visual rendering failed: {type(exc).__name__}")
            return 1
        SUMMARY.write_bytes(canonical_json_bytes(payload))
        passed = True
    print(f"PHASE-04 visual evidence: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
