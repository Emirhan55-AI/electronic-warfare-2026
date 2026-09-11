"""Run the current listening DSP on the preserved physical NFM replay capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.monitoring import AnalogMonitor, AnalogMonitorConfig
from algorithms.p0 import create_realtime_channelizer, find_native_channelizer_library
from platforms.acquisition import decode_ci8


ARCHIVE = ROOT / "results/evidence/phase08/replay-nfmg8-evaluation-20260909.zip"
EVIDENCE = ROOT / "results/evidence/phase05/real-nfm-replay-monitoring-20260911.json"
CAPTURE_MEMBER = "./capture/rx.ci8"
CAPTURE_METADATA_MEMBER = "./capture/capture.json"
INPUT_CENTER_HZ = 825_300_000
OUTPUT_CENTER_HZ = 824_989_819
REFERENCE_FREQUENCY_HZ = 824_989_819.3359375
REFERENCE_TONE_HZ = 1_700.0
START_SECONDS = 21.75
INPUT_FRAMES = 2_442
INPUT_SAMPLES_PER_FRAME = 16_384
OUTPUT_SAMPLES_PER_FRAME = 4_096
RAW_SHA256 = "e7d54711a000944fc02f3224a976709b85b9a990c3be1c204a0518fa53bc0e06"
SOURCES = (
    "algorithms/monitoring/models.py",
    "algorithms/monitoring/dsp.py",
    "algorithms/p0/channelizer.py",
    "algorithms/p0/native_channelizer.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def build_evidence() -> dict[str, object]:
    native_library = find_native_channelizer_library()
    if native_library is None:
        raise RuntimeError("Tekrarlanabilir gerçek kayıt tanısı için yerel kanal seçici gerekli.")
    channelizer = create_realtime_channelizer()
    if getattr(channelizer, "backend_name", "") != "native-cpp":
        raise RuntimeError("Gerçek kayıt tanısı beklenen yerel kanal seçiciyi kullanmıyor.")

    grouped_payload = bytearray()
    blocks: list[np.ndarray] = []
    saturated_input = 0
    saturated_output = 0
    with zipfile.ZipFile(ARCHIVE) as archive:
        metadata = json.loads(archive.read(CAPTURE_METADATA_MEMBER))
        if metadata.get("raw_sha256") != RAW_SHA256 or not metadata.get("transport_valid"):
            raise RuntimeError("Korunan gerçek kayıt kimliği veya taşıma durumu eşleşmiyor.")
        with archive.open(CAPTURE_MEMBER) as stream:
            start_byte = round(START_SECONDS * 8_000_000) * 2
            stream.seek(start_byte)
            for frame_index in range(INPUT_FRAMES):
                payload = stream.read(INPUT_SAMPLES_PER_FRAME * 2)
                if len(payload) != INPUT_SAMPLES_PER_FRAME * 2:
                    raise RuntimeError("Gerçek NFM kaydı seçilen beş saniyelik aralıkta kısa kaldı.")
                channelized, input_rails = channelizer.process_ci8(
                    payload,
                    sequence_number=frame_index,
                    frame_id=frame_index,
                    input_sample_rate_hz=8_000_000,
                    input_center_frequency_hz=INPUT_CENTER_HZ,
                    output_center_frequency_hz=OUTPUT_CENTER_HZ,
                    require_dc_safe_tuning=False,
                )
                saturated_input += int(input_rails)
                saturated_output += int(channelized.saturated_components)
                grouped_payload.extend(channelized.frame.payload)
                if (frame_index + 1) % 123 == 0 or frame_index + 1 == INPUT_FRAMES:
                    blocks.append(decode_ci8(
                        bytes(grouped_payload),
                        expected_complex_samples=len(grouped_payload) // 2,
                    ))
                    grouped_payload.clear()

    result = AnalogMonitor().process_continuous(
        tuple(blocks),
        AnalogMonitorConfig(
            "nfm",
            2_000_000.0,
            REFERENCE_FREQUENCY_HZ - OUTPUT_CENTER_HZ,
            25_000.0,
        ),
    )
    tone_error_hz = abs(result.dominant_tone_hz - REFERENCE_TONE_HZ)
    passed = bool(
        result.input_complex_samples == INPUT_FRAMES * OUTPUT_SAMPLES_PER_FRAME
        and result.audio.size / result.sample_rate_hz >= 4.99
        and len(result.observation_times_s) == 20
        and tone_error_hz <= 10.0
        and result.clipping_count == 0
        and saturated_input == 0
        and saturated_output == 0
        and math.isfinite(result.rf_power_dbfs)
    )
    return {
        "schema": "phase05-real-nfm-replay-monitoring-v1",
        "requirements": ["5.1.3", "KTR-4.3"],
        "status": "diagnostic_passed" if passed else "diagnostic_failed",
        "source": {
            "kind": "physical_hackrf_capture_of_synthetic_nfm_replay",
            "archive_sha256": _sha256(ARCHIVE),
            "raw_member_sha256": RAW_SHA256,
            "input_center_frequency_hz": INPUT_CENTER_HZ,
            "reference_frequency_hz": REFERENCE_FREQUENCY_HZ,
            "start_seconds": START_SECONDS,
            "duration_seconds": INPUT_FRAMES * INPUT_SAMPLES_PER_FRAME / 8_000_000.0,
            "reference_content": "1700 Hz tone, 6000 Hz peak-deviation synthetic NFM replayed over RF",
        },
        "processing": {
            "channelizer": getattr(channelizer, "backend_name", "unknown"),
            "channelizer_binary_sha256": _sha256(native_library),
            "output_sample_rate_hz": 2_000_000,
            "output_complex_samples": result.input_complex_samples,
            "input_saturated_components": saturated_input,
            "output_saturated_components": saturated_output,
            "demodulation": "NFM phase difference with 750 us de-emphasis",
            "channel_bandwidth_hz": 25_000,
        },
        "result": {
            "audio_sample_rate_hz": result.sample_rate_hz,
            "audio_seconds": result.audio.size / result.sample_rate_hz,
            "dominant_tone_hz": result.dominant_tone_hz,
            "reference_tone_hz": REFERENCE_TONE_HZ,
            "tone_error_hz": tone_error_hz,
            "channel_power_dbfs": result.rf_power_dbfs,
            "power_range_dbfs": [
                min(result.channel_power_dbfs_trace),
                max(result.channel_power_dbfs_trace),
            ],
            "residual_frequency_range_hz": [
                min(result.residual_frequency_hz_trace),
                max(result.residual_frequency_hz_trace),
            ],
            "observation_points": len(result.observation_times_s),
            "clipping_count": result.clipping_count,
            "pcm16_sha256": hashlib.sha256(result.pcm16).hexdigest(),
        },
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
        "product_acceptance": False,
        "physical_acceptance": False,
        "claim_boundary": (
            "Korunmuş fiziksel HackRF kaydındaki sentetik 1700 Hz NFM tekrarının güncel host "
            "kanal seçici ve dinleme DSP'siyle tanısıdır. Canlı FPGA olay bağı, gerçek konuşma "
            "anlaşılırlığı, amatör telsiz profili veya saha kabulü değildir."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = build_evidence()
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_bytes(_canonical(current))
    passed = (
        current["status"] == "diagnostic_passed"
        and EVIDENCE.is_file()
        and EVIDENCE.read_bytes() == _canonical(current)
    )
    print(f"KTR-4.3 preserved real NFM diagnostic: {'passed' if passed else 'failed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
