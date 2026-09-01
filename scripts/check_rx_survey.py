"""Run a bounded receive-only survey and preserve its physical observations."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.operator_console.rx_survey import RXSurvey, SurveyConfig
from platforms.acquisition import RealHackRFBackend, load_ed_rx_config


def main():
    parser = argparse.ArgumentParser(description="Yalnız alıcı frekans taraması")
    parser.add_argument("--lower-mhz", type=float, required=True)
    parser.add_argument("--upper-mhz", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lna", type=int, default=32)
    parser.add_argument("--vga", type=int, default=32)
    args = parser.parse_args()
    config = SurveyConfig(round(args.lower_mhz * 1e6), round(args.upper_mhz * 1e6), args.lna, args.vga)
    backend = RealHackRFBackend()
    try:
        inventory = backend.discover_tools(inspect_help=True)
        executable = next(tool.executable_path for tool in inventory.tools if tool.name == "hackrf_transfer")
        device = load_ed_rx_config()
        if not inventory.receive_available or not device.serial:
            raise RuntimeError("Yapılandırılmış alıcı veya alım aracı hazır değil.")
        survey = RXSurvey(executable, device.serial, config, args.output)
        def progress(update):
            if update.state != "running":
                print(json.dumps({"window": update.window.index + 1, "state": update.state,
                                  "observations": len(update.observations), "error": update.error_code}), flush=True)
        result = survey.run(progress)
        print(json.dumps(asdict(result), ensure_ascii=False), flush=True)
        return 0 if result.state == "completed" else 1
    finally:
        backend.close()


if __name__ == "__main__":
    raise SystemExit(main())
