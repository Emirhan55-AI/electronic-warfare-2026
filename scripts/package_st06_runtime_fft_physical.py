#!/usr/bin/env python3
"""Package repeated dynamic-FFT ZedBoard runs with product identity."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08"
RUNS = (
    EVIDENCE / "st06-runtime-fft-physical-20260911.json",
    EVIDENCE / "st06-runtime-fft-physical-20260911-repeat2.json",
    EVIDENCE / "st06-runtime-fft-physical-20260911-repeat3.json",
)
BUILD_REPORT = EVIDENCE / "st06-runtime-fft-build-20260910.json"
BOARD_IDENTITY = EVIDENCE / "st06-runtime-fft-board-identity-20260911.json"
OUTPUT = EVIDENCE / "st06-runtime-fft-physical-repeated-20260911.json"
PRODUCTS = {
    "bitstream": ROOT / "build/p0/st06-rfft-v4-20260910/hardware/p0_system_wrapper.bit.bin",
    "module": ROOT / "build/p0/st06-rfft-v4-20260910/software/lib/modules/6.12.40-xilinx-g31626ef92ff1/updates/p0_dma_client.ko",
    "service": ROOT / "build/p0/st06-rfft-v4-20260910/software/usr/sbin/p0-ed-service",
    "bridge": ROOT / "build/p0/st06-rfft-v4-20260910/software/usr/sbin/p0-ed-network-bridge",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without rewriting evidence")
    args = parser.parse_args()
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in RUNS]
    build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    board = json.loads(BOARD_IDENTITY.read_text(encoding="utf-8-sig"))
    product_sha256 = {name: digest(path) for name, path in PRODUCTS.items()}
    sizes = (4096, 8192, 16384)
    grouped = {
        str(size): [
            next(case for case in run["cases"] if case["fft_size"] == size)
            for run in runs
        ]
        for size in sizes
    }
    checks = {
        "three_runs_present": len(runs) == 3,
        "all_runs_passed": all(run["status"] == "passed" for run in runs),
        "all_run_checks_passed": all(all(run["checks"].values()) for run in runs),
        "all_case_checks_passed": all(
            all(case["checks"].values())
            for cases in grouped.values() for case in cases
        ),
        "each_run_used_4096_measured_frames_per_size": all(
            run["frame_count_per_size"] == 4096 for run in runs
        ),
        "build_report_passed": build["status"] == "passed",
        "board_identity_checks_passed": all(board["checks"].values()),
        "card_artifacts_match_packaged_products": board["card_sha256"] == product_sha256,
    }
    throughput = {
        size: {
            "required_frames_per_second": cases[0]["required_frames_per_second"],
            "measured_frames_per_second": [case["frames_per_second"] for case in cases],
            "minimum_frames_per_second": min(case["frames_per_second"] for case in cases),
            "minimum_realtime_margin": min(case["realtime_margin"] for case in cases),
        }
        for size, cases in grouped.items()
    }
    result = {
        "schema": "phase08-st06-runtime-fft-physical-repeated-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "scope": "three repeated temporary-load ZedBoard dynamic FPGA FFT digital throughput runs",
        "checks": checks,
        "throughput": throughput,
        "board_identity": board,
        "product_sha256": product_sha256,
        "input_sha256": {
            path.relative_to(ROOT).as_posix(): digest(path)
            for path in (*RUNS, BUILD_REPORT, BOARD_IDENTITY)
        },
        "claim_boundary": {
            "hackrf_used": False,
            "rf_input_used": False,
            "pd_pfa_acceptance": False,
            "cold_boot_acceptance": False,
            "persistent_boot_files_changed": False,
            "st06_complete": False,
        },
    }
    archive = OUTPUT.with_suffix(".zip")
    if args.check:
        recorded = json.loads(OUTPUT.read_text(encoding="utf-8"))
        comparable = dict(recorded)
        comparable.pop("archive_sha256", None)
        comparable["generated_at_utc"] = result["generated_at_utc"]
        if comparable != result or recorded.get("archive_sha256") != digest(archive):
            raise ValueError("Evidence or archive differs from current inputs")
        with zipfile.ZipFile(archive) as stored:
            for path in (*RUNS, BUILD_REPORT, BOARD_IDENTITY, *PRODUCTS.values()):
                if stored.read(path.relative_to(ROOT).as_posix()) != path.read_bytes():
                    raise ValueError(f"Archive member differs: {path.name}")
        print(json.dumps({"status": result["status"], "checks": checks}, indent=2))
        return 0 if result["status"] == "passed" else 1
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stored:
        for path in (*RUNS, BUILD_REPORT, BOARD_IDENTITY, *PRODUCTS.values()):
            stored.write(path, path.relative_to(ROOT).as_posix())
    result["archive_sha256"] = digest(archive)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "throughput": throughput,
                      "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
