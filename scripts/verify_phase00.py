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
    allowed = set(REQUIRED_FILES) | set(APPROVED_PHASE01_FILES)
    unexpected = sorted(_repository_files() - allowed)
    return _result(
        "minimal-file-tree",
        not unexpected,
        "repository contains the PHASE-00 baseline and approved PHASE-01 paths"
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
    current_phase_present = "**Mevcut faz: PHASE-" in text
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
        "mevcut faz **phase-01",
        "henüz dsp",
        "rf alma/verme",
    )
    missing = [value for value in required if value not in text]
    return _result(
        "readme-current-state",
        not missing,
        "README preserves the PHASE-00 baseline and unimplemented DSP/RF claims"
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
    allowed = set(APPROVED_PHASE01_FILES) | {
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
        "implementation directories contain only approved PHASE-01 additions"
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
