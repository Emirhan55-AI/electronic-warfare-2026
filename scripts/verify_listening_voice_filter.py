"""Measure the optional listening high-pass response with independent DFT probes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.monitoring.dsp import _remove_voice_rumble


def main() -> int:
    time = np.arange(48_000) / 48_000
    frequencies = (50, 100, 300, 1000, 2500)
    source = sum(np.sin(2 * np.pi * f * time) for f in frequencies)
    filtered = _remove_voice_rumble(source)
    measurements = []
    for frequency in frequencies:
        basis = np.exp(-2j * np.pi * frequency * time[4800:-4800])
        gain = abs(np.mean(filtered[4800:-4800] * basis)) / abs(np.mean(source[4800:-4800] * basis))
        gain_db = float(20 * np.log10(gain))
        measurements.append(dict(frequency_hz=frequency, gain_db=gain_db,
                                 passed=gain_db < -40 if frequency <= 100 else abs(gain_db) < 0.2))
    files = (
        "algorithms/monitoring/dsp.py", "algorithms/monitoring/models.py",
        "app/operator_console/quick_listening_actions.py",
        "app/operator_console/quick_task_completion.py",
        "app/operator_console/quick_view_model.py", "app/operator_console/qml/Main.qml",
        "tests/test_listening_comparison.py", "tests/test_phase05_monitoring.py",
        "scripts/verify_listening_voice_filter.py",
    )
    payload = {
        "schema": "listening-voice-filter-v1", "requirement": "KTR-4.3",
        "scope": "synthetic_filter_response_only", "physical_acceptance": False,
        "sample_rate_hz": 48000, "input_seconds": 1, "edge_excluded_seconds": 0.1,
        "measurements": measurements,
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(item["passed"] for item in measurements) else 1


if __name__ == "__main__":
    raise SystemExit(main())
