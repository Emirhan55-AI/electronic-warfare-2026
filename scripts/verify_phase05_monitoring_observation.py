"""Write or verify the deterministic KTR-4.3 channel-observation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.monitoring import AnalogMonitor, AnalogMonitorConfig


EVIDENCE = ROOT / "results" / "evidence" / "phase05" / "monitoring-observation-v1.json"
SOURCES = (
    "algorithms/monitoring/models.py",
    "algorithms/monitoring/dsp.py",
    "app/operator_console/quick_view_model.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def _drifting_am() -> np.ndarray:
    sample_rate = 192_000.0
    duration = 5.0
    count = int(sample_rate * duration)
    time_axis = np.arange(count, dtype=np.float64) / sample_rate
    drift_hz = -200.0 + 400.0 * time_axis / duration
    phase = 2.0 * np.pi * (24_000.0 * time_axis + np.cumsum(drift_hz) / sample_rate)
    audio = np.sin(2.0 * np.pi * 1_000.0 * time_axis)
    return np.asarray(0.55 * (1.0 + 0.4 * audio) * np.exp(1j * phase), dtype=np.complex128)


def build_evidence() -> dict[str, object]:
    iq = _drifting_am()
    config = AnalogMonitorConfig("am", 192_000.0, 24_000.0, 16_000.0)
    monitor = AnalogMonitor()
    whole = monitor.process_continuous(iq, config)
    chunked = monitor.process_continuous(
        tuple(iq[index:index + 4096] for index in range(0, iq.size, 4096)), config
    )
    first_error = abs(chunked.residual_frequency_hz_trace[0] - (-190.0))
    last_error = abs(chunked.residual_frequency_hz_trace[-1] - 190.0)
    power_span = max(chunked.channel_power_dbfs_trace) - min(chunked.channel_power_dbfs_trace)
    pcm_equal = whole.pcm16 == chunked.pcm16
    power_trace_equal = bool(np.allclose(
        whole.channel_power_dbfs_trace, chunked.channel_power_dbfs_trace, atol=1e-12, rtol=0.0
    ))
    frequency_trace_equal = bool(np.allclose(
        whole.residual_frequency_hz_trace, chunked.residual_frequency_hz_trace, atol=1e-12, rtol=0.0
    ))
    passed = bool(
        len(chunked.observation_times_s) == 20
        and first_error <= 2.0
        and last_error <= 2.0
        and power_span <= 0.02
        and pcm_equal
        and power_trace_equal
        and frequency_trace_equal
    )
    return {
        "schema": "monitoring-observation-v1",
        "requirements": ["5.1.3", "KTR-4.3"],
        "status": "passed" if passed else "failed",
        "processing_location": "host_pc",
        "hardware_status": "not_exercised",
        "live_hackrf_status": "not_exercised",
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
        "method": {
            "interval_seconds": chunked.observation_interval_s,
            "power": "10*log10(mean(abs(channel_iq)^2)) dBFS",
            "residual_frequency": "angle(sum(x[n]*conj(x[n-1])))*Fs/(2*pi) Hz",
        },
        "drift_case": {
            "sample_rate_hz": 192_000,
            "duration_seconds": 5.0,
            "injected_start_hz": -200.0,
            "injected_end_hz": 200.0,
            "expected_first_window_hz": -190.0,
            "expected_last_window_hz": 190.0,
            "measured_first_window_hz": chunked.residual_frequency_hz_trace[0],
            "measured_last_window_hz": chunked.residual_frequency_hz_trace[-1],
            "first_error_hz": first_error,
            "last_error_hz": last_error,
            "power_span_db": power_span,
            "observation_points": len(chunked.observation_times_s),
        },
        "block_invariance": {
            "single_block_vs_4096_sample_blocks_pcm_equal": pcm_equal,
            "power_trace_equal_atol": 1e-12 if power_trace_equal else None,
            "frequency_trace_equal_atol": 1e-12 if frequency_trace_equal else None,
        },
        "claim_boundary": (
            "Deterministik sentetik I/Q üzerinde zamansal güç ve artık merkez frekansı izlemesi; "
            "canlı RF, fiziksel ses anlaşılırlığı veya saha doğruluğu değildir."
        ),
    }


def check() -> bool:
    expected = build_evidence()
    return EVIDENCE.is_file() and EVIDENCE.read_bytes() == _canonical(expected) and expected["status"] == "passed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_bytes(_canonical(build_evidence()))
    passed = check()
    print(f"KTR-4.3 monitoring observation: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
