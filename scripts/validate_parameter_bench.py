"""Independent synthetic characterization of the four product parameter fields.

This is a diagnostic bench, not RF acceptance or a training dataset.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.spectrum import SpectrumConfig
from app.operator_console.measurement_record import measure_and_record, read_measurement, replay_measurement, utc_now

FS = 2_000_000
N = 4096
DF = FS / N


def containment_diagnostic(frames, lower_bin, upper_bin):
    """Characterize whether four frames can prove that an OBW span is complete.

    This diagnostic is deliberately separate from the product estimator.  It
    evaluates a short rectangular-FFT cue and a conservative 16,384-sample
    Hann-periodogram uncertainty bound without changing any product result.
    """
    rectangular = np.mean(np.stack([
        np.abs(np.fft.fftshift(np.fft.fft(np.asarray(frame)))) ** 2
        for frame in frames
    ]), axis=0)
    references = np.r_[
        rectangular[lower_bin - 36:lower_bin - 4],
        rectangular[upper_bin + 5:upper_bin + 37],
    ]
    short_noise = float(np.mean(references))
    short_sigma = short_noise / math.sqrt(len(frames))
    short_excess = np.maximum(rectangular - short_noise - 2.5 * short_sigma, 0.0)
    inside = float(np.sum(short_excess[lower_bin:upper_bin + 1]))
    near = float(
        np.sum(short_excess[max(0, lower_bin - 512):lower_bin])
        + np.sum(short_excess[upper_bin + 1:min(N, upper_bin + 513)])
    )

    x = np.asarray(frames, dtype=np.complex128).reshape(-1)
    x = x - np.mean(x)
    window = np.hanning(x.size)
    long_power = np.abs(np.fft.fftshift(np.fft.fft(x * window))) ** 2
    lower = lower_bin * 4
    upper = upper_bin * 4 + 3
    left = long_power[lower - 144:lower - 20]
    right = long_power[upper + 21:upper + 145]
    left_noise = float(np.median(left) / math.log(2.0))
    right_noise = float(np.median(right) / math.log(2.0))
    noise = max(0.5 * (left_noise + right_noise), np.finfo(float).tiny)
    total = float(np.sum(long_power[lower:upper + 1] - noise))
    far = np.concatenate((
        long_power[80:max(80, lower - 1024)],
        long_power[min(x.size - 80, upper + 1025):x.size - 80],
    ))
    if far.size < 128 or total <= 0.0:
        return {
            "short_rectangular_near_excess_ratio": near / max(inside, np.finfo(float).tiny),
            "long_hann_state": "not_proven",
            "long_hann_tail_upper_bound_fraction": None,
        }
    blocks = np.array_split(far, 8)
    outside_noise = max(
        min(float(np.median(block) / math.log(2.0)) for block in blocks),
        np.finfo(float).tiny,
    )
    inflation = x.size * float(np.sum(window**4)) / float(np.sum(window**2)) ** 2
    reference_size = min(block.size for block in blocks)
    fractions = []
    for outside in (long_power[80:lower], long_power[upper + 1:x.size - 80]):
        excess = float(np.sum(outside) - outside_noise * outside.size)
        uncertainty = 3.0 * outside_noise * math.sqrt(
            inflation * (outside.size + outside.size**2 / reference_size / math.log(2.0) ** 2)
        )
        fractions.append((max(0.0, excess) + uncertainty) / total)
    return {
        "short_rectangular_near_excess_ratio": near / max(inside, np.finfo(float).tiny),
        "long_hann_state": "contained" if max(fractions) <= 0.005 else "not_proven",
        "long_hann_tail_upper_bound_fraction": max(fractions),
    }


def signal(family, seed, snr_db):
    rng = np.random.default_rng(seed)
    t = np.arange(262144) / FS
    offset = 160.25 * DF
    carrier = np.exp(2j * np.pi * offset * t)
    if family == "CW":
        base = np.ones(len(t), complex)
    elif family == "AM":
        base = 1 + .6 * np.cos(2 * np.pi * 3000 * t)
    elif family == "NFM":
        base = np.exp(1j * 2.5 * np.sin(2 * np.pi * 2000 * t))
    else:
        symbols = rng.choice([-1, 1], (len(t) + 99) // 100)
        levels = np.repeat(symbols, 100)[:len(t)]
        base = levels if family == "BPSK" else np.exp(2j * np.pi * np.cumsum(10000 * levels) / FS)
    clean = .15 * base * carrier
    # Independent long-record Hann periodogram; no production PSD/OBW code.
    window = np.hanning(len(clean))
    power = np.abs(np.fft.fftshift(np.fft.fft(clean * window))) ** 2
    frequencies = np.fft.fftshift(np.fft.fftfreq(len(clean), 1 / FS))
    cdf = np.cumsum(power) / power.sum()
    edges = np.interp([.005, .995], cdf, frequencies)
    reference = {
        "emission_center_hz": offset,
        "carrier_offset_hz": offset if family in {"CW", "AM"} else None,
        "power_dbfs": float(10 * np.log10(np.mean(np.abs(clean) ** 2))),
        "input_time_domain_snr_db": float(snr_db),
        "obw99_hz": float(edges[1] - edges[0]),
        "reference_resolution_hz": FS / len(clean),
        "domain": "Analog" if family in {"AM", "NFM"} else "Sayısal" if family in {"BPSK", "FSK"} else None,
    }
    segment = clean[32768:32768 + 4 * N]
    variance = np.mean(np.abs(segment) ** 2) / 10 ** (snr_db / 10)
    observed = segment + np.sqrt(variance / 2) * (rng.normal(size=len(segment)) + 1j * rng.normal(size=len(segment)))
    return tuple(observed.reshape(4, N)), reference


def run(directory):
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for family in ("CW", "AM", "NFM", "BPSK", "FSK"):
        for snr in (12, 24):
            for seed in (73001, 73002, 73003):
                frames, reference = signal(family, seed, snr)
                peak = 2208
                span = AnalysisSpan(peak - 230, peak + 230, "operator_adjusted", 1)
                candidate = MeasurementCandidate(1, 1, peak - 1, peak + 1)
                context = MeasurementContext(1, 1, 1, 1, 1, (True,) * 4, (candidate,))
                intent = MeasurementIntent(1, 1, 1, 1, 1, 0, span, context)
                saved = measure_and_record(intent, frames, sample_rate_hz=FS,
                    center_frequency_hz=700_000_000, spectrum_config=SpectrumConfig(),
                    source={"kind": "synthetic_diagnostic", "family": family, "seed": seed,
                            "snr_db_time_domain": snr, "hardware_capture": False,
                            "owner_binding": "synthetic; detector bypassed"},
                    requested_utc=utc_now(), directory=directory / "records")
                document, _ = read_measurement(saved.path)
                replay_ok = replay_measurement(saved.path) == saved.result
                fields = document["fields"]
                errors = {}
                for name, truth in (("emission_center_frequency", 700_000_000 + reference["emission_center_hz"]),
                                    ("carrier_line_frequency", None if reference["carrier_offset_hz"] is None else 700_000_000 + reference["carrier_offset_hz"]),
                                    ("channel_power_dbfs", reference["power_dbfs"]),
                                    ("occupied_bandwidth", reference["obw99_hz"])):
                    value = fields[name]["value"]
                    errors[name] = None if truth is None or value is None else value - truth
                rows.append({"family": family, "snr_db": snr, "seed": seed,
                             "reference": reference, "fields": fields, "errors": errors,
                             "containment_diagnostic": containment_diagnostic(frames, peak - 230, peak + 230),
                             "record": str(saved.path.relative_to(directory)),
                             "sha256": saved.sha256, "replay_ok": replay_ok})
    summary = {}
    for family in ("CW", "AM", "NFM", "BPSK", "FSK"):
        subset = [r for r in rows if r["family"] == family]
        summary[family] = {"count": len(subset), "domain_outputs": dict(Counter(
            r["fields"]["signal_domain"]["value"] or "Belirsiz" for r in subset))}
        summary[family]["containment_diagnostic"] = {
            "long_hann_states": dict(Counter(
                r["containment_diagnostic"]["long_hann_state"] for r in subset
            )),
            "short_rectangular_near_excess_ratio_range": [
                min(r["containment_diagnostic"]["short_rectangular_near_excess_ratio"] for r in subset),
                max(r["containment_diagnostic"]["short_rectangular_near_excess_ratio"] for r in subset),
            ],
        }
        for field in ("emission_center_frequency", "carrier_line_frequency",
                      "channel_power_dbfs", "occupied_bandwidth"):
            errors = [abs(r["errors"][field]) for r in subset if r["errors"][field] is not None]
            summary[family][field] = {"states": dict(Counter(r["fields"][field]["state"] for r in subset)),
                                     "max_absolute_error": max(errors) if errors else None}
    report = {"schema": "parameter-diagnostic-bench-v1", "created_utc": utc_now(),
              "requirements": ["KTR-4.2", "KTR-4.2-F1"], "hardware_accuracy_proven": False,
              "dbm_calibrated": False, "acceptance": "not_evaluated; diagnostic characterization only",
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "limits": ["No live detector or FPGA exercised", "Only three seeds per family/SNR",
                         "Input time-domain SNR is not compared directly with the in-band spectral SNR estimate",
                         "Long-record spectral OBW reference has finite resolution",
                         "Power reference is total clean signal; finite measurement span can exclude tails",
                         "Containment diagnostics do not alter or validate the locked product method",
                         "The long-Hann bound may abstain when noise uncertainty dominates",
                         "NFM/FSK/BPSK carrier-line applicability not asserted",
                         "No tuning or family-wide accuracy claim from these examples"],
              "summary": summary, "measurements": rows}
    (directory / "report.json").write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Replay: {sum(r['replay_ok'] for r in rows)}/{len(rows)}; report: {directory / 'report.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
