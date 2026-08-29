#!/usr/bin/env python3
"""Verify continuous live HackRF RX through the physical ZedBoard FPGA path."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import queue
import shutil
import sys
import threading
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import (
    P0Channelizer,
    TCPClientIQTransport,
    decode_local_ed_response,
)
from platforms.acquisition import (
    HackRFContinuousRX,
    RXConfig,
    RealHackRFBackend,
    load_ed_rx_config,
)


EVIDENCE_PATH = ROOT / "results/evidence/p0/phase07-live-hackrf-fpga-acceptance.json"
INPUT_CENTER_FREQUENCY_HZ = 103_150_000
OUTPUT_CENTER_FREQUENCY_HZ = 104_650_000
INPUT_SAMPLE_RATE_HZ = 8_000_000
INPUT_SAMPLES_PER_FRAME = 16_384
OUTPUT_SAMPLE_RATE_HZ = 2_000_000
OUTPUT_SAMPLES_PER_FRAME = 4_096
REQUIRED_FRAMES_PER_SECOND = OUTPUT_SAMPLE_RATE_HZ / OUTPUT_SAMPLES_PER_FRAME
ACCEPTANCE_WARMUP_FRAMES = 64
ACCEPTANCE_MEASURED_FRAMES = 4_096
ACCEPTANCE_RUNS = 5
CHANNELIZED_QUEUE_CAPACITY = 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ci8_complex(payload: bytes) -> np.ndarray:
    raw = np.frombuffer(payload, dtype=np.int8)
    if raw.size != INPUT_SAMPLES_PER_FRAME * 2:
        raise RuntimeError("HackRF canlı karesi tam 16.384 kompleks örnek içermiyor.")
    return raw[0::2].astype(np.float64) / 128.0 + 1j * raw[1::2].astype(np.float64) / 128.0


def _run_once(
    *,
    host: str,
    port: int,
    executable: str,
    serial: str,
    warmup_frames: int,
    measured_frames: int,
) -> dict[str, object]:
    total_frames = warmup_frames + measured_frames
    config = RXConfig(
        center_frequency_hz=INPUT_CENTER_FREQUENCY_HZ,
        sample_rate_hz=INPUT_SAMPLE_RATE_HZ,
        sample_count=INPUT_SAMPLES_PER_FRAME,
        rf_amplifier=False,
        lna_gain_db=16,
        vga_gain_db=16,
        device_serial=serial,
    )
    channelizer = P0Channelizer()
    transport = TCPClientIQTransport()
    response_state = {
        "completed": 0,
        "started": None,
        "raw_candidate_total": 0,
        "maximum_active": 0,
        "maximum_ended": 0,
        "response_bytes": 0,
    }
    input_hash = hashlib.sha256()
    input_saturated_components = 0
    output_saturated_components = 0
    processing_seconds = 0.0
    stream_statistics = None
    frame_queue: queue.Queue[object] = queue.Queue(maxsize=CHANNELIZED_QUEUE_CAPACITY)
    producer_error: list[BaseException] = []
    producer_stop = threading.Event()
    end_of_stream = object()
    channelized_queue_high_watermark = 0

    def produce(stream: HackRFContinuousRX) -> None:
        nonlocal input_saturated_components, output_saturated_components
        nonlocal processing_seconds, stream_statistics
        nonlocal channelized_queue_high_watermark
        try:
            for index, payload in enumerate(stream):
                if producer_stop.is_set():
                    return
                input_hash.update(payload)
                raw = np.frombuffer(payload, dtype=np.int8)
                input_saturated_components += int(np.count_nonzero((raw == -128) | (raw == 127)))
                channelized = channelizer.process(
                    _ci8_complex(payload),
                    sequence_number=index,
                    frame_id=index,
                    input_sample_rate_hz=INPUT_SAMPLE_RATE_HZ,
                    input_center_frequency_hz=INPUT_CENTER_FREQUENCY_HZ,
                    output_center_frequency_hz=OUTPUT_CENTER_FREQUENCY_HZ,
                )
                output_saturated_components += channelized.saturated_components
                processing_seconds += channelized.processing_seconds
                while not producer_stop.is_set():
                    try:
                        frame_queue.put(channelized.frame, timeout=0.1)
                        channelized_queue_high_watermark = max(
                            channelized_queue_high_watermark, frame_queue.qsize()
                        )
                        break
                    except queue.Full:
                        continue
            stream_statistics = stream.statistics
        except BaseException as exc:
            producer_error.append(exc)
        finally:
            while not producer_stop.is_set():
                try:
                    frame_queue.put(end_of_stream, timeout=0.1)
                    break
                except queue.Full:
                    continue

    def frames():
        for _ in range(total_frames):
            try:
                item = frame_queue.get(timeout=20.0)
            except queue.Empty as exc:
                raise RuntimeError("Canlı kanal seçici kuyruğu zaman aşımına uğradı.") from exc
            if item is end_of_stream:
                if producer_error:
                    raise RuntimeError("Canlı HackRF üretici aşaması başarısız.") from producer_error[0]
                raise RuntimeError("Canlı HackRF üretici aşaması erken bitti.")
            yield item
        try:
            marker = frame_queue.get(timeout=5.0)
        except queue.Empty as exc:
            raise RuntimeError("Canlı HackRF üretici kapanışı tamamlanmadı.") from exc
        if marker is not end_of_stream:
            raise RuntimeError("Canlı kanal seçici beklenenden fazla kare üretti.")
        if producer_error:
            raise RuntimeError("Canlı HackRF üretici aşaması başarısız.") from producer_error[0]

    def handle_response(response) -> None:
        summary = decode_local_ed_response(response.payload, response.sequence_number)
        if summary.dma_status_flags != 7 or summary.dropped_candidates != 0:
            raise RuntimeError("Canlı HackRF→FPGA karesi DMA veya aday düşümü hatası verdi.")
        response_state["completed"] += 1
        response_state["raw_candidate_total"] += summary.raw_candidate_count
        response_state["maximum_active"] = max(response_state["maximum_active"], summary.active_count)
        response_state["maximum_ended"] = max(response_state["maximum_ended"], summary.ended_count)
        if response_state["completed"] == warmup_frames:
            response_state["started"] = time.perf_counter()
        elif response_state["completed"] > warmup_frames:
            response_state["response_bytes"] += summary.response_bytes

    try:
        transport.connect(host, port, timeout_seconds=3.0)
        with HackRFContinuousRX(executable, config, total_frames) as stream:
            producer = threading.Thread(target=produce, args=(stream,), daemon=True)
            producer.start()
            try:
                completed = transport.exchange_stream(frames(), handle_response)
            except BaseException:
                producer_stop.set()
                stream.close()
                raise
            finally:
                producer.join(timeout=5.0)
            if producer.is_alive():
                producer_stop.set()
                stream.close()
                raise RuntimeError("Canlı HackRF üretici iş parçacığı kapanmadı.")
        if completed != total_frames or response_state["started"] is None:
            raise RuntimeError("Canlı HackRF→FPGA akışı tam kare sayısına ulaşmadı.")
        elapsed = time.perf_counter() - float(response_state["started"])
        statistics = transport.stats
    finally:
        transport.close()

    if stream_statistics is None:
        raise RuntimeError("HackRF canlı RX süreç özeti oluşmadı.")
    frames_per_second = measured_frames / elapsed
    result = {
        "warmup_frames": warmup_frames,
        "measured_frames": measured_frames,
        "completed_frames": completed,
        "elapsed_seconds": elapsed,
        "required_frames_per_second": REQUIRED_FRAMES_PER_SECOND,
        "measured_frames_per_second": frames_per_second,
        "real_time_margin": frames_per_second / REQUIRED_FRAMES_PER_SECOND,
        "hackrf_process_elapsed_seconds": stream_statistics.elapsed_seconds,
        "hackrf_frames_received": stream_statistics.frames_received,
        "hackrf_bytes_received": stream_statistics.bytes_received,
        "hackrf_overruns": stream_statistics.overruns,
        "hackrf_longest_overrun_bytes": stream_statistics.longest_overrun_bytes,
        "hackrf_process_returncode": stream_statistics.process_returncode,
        "input_sha256": input_hash.hexdigest(),
        "input_saturated_components": input_saturated_components,
        "output_saturated_components": output_saturated_components,
        "channelizer_processing_seconds": processing_seconds,
        "channelizer_mean_milliseconds": processing_seconds / total_frames * 1_000.0,
        "channelized_queue_capacity": CHANNELIZED_QUEUE_CAPACITY,
        "channelized_queue_high_watermark": channelized_queue_high_watermark,
        "raw_candidate_total": response_state["raw_candidate_total"],
        "maximum_active": response_state["maximum_active"],
        "maximum_ended": response_state["maximum_ended"],
        "response_bytes": response_state["response_bytes"],
        "transport_frames_sent": statistics.frames_sent,
        "transport_frames_received": statistics.frames_received,
        "transport_sequence_errors": statistics.sequence_errors,
    }
    if (
        not math.isfinite(frames_per_second)
        or frames_per_second < REQUIRED_FRAMES_PER_SECOND
        or stream_statistics.frames_received != total_frames
        or stream_statistics.bytes_received != total_frames * INPUT_SAMPLES_PER_FRAME * 2
        or stream_statistics.overruns != 0
        or stream_statistics.longest_overrun_bytes != 0
        or stream_statistics.process_returncode != 0
        or input_saturated_components != 0
        or output_saturated_components != 0
        or int(response_state["raw_candidate_total"]) <= 0
        or int(response_state["maximum_active"]) <= 0
        or statistics.frames_sent != total_frames
        or statistics.frames_received != total_frames
        or statistics.sequence_errors != 0
    ):
        raise RuntimeError(f"Canlı HackRF→FPGA kabul kapısı başarısız: {result}")
    return result


def evaluate(
    host: str,
    port: int,
    *,
    warmup_frames: int,
    measured_frames: int,
    repeat_runs: int,
) -> dict[str, object]:
    if warmup_frames < 1 or measured_frames < 1 or repeat_runs < 1:
        raise ValueError("Canlı kabul kare ve tekrar sayıları pozitif olmalıdır.")
    config = load_ed_rx_config()
    if config.serial is None:
        raise RuntimeError("ED_RX HackRF seri kimliği atanmamış.")
    physical = RealHackRFBackend()
    inventory = physical.discover_tools(inspect_help=True)
    device = physical.discover_device()
    executable = shutil.which("hackrf_transfer")
    if not inventory.receive_available or executable is None:
        raise RuntimeError("HackRF RX araç zinciri hazır değil.")
    transfer = inventory.get("hackrf_transfer")
    if "-B" not in transfer.supported_options:
        raise RuntimeError("HackRF tampon istatistiği seçeneği doğrulanmadı.")
    if device.state != "ONE_DEVICE" or device.device_count != 1:
        raise RuntimeError("Canlı kabul tam olarak bir HackRF gerektirir.")
    identity = device.devices[0]
    if identity.serial.casefold() != config.serial.casefold():
        raise RuntimeError("Bağlı HackRF, ED_RX seri yapılandırmasıyla eşleşmiyor.")

    runs = [
        _run_once(
            host=host,
            port=port,
            executable=executable,
            serial=config.serial,
            warmup_frames=warmup_frames,
            measured_frames=measured_frames,
        )
        for _ in range(repeat_runs)
    ]
    rates = [float(run["measured_frames_per_second"]) for run in runs]
    sources = (
        ROOT / "algorithms/p0/channelizer.py",
        ROOT / "algorithms/p0/transport.py",
        ROOT / "platforms/acquisition/continuous.py",
        ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c",
        Path(__file__),
    )
    return {
        "schema_version": 1,
        "status": "passed",
        "scope": "kesintisiz fiziksel HackRF RX→PC kanal seçici→Ethernet→ZedBoard DMA→FPGA→ARM kabulü",
        "device": {
            "serial": identity.serial,
            "board_id": identity.board_id,
            "firmware_version": identity.firmware_version,
            "role": config.role,
        },
        "profile": {
            "input_center_frequency_hz": INPUT_CENTER_FREQUENCY_HZ,
            "output_center_frequency_hz": OUTPUT_CENTER_FREQUENCY_HZ,
            "tuning_offset_hz": OUTPUT_CENTER_FREQUENCY_HZ - INPUT_CENTER_FREQUENCY_HZ,
            "input_sample_rate_hz": INPUT_SAMPLE_RATE_HZ,
            "input_samples_per_frame": INPUT_SAMPLES_PER_FRAME,
            "output_sample_rate_hz": OUTPUT_SAMPLE_RATE_HZ,
            "output_samples_per_frame": OUTPUT_SAMPLES_PER_FRAME,
            "rf_amplifier": False,
            "lna_gain_db": 16,
            "vga_gain_db": 16,
            "stdout_stream": True,
            "transmit_enabled": False,
        },
        "repeatability": {
            "runs": repeat_runs,
            "passed_runs": len(runs),
            "warmup_frames_per_run": warmup_frames,
            "measured_frames_per_run": measured_frames,
            "completed_measured_frames": measured_frames * len(runs),
            "minimum_frames_per_second": min(rates),
            "mean_frames_per_second": sum(rates) / len(rates),
            "maximum_frames_per_second": max(rates),
            "minimum_real_time_margin": min(float(run["real_time_margin"]) for run in runs),
            "total_hackrf_overruns": sum(int(run["hackrf_overruns"]) for run in runs),
            "total_transport_sequence_errors": sum(
                int(run["transport_sequence_errors"]) for run in runs
            ),
            "total_raw_candidates": sum(int(run["raw_candidate_total"]) for run in runs),
        },
        "runs": runs,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in sources
        },
        "hackrf_transmit_api_called": False,
        "claim_boundary": (
            "Bu kanıt tek süreçli canlı HackRF RX akışının 8→2 MS/s kanal seçici, "
            "fiziksel Ethernet, kalıcı ZedBoard hizmeti, DMA, FPGA ve ARM yolunda "
            "tekrarlanabilir gerçek zaman kabulünü gösterir. dBm kalibrasyonu, yayın "
            "kimliği, tespit olasılığı, yanlış alarm saha oranı, yön bulma doğruluğu ve "
            "RF yayın işlevleri bu kanıtın dışındadır."
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    warmup = 8 if args.smoke else ACCEPTANCE_WARMUP_FRAMES
    measured = 128 if args.smoke else ACCEPTANCE_MEASURED_FRAMES
    runs = 1 if args.smoke else ACCEPTANCE_RUNS
    if args.write and args.smoke:
        raise SystemExit("Duman testi kalıcı kabul kanıtı olarak yazılamaz.")
    result = evaluate(
        args.host,
        args.port,
        warmup_frames=warmup,
        measured_frames=measured,
        repeat_runs=runs,
    )
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
