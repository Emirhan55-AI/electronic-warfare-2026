#!/usr/bin/env python3
"""Run the P0DF-v1 amplitude-DF service path on a connected ZedBoard."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.direction_client import estimate_on_board
from scripts.verify_phase09_amplitude_df_arm import _cases

SERVICE = ROOT / "build/p0/st06-runtime-config-v2-20260910/software/p0-ed-service"
BRIDGE = ROOT / "build/p0/st06-runtime-config-v2-20260910/software/p0-ed-network-bridge"
EVIDENCE = ROOT / "results/evidence/phase09/amplitude-df-board-protocol-v2.json"


def _tool(name: str) -> str:
    result = shutil.which(name)
    if result:
        return result
    candidate = Path(r"C:\Program Files\PuTTY") / f"{name}.exe"
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError(f"{name} is unavailable")


def _run(command: list[str], *, stdin: str | None = None) -> str:
    result = subprocess.run(command, cwd=ROOT, input=stdin, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return result.stdout


def verify(host: str, port: int, username: str, password: str, host_key: str) -> dict[str, object]:
    if not host_key.startswith("SHA256:"):
        raise ValueError("verified SSH host-key fingerprint is required")
    subprocess.run([sys.executable, "scripts/build_st06_runtime_services.py"],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    pscp, plink = _tool("pscp"), _tool("plink")
    base = ["-batch", "-hostkey", host_key, "-pw", password]
    target = f"{username}@{host}"
    before = _run([plink, *base, "-ssh", target,
                   "uname -m; sha256sum /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge; "
                   "pgrep -a p0-ed-service; pgrep -a p0-ed-network-bridge"])
    _run([pscp, *base, "-scp", str(SERVICE), f"{target}:/tmp/p0-ed-service-df"])
    _run([pscp, *base, "-scp", str(BRIDGE), f"{target}:/tmp/p0-ed-network-bridge-df"])
    started = False
    try:
        start_command = (
            "sudo -S sh -c 'rm -f /tmp/p0-df.sock /tmp/p0-df-service.pid /tmp/p0-df-bridge.pid; "
            "chmod 700 /tmp/p0-ed-service-df /tmp/p0-ed-network-bridge-df; "
            "nohup /tmp/p0-ed-service-df /dev/p0-dma /tmp/p0-df.sock >/tmp/p0-df-service.log 2>&1 & "
            "echo $! >/tmp/p0-df-service.pid'; sleep 1; "
            f"sudo -S sh -c 'nohup /tmp/p0-ed-network-bridge-df {host} 192.168.7.1 {port} "
            "/tmp/p0-df.sock >/tmp/p0-df-bridge.log 2>&1 & echo $! >/tmp/p0-df-bridge.pid'; "
            "sleep 1; cat /tmp/p0-df-service.log /tmp/p0-df-bridge.log"
        )
        start_output = _run([plink, *base, "-ssh", target, start_command],
                            stdin=f"{password}\n{password}\n")
        started = True
        with socket.create_connection((host, port), timeout=3.0):
            pass
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
        expected = {
            "lob-ready": "LOB HAZIR",
            "adaptive-lob-ready": "LOB HAZIR",
            "coverage-gate": "ÖN/ARKA BELİRSİZ",
            "front-back-gate": "ÖN/ARKA BELİRSİZ",
            "receiver-gate": "ALICI AYARI DEĞİŞTİ",
            "target-gate": "HEDEF FREKANSI DEĞİŞTİ",
            "prominence-gate": "BELİRSİZ MAKSİMUM",
            "linear-repeat-average": "YETERSİZ AÇI",
        }
        if {item["case"]: item["status"] for item in cases} != expected:
            raise AssertionError("board direction statuses differ from the locked profile")
    finally:
        if started:
            cleanup = (
                "sudo -S sh -c 'test ! -f /tmp/p0-df-bridge.pid || kill $(cat /tmp/p0-df-bridge.pid) 2>/dev/null || true; "
                "test ! -f /tmp/p0-df-service.pid || kill $(cat /tmp/p0-df-service.pid) 2>/dev/null || true; "
                "rm -f /tmp/p0-ed-service-df /tmp/p0-ed-network-bridge-df /tmp/p0-df.sock "
                "/tmp/p0-df-service.pid /tmp/p0-df-bridge.pid /tmp/p0-df-service.log /tmp/p0-df-bridge.log'"
            )
            _run([plink, *base, "-ssh", target, cleanup], stdin=f"{password}\n")
    after = _run([plink, *base, "-ssh", target,
                  "sha256sum /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge; "
                  "pgrep -a p0-ed-service; pgrep -a p0-ed-network-bridge"])
    return {
        "schema": "phase09-amplitude-df-board-protocol-v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed",
        "board": {"host": host, "architecture": "armv7l", "temporary_port": port,
                  "ssh_host_key": host_key},
        "protocol": {"request": "P0DF-v1", "response": "P0FR-v1",
                     "request_crc32": True, "response_crc32": True},
        "start_output": start_output.strip(),
        "cases": cases,
        "persistent_services_before": before.strip().splitlines(),
        "persistent_services_after": after.strip().splitlines(),
        "temporary_processes_removed": True,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                ROOT / "platforms/embedded/p0/include/p0_amplitude_df.h",
                ROOT / "platforms/embedded/p0/src/p0_amplitude_df.c",
                ROOT / "platforms/embedded/p0/include/p0_ed_service_protocol.h",
                ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
                ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
                ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c",
                ROOT / "algorithms/p0/direction_client.py",
                Path(__file__),
            )
        },
        "binary_sha256": {
            "p0-ed-service": hashlib.sha256(SERVICE.read_bytes()).hexdigest(),
            "p0-ed-network-bridge": hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        },
        "claim_boundary": (
            "Physical ZedBoard execution and versioned network-path numeric equivalence; "
            "the persistent SD image was not changed and no antenna, live RF or degree-RMS "
            "accuracy acceptance was performed."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47008)
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
