#!/usr/bin/env python3
"""Verify PHASE-02 DSP, UI, performance, and repository evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.operator_console.application import build_application, run_playback_benchmark  # noqa: E402
from host.operator_console.ui_text import TEXT, TURKISH_GLYPHS  # noqa: E402
from reference.spectrum import SigMFFrameSource, SpectrumProcessor  # noqa: E402


SUMMARY_PATH = ROOT / "results" / "evidence" / "phase02" / "verification-summary.json"
GOLDEN_PATH = ROOT / "results" / "evidence" / "phase02" / "golden-spectrum.json"
FIXTURE_METADATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
FIXTURE_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
VISUAL_SCRIPT = ROOT / "scripts" / "render_phase02_ui.py"
EXTERNAL_METADATA_ENV = "PHASE01_EXTERNAL_METADATA"
EXTERNAL_DATA_ENV = "PHASE01_EXTERNAL_DATA"

FIXTURE_SHA256 = "d7c7062eb2fcd221a05db3b62b90ed896e179b242aebe3497b7152c44fb8371f"
FIXTURE_SHA512 = (
    "2e0d6f3e2fd2505de06281569cda143d4ddfa75033fb86d9e386f0bd144e8afc"
    "e1e05cb07e3ffc214db6a95c1047caea8b94b56a47283a23d8ff7526f8b60697"
)

HISTORICAL_EVIDENCE_HASHES = {
    "results/evidence/phase00/toolchain.json": "92ba4ca8ca14ab6c85ca1cc43388dee1a115aa17e6661fdf1b7e58b1ddc870a8",
    "results/evidence/phase00/verification-summary.json": "8697c756389b9144bd85104b8b614022ff5ba8e3590eddff0edf53629b1ab862",
    "results/evidence/phase01/fixture-manifest.json": "a994820a1134fe9cd01721987391412037c655942dd10e99e941be2e09aef879",
    "results/evidence/phase01/verification-summary.json": "07c3b0ab1e2017f6d68234853cfc40381b854339cf40077d6cbd3653efdc0832",
    "results/evidence/phase01/external-dataset-manifest.example.json": "63453d96b64f31deb0ecf68a416e2635cbb224feb3d77dee8c4bee470c6f4cfa",
}

PHASE02_TEXT_FILES = (
    "requirements/phase02.txt",
    "docs/decisions/ADR-0003-OPERATOR-APPLICATION-STACK.md",
    "docs/interfaces/SPECTRUM_REFERENCE_CONTRACT.md",
    "reference/spectrum/__init__.py",
    "reference/spectrum/dsp.py",
    "reference/spectrum/source.py",
    "host/operator_console/__init__.py",
    "host/operator_console/__main__.py",
    "host/operator_console/application.py",
    "host/operator_console/controller.py",
    "host/operator_console/main_window.py",
    "host/operator_console/pysidedeploy.spec",
    "host/operator_console/spectrum_view.py",
    "host/operator_console/theme.qss",
    "host/operator_console/ui_text.py",
    "scripts/render_phase02_ui.py",
    "scripts/verify_phase02.py",
    "tests/test_operator_console.py",
    "tests/test_phase02_verifier.py",
    "tests/test_sigmf_frame_source.py",
    "tests/test_spectrum_reference.py",
    "results/evidence/phase02/golden-spectrum.json",
    "results/evidence/phase02/verification-summary.json",
    "results/evidence/phase02/visual-summary.json",
)

UPDATED_TEXT_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/plans/IMPLEMENTATION_ROADMAP.md",
    "docs/requirements/KTR_TRACEABILITY.md",
    "host/README.md",
    "reference/README.md",
    "scripts/verify_phase00.py",
    "tests/test_repository_contract.py",
    "verification/README.md",
)

SCREENSHOT_FILES = (
    "results/evidence/phase02/screenshots/empty-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1920x1080-scale150.png",
    "results/evidence/phase02/screenshots/warning-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/error-1366x768-scale100.png",
)


def result(identifier: str, status: str, detail: str) -> dict[str, str]:
    if status not in {"passed", "failed", "skipped"}:
        raise ValueError(f"invalid verification status: {status}")
    return {"id": identifier, "status": status, "detail": detail}


def golden_payload() -> tuple[dict[str, object], bool]:
    payload = FIXTURE_DATA.read_bytes()
    source = SigMFFrameSource(FIXTURE_METADATA)
    processor = SpectrumProcessor()
    frame_results = [
        processor.process(
            source.read_frame(index),
            sample_rate_hz=source.sample_rate_hz,
            center_frequency_hz=source.center_frequency_hz,
        )
        for index in range(source.frame_count)
    ]
    first = frame_results[0]
    display = first.display
    shifted_peak = int(np.argmax(display.bin_power_fs2))
    unshifted_peaks = [int(np.argmax(item.fft_power_unshifted)) for item in frame_results]
    shifted_peaks = [int(np.argmax(item.display.bin_power_fs2)) for item in frame_results]
    arrays_finite = all(
        np.all(np.isfinite(array))
        for item in frame_results
        for array in (
            item.fft_unshifted.real,
            item.fft_unshifted.imag,
            item.fft_power_unshifted,
            item.display.frequency_offset_hz,
            item.display.frequency_absolute_hz,
            item.display.amplitude_fs,
            item.display.bin_power_fs2,
            item.display.bin_power_dbfs,
            item.display.psd_fs2_per_hz,
            item.display.psd_dbfs_per_hz,
        )
    )
    frames_equal = all(
        np.allclose(frame_results[0].fft_unshifted, item.fft_unshifted, rtol=1e-10, atol=1e-12)
        for item in frame_results[1:]
    )
    non_peak = display.bin_power_fs2.copy()
    non_peak[shifted_peak] = 0.0
    harmonics_present = np.count_nonzero(non_peak) > 0
    fixture_sha256 = hashlib.sha256(payload).hexdigest()
    fixture_sha512 = hashlib.sha512(payload).hexdigest()

    actual = {
        "fixture_sha256": fixture_sha256,
        "fixture_sha512": fixture_sha512,
        "frame_count": len(frame_results),
        "unshifted_peak_indices": unshifted_peaks,
        "shifted_peak_indices": shifted_peaks,
        "peak_offset_hz": round(float(display.frequency_offset_hz[shifted_peak]), 9),
        "peak_absolute_hz": round(float(display.frequency_absolute_hz[shifted_peak]), 9),
        "peak_amplitude_fs": round(float(display.amplitude_fs[shifted_peak]), 12),
        "peak_bin_power_dbfs": round(float(display.bin_power_dbfs[shifted_peak]), 9),
        "peak_psd_dbfs_per_hz": round(float(display.psd_dbfs_per_hz[shifted_peak]), 9),
        "frequency_axis_size": int(display.frequency_offset_hz.size),
        "frequency_offset_first_hz": round(float(display.frequency_offset_hz[0]), 9),
        "frequency_offset_last_hz": round(float(display.frequency_offset_hz[-1]), 9),
        "frequency_absolute_first_hz": round(float(display.frequency_absolute_hz[0]), 9),
        "frequency_absolute_last_hz": round(float(display.frequency_absolute_hz[-1]), 9),
        "all_outputs_finite": arrays_finite,
        "four_frames_equal_within_tolerance": frames_equal,
        "quantization_harmonics_present": harmonics_present,
    }
    expected = {
        "unshifted_peak_index": 256,
        "shifted_peak_index": 2304,
        "peak_offset_hz": 500_000.0,
        "peak_absolute_hz": 100_500_000.0,
        "peak_amplitude_fs": 0.780247925333,
        "peak_bin_power_dbfs": -2.155347549,
        "peak_psd_dbfs_per_hz": -36.823560530,
        "frequency_axis_size": 4096,
        "frequency_offset_first_hz": -4_000_000.0,
        "frequency_offset_last_hz": 3_998_046.875,
        "frequency_absolute_first_hz": 96_000_000.0,
        "frequency_absolute_last_hz": 103_998_046.875,
    }
    tolerances = {
        "frequency_absolute_tolerance_hz": 1e-9,
        "frequency_relative_tolerance": 1e-12,
        "linear_absolute_tolerance": 1e-12,
        "linear_relative_tolerance": 1e-10,
        "db_absolute_tolerance": 1e-8,
    }
    passed = (
        fixture_sha256 == FIXTURE_SHA256
        and fixture_sha512 == FIXTURE_SHA512
        and len(frame_results) == 4
        and unshifted_peaks == [256] * 4
        and shifted_peaks == [2304] * 4
        and math.isclose(actual["peak_offset_hz"], expected["peak_offset_hz"], abs_tol=1e-9, rel_tol=1e-12)
        and math.isclose(actual["peak_absolute_hz"], expected["peak_absolute_hz"], abs_tol=1e-9, rel_tol=1e-12)
        and math.isclose(actual["peak_amplitude_fs"], expected["peak_amplitude_fs"], abs_tol=1e-12, rel_tol=1e-10)
        and math.isclose(actual["peak_bin_power_dbfs"], expected["peak_bin_power_dbfs"], abs_tol=1e-8)
        and math.isclose(actual["peak_psd_dbfs_per_hz"], expected["peak_psd_dbfs_per_hz"], abs_tol=1e-8)
        and actual["frequency_axis_size"] == 4096
        and actual["frequency_offset_first_hz"] == -4_000_000.0
        and actual["frequency_offset_last_hz"] == 3_998_046.875
        and actual["frequency_absolute_first_hz"] == 96_000_000.0
        and actual["frequency_absolute_last_hz"] == 103_998_046.875
        and arrays_finite
        and frames_equal
        and harmonics_present
    )
    evidence = {
        "schema_version": 1,
        "phase": "PHASE-02",
        "fixture": "known-tone-ci8",
        "fixture_model": "repeated 16-sample integer lookup with deterministic quantization harmonics",
        "full_spectrum_digest_is_portable_gate": False,
        "expected": expected,
        "tolerances": tolerances,
        "actual": actual,
    }
    return evidence, passed


def check_required_files() -> dict[str, str]:
    required = (*PHASE02_TEXT_FILES, *UPDATED_TEXT_FILES, *SCREENSHOT_FILES)
    missing = [name for name in required if not (ROOT / name).is_file()]
    return result(
        "required-files",
        "passed" if not missing else "failed",
        "all approved PHASE-02 files are present" if not missing else "missing: " + ", ".join(missing),
    )


def check_runtime_dependencies() -> dict[str, str]:
    expected = {"numpy": "2.2.6", "PySide6": "6.10.2", "pyqtgraph": "0.14.0"}
    found: dict[str, str] = {}
    for package in expected:
        try:
            found[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            found[package] = "unavailable"
    passed = found == expected
    return result(
        "runtime-dependencies",
        "passed" if passed else "failed",
        "required Python runtime versions are available" if passed else "runtime version mismatch",
    )


def check_text_integrity() -> dict[str, str]:
    problems: list[str] = []
    for relative in (*PHASE02_TEXT_FILES, *UPDATED_TEXT_FILES):
        path = ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            problems.append(f"{relative}: invalid UTF-8 at byte {exc.start}")
            continue
        if "\x00" in text:
            problems.append(f"{relative}: NUL byte")
        if "\r" in text:
            problems.append(f"{relative}: non-LF line ending")
        if text and not text.endswith("\n"):
            problems.append(f"{relative}: missing final newline")
        for line_number, line in enumerate(text.split("\n"), start=1):
            if line.endswith((" ", "\t")):
                problems.append(f"{relative}:{line_number}: trailing whitespace")
    return result(
        "text-integrity",
        "passed" if not problems else "failed",
        "all PHASE-02 text files are valid UTF-8 with LF endings and no trailing whitespace"
        if not problems
        else "; ".join(problems),
    )


def check_historical_evidence() -> dict[str, str]:
    mismatches = []
    for relative, expected in HISTORICAL_EVIDENCE_HASHES.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(relative)
    return result(
        "historical-evidence",
        "passed" if not mismatches else "failed",
        "PHASE-00/01 evidence files are byte-for-byte unchanged"
        if not mismatches
        else "historical evidence changed: " + ", ".join(mismatches),
    )


def check_golden_spectrum() -> dict[str, str]:
    evidence, passed = golden_payload()
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result(
        "golden-spectrum",
        "passed" if passed else "failed",
        "fixture hashes, four dominant bins, selected measurements, axis, harmonics, and finiteness passed"
        if passed
        else "golden spectrum values failed",
    )


def check_ui_policy() -> dict[str, str]:
    catalog = "\n".join(TEXT.values())
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    interface = (ROOT / "docs/interfaces/SPECTRUM_REFERENCE_CONTRACT.md").read_text(encoding="utf-8")
    required_agents = (
        "Türkçe ve UTF-8",
        "ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü",
        "Uygulanmamış donanım veya algoritma özellikleri çalışıyormuş gibi gösterilmez",
        "sade, profesyonel ve görev odaklı",
    )
    broken = any(token in catalog for token in ("�", "Ã", "Ä", "Å"))
    forbidden_fake = any(token in catalog for token in ("HackRF Bağlı", "ZedBoard Bağlı", "FPGA Hazır", "TX Etkin"))
    calibrated_claim = "kalibre edilmemiş" in catalog and "dBm değildir" in catalog
    power_contract = "Geniş bant gürültü gücü" in interface and "fiziksel dBm" in interface
    passed = (
        all(character.encode("utf-8").decode("utf-8") == character for character in TURKISH_GLYPHS)
        and all(value in agents for value in required_agents)
        and not broken
        and not forbidden_fake
        and calibrated_claim
        and power_contract
    )
    return result(
        "turkish-ui-and-capability-policy",
        "passed" if passed else "failed",
        "Turkish UTF-8 text, uncalibrated-power wording, and truthful PHASE-02 capability policy passed"
        if passed
        else "UI language, power, or capability policy failed",
    )


def check_visual_evidence() -> dict[str, str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_phase02_ui", VISUAL_SCRIPT)
    if spec is None or spec.loader is None:
        return result("visual-evidence", "failed", "visual verifier could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    problems = module.check_outputs()
    return result(
        "visual-evidence",
        "passed" if not problems else "failed",
        "five real UI states pass logical/physical size, clipping, readability, contrast, and truthfulness checks"
        if not problems
        else "; ".join(problems),
    )


def _wait_for_initial_frame(app: object, controller: object) -> bool:
    from PySide6.QtCore import QEventLoop, QTimer

    if controller.last_result is not None and controller.active_task_count == 0:
        return True
    loop = QEventLoop()
    controller.frame_rendered.connect(loop.quit)
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    controller.frame_rendered.disconnect(loop.quit)
    return controller.last_result is not None and controller.active_task_count == 0


def check_ui_performance() -> tuple[dict[str, str], dict[str, object]]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app, window, controller = build_application(["phase02-performance"])
    window.resize(1280, 720)
    window.show()
    app.processEvents()
    observations: dict[str, object] = {}
    try:
        if not controller.open_source(FIXTURE_METADATA) or not _wait_for_initial_frame(app, controller):
            return result("recorded-playback-performance", "failed", "initial golden frame did not render"), observations
        ten = run_playback_benchmark(window, controller, target_fps=10, duration_seconds=2.0)
        thirty = run_playback_benchmark(window, controller, target_fps=30, duration_seconds=1.5)
        observations = {
            "fps10": round(ten.achieved_fps, 1),
            "fps30": round(thirty.achieved_fps, 1),
            "heartbeat_gap10_ms": round(ten.maximum_heartbeat_gap_ms, 2),
            "heartbeat_gap30_ms": round(thirty.maximum_heartbeat_gap_ms, 2),
            "max_concurrent_tasks": max(ten.maximum_concurrent_tasks, thirty.maximum_concurrent_tasks),
            "max_pending_intents": max(ten.maximum_pending_intents, thirty.maximum_pending_intents),
            "waterfall_rows": thirty.waterfall_rows,
        }
        passed = (
            ten.achieved_fps >= 9.5
            and ten.rendered_frames >= 16
            and thirty.rendered_frames >= 30
            and ten.maximum_heartbeat_gap_ms < 250.0
            and thirty.maximum_heartbeat_gap_ms < 250.0
            and observations["max_concurrent_tasks"] == 1
            and observations["max_pending_intents"] <= 1
            and thirty.waterfall_rows <= 128
            and thirty.active_tasks_after_stop == 0
        )
    finally:
        controller.close()
        window.close()
        app.processEvents()
    detail = (
        "10 fps minimum cadence, 30 fps target observation, responsive heartbeat, single worker, and bounded queue passed"
        if passed
        else "recorded playback cadence, responsiveness, or queue bounds failed"
    )
    return result("recorded-playback-performance", "passed" if passed else "failed", detail), observations


def check_external_frame(frame_index: int | None) -> dict[str, str]:
    metadata_value = os.environ.get(EXTERNAL_METADATA_ENV)
    data_value = os.environ.get(EXTERNAL_DATA_ENV)
    if bool(metadata_value) != bool(data_value):
        return result("external-single-frame", "failed", "both external dataset variables are required")
    if not metadata_value and not data_value:
        return result("external-single-frame", "skipped", "external dataset variables are not set")
    if frame_index is None:
        return result("external-single-frame", "skipped", "external paths are set but no frame index was selected")
    assert metadata_value is not None and data_value is not None
    try:
        data_path = Path(data_value)
        before = data_path.stat()
        source = SigMFFrameSource(Path(metadata_value), data_path, mode="explicit")
        frame = source.read_frame(frame_index)
        spectrum = SpectrumProcessor().process(
            frame,
            sample_rate_hz=source.sample_rate_hz,
            center_frequency_hz=source.center_frequency_hz,
        )
        after = data_path.stat()
        passed = (
            frame.size == 4096
            and np.all(np.isfinite(spectrum.display.psd_dbfs_per_hz))
            and before.st_size == after.st_size
            and before.st_mtime_ns == after.st_mtime_ns
        )
    except (OSError, ValueError) as exc:
        return result("external-single-frame", "failed", f"external frame failed: {type(exc).__name__}")
    return result(
        "external-single-frame",
        "passed" if passed else "failed",
        "one explicitly selected source-native frame was read and processed without hashing the source"
        if passed
        else "external single-frame validation failed",
    )


def check_packaging() -> dict[str, str]:
    deploy = shutil.which("pyside6-deploy")
    dumpbin = shutil.which("dumpbin")
    if not deploy or not dumpbin:
        return result(
            "windows-packaging",
            "skipped",
            "pyside6-deploy or MSVC dumpbin is unavailable; no dependency or compiler installation attempted",
        )
    return result(
        "windows-packaging",
        "passed",
        "pyside6-deploy and MSVC dumpbin are available; deployment spec is present",
    )


BASE_CHECKS: tuple[Callable[[], dict[str, str]], ...] = (
    check_runtime_dependencies,
    check_historical_evidence,
    check_golden_spectrum,
    check_ui_policy,
    check_visual_evidence,
)


def run_checks(external_frame_index: int | None = None) -> tuple[list[dict[str, str]], dict[str, object]]:
    checks: list[dict[str, str]] = []
    for check in BASE_CHECKS:
        try:
            checks.append(check())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            checks.append(result(check.__name__, "failed", f"check could not run: {type(exc).__name__}"))
    performance, observations = check_ui_performance()
    checks.append(performance)
    checks.append(check_external_frame(external_frame_index))
    checks.append(check_packaging())
    checks.append(check_required_files())
    checks.append(check_text_integrity())
    return checks, observations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-frame-index", type=int)
    args = parser.parse_args()
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "phase": "PHASE-02",
                "overall": "failed",
                "checks": [
                    result("verifier-completion", "failed", "verifier did not complete")
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    checks, observations = run_checks(args.external_frame_index)
    overall = "failed" if any(check["status"] == "failed" for check in checks) else "passed"
    payload = {
        "schema_version": 1,
        "phase": "PHASE-02",
        "overall": overall,
        "checks": checks,
    }
    SUMMARY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for check in checks:
        print(f"[{check['status'].upper()}] {check['id']}: {check['detail']}")
    if observations:
        print(
            "[MEASURED] recorded playback: "
            f"10 fps target={observations['fps10']} fps, "
            f"30 fps target={observations['fps30']} fps, "
            f"heartbeat gaps={observations['heartbeat_gap10_ms']}/{observations['heartbeat_gap30_ms']} ms, "
            f"max worker/pending={observations['max_concurrent_tasks']}/{observations['max_pending_intents']}, "
            f"waterfall rows={observations['waterfall_rows']}"
        )
    print(f"Verification summary written to {SUMMARY_PATH}")
    return 0 if overall == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
