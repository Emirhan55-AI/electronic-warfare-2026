"""Measure the bounded five-second listening DSP at the live 2 MS/s scale."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.monitoring import AnalogMonitor, AnalogMonitorConfig


EVIDENCE = ROOT / "results" / "evidence" / "phase05" / "monitoring-live-scale-host-20260911.json"
SOURCES = ("algorithms/monitoring/models.py", "algorithms/monitoring/dsp.py")
SAMPLE_RATE_HZ = 2_000_000
INPUT_SAMPLES = 2_442 * 4_096
MAX_PROCESSING_SECONDS = 10.0
MAX_RSS_INCREASE_MIB = 1_024.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rss_bytes() -> int:
    try:
        import psutil
    except ImportError:
        return 0
    return int(psutil.Process(os.getpid()).memory_info().rss)


def run_benchmark() -> dict[str, object]:
    blocks: list[np.ndarray] = []
    start = 0
    block_size = 123 * 4_096
    while start < INPUT_SAMPLES:
        count = min(block_size, INPUT_SAMPLES - start)
        time_axis = (start + np.arange(count, dtype=np.float64)) / SAMPLE_RATE_HZ
        phase = 2.0 * np.pi * 76_000.0 * time_axis - 2.5 * np.cos(
            2.0 * np.pi * 1_000.0 * time_axis
        )
        blocks.append(np.asarray(0.7 * np.exp(1j * phase), dtype=np.complex128))
        start += count

    baseline_rss = _rss_bytes()
    peak_rss = baseline_rss
    stop = threading.Event()

    def sample_memory() -> None:
        nonlocal peak_rss
        while not stop.wait(0.005):
            peak_rss = max(peak_rss, _rss_bytes())

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        result = AnalogMonitor().process_continuous(
            tuple(blocks), AnalogMonitorConfig("nfm", SAMPLE_RATE_HZ, 76_000.0, 16_000.0)
        )
    finally:
        elapsed = time.perf_counter() - started
        stop.set()
        sampler.join()
        peak_rss = max(peak_rss, _rss_bytes())
    rss_increase_mib = max(0.0, (peak_rss - baseline_rss) / (1024.0 * 1024.0))
    passed = bool(
        elapsed <= MAX_PROCESSING_SECONDS
        and (baseline_rss == 0 or rss_increase_mib <= MAX_RSS_INCREASE_MIB)
        and result.input_complex_samples == INPUT_SAMPLES
        and result.audio.size / result.sample_rate_hz >= 4.99
        and len(result.observation_times_s) == 20
        and abs(result.dominant_tone_hz - 1_000.0) <= 1.0
        and result.clipping_count == 0
    )
    return {
        "schema": "monitoring-live-scale-host-v1",
        "requirements": ["5.1.3", "KTR-4.3"],
        "status": "passed" if passed else "failed",
        "hardware_status": "not_exercised",
        "input": {
            "kind": "deterministic_synthetic_nfm",
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "complex_samples": INPUT_SAMPLES,
            "duration_seconds": INPUT_SAMPLES / SAMPLE_RATE_HZ,
            "blocks": len(blocks),
        },
        "result": {
            "processing_seconds": elapsed,
            "maximum_processing_seconds": MAX_PROCESSING_SECONDS,
            "peak_rss_increase_mib": rss_increase_mib if baseline_rss else None,
            "maximum_rss_increase_mib": MAX_RSS_INCREASE_MIB,
            "audio_seconds": result.audio.size / result.sample_rate_hz,
            "dominant_tone_hz": result.dominant_tone_hz,
            "observation_points": len(result.observation_times_s),
            "clipping_count": result.clipping_count,
        },
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
        "claim_boundary": (
            "Bu makinede canlı veri boyutunda host DSP kaynak gözlemidir; HackRF, "
            "FPGA aktarımı, fiziksel ses ve başka bilgisayarlarda süre garantisi değildir."
        ),
    }


def stored_evidence_current() -> bool:
    if not EVIDENCE.is_file():
        return False
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    return bool(
        document.get("status") == "passed"
        and document.get("source_sha256") == {name: _sha256(ROOT / name) for name in SOURCES}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run_benchmark()
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(
            json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    passed = result["status"] == "passed" and stored_evidence_current()
    print(f"PHASE-05 live-scale host benchmark: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
