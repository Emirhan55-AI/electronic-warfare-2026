#!/usr/bin/env python3
"""Verify the PHASE-00 repository contract using only the standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "evidence" / "phase00" / "verification-summary.json"

REQUIRED_FILES = (
    ".editorconfig",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "datasets/README.md",
    "docs/architecture/SYSTEM_BASELINE.md",
    "docs/decisions/ADR-0001-REFERENCE-HARDWARE.md",
    "docs/plans/IMPLEMENTATION_ROADMAP.md",
    "docs/requirements/KTR_TRACEABILITY.md",
    "docs/safety/RF_TEST_BOUNDARIES.md",
    "host/README.md",
    "reference/README.md",
    "results/evidence/phase00/toolchain.json",
    "results/evidence/phase00/verification-summary.json",
    "rtl/README.md",
    "scripts/phase00_doctor.py",
    "scripts/verify_phase00.py",
    "tests/test_repository_contract.py",
    "verification/README.md",
)

# PHASE-00 remains a historical baseline. Later files are permitted only when
# their paths were explicitly approved by the next phase plan.
APPROVED_PHASE01_FILES = (
    "datasets/external/README.md",
    "datasets/fixtures/phase01/README.md",
    "datasets/fixtures/phase01/known-tone-ci8.sigmf-data",
    "datasets/fixtures/phase01/known-tone-ci8.sigmf-meta",
    "docs/decisions/ADR-0002-SIGMF-DATA-PROFILES.md",
    "docs/interfaces/SIGMF_INPUT_CONTRACT.md",
    "reference/sigmf/__init__.py",
    "reference/sigmf/contract.py",
    "results/evidence/phase01/external-dataset-manifest.example.json",
    "results/evidence/phase01/fixture-manifest.json",
    "results/evidence/phase01/verification-summary.json",
    "scripts/extract_external_sigmf_slice.py",
    "scripts/generate_phase01_fixture.py",
    "scripts/verify_phase01.py",
    "tests/test_external_sigmf_integration.py",
    "tests/test_phase01_fixture.py",
    "tests/test_sigmf_contract.py",
)

APPROVED_PHASE02_FILES = (
    "docs/decisions/ADR-0003-OPERATOR-APPLICATION-STACK.md",
    "docs/interfaces/SPECTRUM_REFERENCE_CONTRACT.md",
    "host/operator_console/__init__.py",
    "host/operator_console/__main__.py",
    "host/operator_console/application.py",
    "host/operator_console/controller.py",
    "host/operator_console/main_window.py",
    "host/operator_console/pysidedeploy.spec",
    "host/operator_console/spectrum_view.py",
    "host/operator_console/theme.qss",
    "host/operator_console/ui_text.py",
    "reference/spectrum/__init__.py",
    "reference/spectrum/dsp.py",
    "reference/spectrum/source.py",
    "requirements/phase02.txt",
    "results/evidence/phase02/golden-spectrum.json",
    "results/evidence/phase02/screenshots/empty-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/error-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1920x1080-scale150.png",
    "results/evidence/phase02/screenshots/warning-1366x768-scale100.png",
    "results/evidence/phase02/verification-summary.json",
    "results/evidence/phase02/visual-summary.json",
    "scripts/render_phase02_ui.py",
    "scripts/verify_phase02.py",
    "tests/test_operator_console.py",
    "tests/test_phase02_verifier.py",
    "tests/test_sigmf_frame_source.py",
    "tests/test_spectrum_reference.py",
)

APPROVED_PHASE03_FILES = (
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

APPROVED_PHASE04_BASE_FILES = (
    "datasets/fixtures/phase04/parameter-scenes.json",
    "datasets/fixtures/phase04/r2-method-lock.json",
    "docs/decisions/ADR-0005-CORE-PARAMETER-EXTRACTION.md",
    "docs/decisions/ADR-0006-PHASE04-R2-BAND-RECOVERY.md",
    "docs/interfaces/PARAMETER_EXTRACTION_CONTRACT.md",
    "reference/parameters/__init__.py",
    "reference/parameters/models.py",
    "reference/parameters/extraction.py",
    "reference/parameters/classification.py",
    "reference/parameters/scenes.py",
    "reference/parameters/evaluation.py",
    "reference/parameters/r2.py",
    "scripts/select_phase04_profile.py",
    "scripts/select_phase04_r2_profile.py",
    "scripts/diagnose_phase04_r2.py",
    "scripts/characterize_phase04_r2_oos.py",
    "scripts/verify_phase04_r2.py",
    "scripts/verify_phase04.py",
    "scripts/render_phase04_ui.py",
    "tests/test_parameter_reference.py",
    "tests/test_parameter_scenes.py",
    "tests/test_parameter_statistics.py",
    "tests/test_phase04_selector.py",
    "tests/test_phase04_verifier.py",
    "tests/test_phase04_r2_diagnostics.py",
    "tests/test_phase04_r2_reference.py",
    "tests/test_phase04_r2_selector.py",
    "tests/test_phase04_r2_verifier.py",
    "tests/test_operator_parameters.py",
    "results/evidence/phase04/parameter-comparison.json",
    "results/evidence/phase04/golden-parameters.json",
    "results/evidence/phase04/verification-summary.json",
    "results/evidence/phase04/r2-family-diagnostic.json",
    "results/evidence/phase04/r2-parameter-comparison.json",
    "results/evidence/phase04/r2-out-of-sample.json",
    "results/evidence/phase04/r2-golden-parameters.json",
    "results/evidence/phase04/r2-verification-summary.json",
)

PHASE04_SUCCESS_ONLY_FILES = (
    "profiles/phase04/operation-default.json",
    "results/evidence/phase04/visual-summary.json",
    "results/evidence/phase04/empty-1366x768-scale100.png",
    "results/evidence/phase04/parameters-valid-1366x768-scale100.png",
    "results/evidence/phase04/carrier-unavailable-1366x768-scale100.png",
    "results/evidence/phase04/classification-uncertain-1366x768-scale100.png",
    "results/evidence/phase04/warning-1366x768-scale100.png",
    "results/evidence/phase04/error-1366x768-scale100.png",
    "results/evidence/phase04/parameters-valid-1920x1080-scale150.png",
)

APPROVED_PHASE04_D1_FILES = (
    "datasets/fixtures/phase04d1/acceptance-gates.json",
    "datasets/fixtures/phase04d1/clean-reference.json",
    "datasets/fixtures/phase04d1/evaluation-lock.json",
    "datasets/fixtures/phase04d1/method-lock.json",
    "datasets/fixtures/phase04d1/obw99-scenes.json",
    "datasets/fixtures/phase04d1/reference-contract.json",
    "docs/decisions/ADR-0007-OCCUPIED-BANDWIDTH-SEMANTICS.md",
    "docs/interfaces/OCCUPIED_BANDWIDTH_CONTRACT.md",
    "reference/parameters/obw99.py",
    "reference/parameters/obw99_evaluation.py",
    "reference/parameters/obw99_reference.py",
    "scripts/generate_phase04d1_reference.py",
    "scripts/lock_phase04d1_evaluation.py",
    "scripts/lock_phase04d1_method.py",
    "scripts/run_phase04d1_evaluation.py",
    "scripts/verify_phase04d1.py",
    "results/evidence/phase04d1/golden-obw99.json",
    "results/evidence/phase04d1/obw99-binding-results.json",
    "results/evidence/phase04d1/obw99-comparison.json",
    "results/evidence/phase04d1/obw99-oos-results.json",
    "results/evidence/phase04d1/verification-summary.json",
    "tests/test_phase04d1_evaluation.py",
    "tests/test_phase04d1_estimator.py",
    "tests/test_phase04d1_method_lock.py",
    "tests/test_phase04d1_reference.py",
    "tests/test_phase04d1_verifier.py",
)

APPROVED_PHASE04_E1_FILES = (
    "datasets/fixtures/phase04e1/acceptance-gates.json",
    "datasets/fixtures/phase04e1/operator-scenes.json",
    "datasets/fixtures/phase04e1/method-lock.json",
    "docs/decisions/ADR-0008-OPERATOR-ASSISTED-PARAMETERS.md",
    "docs/interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md",
    "reference/parameters/operator_assisted.py",
    "reference/parameters/operator_classification.py",
    "reference/parameters/operator_evaluation.py",
    "reference/parameters/operator_reference.py",
    "scripts/generate_phase04e1_reference.py",
    "scripts/lock_phase04e1_method.py",
    "scripts/run_phase04e1_evaluation.py",
    "scripts/verify_phase04e1.py",
    "scripts/render_phase04e1_ui.py",
    "tests/test_phase04e1_algorithms.py",
    "tests/test_phase04e1_evaluation.py",
    "tests/test_phase04e1_profile.py",
    "tests/test_operator_analysis.py",
    "tests/test_phase04e1_verifier.py",
    "results/evidence/phase04e1/golden-parameters.json",
    "results/evidence/phase04e1/binding-results.json",
    "results/evidence/phase04e1/oos-results.json",
    "results/evidence/phase04e1/parameter-comparison.json",
    "results/evidence/phase04e1/verification-summary.json",
    "results/evidence/phase04e1/visual-summary.json",
    "results/evidence/phase04e1/invalid-protocol-run1/binding-results.json",
    "results/evidence/phase04e1/invalid-protocol-run1/oos-results.json",
    "results/evidence/phase04e1/invalid-protocol-run1/parameter-comparison.json",
    "results/evidence/phase04e1/invalid-protocol-run1/golden-parameters.json",
    "results/evidence/phase04e1/invalid-protocol-run1/verification-summary.json",
    "results/evidence/phase04e1/invalid-protocol-run1/method-lock.json",
    "results/evidence/phase04e1/invalid-protocol-run1/invalid-run-manifest.json",
    "results/evidence/phase04e1/empty-1280x720.png",
    "results/evidence/phase04e1/loading-1366x768.png",
    "results/evidence/phase04e1/no-detection-1920x1080.png",
    "results/evidence/phase04e1/tentative-1366x768.png",
    "results/evidence/phase04e1/confirmed-selected-1366x768.png",
    "results/evidence/phase04e1/auto-span-1280x720.png",
    "results/evidence/phase04e1/operator-span-1366x768.png",
    "results/evidence/phase04e1/fields-disabled-1920x1080.png",
    "results/evidence/phase04e1/validation-unavailable-1366x768.png",
    "results/evidence/phase04e1/uncertain-1366x768.png",
    "results/evidence/phase04e1/unmeasured-1280x720.png",
    "results/evidence/phase04e1/warning-1366x768.png",
    "results/evidence/phase04e1/error-1366x768.png",
    "results/evidence/phase04e1/multiple-events-1920x1080.png",
    "results/evidence/phase04e1/scale150-1920x1080.png",
)

PHASE04_E1_SUCCESS_ONLY_FILES = (
    "profiles/phase04e1/operation-default.json",
)

APPROVED_PHASE04_FILES = (
    APPROVED_PHASE04_BASE_FILES
    + PHASE04_SUCCESS_ONLY_FILES
    + APPROVED_PHASE04_D1_FILES
    + APPROVED_PHASE04_E1_FILES
    + PHASE04_E1_SUCCESS_ONLY_FILES
)

APPROVED_PHASE08A_FILES = (
    "docs/decisions/ADR-0009-HACKRF-RX-HOST-PREPARATION.md",
    "docs/interfaces/HACKRF_RX_HOST_CONTRACT.md",
    "host/acquisition/__init__.py",
    "host/acquisition/contracts.py",
    "host/acquisition/hackrf.py",
    "host/acquisition/process.py",
    "host/acquisition/source.py",
    "scripts/render_phase08a_ui.py",
    "scripts/verify_phase08a.py",
    "tests/test_hackrf_acquisition.py",
    "tests/test_operator_hackrf.py",
    "tests/test_phase08a_verifier.py",
    "results/evidence/phase08a/verification-summary.json",
    "results/evidence/phase08a/visual-summary.json",
    "results/evidence/phase08a/tools-missing-1366x768.png",
    "results/evidence/phase08a/device-missing-1366x768.png",
    "results/evidence/phase08a/deterministic-source-1366x768.png",
    "results/evidence/phase08a/cli-error-1366x768.png",
    "results/evidence/phase08a/tools-missing-1920x1080-scale150.png",
)

APPROVED_PHASE05_FILES = (
    "datasets/fixtures/phase05/am-tone-ci8.sigmf-data",
    "datasets/fixtures/phase05/am-tone-ci8.sigmf-meta",
    "datasets/fixtures/phase05/fixture-manifest.json",
    "datasets/fixtures/phase05/nfm-tone-ci8.sigmf-data",
    "datasets/fixtures/phase05/nfm-tone-ci8.sigmf-meta",
    "datasets/fixtures/phase05/noise-only-ci8.sigmf-data",
    "datasets/fixtures/phase05/noise-only-ci8.sigmf-meta",
    "docs/decisions/ADR-0010-RECORDED-ANALOG-MONITORING.md",
    "docs/interfaces/ANALOG_MONITORING_CONTRACT.md",
    "host/operator_console/audio_playback.py",
    "reference/monitoring/__init__.py",
    "reference/monitoring/dsp.py",
    "reference/monitoring/evaluation.py",
    "reference/monitoring/fixtures.py",
    "reference/monitoring/models.py",
    "results/evidence/phase05/am-ready-1366x768.png",
    "results/evidence/phase05/am-ready-1920x1080-scale150.png",
    "results/evidence/phase05/audio-unavailable-1366x768.png",
    "results/evidence/phase05/fixture-manifest.json",
    "results/evidence/phase05/golden-monitoring.json",
    "results/evidence/phase05/nfm-ready-1366x768.png",
    "results/evidence/phase05/noise-no-event-1366x768.png",
    "results/evidence/phase05/no-source-1280x720.png",
    "results/evidence/phase05/verification-summary.json",
    "results/evidence/phase05/visual-summary.json",
    "scripts/generate_phase05_fixtures.py",
    "scripts/render_phase05_ui.py",
    "scripts/verify_phase05.py",
    "tests/test_operator_listening.py",
    "tests/test_phase05_fixtures.py",
    "tests/test_phase05_monitoring.py",
    "tests/test_phase05_verifier.py",
)

EXPECTED_TOOLS = (
    "Git",
    "Python",
    "NumPy",
    "SciPy",
    "pytest",
    "CMake",
    "Ninja",
    "C/C++ compiler",
    "Qt",
    "GHDL",
    "VUnit",
    "Verilator",
    "Icarus Verilog",
    "Vivado",
    "XSim",
    "HackRF command-line tools",
)


def _result(identifier: str, passed: bool, detail: str) -> dict[str, object]:
    return {"id": identifier, "status": "passed" if passed else "failed", "detail": detail}


def check_required_files() -> dict[str, object]:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    return _result(
        "required-files",
        not missing,
        "all required files are present" if not missing else "missing: " + ", ".join(missing),
    )


def _repository_files() -> set[str]:
    files: set[str] = set()
    skipped_directories = {".git", "__pycache__", ".pytest_cache"}
    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if any(part in skipped_directories for part in relative_parts):
            continue
        if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
            files.add(path.relative_to(ROOT).as_posix())
    return files


def check_allowed_tree() -> dict[str, object]:
    allowed = (
        set(REQUIRED_FILES)
        | set(APPROVED_PHASE01_FILES)
        | set(APPROVED_PHASE02_FILES)
        | set(APPROVED_PHASE03_FILES)
        | set(APPROVED_PHASE04_FILES)
        | set(APPROVED_PHASE08A_FILES)
        | set(APPROVED_PHASE05_FILES)
    )
    unexpected = sorted(_repository_files() - allowed)
    return _result(
        "minimal-file-tree",
        not unexpected,
        "repository contains the PHASE-00 baseline and approved later-phase paths"
        if not unexpected
        else "unexpected files: " + ", ".join(unexpected),
    )


def check_text_integrity() -> dict[str, object]:
    problems: list[str] = []
    for relative in REQUIRED_FILES:
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
    return _result(
        "text-integrity",
        not problems,
        "all PHASE-00 text files are valid UTF-8 with LF endings and no trailing whitespace"
        if not problems
        else "; ".join(problems),
    )


def check_adr() -> dict[str, object]:
    text = (ROOT / "docs/decisions/ADR-0001-REFERENCE-HARDWARE.md").read_text(encoding="utf-8")
    required = (
        "Accepted",
        "2× HackRF One",
        "ZedBoard Zynq-7000",
        "Laptop",
        "MUSIC",
        "PA",
        "yüksek güçlü ET",
    )
    missing = [value for value in required if value.casefold() not in text.casefold()]
    return _result(
        "reference-hardware-adr",
        not missing,
        "accepted reference hardware decision and limitations are documented"
        if not missing
        else "ADR missing: " + ", ".join(missing),
    )


def check_ktr_traceability() -> dict[str, object]:
    text = (ROOT / "docs/requirements/KTR_TRACEABILITY.md").read_text(encoding="utf-8")
    identifiers = tuple(f"KTR-{item}" for item in ("4.1", "4.2", "4.3", "4.4", "4.5", "5.1", "5.2", "5.3", "5.4", "6"))
    missing = [identifier for identifier in identifiers if f"| {identifier} |" not in text]
    completed = re.findall(r"\|\s*(?:Tamamlandı|Doğrulandı)\s*\|", text, flags=re.IGNORECASE)
    passed = not missing and not completed
    detail = "all required KTR rows are present and remain planned/not implemented"
    if missing:
        detail = "missing KTR rows: " + ", ".join(missing)
    elif completed:
        detail = "KTR rows must not claim completion"
    return _result("ktr-traceability", passed, detail)


def check_roadmap() -> dict[str, object]:
    text = (ROOT / "docs/plans/IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
    phase_positions = [text.find(f"| PHASE-{number:02d} |") for number in range(14)]
    ordered = all(position >= 0 for position in phase_positions) and phase_positions == sorted(phase_positions)
    baseline_present = "| PHASE-00 | Repository ve mühendislik temeli |" in text
    current_phase_present = "**Mevcut ana açık fazlar: PHASE-04 ve PHASE-05**" in text
    return _result(
        "phase-roadmap",
        ordered and baseline_present and current_phase_present,
        "roadmap retains the PHASE-00 baseline and preserves PHASE-00 through PHASE-13 order"
        if ordered and baseline_present and current_phase_present
        else "roadmap phase order, baseline, or current-phase marker is invalid",
    )


def check_readme_truthfulness() -> dict[str, object]:
    text = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
    required = (
        "phase-00 repository temelini kurmuştur",
        "phase-04 parametre doğrulaması açık kalırken",
        "phase-05 — sinyal izleme ve analog dinleme",
        "gerçek cihaz, canlı i/q ve canlı analog dinleme henüz çalıştırılmamış",
        "rf yayın",
    )
    missing = [value for value in required if value not in text]
    return _result(
        "readme-current-state",
        not missing,
        "README preserves the baseline and truthful PHASE-04/05/RF claims"
        if not missing
        else "README lacks explicit current-state markers: " + ", ".join(missing),
    )


def check_rf_boundaries() -> dict[str, object]:
    text = (ROOT / "docs/safety/RF_TEST_BOUNDARIES.md").read_text(encoding="utf-8").casefold()
    required = (
        "phase-00 kapsamında rf yayını yoktur",
        "antene bağlı kontrolsüz tx testi yapılmaz",
        "gnss aldatma",
        "pa bulunmadığından",
        "hackrf-2 bu aşamada kullanılmaz",
        "tx kodu eklenmez",
    )
    missing = [value for value in required if value not in text]
    return _result(
        "rf-test-boundaries",
        not missing,
        "all mandatory PHASE-00 RF safety boundaries are documented"
        if not missing
        else "RF boundary text missing: " + ", ".join(missing),
    )


def check_no_future_sources() -> dict[str, object]:
    implementation_directories = ("rtl", "reference", "verification", "host", "datasets")
    allowed = set(APPROVED_PHASE01_FILES) | set(APPROVED_PHASE02_FILES) | set(APPROVED_PHASE03_FILES) | set(APPROVED_PHASE04_FILES) | set(APPROVED_PHASE08A_FILES) | set(APPROVED_PHASE05_FILES) | {
        "rtl/README.md",
        "reference/README.md",
        "verification/README.md",
        "host/README.md",
        "datasets/README.md",
    }
    unexpected: list[str] = []
    for directory in implementation_directories:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file():
                relative = path.relative_to(ROOT).as_posix()
                if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                    continue
                if relative not in allowed:
                    unexpected.append(relative)
    return _result(
        "no-future-phase-sources",
        not unexpected,
        "implementation directories contain only approved later-phase additions"
        if not unexpected
        else "future-phase files found: " + ", ".join(sorted(unexpected)),
    )


def check_toolchain_inventory() -> dict[str, object]:
    path = ROOT / "results/evidence/phase00/toolchain.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _result("toolchain-inventory", False, f"inventory cannot be read: {type(exc).__name__}: {exc}")

    tools = payload.get("tools")
    if not isinstance(tools, list):
        return _result("toolchain-inventory", False, "tools must be a list")
    names = tuple(tool.get("name") for tool in tools if isinstance(tool, dict))
    if names != EXPECTED_TOOLS:
        return _result("toolchain-inventory", False, "inventory entries are missing, extra, or out of order")

    allowed_statuses = {"available", "unavailable", "unknown"}
    problems: list[str] = []
    for tool in tools:
        status = tool.get("status")
        evidence = tool.get("evidence")
        if status not in allowed_statuses:
            problems.append(f"{tool.get('name')}: invalid status {status!r}")
        if not isinstance(evidence, str) or not evidence.strip():
            problems.append(f"{tool.get('name')}: missing evidence")
        if status == "available" and not (
            isinstance(evidence, str)
            and (evidence.startswith("executable: ") or evidence.startswith("python-module: "))
        ):
            problems.append(f"{tool.get('name')}: available status lacks detection evidence")
        if status == "unknown" and "failed" not in str(evidence).casefold():
            problems.append(f"{tool.get('name')}: unknown status lacks a reason")

    return _result(
        "toolchain-inventory",
        not problems,
        "all toolchain entries have valid statuses and detection evidence; unavailable/unknown are informational"
        if not problems
        else "; ".join(problems),
    )


CHECKS: tuple[Callable[[], dict[str, object]], ...] = (
    check_required_files,
    check_allowed_tree,
    check_text_integrity,
    check_adr,
    check_ktr_traceability,
    check_roadmap,
    check_readme_truthfulness,
    check_rf_boundaries,
    check_no_future_sources,
    check_toolchain_inventory,
)


def run_checks() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for check in CHECKS:
        try:
            results.append(check())
        except (OSError, UnicodeDecodeError) as exc:
            results.append(_result(check.__name__, False, f"check could not run: {type(exc).__name__}: {exc}"))
    return results


def main() -> int:
    checks = run_checks()
    passed = all(check["status"] == "passed" for check in checks)
    payload = {
        "schema_version": 1,
        "phase": "PHASE-00",
        "overall": "passed" if passed else "failed",
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for check in checks:
        print(f"[{check['status'].upper()}] {check['id']}: {check['detail']}")
    print(f"Verification summary written to {SUMMARY}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
