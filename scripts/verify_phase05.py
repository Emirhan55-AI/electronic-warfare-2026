"""Write or read-only verify deterministic PHASE-05 evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.monitoring.evaluation import build_phase05_evidence, canonical_bytes
from reference.monitoring.fixtures import build_fixture_files


EVIDENCE = ROOT / "results" / "evidence" / "phase05"
GOLDEN = EVIDENCE / "golden-monitoring.json"
SUMMARY = EVIDENCE / "verification-summary.json"
FIXTURES = ROOT / "datasets" / "fixtures" / "phase05"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def historical_integrity() -> tuple[int, bool]:
    # PHASE-05 evidence records the protected baseline that existed before its
    # own checkpoint.  Excluding its owned outputs prevents the count from
    # becoming self-referential after that checkpoint is committed.
    paths = [
        path
        for path in _git("ls-tree", "-r", "--name-only", "HEAD", "results/evidence", "profiles").splitlines()
        if not path.startswith("results/evidence/phase05/")
    ]
    return len(paths), all(_git("hash-object", "--", path) == _git("rev-parse", f"HEAD:{path}") for path in paths)


def expected_documents() -> tuple[dict[str, object], dict[str, object]]:
    golden, summary = build_phase05_evidence()
    count, intact = historical_integrity()
    summary = dict(summary)
    summary["historical_integrity"] = {"files": count, "status": "passed" if intact else "failed"}
    if not intact:
        summary["status"] = "failed"
    return golden, summary


def check() -> bool:
    expected_fixture_files, _ = build_fixture_files()
    fixtures_ok = all((FIXTURES / name).is_file() and (FIXTURES / name).read_bytes() == payload for name, payload in expected_fixture_files.items())
    golden, summary = expected_documents()
    evidence_ok = (
        GOLDEN.is_file()
        and SUMMARY.is_file()
        and GOLDEN.read_bytes() == canonical_bytes(golden)
        and SUMMARY.read_bytes() == canonical_bytes(summary)
    )
    safe = True
    for path in (GOLDEN, SUMMARY, EVIDENCE / "fixture-manifest.json"):
        if not path.is_file():
            safe = False
            continue
        text = path.read_text(encoding="utf-8")
        safe = safe and "C:\\Users" not in text and "timestamp" not in text and "machine" not in text
        document = json.loads(text)
        safe = safe and document.get("status", "passed") in {"passed", "failed", "skipped"}
    return fixtures_ok and evidence_ok and safe and summary["status"] == "passed"


def write() -> None:
    golden, summary = expected_documents()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_bytes(canonical_bytes(golden))
    SUMMARY.write_bytes(canonical_bytes(summary))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    passed = check()
    print(f"PHASE-05 verification: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
