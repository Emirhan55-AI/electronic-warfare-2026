"""Measure bounded RX-only HackRF streams at 8/10/20 MS/s."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.acquisition.continuous import HackRFContinuousRX
from platforms.acquisition.contracts import RXConfig
from platforms.acquisition.hackrf import RealHackRFBackend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--center-hz", type=int, default=820_000_000)
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Var olan gözlemin üzerine yazılmaz.")
    if not 0.5 <= args.seconds <= 5.0 or not 1 <= args.repeats <= 5:
        parser.error("Süre 0,5–5 saniye, tekrar 1–5 arasında olmalıdır.")
    executable = shutil.which("hackrf_transfer")
    if executable is None:
        parser.error("hackrf_transfer bulunamadı.")
    backend = RealHackRFBackend()
    tools = backend.discover_tools(inspect_help=True)
    devices = backend.discover_device()
    device = next((item for item in devices.devices if item.serial.casefold() == args.serial.casefold()), None)
    if device is None or not tools.receive_available:
        parser.error("İstenen HackRF veya RX aracı doğrulanamadı.")
    runs = []
    for rate in (8_000_000, 10_000_000, 20_000_000):
        frames = math.ceil(args.seconds * rate / 16_384)
        for repeat in range(args.repeats):
            config = RXConfig(args.center_hz, rate, 16_384, False, 16, 16, args.serial)
            stream = HackRFContinuousRX(executable, config, frames)
            with stream:
                for _ in stream:
                    pass
            runs.append({"sample_rate_hz": rate, "repeat": repeat + 1,
                         "requested_seconds": args.seconds,
                         "statistics": asdict(stream.statistics)})
    source_names = (
        "scripts/measure_hackrf_rx_rates.py", "platforms/acquisition/continuous.py",
        "platforms/acquisition/contracts.py", "platforms/acquisition/windows_pipe.py",
    )
    document = {
        "schema": "hackrf-rx-rate-observation-v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "receive_only": True,
        "device": asdict(device),
        "tool_inventory": asdict(tools),
        "configuration": {"center_frequency_hz": args.center_hz, "lna_gain_db": 16,
                          "vga_gain_db": 16, "rf_amplifier": False,
                          "repeats": args.repeats},
        "runs": runs,
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in source_names},
        "limits": [
            "Bu gözlem yalnız USB RX taşımasını ölçer; FPGA/ARM veya RF tespit doğruluğu değildir.",
            "Başka USB yerleşimi, firmware, bilgisayar veya süre için sonuç aktarılmaz.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
