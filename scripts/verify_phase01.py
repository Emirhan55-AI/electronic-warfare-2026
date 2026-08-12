#!/usr/bin/env python3
"""Verify the deterministic PHASE-01 repository and optional external dataset."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase01_fixture import check_outputs, serialized_outputs  # noqa: E402
from reference.sigmf.contract import inspect_sigmf  # noqa: E402


SUMMARY_PATH = ROOT / "results" / "evidence" / "phase01" / "verification-summary.json"
EXTERNAL_METADATA_ENV = "PHASE01_EXTERNAL_METADATA"
EXTERNAL_DATA_ENV = "PHASE01_EXTERNAL_DATA"

PHASE01_FILES = (
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

PHASE01_UPDATED_TEXT_FILES = (
    ".gitignore",
    "README.md",
    "datasets/README.md",
    "docs/plans/IMPLEMENTATION_ROADMAP.md",
    "docs/requirements/KTR_TRACEABILITY.md",
    "reference/README.md",
    "scripts/verify_phase00.py",
    "tests/test_repository_contract.py",
    "verification/README.md",
)


def result(identifier: str, status: str, detail: str) -> dict[str, str]:
    if status not in {"passed", "failed", "skipped"}:
        raise ValueError(f"invalid verification status: {status}")
    return {"id": identifier, "status": status, "detail": detail}


def check_required_files() -> dict[str, str]:
    missing = [name for name in PHASE01_FILES if not (ROOT / name).is_file()]
    return result(
        "required-files",
        "passed" if not missing else "failed",
        "all approved PHASE-01 files are present" if not missing else "missing: " + ", ".join(missing),
    )


def check_fixture_determinism() -> dict[str, str]:
    failures = check_outputs(serialized_outputs())
    return result(
        "fixture-determinism",
        "passed" if not failures else "failed",
        "golden fixture metadata, data, and hashes are byte-for-byte deterministic"
        if not failures
        else "; ".join(failures),
    )


def check_text_integrity() -> dict[str, str]:
    problems: list[str] = []
    text_files = [name for name in PHASE01_FILES if name != "datasets/fixtures/phase01/known-tone-ci8.sigmf-data"]
    text_files.extend(PHASE01_UPDATED_TEXT_FILES)
    for relative in text_files:
        data = (ROOT / relative).read_bytes()
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
        "all PHASE-01 text files are valid UTF-8 with LF endings and no trailing whitespace"
        if not problems
        else "; ".join(problems),
    )


def check_fixture_contract() -> dict[str, str]:
    fixture_metadata = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
    report = inspect_sigmf(fixture_metadata, mode="standard")
    expected = (
        report.valid
        and report.source_datatype == "ci8"
        and report.sample_rate == 8_000_000
        and report.center_frequency == 100_000_000
        and report.total_complex_samples == 16_384
        and report.full_frame_count == 4
        and report.dropped_complex_samples == 0
        and report.frequency_bin_spacing_hz == 1953.125
    )
    return result(
        "fixture-contract",
        "passed" if expected else "failed",
        "golden fixture satisfies the canonical ci8 interchange contract"
        if expected
        else "golden fixture contract values are invalid",
    )


def check_standard_library_only() -> dict[str, str]:
    files = (
        ROOT / "reference" / "sigmf" / "contract.py",
        ROOT / "scripts" / "generate_phase01_fixture.py",
        ROOT / "scripts" / "extract_external_sigmf_slice.py",
        ROOT / "scripts" / "verify_phase01.py",
    )
    forbidden = {"numpy", "scipy", "pytest", "pandas"}
    hits: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module.split(".")[0]]
            else:
                modules = []
            for module in modules:
                if module in forbidden:
                    hits.append(f"{path.name}: {module}")
    return result(
        "standard-library-only",
        "passed" if not hits else "failed",
        "PHASE-01 implementation has no third-party runtime dependency"
        if not hits
        else "forbidden imports: " + ", ".join(hits),
    )


def check_documentation_policy() -> dict[str, str]:
    contract = (ROOT / "docs" / "interfaces" / "SIGMF_INPUT_CONTRACT.md").read_text(encoding="utf-8")
    adr = (ROOT / "docs" / "decisions" / "ADR-0002-SIGMF-DATA-PROFILES.md").read_text(encoding="utf-8")
    required = (
        "HackRF/PC giriş, kayıt ve sistemler arası değişim biçimi",
        "PL iç veri biçimi",
        "KTR teknik parametrelerin bağlayıcı kaynağı değildir",
        "56 MS/s",
        "license_status: unverified",
    )
    combined = contract + "\n" + adr
    missing = [phrase for phrase in required if phrase not in combined]
    forbidden_claims = ("KTR 56 MHz uyumluluğu", "KTR performans hedefini karşılar")
    forbidden_hits = [phrase for phrase in forbidden_claims if phrase in combined]
    passed = not missing and not forbidden_hits
    detail = "data profiles, PL boundary, KTR role, and external-license policy are documented"
    if missing:
        detail = "missing policy text: " + ", ".join(missing)
    elif forbidden_hits:
        detail = "forbidden performance claim: " + ", ".join(forbidden_hits)
    return result("documentation-policy", "passed" if passed else "failed", detail)


def external_environment() -> tuple[str | None, str | None, dict[str, str]]:
    metadata_value = os.environ.get(EXTERNAL_METADATA_ENV)
    data_value = os.environ.get(EXTERNAL_DATA_ENV)
    if bool(metadata_value) != bool(data_value):
        missing = EXTERNAL_DATA_ENV if metadata_value else EXTERNAL_METADATA_ENV
        return metadata_value, data_value, result(
            "external-dataset-configuration",
            "failed",
            f"both external dataset variables are required; missing {missing}",
        )
    return metadata_value, data_value, result(
        "external-dataset-configuration",
        "passed",
        "external dataset variables are paired" if metadata_value else "external dataset variables are not set",
    )


def check_external_integration(metadata_value: str | None, data_value: str | None) -> dict[str, str]:
    if not metadata_value and not data_value:
        return result("external-dataset-integration", "skipped", "external dataset unavailable")
    assert metadata_value is not None and data_value is not None
    metadata_path = Path(metadata_value)
    data_path = Path(data_value)
    try:
        before = data_path.stat()
        report = inspect_sigmf(metadata_path, data_path, mode="explicit")
        if not report.valid:
            return result(
                "external-dataset-integration",
                "failed",
                "external contract errors: " + ", ".join(issue.code for issue in report.errors),
            )
        expected = (
            report.source_datatype == "ci16_le"
            and report.sample_rate == 56_000_000
            and report.center_frequency == 2_430_000_000
            and report.channel_count == 1
            and report.channel_count_source == "defaulted"
            and report.total_complex_samples == 2_828_312_576
            and report.full_frame_count == 690_506
            and report.dropped_complex_samples == 0
        )
        with data_path.open("rb") as source:
            slice_data = source.read(65_536)
        first_hash = hashlib.sha256(slice_data).hexdigest()
        with data_path.open("rb") as source:
            repeat_data = source.read(65_536)
        repeat_hash = hashlib.sha256(repeat_data).hexdigest()
        after = data_path.stat()
        unchanged = before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
        expected = expected and len(slice_data) == 65_536 and first_hash == repeat_hash and unchanged
    except OSError as exc:
        return result(
            "external-dataset-integration",
            "failed",
            f"external dataset could not be inspected: {type(exc).__name__}",
        )
    return result(
        "external-dataset-integration",
        "passed" if expected else "failed",
        "external ism_band_24 metadata, 690506 source-native frames, and deterministic 65536-byte read passed"
        if expected
        else "external dataset values or source stability check failed",
    )


def check_external_git_policy() -> dict[str, str]:
    command = subprocess.run(
        ["git", "ls-files", "--", "datasets/external"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if command.returncode != 0:
        return result("external-git-policy", "failed", "git index inspection failed")
    tracked = [line for line in command.stdout.splitlines() if line]
    allowed = {
        "datasets/external/README.md",
        "results/evidence/phase01/external-dataset-manifest.example.json",
    }
    forbidden = [name for name in tracked if name not in allowed]
    ignored_probe = subprocess.run(
        ["git", "check-ignore", "-q", "datasets/external/local/example.sigmf-data"],
        cwd=ROOT,
        check=False,
    )
    passed = not forbidden and ignored_probe.returncode == 0
    return result(
        "external-git-policy",
        "passed" if passed else "failed",
        "external binary data is excluded from Git"
        if passed
        else "external binary path is not ignored or a binary is tracked",
    )


MANDATORY_CHECKS: tuple[Callable[[], dict[str, str]], ...] = (
    check_required_files,
    check_text_integrity,
    check_fixture_determinism,
    check_fixture_contract,
    check_standard_library_only,
    check_documentation_policy,
    check_external_git_policy,
)


def run_checks() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for check in MANDATORY_CHECKS:
        try:
            checks.append(check())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, SyntaxError) as exc:
            checks.append(result(check.__name__, "failed", f"check could not run: {type(exc).__name__}"))
    metadata_value, data_value, configuration = external_environment()
    checks.append(configuration)
    checks.append(
        check_external_integration(metadata_value, data_value)
        if configuration["status"] == "passed"
        else result("external-dataset-integration", "skipped", "external dataset configuration is invalid")
    )
    return checks


def main() -> int:
    checks = run_checks()
    overall = "failed" if any(check["status"] == "failed" for check in checks) else "passed"
    payload = {
        "schema_version": 1,
        "phase": "PHASE-01",
        "overall": overall,
        "checks": checks,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for check in checks:
        print(f"[{check['status'].upper()}] {check['id']}: {check['detail']}")
    print(f"Verification summary written to {SUMMARY_PATH}")
    return 0 if overall == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
