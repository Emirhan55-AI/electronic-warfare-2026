"""Taşıyıcı geri kazanımını ARM C çekirdeği ve bağımsız NumPy modeliyle doğrula."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from verify_p0_parameter_runtime import _build, _ci8
from algorithms.parameters.carrier_recovery import recover_carrier
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor
from app.operator_console.measurement_record import read_measurement


def verify(records: list[Path]) -> dict:
    cases = []
    processor = SpectrumProcessor()
    with tempfile.TemporaryDirectory(prefix="carrier-recovery-") as raw:
        directory = Path(raw)
        executable, state_executable, compiler = _build(directory)
        subprocess.run([str(state_executable)], check=True, capture_output=True)

        def run(name, frames, rate, center, lower, upper, truth=None):
            paths, decoded = [], []
            for index, frame in enumerate(frames):
                iq, ci8_frame = _ci8(frame)
                decoded.append(ci8_frame)
                spectrum = processor.process(ci8_frame, sample_rate_hz=rate, center_frequency_hz=center)
                power = np.rint(np.asarray(spectrum.fft_power_unshifted) * (1 << 30)).astype("<u8")
                iq_path, power_path = directory / f"{index}.iq", directory / f"{index}.power"
                iq_path.write_bytes(iq)
                power_path.write_bytes(power.tobytes())
                paths.extend((iq_path, power_path))
            result_path = directory / "result.json"
            subprocess.run([
                str(executable), str(rate), str(center), str(lower), str(upper),
                *map(str, paths), str(result_path),
            ], env={**os.environ, "P0_PARAMETER_RECOVERY": "1"}, check=True, capture_output=True)
            actual = json.loads(result_path.read_text(encoding="utf-8"))
            reference = None
            if (actual["lower_occupied_edge_hz"]["state"] == 1
                    and actual["upper_occupied_edge_hz"]["state"] == 1
                    and actual["snr_estimate_db"]["state"] == 1
                    and actual["carrier_line_frequency_hz"]["state"] != 1):
                reference = recover_carrier(
                    decoded, sample_rate_hz=rate, center_frequency_hz=center,
                    lower_shifted_bin=lower, upper_shifted_bin=upper,
                    lower_band_edge_hz=actual["lower_occupied_edge_hz"]["value"],
                    upper_band_edge_hz=actual["upper_occupied_edge_hz"]["value"],
                    snr_db=actual["snr_estimate_db"]["value"],
                )
                observed = actual["recovered_carrier_frequency_hz"]["state"] == 1
                assert observed == (reference.frequency_hz is not None), (name, actual, reference)
                if observed:
                    assert actual["carrier_recovery_order"] == reference.order
                    assert abs(actual["recovered_carrier_frequency_hz"]["value"] - reference.frequency_hz) < 0.01
            else:
                assert actual["recovered_carrier_frequency_hz"]["state"] != 1
            recovered = actual["recovered_carrier_frequency_hz"]
            if truth is False:
                assert recovered["state"] != 1, (name, actual)
            elif isinstance(truth, float) and recovered["state"] == 1:
                assert abs(recovered["value"] - truth) < 0.05 * rate / 4096, (name, actual)
            item = {"name": name, "rate_hz": rate, "center_hz": center,
                    "span": [lower, upper], "actual": actual,
                    "reference": asdict(reference) if reference else None,
                    "truth_frequency_hz": truth}
            cases.append(item)
            return actual

        catalog = load_parameter_catalog()
        for rate in (2_000_000, 8_000_000):
            for snr in (6.0, 12.0):
                for scene_id in ("bpsk", "qpsk", "dsb-sc", "two-fsk", "wideband-noise-like"):
                    scene = next(item for item in catalog["scenes"] if item["id"] == scene_id)
                    band = scene["band_definition"]
                    center_bin = 2048 + scene.get("signed_center_bin", 0)
                    if "lower_offset_bins" in band:
                        lower = int(np.floor(center_bin + band["lower_offset_bins"] - 20))
                        upper = int(np.ceil(center_bin + band["upper_offset_bins"] + 20))
                    else:
                        lower = int(np.floor(band["lower_shifted_edge"] - 20))
                        upper = int(np.ceil(band["upper_shifted_edge"] + 20))
                    for seed in range(3):
                        frames = tuple(generate_parameter_scene(
                            scene_id, trial_index=seed, frame_index=index,
                            scene_seed_override=2026091800 + 101 * seed,
                            clean_power_dbfs=-24, snr_db=snr, catalog=catalog,
                        ).samples for index in range(16))
                        truth = (False if scene_id in ("two-fsk", "wideband-noise-like") else
                                 float(431_000_000 + scene["signed_center_bin"] * rate / 4096))
                        run(f"{scene_id}-{rate}-{snr}-{seed}", frames, rate,
                            431_000_000, lower, upper, truth)

        # Broad, stationary real-valued baseband recovers through squaring;
        # quarter-window jumps and circular noise must never acquire a carrier.
        rng = np.random.default_rng(2026091842)
        rate = 2_000_000
        t = np.arange(16 * 4096) / rate
        base = rng.normal(size=len(t))
        spectrum = np.fft.fft(base)
        spectrum[abs(np.fft.fftfreq(len(t), 1 / rate)) > 150_000] = 0
        base = np.fft.ifft(spectrum).real
        base *= 0.08 / np.sqrt(np.mean(base ** 2))
        noise = 0.02 / np.sqrt(2) * (rng.normal(size=len(t)) + 1j * rng.normal(size=len(t)))
        stable = (base * np.exp(2j * np.pi * 40_000 * t) + noise).reshape(16, 4096)
        stable_result = run("broad-suppressed-carrier", stable, rate, 913_000_000, 1700, 2600, 913_040_000.0)
        assert stable_result["recovered_carrier_frequency_hz"]["state"] == 1
        jumps = np.repeat([-50_000, 0, 50_000, 100_000], 4 * 4096)
        jumping = (base * np.exp(2j * np.pi * jumps * t) + noise).reshape(16, 4096)
        run("frequency-jump", jumping, rate, 913_000_000, 1400, 2900, False)
        run("circular-noise", (noise * 4).reshape(16, 4096), rate, 913_000_000, 1400, 2900, False)
        low_snr = (base * np.exp(2j * np.pi * 40_000 * t) + noise * 10).reshape(16, 4096)
        run("low-snr", low_snr, rate, 913_000_000, 1700, 2600, False)

        for path in records:
            document, frames = read_measurement(path)
            span = document["intent"]["span"]
            run(path.name, frames, int(document["sample_rate_hz"]),
                int(document["center_frequency_hz"]), span["lower_shifted_bin"], span["upper_shifted_bin"])

    recovered_count = sum(item["actual"]["recovered_carrier_frequency_hz"]["state"] == 1 for item in cases)
    assert recovered_count > 0
    return {
        "status": "passed", "compiler": compiler, "cases": cases,
        "case_count": len(cases), "recovered_count": recovered_count,
        "physical_execution": False, "rf_accuracy_acceptance": False,
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ("platforms/embedded/p0/src/p0_parameter_runtime.c",
                                       "platforms/embedded/p0/include/p0_parameter_runtime.h",
                                       "platforms/embedded/p0/src/p0_parameter_run.c",
                                       "tests/p0/p0_parameter_runtime_test.c",
                                       "algorithms/parameters/carrier_recovery.py", "scripts/verify_carrier_recovery.py")},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("status", "case_count", "recovered_count")}, ensure_ascii=False))
