"""Record sequential RX-only full64/full128/fast runs without claiming RF accuracy."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import signal
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.operator_console.rx_survey import RXSurvey, SurveyConfig
from platforms.acquisition.hackrf import RealHackRFBackend


def main():
    parser = argparse.ArgumentParser(description="Aynı aralıkta üç RX tarama profilini ölçer; RF doğruluk kabulü üretmez.")
    parser.add_argument("--lower-mhz", type=float, required=True)
    parser.add_argument("--upper-mhz", type=float, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--lna", type=int, default=16)
    parser.add_argument("--vga", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = dict(lower_hz=round(args.lower_mhz * 1e6), upper_hz=round(args.upper_mhz * 1e6),
                lna_gain_db=args.lna, vga_gain_db=args.vga)
    configs = [("full128", SurveyConfig(**base)),
               ("full64", SurveyConfig(**base, frames_per_window=64)),
               ("fast", SurveyConfig(**base, mode="fast"))]
    backend = RealHackRFBackend()
    tools = backend.discover_tools(inspect_help=True)
    devices = backend.discover_device()
    if not tools.receive_available or args.serial.casefold() not in {d.serial.casefold() for d in devices.devices}:
        parser.error("İstenen HackRF ve RX araçları görünür/doğrulanmış değil.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        rows = []
        for name, config in configs:
            audit = args.output.parent / f"{name}-{uuid4().hex}.jsonl"
            survey = RXSurvey(tools.get("hackrf_transfer").executable_path, args.serial, config, audit)
            previous = signal.signal(signal.SIGINT, lambda *_: survey.cancel())
            try:
                result = survey.run()
            finally:
                signal.signal(signal.SIGINT, previous)
            rows.append({"profile": name, "config": asdict(config), "result": asdict(result)})
            stream.seek(0)
            json.dump({"schema": "rx-scan-profile-comparison-v1", "runs": rows,
                       "devices": asdict(devices), "tools": asdict(tools),
                       "gui_exercised": False, "physical_accuracy_proven": False,
                       "same_rf_environment_proven": False}, stream, ensure_ascii=False, indent=2)
            stream.truncate()
            stream.flush()
            print(f"{name}: {result.state} · {result.elapsed_seconds:.3f} s")
            if result.state != "completed":
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
