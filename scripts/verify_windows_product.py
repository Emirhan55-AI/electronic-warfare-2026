"""Verify standalone assets and startup without the host Python environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "dist/operator-console-20260918/BAZ")
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/evidence/app/windows-product-20260918.json")
    args = parser.parse_args()
    package = args.package.resolve()
    executable = package / "BAZ.exe"
    source_inputs = json.loads((ROOT / "build/app-package-20260918/source-inputs.json").read_text(encoding="utf-8"))
    stale_sources = [path for path, digest in source_inputs.items()
                     if not (ROOT / path).is_file() or sha256(ROOT / path) != digest]
    if stale_sources:
        raise RuntimeError(f"Derleme kaynakları güncel kaynakla eşleşmiyor: {stale_sources}")
    manifest = json.loads((ROOT / "config/app/product-package.json").read_text(encoding="utf-8"))
    required = set(manifest["allowed_runtime_assets"]) | set(manifest["required_provenance_assets"])
    for path in (ROOT / "app/operator_console/qml").rglob("*"):
        if path.is_file():
            required.add(path.relative_to(ROOT).as_posix())
    mismatches = []
    asset_hashes = {}
    for relative in sorted(required):
        target = package / relative
        source = ROOT / relative
        if relative == "algorithms/p0/native/bin/p0_channelizer.dll":
            source = ROOT / "build/native/p0_channelizer/Release/p0_channelizer.dll"
        if not target.is_file() or sha256(target) != sha256(source):
            mismatches.append(relative)
        else:
            asset_hashes[relative] = sha256(target)
    if mismatches:
        raise RuntimeError(f"Paket varlıkları eksik veya farklı: {mismatches}")
    package_hashes = {path.relative_to(package).as_posix(): sha256(path)
                      for path in sorted(package.rglob("*")) if path.is_file()}
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PYTHON", "QT_", "QML"))}
    environment["PATH"] = str(Path(os.environ["WINDIR"]) / "System32")
    with tempfile.TemporaryDirectory(prefix="BÂZ paket denetimi ") as directory:
        environment["TEMP"] = directory
        environment["TMP"] = directory
        environment["QT_QPA_PLATFORM"] = "offscreen"
        completed = subprocess.run([str(executable), "--smoke-test", "--no-intro"],
                                   cwd=directory, env=environment, timeout=60, check=False)
    evidence = {
        "schema": "windows-product-package-v1",
        "requirements": ["KTR-4.1", "KTR-4.2", "KTR-4.3", "KTR-4.4"],
        "status": "passed" if completed.returncode == 0 else "failed",
        "executable_sha256": sha256(executable),
        "source_sha256": source_inputs,
        "asset_sha256": asset_hashes,
        "package_file_sha256": package_hashes,
        "package_sha256": hashlib.sha256(json.dumps(package_hashes, sort_keys=True).encode("utf-8")).hexdigest(),
        "windows_icu_sha256": {name: sha256(Path(os.environ["WINDIR"]) / "System32" / name)
                               for name in ("icu.dll", "icuuc.dll", "icuin.dll")},
        "smoke_test": {"exit_code": completed.returncode, "host_python_on_path": False,
                       "project_working_directory": False, "isolated_temporary_directory": True,
                       "qt_platform": "offscreen"},
        "physical_acceptance": False,
        "claim_boundary": "Paket bütünlüğü ve bağımsız açılış; canlı RX/FPGA/RF kabulü değildir.",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"EXE paket denetimi: {evidence['status']} ({len(asset_hashes)} varlık)")
    return 0 if completed.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
