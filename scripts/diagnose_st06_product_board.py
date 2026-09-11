"""Deterministik dijital I/Q ile kart hizmeti tanısı; RF yayın yolu içermez."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.p0 import IQFrame, TCPClientIQTransport
from app.operator_console.live_ed import decode_live_ed_response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=("zero", "independent_noise",
                                           "tone_independent_noise",
                                           "wide_independent_noise",
                                           "repeated_tone_throughput"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(6100602)
    sample = np.arange(4096)
    tone = 32 * np.exp(2j * np.pi * 1024 * sample / 4096)

    def encode(values: np.ndarray) -> bytes:
        components = np.column_stack((values.real, values.imag)).round()
        if np.max(np.abs(components)) > 127:
            raise ValueError("Tanı girdisi kırpılıyor.")
        return components.astype(np.int8).tobytes()

    def noise() -> np.ndarray:
        return rng.normal(0, 2, 4096) + 1j * rng.normal(0, 2, 4096)

    cases = {"zero": [bytes(8192)] * 256,
             "independent_noise": [encode(noise()) for _ in range(256)],
             "tone_independent_noise": [encode(tone + noise()) for _ in range(256)]}
    wide = []
    for _ in range(256):
        spectrum = np.zeros(4096, dtype=complex)
        spectrum[252:452] = (rng.normal(size=200) + 1j * rng.normal(size=200)) * 1800
        wide.append(encode(np.fft.ifft(spectrum) + noise()))
    cases["wide_independent_noise"] = wide
    # Aynı kareyi tekrarlayan hız yükü doğruluk/Pfa popülasyonu değildir.
    cases["repeated_tone_throughput"] = [cases["tone_independent_noise"][0]] * 4160
    if args.case is not None:
        cases = {args.case: cases[args.case]}
    report = {"schema_version": 1, "seed": 6100602,
              "scope": "physical_board_digital_iq_diagnostic_not_rf_acceptance",
              "sample_rate_hz": 2000000, "samples_per_frame": 4096,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "cases": {}}
    for name, payloads in cases.items():
        stimulus_frames = len(payloads)
        payloads = payloads + [bytes(8192)] * 16
        input_path = args.output / f"{name}.ci8"
        input_path.write_bytes(b"".join(payloads))
        rows = []
        responses = []
        times = []
        transport = TCPClientIQTransport()
        transport.connect(args.host, 47007, timeout_seconds=5)
        frames = [IQFrame(sequence_number=i, frame_id=i, sample_rate_hz=2000000,
                          center_frequency_hz=101500000, payload=payload)
                  for i, payload in enumerate(payloads)]

        def receive(response):
            times.append(time.perf_counter())
            decoded = decode_live_ed_response(response.payload, response.sequence_number)
            rows.append(asdict(decoded))
            responses.append(len(response.payload).to_bytes(4, "little") + response.payload)

        try:
            started = time.perf_counter()
            transport.exchange_stream(frames, receive)
            elapsed = time.perf_counter() - started
        finally:
            transport.close()
            (args.output / f"{name}.frames.json").write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            (args.output / f"{name}.responses.bin").write_bytes(b"".join(responses))
        (args.output / f"{name}.arrival-times.json").write_text(
            json.dumps(times), encoding="utf-8")
        measured = rows[:stimulus_frames]
        confirmed = {e["event_id"] for r in measured for e in r["active"]
                     if e["state"] == "confirmed"}
        summary = {
            "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "response_sha256": hashlib.sha256(b"".join(responses)).hexdigest(),
            "stimulus_frames": stimulus_frames, "zero_tail_frames": 16,
            "received_frames": len(rows), "elapsed_seconds": elapsed,
            "max_raw_candidates": max(r["raw_candidate_count"] for r in measured),
            "max_active_events": max(len(r["active"]) for r in measured),
            "distinct_confirmed_events": len(confirmed),
            "dropped_candidates_total": sum(r["dropped_candidates"] for r in rows),
            "dma_bad_frames": sum(r["dma_status_flags"] != 7 for r in rows),
            "reset_frames": [r["frame_id"] for r in rows if r["reset_applied"]],
            "last_active_count": len(rows[-1]["active"]),
            "first_empty_tail_offset": next((i for i, r in enumerate(rows[stimulus_frames:])
                                             if not r["active"]), None),
            "transport": asdict(transport.stats),
        }
        if name == "repeated_tone_throughput":
            summary["measured_fps_after_64_warmup"] = 4096 / (times[4159] - times[63])
            summary["required_fps"] = 2000000 / 4096
        if name == "tone_independent_noise":
            summary["confirmed_target_frames"] = sum(any(
                e["state"] == "confirmed" and e["start_shifted_bin"] <= 3072 <= e["end_shifted_bin"]
                for e in r["active"]) for r in measured)
        if name == "wide_independent_noise":
            summary["confirmed_wide_target_frames"] = sum(any(
                e["state"] == "confirmed" and e["flags"] & 16 and
                e["start_shifted_bin"] <= 2400 <= e["end_shifted_bin"]
                for e in r["active"]) for r in measured)
        report["cases"][name] = summary
        (args.output / "summary.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(name, json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
