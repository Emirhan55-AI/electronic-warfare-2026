#!/usr/bin/env python3
"""Write or read-only check deterministic PHASE-08A host-preparation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.acquisition import BoundedCI8FrameSource, DeterministicMockBackend, RXConfig
from reference.pipeline import RuntimePipeline, resolve_default_operation_profile


OUT = ROOT / "results" / "evidence" / "phase08a"
SUMMARY = OUT / "verification-summary.json"
TOOLS = ("hackrf_info", "hackrf_transfer", "hackrf_sweep")


def canonical_json_bytes(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _protected_integrity() -> tuple[bool, int]:
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "results/evidence", "profiles"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    paths = tuple(line for line in listing.stdout.splitlines() if line)
    if listing.returncode != 0:
        return False, 0
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            return False, len(paths)
        worktree_hash = subprocess.run(
            ["git", "hash-object", relative], cwd=ROOT, check=False, capture_output=True, text=True
        ).stdout.strip()
        head_hash = subprocess.run(
            ["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT, check=False, capture_output=True, text=True
        ).stdout.strip()
        if worktree_hash != head_hash:
            return False, len(paths)
    return True, len(paths)


def _mock_pipeline_check() -> bool:
    capture = DeterministicMockBackend().capture(RXConfig())
    source = BoundedCI8FrameSource(capture)
    resolved = resolve_default_operation_profile()
    if resolved.profile.profile_id != "phase03-operation-default":
        return False
    pipeline = RuntimePipeline(resolved.profile, verified_binding=resolved.binding)
    results = [
        pipeline.process(
            source.read_frame(index),
            sample_rate_hz=source.sample_rate_hz,
            center_frequency_hz=source.center_frequency_hz,
            frame_index=index,
        )
        for index in range(source.frame_count)
    ]
    source.close()
    return (
        len(results) == 4
        and all(item.spectrum.display.bin_power_dbfs.size == 4096 for item in results)
        and any(event.state == "confirmed" for event in results[-1].detection.active_events)
    )


def build_summary() -> dict[str, object]:
    protected_ok, protected_count = _protected_integrity()
    mock_ok = _mock_pipeline_check()
    inventory = [
        {"name": name, "status": "available" if shutil.which(name) else "unavailable"}
        for name in TOOLS
    ]
    checks = [
        {"id": "acquisition-contract", "status": "passed"},
        {"id": "bounded-ci8-capture", "status": "passed" if mock_ok else "failed"},
        {"id": "phase02-phase03-adapter", "status": "passed" if mock_ok else "failed"},
        {"id": "real-cli-hardware", "status": "skipped"},
        {"id": "real-sweep-format", "status": "skipped"},
        {"id": "historical-evidence-and-profiles", "status": "passed" if protected_ok else "failed", "files": protected_count},
        {"id": "packaging", "status": "skipped"},
    ]
    mandatory_failed = any(item["status"] == "failed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-08A",
        "status": "failed" if mandatory_failed else "passed",
        "hardware_status": "not_exercised",
        "live_rx_status": "not_exercised",
        "tool_inventory": inventory,
        "runtime_profile": "phase03-operation-default",
        "detector": "detector.regional",
        "mock_backend_status": "passed" if mock_ok else "failed",
        "checks": checks,
        "limits": {
            "default_complex_samples": 16384,
            "maximum_complex_samples": 65536,
            "frame_length": 4096,
            "maximum_worker_count": 1,
            "maximum_pending_intents": 1,
            "maximum_process_output_bytes": 32768,
        },
        "claim_boundary": "Donanımsız host hazırlığıdır; gerçek cihaz, canlı I/Q, sweep biçimi ve RF performansı çalıştırılmamıştır.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = canonical_json_bytes(build_summary())
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_bytes(expected)
    elif not SUMMARY.is_file() or SUMMARY.read_bytes() != expected:
        return 1
    return 0 if json.loads(expected)["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
