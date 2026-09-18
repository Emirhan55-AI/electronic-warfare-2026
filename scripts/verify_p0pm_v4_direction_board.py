#!/usr/bin/env python3
"""Verify the P0PM-v4 locked-direction power contract on the physical board."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0.detection_config import exchange_profile
from algorithms.p0.parameter_client import BoardAnalysisSpan, measure_on_board
from algorithms.parameters import MeasurementIntent


DEFAULT_PRODUCTS = ROOT / "build/p0/p0pm-v4-direction-20260916/software"
DEFAULT_OUTPUT = ROOT / "results/evidence/phase09/p0pm-v4-direction-power-physical-20260916.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _field(field) -> dict[str, object]:
    return {
        "state": field.state,
        "value": field.value,
        "unit": field.unit,
        "reason": field.reason,
    }


def verify(host: str, port: int, products: Path) -> dict[str, object]:
    intent = MeasurementIntent(
        1, 1, 1, 44, 1, 100,
        BoardAnalysisSpan(2000, 2031, "operator_adjusted", 1),
    )
    # An impulse at the Hann-window centre produces equal non-zero FFT power
    # in every bin. Normal P0PM must reject its zero excess over reference;
    # P0PM-v4 must retain the fixed channel's finite total power.
    frame = bytearray(8192)
    frame[2 * 2048] = 64
    iq = bytes(frame) * 4
    profile_before = exchange_profile(host, port)
    if profile_before.fft_size != 4096:
        raise AssertionError("P0PM-v4 fiziksel doğrulaması 4096 FFT gerektirir.")
    normal = measure_on_board(
        host, port, intent, iq,
        sample_rate_hz=2_000_000,
        center_frequency_hz=2_300_000_000,
    )
    locked = measure_on_board(
        host, port, intent, iq,
        sample_rate_hz=2_000_000,
        center_frequency_hz=2_300_000_000,
        locked_channel_power=True,
    )
    profile_after = exchange_profile(host, port)
    normal_version = struct.unpack_from("<H", normal.response, 4)[0]
    locked_version = struct.unpack_from("<H", locked.response, 4)[0]
    if normal_version not in (1, 2) or locked_version != 4:
        raise AssertionError("Kart P0PM-v4 yanıt sürümünü doğrulamadı.")
    if normal.result.channel_power_dbfs.state == "valid":
        raise AssertionError("Normal P0PM düz spektrumu yanlışlıkla geçerli sinyal gücü saydı.")
    locked_power = locked.result.channel_power_dbfs
    if (locked_power.state != "valid" or
            not isinstance(locked_power.value, (int, float)) or
            not math.isfinite(float(locked_power.value))):
        raise AssertionError("P0PM-v4 kilitli kanal toplam gücünü üretmedi.")
    if profile_after != profile_before:
        raise AssertionError("P0PM-v4 ölçümü FPGA tespit profilini değiştirdi.")
    return {
        "schema": "p0pm-v4-direction-power-physical-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed",
        "requirements": ["KTR-4.4"],
        "board": {"host": host, "port": port, "architecture": "armv7l"},
        "profile_before": asdict(profile_before),
        "profile_after": asdict(profile_after),
        "stimulus": {
            "kind": "hann_center_impulse_flat_fft_power",
            "frames": 4,
            "frame_bytes": 8192,
            "ci8_sha256": hashlib.sha256(iq).hexdigest(),
            "span": [2000, 2031],
        },
        "normal_parameter": {
            "protocol_version": normal_version,
            "channel_power": _field(normal.result.channel_power_dbfs),
            "quality": asdict(normal.result.quality),
            "elapsed_us": normal.elapsed_us,
        },
        "locked_direction": {
            "protocol_version": locked_version,
            "power_basis": "locked_channel_total_signal_plus_noise",
            "channel_power": _field(locked_power),
            "quality": asdict(locked.result.quality),
            "elapsed_us": locked.elapsed_us,
        },
        "binaries": {
            name: _sha256(products / name)
            for name in ("p0-ed-service", "p0-ed-network-bridge")
        },
        "sources": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                ROOT / "algorithms/p0/parameter_client.py",
                ROOT / "platforms/embedded/p0/include/p0_ed_service_protocol.h",
                ROOT / "platforms/embedded/p0/include/p0_parameter_runtime.h",
                ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
                ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
                ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
                Path(__file__).resolve(),
            )
        },
        "claim_boundary": (
            "Physical ZedBoard PL/ARM and P0PM-v4 network-path functional proof on a "
            "deterministic flat-power CI8 fixture; no antenna, live RF, calibration, "
            "bearing, multipath or degree-RMS accuracy acceptance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47008)
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = verify(args.host, args.port, args.products)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "normal_power_state": result["normal_parameter"]["channel_power"]["state"],
        "locked_power_dbfs": result["locked_direction"]["channel_power"]["value"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
