#!/usr/bin/env python3
"""Verify PHASE-03 detection, profile, bounded integration, and UI gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.detection import (  # noqa: E402
    ALLOWED_PFA_VALUES,
    DetectorConfig,
    LinearPowerDetector,
    ca_threshold_multiplier,
    os_threshold_multiplier,
    regional_threshold_multiplier,
)
from reference.detection.scenes import generate_scene, load_scene_catalog  # noqa: E402
from reference.pipeline import RuntimePipeline, canonical_profile_bytes, load_profile  # noqa: E402
from reference.spectrum import SigMFFrameSource, SpectrumProcessor  # noqa: E402


COMPARISON_PATH = ROOT / "results" / "evidence" / "phase03" / "detector-comparison.json"
PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
GOLDEN_PATH = ROOT / "results" / "evidence" / "phase03" / "golden-detection.json"
SUMMARY_PATH = ROOT / "results" / "evidence" / "phase03" / "verification-summary.json"
CATALOG_PATH = ROOT / "datasets" / "fixtures" / "phase03" / "detection-scenes.json"
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
FIXTURE_DATA = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-data"
EXTERNAL_METADATA_ENV = "PHASE01_EXTERNAL_METADATA"
EXTERNAL_DATA_ENV = "PHASE01_EXTERNAL_DATA"
HISTORICAL_PREFIXES = (
    "results/evidence/phase00/",
    "results/evidence/phase01/",
    "results/evidence/phase02/",
)
PHASE03_FILES = (
    "datasets/fixtures/phase03/detection-scenes.json",
    "docs/decisions/ADR-0004-ADAPTIVE-DETECTION.md",
    "docs/interfaces/DETECTION_CONTRACT.md",
    "docs/interfaces/PROCESSING_PROFILE_CONTRACT.md",
    "profiles/phase03/operation-default.json",
    "reference/detection/__init__.py",
    "reference/detection/cfar.py",
    "reference/detection/pipeline.py",
    "reference/detection/scenes.py",
    "reference/pipeline/__init__.py",
    "reference/pipeline/profile.py",
    "results/evidence/phase03/detector-comparison.json",
    "results/evidence/phase03/golden-detection.json",
    "results/evidence/phase03/screenshots/confirmed-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/confirmed-1920x1080-scale150.png",
    "results/evidence/phase03/screenshots/empty-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/error-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/noise-only-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/tentative-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/warning-1366x768-scale100.png",
    "results/evidence/phase03/verification-summary.json",
    "results/evidence/phase03/visual-summary.json",
    "scripts/render_phase03_ui.py",
    "scripts/select_phase03_profile.py",
    "scripts/verify_phase03.py",
    "tests/test_detection_reference.py",
    "tests/test_detection_statistics.py",
    "tests/test_operator_detection.py",
    "tests/test_phase03_selector.py",
    "tests/test_phase03_verifier.py",
    "tests/test_processing_profile.py",
)
PHASE03_SCREENSHOTS = tuple(name for name in PHASE03_FILES if name.endswith(".png"))
PHASE03_TEXT_FILES = tuple(name for name in PHASE03_FILES if not name.endswith(".png"))
APPROVED_WIDEBAND_GATES = {
    "minimum_coverage": 0.60,
    "minimum_iou": 0.50,
    "maximum_overreach": 0.25,
}


def _round(value: float) -> float:
    return round(float(value), 12)


def _check(identifier: str, status: str, detail: str) -> dict[str, str]:
    if status not in {"passed", "failed", "skipped"}:
        raise ValueError("invalid verification status")
    return {"id": identifier, "status": status, "detail": detail}


def _sha(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65_536), b""):
            digest.update(block)
    return digest.hexdigest()


def _historical_evidence_check() -> dict[str, str]:
    process = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "results/evidence/phase00", "results/evidence/phase01", "results/evidence/phase02"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if process.returncode != 0:
        return _check("historical-evidence", "failed", "HEAD evidence inventory could not be read")
    paths = [line for line in process.stdout.splitlines() if line.startswith(HISTORICAL_PREFIXES)]
    for relative in paths:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        path = ROOT / relative
        if blob.returncode != 0 or not path.is_file() or blob.stdout != path.read_bytes():
            return _check("historical-evidence", "failed", f"historical blob differs: {relative}")
    return _check("historical-evidence", "passed", f"{len(paths)} PHASE-00/01/02 evidence blobs match HEAD")


def _phase03_file_check() -> dict[str, str]:
    missing = [relative for relative in PHASE03_FILES if not (ROOT / relative).is_file()]
    return _check(
        "phase03-files",
        "passed" if not missing and len(PHASE03_FILES) == 31 else "failed",
        "all 31 approved PHASE-03 files are present" if not missing else "missing approved PHASE-03 files",
    )


def _text_integrity_check() -> dict[str, str]:
    failures: list[str] = []
    for relative in PHASE03_TEXT_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            failures.append(relative)
            continue
        if "\x00" in text or "\r" in text or (text and not text.endswith("\n")):
            failures.append(relative)
            continue
        if any(line.endswith((" ", "\t")) for line in text.split("\n")):
            failures.append(relative)
    sensitive_documents = (
        COMPARISON_PATH,
        PROFILE_PATH,
        GOLDEN_PATH,
        SUMMARY_PATH,
        ROOT / "results/evidence/phase03/visual-summary.json",
        ROOT / "docs/interfaces/DETECTION_CONTRACT.md",
        ROOT / "docs/interfaces/PROCESSING_PROFILE_CONTRACT.md",
        ROOT / "docs/decisions/ADR-0004-ADAPTIVE-DETECTION.md",
    )
    for path in sensitive_documents:
        if path.is_file() and "c:\\users" in path.read_text(encoding="utf-8").casefold():
            failures.append(path.relative_to(ROOT).as_posix())
    return _check(
        "phase03-text-integrity",
        "passed" if not failures else "failed",
        "PHASE-03 text is UTF-8/LF clean and evidence has no absolute user path"
        if not failures
        else "PHASE-03 text or path-integrity failure",
    )


def _visual_evidence_check() -> dict[str, str]:
    try:
        summary = json.loads((ROOT / "results/evidence/phase03/visual-summary.json").read_text(encoding="utf-8"))
        records = summary["screenshots"]
        passed = len(records) == 7 and all(
            all(value is True for value in record["checks"].values()) for record in records
        )
        passed = passed and all((ROOT / relative).is_file() for relative in PHASE03_SCREENSHOTS)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        passed = False
    return _check(
        "visual-evidence",
        "passed" if passed else "failed",
        "seven real pipeline UI states passed fixed visual checks" if passed else "visual evidence is incomplete",
    )


def _profile_and_comparison() -> tuple[dict[str, Any], dict[str, Any], str]:
    comparison = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))
    profile_document = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile = load_profile(PROFILE_PATH)
    selected = comparison.get("selected_detector")
    if comparison.get("overall") != "passed" or selected not in {"regional", "ca_cfar", "os_cfar", "os_regional_cap"}:
        raise ValueError("detector comparison has no eligible selected method")
    if profile.detector_method != selected:
        raise ValueError("comparison and operation profile detector differ")
    if PROFILE_PATH.read_bytes() != canonical_profile_bytes(profile):
        raise ValueError("operation profile is not canonical")
    runtime = RuntimePipeline(profile)
    if runtime.detector_method != selected:
        raise ValueError("runtime detector differs from the validated profile")
    return comparison, profile_document, str(selected)


def _wideband_contract_check(
    catalog_path: Path = CATALOG_PATH,
    comparison_path: Path = COMPARISON_PATH,
) -> dict[str, str]:
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        catalog_gates = catalog["evaluation_contract"]["wideband"]
        methods = comparison["methods"]
        evidence_gates = [
            {
                key: method["quality"]["wideband"][key]
                for key in APPROVED_WIDEBAND_GATES
            }
            for method in methods
        ]
        passed = (
            catalog_gates == APPROVED_WIDEBAND_GATES
            and bool(methods)
            and all(gates == APPROVED_WIDEBAND_GATES for gates in evidence_gates)
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        passed = False
    return _check(
        "wideband-acceptance-contract",
        "passed" if passed else "failed",
        "catalog and comparison use coverage 0.60, IoU 0.50, and overreach 0.25"
        if passed
        else "catalog or comparison differs from the approved wideband acceptance gates",
    )


def _golden_detection() -> tuple[dict[str, Any], bool]:
    comparison, profile_document, selected = _profile_and_comparison()
    profile = load_profile(PROFILE_PATH)
    source = SigMFFrameSource(FIXTURE_META)
    pipeline = RuntimePipeline(profile)
    outputs = []
    try:
        for index in range(source.frame_count):
            outputs.append(
                pipeline.process(
                    source.read_frame(index),
                    sample_rate_hz=source.sample_rate_hz,
                    center_frequency_hz=source.center_frequency_hz,
                    frame_index=index,
                )
            )
    finally:
        source.close()
    peak_bins = [int(np.argmax(item.spectrum.display.bin_power_fs2)) for item in outputs]
    containing_peak = [
        any(region.start_bin <= 2304 <= region.end_bin for region in item.detection.regions)
        for item in outputs
    ]
    cell_vectors_equal = all(
        np.array_equal(outputs[0].detection.cells.detected_mask, item.detection.cells.detected_mask)
        for item in outputs[1:]
    )

    catalog = load_scene_catalog()
    wide = generate_scene("wideband-noise-like", trial_index=0, catalog=catalog)
    spectrum = SpectrumProcessor().process(
        wide.samples,
        sample_rate_hz=float(catalog["common"]["sample_rate_hz"]),
        center_frequency_hz=float(catalog["common"]["center_frequency_hz"]),
    )
    truth = wide.ground_truth[0]
    expected_bins = np.arange(
        int(truth["shifted_start_bin"]), int(truth["shifted_end_bin"]) + 1
    )
    strongest = np.argpartition(spectrum.display.bin_power_fs2, -expected_bins.size)[-expected_bins.size :]
    shifted_roundtrip_overlap = float(np.intersect1d(strongest, expected_bins).size / expected_bins.size)

    include = LinearPowerDetector(DetectorConfig(method=selected, evaluate_center=True)).detect(
        np.ones(4096, dtype=np.float64)
    )
    exclude = LinearPowerDetector(DetectorConfig(method=selected, evaluate_center=False)).detect(
        np.ones(4096, dtype=np.float64)
    )
    coefficient_table = [
        {
            "pfa_per_cut": pfa,
            "regional_multiplier": _round(regional_threshold_multiplier(pfa)),
            "ca_multiplier": _round(ca_threshold_multiplier(pfa)),
            "os_multiplier": _round(os_threshold_multiplier(pfa)),
        }
        for pfa in ALLOWED_PFA_VALUES
    ]
    actual = {
        "selected_method": selected,
        "profile_sha256": hashlib.sha256(canonical_profile_bytes(profile)).hexdigest(),
        "comparison_sha256": hashlib.sha256(COMPARISON_PATH.read_bytes()).hexdigest(),
        "fixture_sha256": _sha(FIXTURE_DATA, "sha256"),
        "fixture_sha512": _sha(FIXTURE_DATA, "sha512"),
        "fixture_frame_count": len(outputs),
        "fixture_shifted_peak_bins": peak_bins,
        "fixture_peak_detected_per_frame": containing_peak,
        "fixture_cell_vectors_equal": cell_vectors_equal,
        "include_center_evaluated_cut_count": include.evaluated_count,
        "exclude_center_evaluated_cut_count": exclude.evaluated_count,
        "exclude_center_mask_value": bool(exclude.evaluated_mask[2048]),
        "wideband_shifted_roundtrip_overlap": _round(shifted_roundtrip_overlap),
        "all_outputs_finite": all(
            np.all(np.isfinite(item.spectrum.display.bin_power_fs2))
            and np.all(np.isfinite(item.detection.cells.threshold_power))
            and np.all(np.isfinite(item.detection.cells.noise_power))
            for item in outputs
        ),
    }
    expected = {
        "fixture_shifted_peak_bin": 2304,
        "include_center_evaluated_cut_count": 4056,
        "exclude_center_evaluated_cut_count": 4055,
        "minimum_wideband_shifted_roundtrip_overlap": 0.95,
    }
    passed = (
        comparison["coefficient_table"] == coefficient_table
        and len(outputs) == 4
        and peak_bins == [2304] * 4
        and containing_peak == [True] * 4
        and cell_vectors_equal
        and include.evaluated_count == 4056
        and exclude.evaluated_count == 4055
        and not exclude.evaluated_mask[2048]
        and shifted_roundtrip_overlap >= 0.95
        and actual["all_outputs_finite"]
    )
    return {
        "schema_version": 1,
        "phase": "PHASE-03",
        "coefficient_table": coefficient_table,
        "expected": expected,
        "tolerances": {"coefficient_absolute": 1e-10, "wideband_roundtrip_overlap_minimum": 0.95},
        "actual": actual,
    }, passed


def _external_integration(start_frame: int, frame_count: int) -> tuple[dict[str, str], dict[str, Any]]:
    metadata_value = os.environ.get(EXTERNAL_METADATA_ENV)
    data_value = os.environ.get(EXTERNAL_DATA_ENV)
    if not metadata_value and not data_value:
        return _check("external-ism-bounded", "skipped", "external metadata and data variables are not set"), {}
    if bool(metadata_value) != bool(data_value):
        return _check("external-ism-bounded", "failed", "external metadata and data variables must be set together"), {}
    if not 1 <= frame_count <= 4 or start_frame < 0:
        return _check("external-ism-bounded", "failed", "external frame range must use count 1-4 and a non-negative start"), {}
    source: SigMFFrameSource | None = None
    try:
        source = SigMFFrameSource(Path(metadata_value or ""), Path(data_value or ""), mode="explicit")
        before = (source.data_path.stat().st_size, source.data_path.stat().st_mtime_ns)
        if start_frame + frame_count > source.frame_count:
            raise ValueError("requested external frame range exceeds the source")

        def run_once() -> list[tuple[int, tuple[tuple[int, int, int], ...], str]]:
            pipeline = RuntimePipeline(load_profile(PROFILE_PATH))
            result: list[tuple[int, tuple[tuple[int, int, int], ...], str]] = []
            for offset in range(frame_count):
                index = start_frame + offset
                output = pipeline.process(
                    source.read_frame(index),
                    sample_rate_hz=source.sample_rate_hz,
                    center_frequency_hz=source.center_frequency_hz,
                    frame_index=index,
                )
                regions = tuple(
                    (region.start_bin, region.end_bin, region.peak_bin) for region in output.detection.regions
                )
                mask_digest = hashlib.sha256(output.detection.cells.detected_mask.tobytes()).hexdigest()
                result.append((index, regions, mask_digest))
            return result

        first = run_once()
        second = run_once()
        after = (source.data_path.stat().st_size, source.data_path.stat().st_mtime_ns)
        passed = first == second and before == after
        detail = {
            "frame_start": start_frame,
            "frame_count": frame_count,
            "datatype": source.report.source_datatype,
            "sample_rate_hz": source.sample_rate_hz,
            "center_frequency_hz": source.center_frequency_hz,
            "deterministic_output": first == second,
            "source_size_and_mtime_unchanged": before == after,
            "source_check_is_cryptographic": False,
            "full_source_hashed": False,
        }
        return _check(
            "external-ism-bounded",
            "passed" if passed else "failed",
            "bounded ci16_le frames processed deterministically" if passed else "bounded integration check failed",
        ), detail
    except Exception as exc:
        return _check("external-ism-bounded", "failed", f"bounded integration failed: {type(exc).__name__}"), {}
    finally:
        if source is not None:
            source.close()


def _performance_gate() -> tuple[dict[str, str], dict[str, float | int]]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QEventLoop, QTimer

        from host.operator_console.application import build_application, run_playback_benchmark

        app, window, controller = build_application([])
        controller.open_source(FIXTURE_META)
        deadline = time.perf_counter() + 5.0
        while (controller.active_task_count or controller.last_result is None) and time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(0.001)
        if controller.last_result is None:
            raise RuntimeError("fixture did not load")
        result10 = run_playback_benchmark(window, controller, target_fps=10, duration_seconds=2.2)
        result30 = run_playback_benchmark(window, controller, target_fps=30, duration_seconds=2.2)
        controller.close()
        QTimer.singleShot(0, app.quit)
        loop = QEventLoop()
        QTimer.singleShot(1, loop.quit)
        loop.exec()
        passed = (
            result10.achieved_fps >= 9.5
            and result10.maximum_heartbeat_gap_ms <= 200.0
            and result10.maximum_concurrent_tasks <= 1
            and result10.maximum_pending_intents <= 1
            and result10.active_tasks_after_stop == 0
            and result10.waterfall_rows <= 128
            and result30.maximum_concurrent_tasks <= 1
            and result30.maximum_pending_intents <= 1
        )
        measurements: dict[str, float | int] = {
            "fps10_achieved": round(result10.achieved_fps, 3),
            "fps10_heartbeat_max_ms": round(result10.maximum_heartbeat_gap_ms, 3),
            "fps30_characterization": round(result30.achieved_fps, 3),
            "max_concurrent_workers": max(result10.maximum_concurrent_tasks, result30.maximum_concurrent_tasks),
            "max_pending_intents": max(result10.maximum_pending_intents, result30.maximum_pending_intents),
        }
        return _check(
            "worker-performance",
            "passed" if passed else "failed",
            "10 FPS and bounded worker gate passed; 30 FPS characterized" if passed else "worker performance gate failed",
        ), measurements
    except Exception as exc:
        return _check("worker-performance", "failed", f"performance check failed: {type(exc).__name__}"), {}


def _summary(checks: list[dict[str, str]], external_detail: dict[str, Any]) -> dict[str, Any]:
    mandatory_failed = any(item["status"] == "failed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-03",
        "overall": "failed" if mandatory_failed else "passed",
        "checks": checks,
        "external_integration": external_detail,
        "determinism": {
            "absolute_paths_present": False,
            "dynamic_timing_values_recorded": False,
        },
    }


def _canonical(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PHASE-03 tespit ve profil doğrulayıcısı")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="PHASE-03 verifier evidence dosyalarını kur")
    mode.add_argument("--check", action="store_true", help="evidence dosyalarını değiştirmeden doğrula")
    parser.add_argument("--external-start-frame", type=int, default=0)
    parser.add_argument("--external-frame-count", type=int, default=4)
    args = parser.parse_args(argv)

    checks: list[dict[str, str]] = []
    comparison: dict[str, Any] = {}
    profile_error = "comparison mismatch"
    try:
        comparison, _, selected = _profile_and_comparison()
        profile_ok = comparison.get("selected_detector") == selected
    except Exception as exc:
        profile_ok = False
        selected = "unavailable"
        profile_error = type(exc).__name__
    checks.append(
        _check(
            "profile-comparison-runtime",
            "passed" if profile_ok else "failed",
            f"selected detector {selected} matches comparison, profile, and runtime"
            if profile_ok
            else f"profile consistency failed: {profile_error}",
        )
    )
    checks.append(_wideband_contract_check())
    checks.append(_phase03_file_check())
    try:
        golden, golden_ok = _golden_detection()
    except Exception as exc:
        golden = {"schema_version": 1, "phase": "PHASE-03", "error": type(exc).__name__}
        golden_ok = False
    checks.append(
        _check(
            "golden-detection",
            "passed" if golden_ok else "failed",
            "fixture, coefficients, center mask, and shifted-scene gates passed"
            if golden_ok
            else "golden detection gate failed",
        )
    )
    checks.append(_historical_evidence_check())
    checks.append(_text_integrity_check())
    checks.append(_visual_evidence_check())
    external_check, external_detail = _external_integration(
        args.external_start_frame, args.external_frame_count
    )
    checks.append(external_check)
    performance_check, measurements = _performance_gate()
    checks.append(performance_check)
    checks.append(
        _check(
            "detector-selection",
            "passed" if profile_ok and comparison.get("overall") == "passed" else "failed",
            "all mandatory gates and predetermined selection rule were applied",
        )
    )
    summary = _summary(checks, external_detail)

    if args.write:
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_bytes(_canonical(golden))
        SUMMARY_PATH.write_bytes(_canonical(summary))
    else:
        for path, expected in ((GOLDEN_PATH, golden), (SUMMARY_PATH, None)):
            if not path.is_file():
                checks.append(_check("tracked-evidence", "failed", f"missing: {path.name}"))
                summary["overall"] = "failed"
                break
            if expected is not None and path.read_bytes() != _canonical(expected):
                checks.append(_check("tracked-evidence", "failed", f"content mismatch: {path.name}"))
                summary["overall"] = "failed"
                break
        try:
            stored_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
            if stored_summary.get("overall") != "passed" or any(
                item.get("status") not in {"passed", "failed", "skipped"}
                for item in stored_summary.get("checks", [])
            ):
                summary["overall"] = "failed"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            summary["overall"] = "failed"

    print(f"PHASE-03 verification: {summary['overall']}; selected={selected}")
    if external_check["status"] != "skipped":
        print(f"External integration: {external_check['status']}")
    else:
        print("External integration: skipped")
    if measurements:
        print(
            "Performance: "
            f"10 FPS={measurements['fps10_achieved']}, "
            f"heartbeat={measurements['fps10_heartbeat_max_ms']} ms, "
            f"30 FPS={measurements['fps30_characterization']}"
        )
    return 0 if summary["overall"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
