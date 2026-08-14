"""Generate or byte-check the deterministic PHASE-05 SigMF fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.monitoring import build_fixture_files


FIXTURE_DIR = ROOT / "datasets" / "fixtures" / "phase05"
EVIDENCE_MANIFEST = ROOT / "results" / "evidence" / "phase05" / "fixture-manifest.json"


def expected_files() -> dict[Path, bytes]:
    files, _ = build_fixture_files()
    expected = {FIXTURE_DIR / name: payload for name, payload in files.items()}
    expected[EVIDENCE_MANIFEST] = files["fixture-manifest.json"]
    return expected


def check() -> bool:
    return all(path.is_file() and path.read_bytes() == payload for path, payload in expected_files().items())


def write() -> None:
    for path, payload in expected_files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="PHASE-05 deterministik fixture üreticisi")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"PHASE-05 fixture: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
