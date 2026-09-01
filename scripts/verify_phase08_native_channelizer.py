"""Reproducible native channelizer equivalence and latency evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from algorithms.p0 import (
    NativeP0Channelizer,
    P0Channelizer,
    find_native_channelizer_library,
    native_channelizer_cpu_supported,
)


SOURCES = (
    "algorithms/p0/channelizer.py",
    "algorithms/p0/native_channelizer.py",
    "algorithms/p0/native/CMakeLists.txt",
    "algorithms/p0/native/channelizer_native.cpp",
    "app/operator_console/live_ed.py",
    "scripts/verify_phase08_native_channelizer.py",
    "tests/test_p0_native_channelizer.py",
)


def main() -> int:
    output = ROOT / "results/evidence/phase08/native-channelizer-v3.json"
    if output.exists():
        raise SystemExit("Var olan kanıtın üzerine yazılmaz.")
    library = find_native_channelizer_library()
    if library is None:
        raise SystemExit("Önce Release p0_channelizer kitaplığını derleyin.")
    source_bytes = {name: (ROOT / name).read_bytes() for name in SOURCES}
    rng = np.random.default_rng(20260831)
    comparisons = []
    exact = True
    for offset_hz in (1_250_000, 1_300_000, 1_500_000, 2_750_000, -1_500_000):
        reference, native = P0Channelizer(), NativeP0Channelizer(library_path=library)
        maximum_lsb_error = 0
        for sequence in range(16):
            payload = rng.integers(-64, 65, 32_768, dtype=np.int8).tobytes()
            arguments = dict(
                sequence_number=sequence,
                frame_id=sequence,
                input_sample_rate_hz=8_000_000,
                input_center_frequency_hz=100_000_000,
                output_center_frequency_hz=100_000_000 + offset_hz,
            )
            expected, _ = reference.process_ci8(payload, **arguments)
            observed, _ = native.process_ci8(payload, **arguments)
            error = int(np.max(np.abs(
                np.frombuffer(expected.frame.payload, dtype=np.int8).astype(np.int16)
                - np.frombuffer(observed.frame.payload, dtype=np.int8).astype(np.int16)
            )))
            maximum_lsb_error = max(maximum_lsb_error, error)
        comparisons.append({"offset_hz": offset_hz, "frames": 16, "maximum_lsb_error": maximum_lsb_error})
        exact &= maximum_lsb_error == 0

    payload = rng.integers(-64, 65, 32_768, dtype=np.int8).tobytes()
    native = NativeP0Channelizer(library_path=library)
    samples_ms = []
    for sequence in range(2_000):
        started = time.perf_counter()
        native.process_ci8(
            payload,
            sequence_number=sequence,
            frame_id=sequence,
            input_sample_rate_hz=8_000_000,
            input_center_frequency_hz=100_000_000,
            output_center_frequency_hz=101_500_000,
        )
        samples_ms.append((time.perf_counter() - started) * 1_000.0)
    p95_ms = float(np.percentile(samples_ms, 95))
    checks = {
        "runtime_supports_avx2_and_fma3": native_channelizer_cpu_supported(),
        "ci8_exact_against_numpy_reference": exact,
        "all_locked_offsets_covered": len(comparisons) == 5,
        "standalone_p95_below_2_048ms_input_period": p95_ms < 2.048,
    }
    report = {
        "schema": "phase08-native-channelizer-evidence-v3",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "comparison": comparisons,
        "latency_ms": {
            "samples": len(samples_ms),
            "p50": float(np.percentile(samples_ms, 50)),
            "p95": p95_ms,
            "maximum": max(samples_ms),
        },
        "input_period_ms": 2.048,
        "library": {
            "path": str(library.resolve()),
            "sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        },
        "limits": [
            "Tek başına mikro ölçüm bütün uygulamanın gerçek zamanlı olduğunu kanıtlamaz.",
            "Fiziksel HackRF ve GUI kabulü ayrı uzun süreli koşuyla yapılır.",
        ],
        "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in source_bytes.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "checks", "latency_ms")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
