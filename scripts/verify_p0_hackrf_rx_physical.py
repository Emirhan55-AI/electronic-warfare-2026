#!/usr/bin/env python3
"""Run the bounded receive-only PHASE-08 HackRF physical acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import HackRFSearchPlanner, P0SearchEngine, SearchRequest
from platforms.acquisition import CaptureResult, HackRFSearchBackend, RealHackRFBackend, load_ed_rx_config


DEFAULT_LOWER_MHZ = 104.4
DEFAULT_UPPER_MHZ = 104.9
REPEAT_RUNS = 5
MAX_RECORDED_SIGNALS = 8


class RecordingReceiveBackend:
    """Record bounded capture integrity while preserving the real RX backend."""

    backend_kind = "real"

    def __init__(self, backend: RealHackRFBackend) -> None:
        self.backend = backend
        self.captures: list[dict[str, object]] = []

    def capture(self, config, cancellation=None) -> CaptureResult:
        result = self.backend.capture(config, cancellation)
        raw = np.frombuffer(result.payload, dtype=np.int8)
        self.captures.append(
            {
                "center_frequency_hz": config.center_frequency_hz,
                "sample_rate_hz": config.sample_rate_hz,
                "complex_samples": config.sample_count,
                "bytes": len(result.payload),
                "sha256": hashlib.sha256(result.payload).hexdigest(),
                "saturated_components": int(np.count_nonzero((raw == -128) | (raw == 127))),
            }
        )
        return result

    def cancel(self) -> None:
        self.backend.cancel()

    def close(self) -> None:
        self.backend.close()


def _parameter_document(parameter) -> dict[str, object]:
    return {
        "emission_center_frequency_hz": parameter.emission_center_frequency_hz,
        "lower_frequency_hz": parameter.lower_frequency_hz,
        "upper_frequency_hz": parameter.upper_frequency_hz,
        "bandwidth_hz": parameter.bandwidth_hz,
        "snr_db": parameter.snr_db,
        "channel_power_dbfs": parameter.channel_power_dbfs,
        "signal_domain": parameter.signal_domain,
        "confirmed": parameter.confirmed,
        "provenance": parameter.provenance,
    }


def run_acceptance(lower_mhz: float, upper_mhz: float) -> dict[str, object]:
    config = load_ed_rx_config()
    if config.serial is None:
        raise RuntimeError("ED_RX HackRF seri kimliği atanmamış.")

    physical = RealHackRFBackend()
    inventory = physical.discover_tools(inspect_help=True)
    device = physical.discover_device()
    if not inventory.receive_available:
        raise RuntimeError("HackRF RX araç zinciri hazır değil.")
    if device.state != "ONE_DEVICE" or device.device_count != 1:
        raise RuntimeError("Fiziksel kabul tam olarak bir HackRF gerektirir.")
    identity = device.devices[0]
    if identity.serial.casefold() != config.serial.casefold():
        raise RuntimeError("Bağlı HackRF, ED_RX seri yapılandırmasıyla eşleşmiyor.")

    request = SearchRequest.judge_band_mhz(lower_mhz, upper_mhz)
    planner = HackRFSearchPlanner()
    plan = planner.plan(request)
    recorder = RecordingReceiveBackend(physical)
    acquisition = HackRFSearchBackend(recorder, device_serial=config.serial, planner=planner)
    engine = P0SearchEngine(acquisition)
    runs: list[dict[str, object]] = []
    try:
        for index in range(REPEAT_RUNS):
            result = engine.execute(request)
            signals = tuple(result.parameters[:MAX_RECORDED_SIGNALS])
            runs.append(
                {
                    "index": index + 1,
                    "status": result.status,
                    "examined_window_ids": list(result.examined_window_ids),
                    "confirmed_signal_count": len(signals),
                    "signals": [_parameter_document(item) for item in signals],
                }
            )
    finally:
        recorder.close()

    passed = all(
        run["status"] == "COMPLETED_SIGNAL_FOUND"
        and int(run["confirmed_signal_count"]) >= 1
        and all(
            signal["confirmed"] is True and signal["provenance"] == "LIVE_HACKRF"
            for signal in run["signals"]
        )
        for run in runs
    )
    captures = recorder.captures
    expected_capture_count = REPEAT_RUNS * len(plan.windows)
    passed = passed and len(captures) == expected_capture_count and all(
        item["bytes"] == int(item["complex_samples"]) * 2 for item in captures
    )
    source_paths = {
        "hackrf_search.py": ROOT / "algorithms/p0/hackrf_search.py",
        "search.py": ROOT / "algorithms/p0/search.py",
        "acquisition_hackrf.py": ROOT / "platforms/acquisition/hackrf.py",
        "acquisition_search.py": ROOT / "platforms/acquisition/search.py",
        "hackrf_ed_rx.json": ROOT / "config/p0/hackrf_ed_rx.json",
        "verify_p0_hackrf_rx_physical.py": Path(__file__),
    }
    return {
        "schema_version": 1,
        "recorded_at": date.today().isoformat(),
        "status": "passed" if passed else "failed",
        "scope": "fiziksel HackRF-1 RX ve host ED tespit kabulü",
        "device": {
            "serial": identity.serial,
            "board_id": identity.board_id,
            "firmware_version": identity.firmware_version,
            "part_id": identity.part_id,
            "role": config.role,
        },
        "receive_profile": {
            "sample_rate_hz": planner.profile.sample_rate_hz,
            "sample_count_per_window": planner.profile.sample_count,
            "rf_amplifier": False,
            "lna_gain_db": 16,
            "vga_gain_db": 16,
            "dc_exclusion_hz": planner.profile.dc_exclusion_hz,
            "offset_tuning_hz": planner.profile.offset_tuning_hz,
            "requested_lower_frequency_hz": round(lower_mhz * 1_000_000),
            "requested_upper_frequency_hz": round(upper_mhz * 1_000_000),
            "planned_windows": [asdict(item) for item in plan.windows],
        },
        "repeatability": {
            "runs": REPEAT_RUNS,
            "passed_runs": sum(run["status"] == "COMPLETED_SIGNAL_FOUND" for run in runs),
            "capture_count": len(captures),
            "expected_capture_count": expected_capture_count,
            "all_capture_lengths_exact": all(
                item["bytes"] == int(item["complex_samples"]) * 2 for item in captures
            ),
            "total_complex_samples": sum(int(item["complex_samples"]) for item in captures),
            "total_saturated_components": sum(int(item["saturated_components"]) for item in captures),
        },
        "captures": captures,
        "runs": runs,
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_paths.items()
        },
        "transmit_api_called": False,
        "claim_boundary": (
            "Bu kanıt fiziksel HackRF üzerinde bounded RX, offset tuning, DC dışlama ve host tespit "
            "tekrarlanabilirliğini gösterir. ZedBoard/FPGA aktarımı, dBm kalibrasyonu, yayın kimliği, "
            "parametre doğruluğu, yön bulma, saha kapsaması veya RF TX kanıtı değildir."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lower-mhz", type=float, default=DEFAULT_LOWER_MHZ)
    parser.add_argument("--upper-mhz", type=float, default=DEFAULT_UPPER_MHZ)
    args = parser.parse_args()
    result = run_acceptance(args.lower_mhz, args.upper_mhz)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
