#!/usr/bin/env python3
"""Verify the persistent PHASE-09 image and ARM direction service after reboot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.direction_client import estimate_on_board
from scripts.verify_phase09_amplitude_df_arm import _cases

IMAGE_DIR = ROOT / "build/p0/phase09-amplitude-df-image"
EVIDENCE = ROOT / "results/evidence/phase09/amplitude-df-persistent-image-v1.json"


def _tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    candidate = Path(r"C:\Program Files\PuTTY") / f"{name}.exe"
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError(f"{name} is unavailable")


def _run(command: list[str], *, stdin: str | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return result.stdout


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(host: str, port: int, username: str, password: str, host_key: str) -> dict[str, object]:
    if not host_key.startswith("SHA256:"):
        raise ValueError("verified SSH host-key fingerprint is required")
    image = IMAGE_DIR / "image.ub"
    boot = IMAGE_DIR / "BOOT.BIN"
    manifest = IMAGE_DIR / "rootfs.manifest"
    for path in (image, boot, manifest):
        if not path.is_file():
            raise FileNotFoundError(path)

    plink = _tool("plink")
    base = ["-batch", "-hostkey", host_key, "-pw", password, "-ssh", f"{username}@{host}"]
    runtime = _run([
        plink,
        *base,
        "uname -m; cat /proc/uptime; "
        "sha256sum /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge "
        "/usr/bin/p0-amplitude-df-run; "
        "pgrep -a p0-ed-service; pgrep -a p0-ed-network-bridge",
    ])
    boot_files = _run(
        [
            plink,
            *base,
            "sudo -S sh -c 'sha256sum /run/media/ZEDBOOT-mmcblk0p1/image.ub "
            "/run/media/ZEDBOOT-mmcblk0p1/BOOT.BIN "
            "/run/media/ZEDBOOT-mmcblk0p1/rootfs.manifest; "
            "grep p0-dma /run/media/ZEDBOOT-mmcblk0p1/rootfs.manifest'",
        ],
        stdin=f"{password}\n",
    )
    expected_hashes = {
        "image.ub": _sha256(image),
        "BOOT.BIN": _sha256(boot),
        "rootfs.manifest": _sha256(manifest),
    }
    for name, digest in expected_hashes.items():
        if f"{digest}  /run/media/ZEDBOOT-mmcblk0p1/{name}" not in boot_files:
            raise AssertionError(f"persistent {name} hash differs")
    if "p0-dma zynq_generic_7z020 1.0" not in boot_files:
        raise AssertionError("p0-dma is absent from the persistent rootfs manifest")
    if "armv7l" not in runtime or "p0-ed-service" not in runtime or "p0-ed-network-bridge" not in runtime:
        raise AssertionError("persistent ARM services are not running")

    cases = []
    for name, measurements in _cases().items():
        estimate = estimate_on_board(host, port, tuple(measurements)).estimate
        cases.append({
            "case": name,
            "status": estimate.status,
            "angle_deg": estimate.estimated_angle_deg,
            "measurement_count": estimate.measurement_count,
            "distinct_angle_count": estimate.distinct_angle_count,
            "maximum_gap_deg": estimate.maximum_angular_gap_deg,
            "prominence_db": estimate.peak_prominence_db,
            "front_to_back_db": estimate.front_to_back_db,
            "sampling_rms_deg": estimate.angular_sampling_rms_deg,
        })
    expected_statuses = {
        "lob-ready": "LOB HAZIR",
        "coverage-gate": "YETERSİZ AÇI KAPSAMI",
        "front-back-gate": "ÖN/ARKA BELİRSİZ",
        "receiver-gate": "ALICI AYARI DEĞİŞTİ",
        "target-gate": "HEDEF FREKANSI DEĞİŞTİ",
        "prominence-gate": "BELİRSİZ MAKSİMUM",
        "linear-repeat-average": "YETERSİZ AÇI",
    }
    if {case["case"]: case["status"] for case in cases} != expected_statuses:
        raise AssertionError("persistent direction responses differ from the locked profile")

    return {
        "schema": "phase09-amplitude-df-persistent-image-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed",
        "requirements": ["KTR-4.4"],
        "board": {
            "host": host,
            "architecture": "armv7l",
            "persistent_port": port,
            "ssh_host_key_verified_over_serial": host_key,
        },
        "persistent_boot_hashes": expected_hashes,
        "runtime_observation": runtime.strip().splitlines(),
        "boot_observation": boot_files.strip().splitlines(),
        "cases": cases,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                ROOT / "platforms/embedded/p0/include/p0_amplitude_df.h",
                ROOT / "platforms/embedded/p0/src/p0_amplitude_df.c",
                ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
                ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c",
                ROOT / "algorithms/p0/direction_client.py",
                Path(__file__),
            )
        },
        "claim_boundary": (
            "The SD image booted, persistent ARM services started, and seven deterministic "
            "P0DF-v1 cases passed on the ZedBoard. No HackRF, antenna pattern, live RF, "
            "known-bearing source, field multipath, or degree-RMS accuracy acceptance was performed."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--username", default="petalinux")
    parser.add_argument("--host-key", required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    password = os.environ.get("P0_BOARD_PASSWORD")
    if not password:
        raise SystemExit("P0_BOARD_PASSWORD is required")
    result = verify(args.host, args.port, args.username, password, args.host_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
