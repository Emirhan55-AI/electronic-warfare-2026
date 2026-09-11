"""Record or verify the standalone KTR-4.3 operator product package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "dist" / "operator-console-20260911" / "BAZ.dist"
EXECUTABLE = PACKAGE / "baz_operator_console.exe"
EVIDENCE = ROOT / "results" / "evidence" / "phase05" / "listening-product-package-20260911.json"
SOURCES = (
    "baz_operator_console.py",
    "app/operator_console/pysidedeploy.spec",
    "app/operator_console/quick_listening_actions.py",
    "app/operator_console/quick_view_model.py",
    "app/operator_console/qml/Main.qml",
    "app/operator_console/qml/ParameterMeasurementPanel.qml",
)
REQUIRED_ASSETS = (
    "app/operator_console/qml/ParameterMeasurementPanel.qml",
    "app/operator_console/qml/DetectionSettings.qml",
    "algorithms/p0/native/bin/p0_channelizer.dll",
    "profiles/phase03/operation-default.json",
    "profiles/phase04f5/operation-default.json",
    "config/p0/hackrf_ed_rx.json",
    "config/p0/hackrf_spurs.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def build_evidence() -> dict[str, object]:
    missing = [path for path in REQUIRED_ASSETS if not (PACKAGE / path).is_file()]
    if not EXECUTABLE.is_file() or missing:
        raise FileNotFoundError(f"Paket veya zorunlu varlık eksik: {missing}")
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [str(EXECUTABLE), "--smoke-test", "--no-intro"],
        cwd=PACKAGE,
        env=environment,
        capture_output=True,
        timeout=20,
        check=False,
    )
    passed = completed.returncode == 0
    return {
        "schema": "phase05-listening-product-package-v1",
        "requirements": ["5.1.3", "KTR-4.3"],
        "status": "passed" if passed else "failed",
        "package": {
            "executable": str(EXECUTABLE.relative_to(ROOT)).replace("\\", "/"),
            "executable_sha256": _sha256(EXECUTABLE),
            "executable_bytes": EXECUTABLE.stat().st_size,
            "required_assets": {
                path: _sha256(PACKAGE / path) for path in REQUIRED_ASSETS
            },
        },
        "smoke_test": {
            "arguments": ["--smoke-test", "--no-intro"],
            "qt_platform": "offscreen",
            "exit_code": completed.returncode,
        },
        "source_sha256": {path: _sha256(ROOT / path) for path in SOURCES},
        "hardware_status": "zedboard_not_exercised_by_package_smoke_test",
        "hackrf_status": "not_connected",
        "physical_acceptance": False,
        "claim_boundary": (
            "Windows standalone paketinin başlangıç, QML ve zorunlu varlık bütünlüğü "
            "kanıtıdır; canlı HackRF, FPGA işlem sonucu veya analog ses kabulü değildir."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        current = build_evidence()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"KTR-4.3 product package rejected: {exc}")
        return 1
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_bytes(_canonical(current))
    passed = (
        current["status"] == "passed"
        and EVIDENCE.is_file()
        and EVIDENCE.read_bytes() == _canonical(current)
    )
    print(f"KTR-4.3 product package: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
