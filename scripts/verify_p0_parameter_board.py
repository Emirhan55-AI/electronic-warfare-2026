#!/usr/bin/env python3
"""Verify recorded CI8 -> physical PL -> ARM numeric parameter equivalence."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.p0 import IQFrame, TCPClientIQTransport, decode_local_ed_response
from algorithms.p0.detection_config import exchange_profile
from algorithms.p0.parameter_client import encode_request, measure_on_board
from algorithms.parameters.f1_development import _intent, _truth
from algorithms.parameters.f5_estimator import F5ParameterEstimator
from algorithms.parameters.scenes import generate_parameter_scene, load_parameter_catalog
from algorithms.spectrum import SpectrumProcessor

SAMPLE_RATE = 2_000_000
CENTER = 100_000_000
SCENES = ("tone-bin-centered", "tone-off-bin", "am-carrier", "nfm",
          "wideband-noise-like", "dsb-sc")
FIELDS = ("emission_center_frequency", "carrier_line_frequency", "lower_band_edge",
          "upper_band_edge", "occupied_bandwidth", "channel_power_dbfs", "snr_estimate_db")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ci8(samples: np.ndarray) -> tuple[bytes, np.ndarray]:
    values = np.stack((samples.real, samples.imag), axis=1) * 128.0
    raw = np.clip(np.rint(values), -128, 127).astype(np.int8)
    decoded = raw[:, 0].astype(float) / 128 + 1j * raw[:, 1].astype(float) / 128
    return raw.tobytes(), decoded


def one_case(host: str, port: int, scene: str, seed: int) -> dict:
    catalog = load_parameter_catalog()
    processor = SpectrumProcessor()
    generated = tuple(generate_parameter_scene(scene, trial_index=0, condition_index=3,
        frame_index=index, clean_power_dbfs=-18.0, snr_db=12.0, catalog=catalog,
        scene_seed_override=seed) for index in range(4))
    clean = tuple(processor.process(frame.clean_samples, sample_rate_hz=SAMPLE_RATE,
        center_frequency_hz=CENTER) for frame in generated)
    span = tuple(int(value) for value in _truth(clean, 12)["span"])
    raws, samples, spectra = [], [], []
    for frame in generated:
        raw, decoded = ci8(np.asarray(frame.samples, dtype=np.complex128))
        raws.append(raw); samples.append(decoded)
        spectra.append(processor.process(decoded, sample_rate_hz=SAMPLE_RATE,
                                         center_frequency_hz=CENTER))
    intent = _intent(span, 1, 1)
    expected = F5ParameterEstimator().measure(intent, tuple(samples), tuple(spectra))
    board = measure_on_board(host, port, intent, b"".join(raws),
                             sample_rate_hz=SAMPLE_RATE, center_frequency_hz=CENTER)
    comparisons = {}
    for name in FIELDS:
        reference = getattr(expected, name)
        actual = getattr(board.result, name)
        if actual.state != reference.state:
            raise AssertionError(f"{scene} {name} state {actual.state} != {reference.state}")
        item = {"state": actual.state}
        if actual.state == "valid":
            error = abs(float(actual.value) - float(reference.value))
            tolerance = 2.0 if name.endswith("frequency") or "edge" in name else (
                        4.0 if name == "occupied_bandwidth" else 0.02)
            if error > tolerance:
                raise AssertionError(f"{scene} {name} error {error} > {tolerance}")
            item.update(reference=float(reference.value), board=float(actual.value),
                        absolute_error=error, tolerance=tolerance)
        comparisons[name] = item
    return {"scene": scene, "span": span, "elapsed_us": board.elapsed_us,
            "profile_generation": board.profile_generation,
            "response_sha256": hashlib.sha256(board.response).hexdigest(),
            "fields": comparisons}


def transport_probe(host: str, port: int, sequence: int) -> dict:
    transport = TCPClientIQTransport()
    try:
        transport.connect(host, port, timeout_seconds=10)
        response = transport.exchange(IQFrame(sequence, SAMPLE_RATE, CENTER,
                                               bytes([1, 2]) * 4096, frame_id=sequence))
        decoded = decode_local_ed_response(response.payload, sequence)
    finally:
        transport.close()
    return {"frame_id": decoded.frame_id, "dma_status_flags": decoded.dma_status_flags,
            "transport": asdict(transport.stats)}


def verify(host: str, port: int, products: Path) -> dict:
    profile_before = exchange_profile(host, port)
    if profile_before.fft_size != 4096:
        raise AssertionError("parameter measurement requires the 4096 FPGA FFT profile")
    before = transport_probe(host, port, 0)
    cases = [one_case(host, port, scene, 3502604761305545000 + index)
             for index, scene in enumerate(SCENES)]
    intent = _intent((2280, 2328), 1, 1)
    request = bytearray(encode_request(intent, bytes(32768), SAMPLE_RATE, CENTER, 19))
    request[-1] ^= 1
    with socket.create_connection((host, port), timeout=5) as connection:
        connection.sendall(request)
        corrupt_rejected = connection.recv(176) == b""
    profile_after = exchange_profile(host, port)
    after = transport_probe(host, port, 0)
    if not corrupt_rejected or before["dma_status_flags"] != 7 or after["dma_status_flags"] != 7:
        raise AssertionError("fail-closed or post-measurement detection probe failed")
    if profile_after != profile_before:
        raise AssertionError("parameter measurement changed the FPGA profile")
    sources = [ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
               ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
               ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
               ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c",
               ROOT / "platforms/embedded/p0/include/p0_parameter_runtime.h",
               ROOT / "platforms/embedded/p0/include/p0_ed_service_protocol.h",
               ROOT / "algorithms/p0/parameter_client.py", Path(__file__).resolve()]
    return {"schema_version": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed", "scope": "physical PL and ZedBoard ARM numeric integration",
        "requirements": ["KTR-4.2", "PÇ-02", "PÇ-04"],
        "profile_before": asdict(profile_before), "profile_after": asdict(profile_after),
        "cases": cases, "corrupt_payload_rejected": corrupt_rejected,
        "normal_detection_before": before, "normal_detection_after": after,
        "products": {name: sha(products / name) for name in ("p0-ed-service", "p0-ed-network-bridge")},
        "sources": {path.relative_to(ROOT).as_posix(): sha(path) for path in sources},
        "not_verified": ["live HackRF RF accuracy", "dBm calibration", "cold boot persistence",
                         "analog/digital classification", "field Pd/Pfa"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--products", type=Path,
        default=ROOT / "build/p0/parameter-board-v1-20260911")
    args = parser.parse_args()
    result = verify(args.host, args.port, args.products)
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream: stream.write(payload)
        with zipfile.ZipFile(args.output.with_suffix(".zip"), "x", zipfile.ZIP_STORED) as archive:
            archive.writestr(args.output.name, payload)
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "elapsed_us": [case["elapsed_us"] for case in result["cases"]]}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
