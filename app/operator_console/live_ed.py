"""Bounded live HackRF-to-FPGA receive session used by the operator product."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from collections import OrderedDict, deque
import hashlib
import math
import queue
import struct
import threading
import time
from typing import Callable, Protocol

import numpy as np

from algorithms.p0.native_channelizer import create_realtime_channelizer
from algorithms.p0.transport import (
    IQFrame,
    IQResponse,
    TCPClientIQTransport,
    TransportError,
    TransportStats,
    decode_local_ed_response,
)

from platforms.acquisition.continuous import (
    MAX_STREAM_FRAMES,
    HackRFContinuousRX,
    HackRFStreamStatistics,
)
from platforms.acquisition.contracts import AcquisitionError, RXConfig


LIVE_INPUT_SAMPLE_RATE_HZ = 8_000_000
LIVE_INPUT_SAMPLES_PER_FRAME = 16_384
LIVE_OUTPUT_SAMPLE_RATE_HZ = 2_000_000
LIVE_OUTPUT_SAMPLES_PER_FRAME = 4_096
LIVE_TUNING_OFFSET_HZ = 1_500_000
LIVE_MIN_TUNING_OFFSET_HZ = 1_250_000
LIVE_MAX_TUNING_OFFSET_HZ = 2_750_000
LIVE_DEFAULT_LNA_GAIN_DB = 32
LIVE_DEFAULT_VGA_GAIN_DB = 32
LIVE_USABLE_HALF_BAND_HZ = 700_000
LIVE_BOARD_HOST = "192.168.7.2"
LIVE_BOARD_PORT = 47_007
LIVE_REQUIRED_FRAMES_PER_SECOND = LIVE_OUTPUT_SAMPLE_RATE_HZ / LIVE_OUTPUT_SAMPLES_PER_FRAME
LIVE_CAPTURE_QUEUE_CAPACITY = 512
LIVE_CHANNEL_QUEUE_CAPACITY = 64
LIVE_MAX_DISPLAY_INTERVAL_FRAMES = 65_536
LOCAL_RESPONSE_HEADER_BYTES = 48
LOCAL_RESULT_HEADER_BYTES = 20
LOCAL_EVENT_BYTES = 68
LOCAL_MAX_EVENTS = 64
LOCAL_EVENT_RECORD_VALID = 0x01
LOCAL_EVENT_EVALUATE_CENTER = 0x02
LOCAL_EVENT_WEAK_EVIDENCE = 0x04
LOCAL_EVENT_SINGLE_FRAME_CONFIDENT = 0x08
LOCAL_EVENT_WIDEBAND_EVIDENCE = 0x10
LOCAL_EVENT_ALLOWED_FLAGS = 0x1F
LIVE_MEASUREMENT_WINDOW_FRAMES = 4
LIVE_MEASUREMENT_WINDOW_CAPACITY = 64
LIVE_AUDIO_WINDOW_SECONDS = 5.0
LIVE_AUDIO_WINDOW_FRAMES = math.ceil(
    LIVE_AUDIO_WINDOW_SECONDS * LIVE_OUTPUT_SAMPLE_RATE_HZ / LIVE_OUTPUT_SAMPLES_PER_FRAME
)


@dataclass(frozen=True)
class LiveEDConfiguration:
    output_center_frequency_hz: int
    device_serial: str
    lna_gain_db: int = LIVE_DEFAULT_LNA_GAIN_DB
    vga_gain_db: int = LIVE_DEFAULT_VGA_GAIN_DB
    frame_count: int = 4_096
    board_host: str = LIVE_BOARD_HOST
    board_port: int = LIVE_BOARD_PORT
    display_interval_frames: int = 15
    input_center_frequency_hz_override: int | None = None
    fpga_enabled: bool = True
    assess_receive_level: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.assess_receive_level, bool):
            raise AcquisitionError("invalid_rx_config", "Alım seviyesi denetim modu geçersizdir.")
        if not isinstance(self.fpga_enabled, bool):
            raise AcquisitionError("invalid_rx_config", "FPGA alım modu geçersizdir.")
        if isinstance(self.output_center_frequency_hz, bool) or not isinstance(
            self.output_center_frequency_hz, int
        ):
            raise AcquisitionError("invalid_center_frequency", "İzleme merkez frekansı tam sayı Hz olmalıdır.")
        if not 1_000_000 <= self.output_center_frequency_hz <= 6_000_000_000:
            raise AcquisitionError("invalid_center_frequency", "İzleme merkez frekansı HackRF sınırının dışındadır.")
        if not 1 <= self.frame_count <= MAX_STREAM_FRAMES:
            raise AcquisitionError("invalid_stream_length", "Canlı oturum kare sayısı güvenli sınırın dışındadır.")
        if not 1 <= self.display_interval_frames <= LIVE_MAX_DISPLAY_INTERVAL_FRAMES:
            raise AcquisitionError("invalid_display_interval", "Canlı görünüm aralığı geçersizdir.")
        if not self.board_host or not 1 <= self.board_port <= 65_535:
            raise AcquisitionError("invalid_endpoint", "ZedBoard ağ uç noktası geçersizdir.")
        if self.input_center_frequency_hz_override is not None:
            input_center = self.input_center_frequency_hz_override
            if isinstance(input_center, bool) or not isinstance(input_center, int):
                raise AcquisitionError(
                    "invalid_input_center_frequency",
                    "Alıcı merkez frekansı tam sayı Hz olmalıdır.",
                )
            if not 1_000_000 <= input_center <= 6_000_000_000:
                raise AcquisitionError(
                    "invalid_input_center_frequency",
                    "Alıcı merkez frekansı HackRF sınırının dışındadır.",
                )
            tuning_offset = abs(self.output_center_frequency_hz - input_center)
            if not LIVE_MIN_TUNING_OFFSET_HZ <= tuning_offset <= LIVE_MAX_TUNING_OFFSET_HZ:
                raise AcquisitionError(
                    "invalid_tuning_offset",
                    "Alıcı merkez frekansı doğrulanmış DC-güvenli ofset aralığıyla eşleşmiyor.",
                )
        _ = self.rx_config

    @property
    def input_center_frequency_hz(self) -> int:
        if self.input_center_frequency_hz_override is not None:
            return self.input_center_frequency_hz_override
        lower = self.output_center_frequency_hz - LIVE_TUNING_OFFSET_HZ
        return lower if lower >= 1_000_000 else self.output_center_frequency_hz + LIVE_TUNING_OFFSET_HZ

    @property
    def rx_config(self) -> RXConfig:
        return RXConfig(
            center_frequency_hz=self.input_center_frequency_hz,
            sample_rate_hz=LIVE_INPUT_SAMPLE_RATE_HZ,
            sample_count=LIVE_INPUT_SAMPLES_PER_FRAME,
            rf_amplifier=False,
            lna_gain_db=self.lna_gain_db,
            vga_gain_db=self.vga_gain_db,
            device_serial=self.device_serial,
        )


@dataclass(frozen=True)
class LiveEDEvent:
    event_id: int
    first_frame_id: int
    last_seen_frame_id: int
    seen_count: int
    state: str
    observed_this_frame: bool
    start_shifted_bin: int
    end_shifted_bin: int
    peak_shifted_bin: int
    coarse_span_bins: int
    pfa_select: int
    flags: int
    peak_power: float
    noise_power: float
    threshold_power: float

    @property
    def peak_to_noise_db(self) -> float:
        if self.peak_power <= 0.0 or self.noise_power <= 0.0:
            return float("nan")
        return 10.0 * math.log10(self.peak_power / self.noise_power)

    @property
    def weak_evidence(self) -> bool:
        return bool(self.flags & LOCAL_EVENT_WEAK_EVIDENCE)

    @property
    def single_frame_confident(self) -> bool:
        return bool(self.flags & LOCAL_EVENT_SINGLE_FRAME_CONFIDENT)

    @property
    def wideband_evidence(self) -> bool:
        return bool(self.flags & LOCAL_EVENT_WIDEBAND_EVIDENCE)


@dataclass(frozen=True)
class LiveEDResponse:
    frame_id: int
    raw_candidate_count: int
    dma_status_flags: int
    dropped_candidates: int
    reset_applied: bool
    evicted_history_count: int
    active: tuple[LiveEDEvent, ...]
    ended: tuple[LiveEDEvent, ...]
    response_bytes: int


@dataclass(frozen=True)
class LiveEDSnapshot:
    sequence_number: int
    output_frame: IQFrame
    response: LiveEDResponse


@dataclass(frozen=True)
class LiveEDPreview:
    """Received I/Q for presentation; it is not a validated FPGA result."""

    sequence_number: int
    output_frame: IQFrame
    received_monotonic: float
    display_frame: IQFrame | None = None


@dataclass(frozen=True)
class LiveEDSessionResult:
    completed_frames: int
    elapsed_seconds: float
    frames_per_second: float
    real_time_margin: float
    raw_candidate_total: int
    maximum_active_events: int
    input_saturated_components: int
    output_saturated_components: int
    capture_queue_high_watermark: int
    channelized_queue_high_watermark: int
    hackrf_statistics: HackRFStreamStatistics
    transport_statistics: TransportStats
    preview_frames: int = 0
    processing_timings: dict | None = None
    fpga_enabled: bool = True


def _decode_event(payload: bytes, offset: int, *, ended: bool) -> LiveEDEvent:
    event_id, first_frame, last_seen, seen_count = struct.unpack_from("<QIIQ", payload, offset)
    state_code = payload[offset + 24]
    observed_code = payload[offset + 25]
    start_bin, end_bin, peak_bin, coarse_span = struct.unpack_from("<HHHH", payload, offset + 28)
    pfa_select, flags = struct.unpack_from("<BB", payload, offset + 36)
    peak_power, noise_power, threshold_power = struct.unpack_from("<QQQ", payload, offset + 40)
    states = {1: "tentative", 2: "confirmed", 3: "ended"}
    if (
        struct.unpack_from("<H", payload, offset + 26)[0] != 0
        or struct.unpack_from("<H", payload, offset + 38)[0] != 0
        or struct.unpack_from("<I", payload, offset + 64)[0] != 0
        or event_id == 0
        or first_frame > last_seen
        or seen_count == 0
        or observed_code not in {0, 1}
        or state_code not in states
        or (ended and state_code != 3)
        or (not ended and state_code not in {1, 2})
        or (flags & ~LOCAL_EVENT_ALLOWED_FLAGS) != 0
        or (flags & LOCAL_EVENT_RECORD_VALID) == 0
        or (
            (flags & LOCAL_EVENT_SINGLE_FRAME_CONFIDENT) != 0
            and (flags & LOCAL_EVENT_WEAK_EVIDENCE) == 0
        )
        or not (0 <= start_bin <= peak_bin <= end_bin < LIVE_OUTPUT_SAMPLES_PER_FRAME)
        or coarse_span == 0
    ):
        raise TransportError("local_response_event", "Yerel kart olay kaydı doğrulanamadı.")
    scale = float(1 << 30)
    return LiveEDEvent(
        event_id=event_id,
        first_frame_id=first_frame,
        last_seen_frame_id=last_seen,
        seen_count=seen_count,
        state=states[state_code],
        observed_this_frame=bool(observed_code),
        start_shifted_bin=start_bin,
        end_shifted_bin=end_bin,
        peak_shifted_bin=peak_bin,
        coarse_span_bins=coarse_span,
        pfa_select=pfa_select,
        flags=flags,
        peak_power=peak_power / scale,
        noise_power=noise_power / scale,
        threshold_power=threshold_power / scale,
    )


def decode_live_ed_response(payload: bytes, expected_frame_id: int) -> LiveEDResponse:
    """Decode and validate all compact ABI-v3 event records for live presentation."""
    summary = decode_local_ed_response(payload, expected_frame_id)
    result = payload[LOCAL_RESPONSE_HEADER_BYTES:]
    active_count, ended_count = struct.unpack_from("<HH", result, 4)
    if active_count > LOCAL_MAX_EVENTS or ended_count > LOCAL_MAX_EVENTS:
        raise TransportError("local_response_result", "Yerel kart olay sayısı güvenli sınırı aşıyor.")
    offset = LOCAL_RESULT_HEADER_BYTES
    active = tuple(
        _decode_event(result, offset + index * LOCAL_EVENT_BYTES, ended=False)
        for index in range(active_count)
    )
    offset += active_count * LOCAL_EVENT_BYTES
    ended_events = tuple(
        _decode_event(result, offset + index * LOCAL_EVENT_BYTES, ended=True)
        for index in range(ended_count)
    )
    return LiveEDResponse(
        frame_id=summary.frame_id,
        raw_candidate_count=summary.raw_candidate_count,
        dma_status_flags=summary.dma_status_flags,
        dropped_candidates=summary.dropped_candidates,
        reset_applied=bool(summary.reset_applied),
        evicted_history_count=struct.unpack_from("<Q", result, 12)[0],
        active=active,
        ended=ended_events,
        response_bytes=summary.response_bytes,
    )


class _ContinuousStream(Protocol):
    statistics: HackRFStreamStatistics | None

    def __enter__(self) -> _ContinuousStream: ...
    def __iter__(self): ...
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...
    def close(self) -> None: ...


class LiveEDSession:
    """Run one cancellable, bounded live RX session without any transmit path."""

    def __init__(
        self,
        executable: str,
        configuration: LiveEDConfiguration,
        *,
        stream_factory: Callable[..., _ContinuousStream] = HackRFContinuousRX,
        transport_factory: Callable[[], TCPClientIQTransport] = TCPClientIQTransport,
        channelizer_factory: Callable[[], object] = create_realtime_channelizer,
    ) -> None:
        self.executable = executable
        self.configuration = configuration
        self._stream_factory = stream_factory
        self._transport = transport_factory()
        self._channelizer_factory = channelizer_factory
        self._cancellation = threading.Event()
        self._active_stream: _ContinuousStream | None = None
        self._lock = threading.Lock()
        self._measurement_lock = threading.Lock()
        self._measurement_histories: dict[int, list[LiveEDSnapshot]] = {}
        self._measurement_windows: OrderedDict[int, tuple[LiveEDSnapshot, ...]] = OrderedDict()
        self._audio_lock = threading.Lock()
        self._audio_frames: deque[IQFrame] = deque(maxlen=LIVE_AUDIO_WINDOW_FRAMES)
        self._audio_observations: dict[int, int] = {}
        self._preview_handler: Callable[[LiveEDPreview], None] | None = None
        self.last_diagnostics: dict = {}
        self.measurement_channelizer: dict | None = None

    def set_preview_handler(self, handler: Callable[[LiveEDPreview], None] | None) -> None:
        """Install before run; the callback runs outside the GUI and TCP loops."""
        self._preview_handler = handler

    def cancel(self) -> None:
        self._cancellation.set()
        with self._lock:
            stream = self._active_stream
        if stream is not None:
            stream.close()
        self._transport.close()

    def measurement_window(self, event_id: int) -> tuple[LiveEDSnapshot, ...]:
        """Return the latest immutable four-frame window for one confirmed event."""
        with self._measurement_lock:
            return self._measurement_windows.get(int(event_id), ())

    def current_measurement_window(self, event_id: int) -> tuple[LiveEDSnapshot, ...]:
        """Snapshot four observations ending at the most recently processed response."""
        with self._measurement_lock:
            history = self._measurement_histories.get(int(event_id), ())
            return tuple(history) if len(history) == LIVE_MEASUREMENT_WINDOW_FRAMES else ()

    def audio_window_frame_count(self, event_id: int | None = None) -> int:
        with self._audio_lock:
            return len(self._audio_frames) if event_id is None else min(
                len(self._audio_frames), self._audio_observations.get(event_id, 0)
            )

    def audio_window_ready(self, event_id: int | None = None) -> bool:
        return self.audio_window_frame_count(event_id) == LIVE_AUDIO_WINDOW_FRAMES

    def audio_window(self, event_id: int | None = None) -> tuple[IQFrame, ...]:
        """Snapshot contiguous submitted I/Q whose FPGA responses were validated."""
        with self._audio_lock:
            if len(self._audio_frames) != LIVE_AUDIO_WINDOW_FRAMES:
                return ()
            if event_id is not None and self._audio_observations.get(event_id, 0) < LIVE_AUDIO_WINDOW_FRAMES:
                return ()
            return tuple(self._audio_frames)

    def _record_audio_frame(self, frame: IQFrame, observed_ids: tuple[int, ...] = ()) -> None:
        with self._audio_lock:
            if self._audio_frames and frame.sequence_number != self._audio_frames[-1].sequence_number + 1:
                self._audio_frames.clear()
                self._audio_observations.clear()
            self._audio_frames.append(frame)
            self._audio_observations = {
                event_id: min(LIVE_AUDIO_WINDOW_FRAMES, self._audio_observations.get(event_id, 0) + 1)
                for event_id in observed_ids
            }

    def _record_measurement_snapshot(self, snapshot: LiveEDSnapshot) -> None:
        observed_ids: set[int] = set()
        with self._measurement_lock:
            for event in snapshot.response.active:
                if event.state != "confirmed" or not event.observed_this_frame:
                    continue
                event_id = int(event.event_id)
                observed_ids.add(event_id)
                history = self._measurement_histories.setdefault(event_id, [])
                if history and snapshot.sequence_number != history[-1].sequence_number + 1:
                    history.clear()
                history.append(snapshot)
                del history[:-LIVE_MEASUREMENT_WINDOW_FRAMES]
                if len(history) == LIVE_MEASUREMENT_WINDOW_FRAMES:
                    self._measurement_windows[event_id] = tuple(history)
                    self._measurement_windows.move_to_end(event_id)
                    while len(self._measurement_windows) > LIVE_MEASUREMENT_WINDOW_CAPACITY:
                        self._measurement_windows.popitem(last=False)
            for event_id in tuple(self._measurement_histories):
                if event_id not in observed_ids:
                    del self._measurement_histories[event_id]

    def run(self, snapshot_handler: Callable[[LiveEDSnapshot], None] | None = None) -> LiveEDSessionResult:
        if self._cancellation.is_set():
            raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")
        config = self.configuration
        channelizer = self._channelizer_factory()
        channelizer_backend = str(getattr(channelizer, "backend_name", "unknown"))
        profile = getattr(channelizer, "profile", None)
        self.measurement_channelizer = {
            "backend": channelizer_backend,
            "profile": asdict(profile) if is_dataclass(profile) else {},
            "library_sha256": (
                hashlib.sha256(channelizer.library_path.read_bytes()).hexdigest()
                if getattr(channelizer, "library_path", None) is not None else None
            ),
        }
        if self._stream_factory is HackRFContinuousRX and channelizer_backend != "native-cpp":
            raise AcquisitionError(
                "native_channelizer_required",
                "8 MS/s canlı HackRF akışı için derlenmiş P0 kanal seçici gereklidir.",
            )
        capture_queue: queue.Queue[object] = queue.Queue(maxsize=LIVE_CAPTURE_QUEUE_CAPACITY)
        channel_queue: queue.Queue[object] = queue.Queue(maxsize=LIVE_CHANNEL_QUEUE_CAPACITY)
        end_of_stream = object()
        producer_error: list[Exception] = []
        channel_error: list[Exception] = []
        pending_frames: dict[int, IQFrame] = {}
        input_saturated = 0
        output_saturated = 0
        capture_queue_high_watermark = 0
        channel_queue_high_watermark = 0
        preview_frames = 0
        timing_samples = {name: deque(maxlen=4096) for name in ("capture_queue_age_ms", "channelizer_ms", "preview_callback_ms")}
        raw_candidate_total = 0
        maximum_active = 0
        completed = 0
        # Queue occupancy and stage timings are diagnostics; sampling them on
        # every 2 ms frame adds avoidable lock/clock work to the real-time
        # path. Keep exact per-frame diagnostics for short test sessions, and
        # use a bounded stride for production-length captures.
        diagnostic_stride = 1 if config.frame_count <= 128 else 16
        stream_statistics: HackRFStreamStatistics | None = None
        started = time.perf_counter()

        def capture(stream: _ContinuousStream) -> None:
            nonlocal capture_queue_high_watermark, stream_statistics
            try:
                for index, payload in enumerate(stream):
                    preview_needed = self._preview_handler is not None and (
                        index == 0
                        or index + 1 == config.frame_count
                        or (index + 1) % config.display_interval_frames == 0
                    )
                    received = (
                        time.perf_counter()
                        if index % diagnostic_stride == 0 or preview_needed
                        else 0.0
                    )
                    if self._cancellation.is_set():
                        raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")
                    while not self._cancellation.is_set():
                        try:
                            capture_queue.put((index, payload, received), timeout=0.1)
                            if index % diagnostic_stride == 0:
                                capture_queue_high_watermark = max(
                                    capture_queue_high_watermark,
                                    capture_queue.qsize(),
                                )
                            break
                        except queue.Full:
                            continue
                stream_statistics = stream.statistics
            except Exception as exc:
                producer_error.append(exc)
            finally:
                while not self._cancellation.is_set():
                    try:
                        capture_queue.put(end_of_stream, timeout=0.1)
                        break
                    except queue.Full:
                        continue

        def take_work(work_queue, label, timeout_code):
            deadline = time.monotonic() + 5.0
            while not self._cancellation.is_set():
                try:
                    return work_queue.get(timeout=0.1)
                except queue.Empty:
                    if time.monotonic() >= deadline:
                        raise AcquisitionError(timeout_code, f"{label} beş saniye içinde veri üretmedi.")
            raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")

        def channelized_frames():
            nonlocal input_saturated, output_saturated
            level_nonzero = 0
            for _ in range(config.frame_count):
                if self._cancellation.is_set():
                    raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")
                item = take_work(capture_queue, "Alım", "live_capture_timeout")
                if item is end_of_stream:
                    if producer_error:
                        raise producer_error[0]
                    raise AcquisitionError("short_stream", "Canlı HackRF akışı erken bitti.")
                index, payload, received = item
                sampled = index % diagnostic_stride == 0
                if sampled:
                    timing_samples["capture_queue_age_ms"].append((time.perf_counter() - received) * 1000)
                processing_started = time.perf_counter() if sampled else 0.0
                channelized, frame_input_saturated = channelizer.process_ci8(
                    payload,
                    sequence_number=index,
                    frame_id=index,
                    input_sample_rate_hz=LIVE_INPUT_SAMPLE_RATE_HZ,
                    input_center_frequency_hz=config.input_center_frequency_hz,
                    output_center_frequency_hz=config.output_center_frequency_hz,
                )
                input_saturated += frame_input_saturated
                if frame_input_saturated:
                    raise AcquisitionError(
                        "iq_saturation",
                        "Canlı I/Q akışında kırpılan giriş örneği oluştu; alıcı kazançlarını azaltın.",
                    )
                output_saturated += channelized.saturated_components
                if channelized.saturated_components:
                    raise AcquisitionError(
                        "iq_saturation",
                        "Kanal seçici çıkışında kırpılan örnek oluştu; alıcı kazançlarını azaltın.",
                    )
                # Ignore the first 16 startup frames, then assess 32 consecutive
                # frames. This detects coarse CI8 quantization, not RF absence.
                if config.assess_receive_level and 16 <= index < 48:
                    level_nonzero += len(channelized.frame.payload) - channelized.frame.payload.count(0)
                    if index == 47 and level_nonzero < 32 * 8192 * 0.05:
                        raise AcquisitionError(
                            "rx_level_low",
                            "Kanal seçici çıkışının %95'inden fazlası sıfır; alım seviyesi ayarlanmalı.",
                        )
                frame = channelized.frame
                if sampled:
                    timing_samples["channelizer_ms"].append((time.perf_counter() - processing_started) * 1000)
                yield frame, received, payload

        def channelize():
            nonlocal channel_queue_high_watermark, preview_frames
            try:
                for frame, received, payload in channelized_frames():
                    count = frame.sequence_number + 1
                    if self._preview_handler is not None and (
                        count == 1 or count == config.frame_count or count % config.display_interval_frames == 0
                    ):
                        callback_started = time.perf_counter()
                        display_frame = IQFrame(
                            sequence_number=frame.sequence_number,
                            sample_rate_hz=LIVE_INPUT_SAMPLE_RATE_HZ,
                            center_frequency_hz=config.input_center_frequency_hz,
                            payload=payload,
                            frame_id=frame.sequence_number,
                        )
                        self._preview_handler(LiveEDPreview(frame.sequence_number, frame, received, display_frame))
                        timing_samples["preview_callback_ms"].append((time.perf_counter() - callback_started) * 1000)
                        preview_frames += 1
                    while not self._cancellation.is_set():
                        try:
                            channel_queue.put(frame, timeout=0.1)
                            if frame.sequence_number % diagnostic_stride == 0:
                                channel_queue_high_watermark = max(
                                    channel_queue_high_watermark,
                                    channel_queue.qsize(),
                                )
                            break
                        except queue.Full:
                            continue
            except Exception as exc:
                channel_error.append(exc)
            finally:
                while not self._cancellation.is_set():
                    try:
                        channel_queue.put(end_of_stream, timeout=0.1)
                        break
                    except queue.Full:
                        continue

        def frames():
            for _ in range(config.frame_count):
                frame = take_work(channel_queue, "Kanal seçici", "live_channelizer_timeout")
                if frame is end_of_stream:
                    if channel_error:
                        raise channel_error[0]
                    raise AcquisitionError("short_stream", "Kanal seçici akışı erken bitti.")
                pending_frames[frame.sequence_number] = frame
                yield frame

        def handle_response(response: IQResponse) -> None:
            nonlocal completed, raw_candidate_total, maximum_active
            decoded = decode_live_ed_response(response.payload, response.sequence_number)
            if decoded.dma_status_flags != 7:
                raise TransportError("dma_status", "Canlı FPGA DMA durumu geçersizdir.")
            if decoded.dropped_candidates != 0:
                raise TransportError("candidate_drop", "Canlı FPGA olay zincirinde aday düşürüldü.")
            output_frame = pending_frames.pop(response.sequence_number)
            snapshot = LiveEDSnapshot(response.sequence_number, output_frame, decoded)
            self._record_audio_frame(output_frame, tuple(
                event.event_id for event in decoded.active
                if event.state == "confirmed" and event.observed_this_frame
            ))
            self._record_measurement_snapshot(snapshot)
            completed += 1
            raw_candidate_total += decoded.raw_candidate_count
            maximum_active = max(maximum_active, len(decoded.active))
            if snapshot_handler is not None and (
                completed == 1
                or completed == config.frame_count
                or completed % config.display_interval_frames == 0
            ):
                snapshot_handler(snapshot)

        producer: threading.Thread | None = None
        channel_worker: threading.Thread | None = None
        try:
            if config.fpga_enabled:
                self._transport.connect(config.board_host, config.board_port, timeout_seconds=3.0)
            stream = self._stream_factory(
                self.executable,
                config.rx_config,
                config.frame_count,
                cancellation=self._cancellation,
            )
            with self._lock:
                self._active_stream = stream
            with stream:
                producer = threading.Thread(target=capture, args=(stream,), daemon=True)
                channel_worker = threading.Thread(target=channelize, daemon=True)
                producer.start()
                channel_worker.start()
                if config.fpga_enabled:
                    exchanged = self._transport.exchange_stream(frames(), handle_response)
                else:
                    exchanged = 0
                    for frame in frames():
                        pending_frames.pop(frame.sequence_number)
                        completed += 1
                        exchanged += 1
                producer.join(timeout=5.0)
                channel_worker.join(timeout=5.0)
                if producer.is_alive():
                    raise AcquisitionError("producer_shutdown_timeout", "Canlı RX üreticisi kapanmadı.")
                if producer_error:
                    raise producer_error[0]
                if channel_worker.is_alive():
                    raise AcquisitionError("producer_shutdown_timeout", "Kanal seçici kapanmadı.")
                if channel_error:
                    raise channel_error[0]
                if exchanged != config.frame_count or completed != config.frame_count:
                    raise AcquisitionError("short_stream", "Canlı ED oturumu tam kare sayısına ulaşmadı.")
                stream_statistics = stream.statistics
        except Exception as exc:
            if self._cancellation.is_set():
                raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.") from exc
            raise
        finally:
            self._cancellation.set()
            with self._lock:
                self._active_stream = None
            self._transport.close()
            if producer is not None and producer.is_alive():
                producer.join(timeout=1.0)
            if channel_worker is not None and channel_worker.is_alive():
                channel_worker.join(timeout=1.0)
            self.last_diagnostics = {
                "fpga_enabled": config.fpga_enabled,
                "completed_frames": completed,
                "capture_queue_high_watermark": capture_queue_high_watermark,
                "channel_queue_high_watermark": channel_queue_high_watermark,
                "channelizer_backend": channelizer_backend,
                "hackrf_statistics": asdict(stream_statistics) if stream_statistics is not None else None,
                "timing_scope": "most_recent_at_most_4096_observations_per_stage",
                "timing_ms": {name: {"samples": len(values),
                    "p50": float(np.percentile(values, 50)) if values else 0.0,
                    "p95": float(np.percentile(values, 95)) if values else 0.0,
                    "maximum": max(values, default=0.0)} for name, values in timing_samples.items()},
            }

        if stream_statistics is None:
            raise AcquisitionError("stream_statistics_missing", "HackRF canlı RX özeti oluşmadı.")
        if (
            stream_statistics.frames_received != config.frame_count
            or stream_statistics.bytes_received
            != config.frame_count * LIVE_INPUT_SAMPLES_PER_FRAME * 2
            or stream_statistics.process_returncode != 0
        ):
            raise AcquisitionError("stream_integrity", "HackRF canlı RX bütünlüğü doğrulanamadı.")
        if stream_statistics.overruns != 0:
            raise AcquisitionError("usb_overrun", "HackRF USB akışında tampon taşması oluştu.")
        if input_saturated != 0 or output_saturated != 0:
            raise AcquisitionError("iq_saturation", "Canlı I/Q akışında kırpılan örnek bileşeni oluştu.")
        transport_statistics = self._transport.stats
        if config.fpga_enabled and (
            transport_statistics.frames_sent != config.frame_count
            or transport_statistics.frames_received != config.frame_count
            or transport_statistics.sequence_errors != 0
            or transport_statistics.queue_drops != 0
        ):
            raise AcquisitionError("transport_integrity", "Canlı ZedBoard taşıma bütünlüğü doğrulanamadı.")
        elapsed = time.perf_counter() - started
        frames_per_second = completed / elapsed
        return LiveEDSessionResult(
            completed_frames=completed,
            elapsed_seconds=elapsed,
            frames_per_second=frames_per_second,
            real_time_margin=frames_per_second / LIVE_REQUIRED_FRAMES_PER_SECOND,
            raw_candidate_total=raw_candidate_total,
            maximum_active_events=maximum_active,
            input_saturated_components=input_saturated,
            output_saturated_components=output_saturated,
            capture_queue_high_watermark=capture_queue_high_watermark,
            channelized_queue_high_watermark=channel_queue_high_watermark,
            hackrf_statistics=stream_statistics,
            transport_statistics=transport_statistics,
            preview_frames=preview_frames,
            processing_timings={
                "scope": "most_recent_at_most_4096_observations_per_stage",
                "stages": {name: {"samples": len(values),
                    "p50_ms": float(np.percentile(values, 50)) if values else 0.0,
                    "p95_ms": float(np.percentile(values, 95)) if values else 0.0,
                    "maximum_ms": max(values, default=0.0)} for name, values in timing_samples.items()},
            },
            fpga_enabled=config.fpga_enabled,
        )
