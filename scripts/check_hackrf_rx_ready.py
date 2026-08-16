"""Report receive-only HackRF host readiness without performing a capture or TX."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.acquisition import RealHackRFBackend, load_ed_rx_config


def _tool_version(executable: str | None) -> dict[str, object]:
    if executable is None:
        return {"status": "NOT_READY", "version": None, "libhackrf_version": None, "output": "executable not found"}
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            timeout=3.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "NOT_READY", "version": None, "libhackrf_version": None, "output": type(exc).__name__}
    output = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace").strip()
    host_match = re.search(r"hackrf_info version:\s*([^\s]+)", output, flags=re.IGNORECASE)
    library_match = re.search(r"libhackrf version:\s*([^\s]+(?:\s+\([^)]*\))?)", output, flags=re.IGNORECASE)
    return {
        "status": "READY" if host_match and library_match else "NOT_READY",
        "version": host_match.group(1) if host_match else None,
        "libhackrf_version": library_match.group(1) if library_match else None,
        "output": output,
    }


def _usb_state() -> dict[str, object]:
    if sys.platform != "win32" or shutil.which("pnputil") is None:
        return {"status": "UNAVAILABLE", "present_vid_1d50_count": None}
    try:
        result = subprocess.run(
            ["pnputil", "/enum-devices", "/connected"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "ERROR", "present_vid_1d50_count": None}
    matches = re.findall(r"VID_1D50", result.stdout, flags=re.IGNORECASE)
    return {"status": "ENUMERATED", "present_vid_1d50_count": len(matches)}


def collect_readiness() -> dict[str, object]:
    config = load_ed_rx_config()
    backend = RealHackRFBackend()
    inventory = backend.discover_tools(inspect_help=True)
    device = backend.discover_device()
    info = inventory.get("hackrf_info")
    transfer = inventory.get("hackrf_transfer")
    info_version = _tool_version(info.executable_path)
    libhackrf_path = (
        str(Path(info.executable_path).with_name("libhackrf.dll"))
        if info.executable_path is not None and Path(info.executable_path).with_name("libhackrf.dll").is_file()
        else None
    )
    toolchain_ready = inventory.receive_available and libhackrf_path is not None and info_version["status"] == "READY"
    serials = [identity.serial for identity in device.devices]
    configured = config.serial
    if not toolchain_ready:
        recommendation = "FAIL_INSTALL_OR_REPAIR_HOST_TOOLCHAIN"
    elif device.state == "NO_DEVICE":
        recommendation = "CONNECT_PHYSICAL_ED_HACKRF"
    elif device.state == "MULTIPLE_DEVICES" and configured is None:
        recommendation = "CONNECT_ONLY_ED_HACKRF_OR_ASSIGN_SERIAL"
    elif configured is None:
        recommendation = "ASSIGN_DISCOVERED_SERIAL_TO_ED_RX_CONFIG"
    elif configured.casefold() not in {serial.casefold() for serial in serials}:
        recommendation = "CONFIGURED_ED_RX_SERIAL_NOT_PRESENT"
    else:
        recommendation = "READY_FOR_BOUNDED_RX_ACCEPTANCE"
    return {
        "schema_version": 1,
        "operation": "P0_BLOCK_B0_RECEIVE_ONLY_READINESS",
        "toolchain": {
            "status": "READY" if toolchain_ready else "NOT_READY",
            "hackrf_info": asdict(info),
            "hackrf_transfer": asdict(transfer),
            "hackrf_sweep": asdict(inventory.get("hackrf_sweep")),
            "version_probe": info_version,
            "libhackrf_path": libhackrf_path,
        },
        "usb": _usb_state(),
        "device": {
            "state": device.state,
            "count": device.device_count,
            "serials": serials,
            "board_details": [asdict(identity) for identity in device.devices],
            "reason_code": device.reason_code,
        },
        "configuration": {
            "role": config.role,
            "device_type": config.device_type,
            "serial": configured if configured is not None else "UNASSIGNED",
            "search_ranges_hz": [list(item) for item in config.search_ranges_hz],
        },
        "recommendation": recommendation,
        "physical_capture_performed": False,
        "transmit_api_called": False,
        "claim_boundary": "Host toolchain/readiness only; no physical RX, live IQ, RF accuracy, FPGA, ZedBoard or TX proof.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true", help="tek satır JSON üret")
    args = parser.parse_args()
    result = collect_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
    return 0 if result["toolchain"]["status"] == "READY" else 1  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
