"""Bounded live HackRF-to-FPGA receive session used by the operator product."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass, replace
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
from algorithms.p0.channelizer import P0ChannelizerProfile
from algorithms.p0.direct_frame import DirectP0FrameAdapter, DirectP0Profile
from algorithms.p0.parameter_client import MAXIMUM_BOARD_SPAN_BINS
from algorithms.p0.transport import (
    IQFrame,
    IQResponse,
    InlineParameterResult,
    TCPClientIQTransport,
    TransportError,
    TransportStats,
    decode_local_ed_response,
)
from .automatic_parameter import (
    AutomaticParameterOutcome,
    AutomaticParameterScheduler,
)

from platforms.acquisition.continuous import (
    MAX_CAPTURE_FRAMES,
    MAX_STREAM_FRAMES,
    HackRFContinuousRX,
    HackRFStreamStatistics,
)
from platforms.acquisition.contracts import AcquisitionError, RXConfig


LIVE_INPUT_SAMPLE_RATE_HZ = 8_000_000
LIVE_WIDEBAND_INPUT_SAMPLE_RATE_HZ = 10_000_000
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
LIVE_STARTUP_SETTLING_FRAMES = 8
LIVE_WIDEBAND_MAX_BURST_FRAMES = 256
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
LIVE_AUDIO_MIN_OBSERVED_FRACTION = 0.95
LIVE_AUDIO_MAX_CONSECUTIVE_MISSES = 8
LIVE_AUDIO_TARGET_MARGIN_HZ = 50_000.0


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
    display_fft_size: int = 16384
    fpga_fft_size: int = 4096
    automatic_parameters_enabled: bool = True
    direct_fpga_input: bool = False
    startup_settling_frames: int = 0
    rf_amplifier: bool = False

    def __post_init__(self) -> None:
        if type(self.rf_amplifier) is not bool:
            raise AcquisitionError("invalid_rx_config", "RF yükselteci seçimi açık veya kapalı olmalıdır.")
        if (isinstance(self.fpga_fft_size, bool) or not isinstance(self.fpga_fft_size, int)
                or self.fpga_fft_size not in (4096, 8192, 16384)):
            raise AcquisitionError("invalid_rx_config", "FPGA FFT boyutu 4096, 8192 veya 16384 olmalıdır.")
        if (isinstance(self.display_fft_size, bool) or not isinstance(self.display_fft_size, int)
                or self.display_fft_size not in (4096, 8192, 16384)):
            raise AcquisitionError("invalid_rx_config", "Görüntü FFT boyutu 4096, 8192 veya 16384 olmalıdır.")
        if not isinstance(self.fpga_enabled, bool):
            raise AcquisitionError("invalid_rx_config", "FPGA alım modu geçersizdir.")
        if not isinstance(self.automatic_parameters_enabled, bool):
            raise AcquisitionError(
                "invalid_rx_config", "Otomatik parametre çıkarımı ayarı geçersizdir."
            )
        if not isinstance(self.direct_fpga_input, bool):
            raise AcquisitionError("invalid_rx_config", "Doğrudan FPGA giriş ayarı geçersizdir.")
        if self.direct_fpga_input and self.automatic_parameters_enabled:
            raise AcquisitionError(
                "invalid_rx_config",
                "10 MS/s doğrudan FPGA taramasında otomatik parametre çıkarımı kapalı olmalıdır.",
            )
        if isinstance(self.output_center_frequency_hz, bool) or not isinstance(
            self.output_center_frequency_hz, int
        ):
            raise AcquisitionError("invalid_center_frequency", "İzleme merkez frekansı tam sayı Hz olmalıdır.")
        if not 1_000_000 <= self.output_center_frequency_hz <= 6_000_000_000:
            raise AcquisitionError("invalid_center_frequency", "İzleme merkez frekansı HackRF sınırının dışındadır.")
        if not 1 <= self.frame_count <= MAX_STREAM_FRAMES:
            raise AcquisitionError("invalid_stream_length", "Canlı oturum kare sayısı güvenli sınırın dışındadır.")
        if (
            isinstance(self.startup_settling_frames, bool)
            or not isinstance(self.startup_settling_frames, int)
            or not 0 <= self.startup_settling_frames <= 64
        ):
            raise AcquisitionError(
                "invalid_rx_config", "Başlangıç yerleşme kare sayısı 0–64 arasında olmalıdır."
            )
        if self.capture_frame_count > MAX_CAPTURE_FRAMES:
            raise AcquisitionError(
                "invalid_stream_length",
                "Başlangıç yerleşmesiyle birlikte canlı RX kare sınırı aşılıyor.",
            )
        if self.direct_fpga_input and self.frame_count > LIVE_WIDEBAND_MAX_BURST_FRAMES:
            raise AcquisitionError(
                "invalid_stream_length",
                "10 MS/s doğrudan FPGA taraması en fazla 256 karelik burst ile sınırlandırılmıştır.",
            )
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
            if self.direct_fpga_input and tuning_offset != 0:
                raise AcquisitionError(
                    "invalid_tuning_offset",
                    "10 MS/s doğrudan FPGA yolunda alıcı ve işleme merkezi aynı olmalıdır.",
                )
            if not self.direct_fpga_input and not (
                LIVE_MIN_TUNING_OFFSET_HZ <= tuning_offset <= LIVE_MAX_TUNING_OFFSET_HZ
            ):
                raise AcquisitionError(
                    "invalid_tuning_offset",
                    "Alıcı merkez frekansı doğrulanmış DC-güvenli ofset aralığıyla eşleşmiyor.",
                )
        _ = self.rx_config

    @property
    def input_center_frequency_hz(self) -> int:
        if self.input_center_frequency_hz_override is not None:
            return self.input_center_frequency_hz_override
        if self.direct_fpga_input:
            return self.output_center_frequency_hz
        lower = self.output_center_frequency_hz - LIVE_TUNING_OFFSET_HZ
        return lower if lower >= 1_000_000 else self.output_center_frequency_hz + LIVE_TUNING_OFFSET_HZ

    @property
    def rx_config(self) -> RXConfig:
        return RXConfig(
            center_frequency_hz=self.input_center_frequency_hz,
            sample_rate_hz=(
                LIVE_WIDEBAND_INPUT_SAMPLE_RATE_HZ
                if self.direct_fpga_input else LIVE_INPUT_SAMPLE_RATE_HZ
            ),
            sample_count=(self.fpga_fft_size if self.direct_fpga_input else 4 * self.fpga_fft_size),
            rf_amplifier=self.rf_amplifier,
            lna_gain_db=self.lna_gain_db,
            vga_gain_db=self.vga_gain_db,
            device_serial=self.device_serial,
        )

    @property
    def processing_sample_rate_hz(self) -> int:
        return (
            LIVE_WIDEBAND_INPUT_SAMPLE_RATE_HZ
            if self.direct_fpga_input else LIVE_OUTPUT_SAMPLE_RATE_HZ
        )

    @property
    def capture_frame_count(self) -> int:
        return self.frame_count + self.startup_settling_frames


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
    parameter: InlineParameterResult | None = None


@dataclass(frozen=True)
class LiveEDSnapshot:
    sequence_number: int
    output_frame: IQFrame
    response: LiveEDResponse
    automatic_parameter_outcomes: tuple[AutomaticParameterOutcome, ...] = ()


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
    """Decode compact detection responses and full inline-parameter responses."""
    summary = decode_local_ed_response(payload, expected_frame_id)
    result = payload[summary.result_offset : summary.result_offset + summary.result_bytes]
    active_count, ended_count = struct.unpack_from("<HH", result, 4)
    if active_count > LOCAL_MAX_EVENTS or ended_count > LOCAL_MAX_EVENTS:
        raise TransportError("local_response_result", "Yerel kart olay sayısı güvenli sınırı aşıyor.")
    offset = LOCAL_RESULT_HEADER_BYTES
    active = tuple(
        _decode_event(result, offset + index * LOCAL_EVENT_BYTES, ended=False)
        for index in range(active_count)
    )
    offset = (
        LOCAL_RESULT_HEADER_BYTES + LOCAL_MAX_EVENTS * LOCAL_EVENT_BYTES
        if not summary.compact_result
        else offset + active_count * LOCAL_EVENT_BYTES
    )
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
        parameter=summary.parameter,
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
        self._parameter_span: tuple[int, int] | None = None
        self._parameter_frames: list[LiveEDSnapshot] = []
        self._parameter_reason = ""
        self._parameter_after_sequence = -1
        self._direction_span: tuple[int, int] | None = None
        self._direction_frames: list[LiveEDSnapshot] = []
        self._direction_reason = ""
        self._direction_require_observed_target = True
        self._latest_capture_sequence = -1
        self._latest_response_sequence = -1
        self._direction_after_sequence = -1
        self._audio_lock = threading.RLock()
        self._audio_frames: deque[IQFrame] = deque(maxlen=LIVE_AUDIO_WINDOW_FRAMES)
        self._audio_event_observations: dict[int, deque[bool]] = {}
        self._audio_snapshots: deque[LiveEDSnapshot | None] = deque(
            maxlen=LIVE_AUDIO_WINDOW_FRAMES
        )
        self._preview_handler: Callable[[LiveEDPreview], None] | None = None
        self.last_diagnostics: dict = {}
        self.measurement_channelizer: dict | None = None
        self.automatic_parameter_status = "Henüz denetlenmedi"

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

    @property
    def parameter_measurement_frame_count(self) -> int:
        capabilities = getattr(self._transport, "capabilities", None)
        return 16 if bool(getattr(capabilities, "extended_parameter", False)) else 4

    def begin_parameter_capture(self, lower: int, upper: int) -> None:
        """Collect 4 or 16 fresh frames, according to the board capability."""
        if (
            self.configuration.fpga_fft_size != 4096
            or not 56 <= lower <= upper <= 4039
            or not 8 <= upper - lower + 1 <= MAXIMUM_BOARD_SPAN_BINS
        ):
            raise ValueError("Parametre ölçümü için 4096 FFT ve geçerli hedef kanalı gerekir.")
        with self._measurement_lock:
            span = (int(lower), int(upper))
            if self._parameter_span == span:
                return
            self._parameter_span = span
            # Exclude queued host work and the capture already in flight.
            self._parameter_after_sequence = max(
                self._latest_capture_sequence, self._latest_response_sequence
            ) + 1
            self._parameter_frames = []
            self._parameter_reason = "Seçili kanalda sinyal bekleniyor."

    def cancel_parameter_capture(self) -> None:
        with self._measurement_lock:
            self._parameter_span = None
            self._parameter_frames = []

    def parameter_capture(self) -> tuple[tuple[LiveEDSnapshot, ...], str]:
        with self._measurement_lock:
            return tuple(self._parameter_frames), self._parameter_reason

    def begin_direction_capture(
        self,
        lower: int,
        upper: int,
        require_observed_target: bool = True,
    ) -> None:
        """Collect fresh channel-power frames after an operator angle request.

        The first point establishes the selected channel with four confirmed
        observations.  Once that lock exists, direction finding must also keep
        the low-power/back-lobe samples for which the detector quite correctly
        produces no event.  In that mode a newly observed neighbour still
        invalidates the window, but an empty locked channel does not.
        """
        if (
            self.configuration.fpga_fft_size != 4096
            or not 56 <= lower <= upper <= 4039
            or not 8 <= upper - lower + 1 <= MAXIMUM_BOARD_SPAN_BINS
        ):
            raise ValueError("Yön ölçümü için 4096 FFT ve geçerli hedef kanalı gerekir.")
        with self._measurement_lock:
            self._direction_span = (lower, upper)
            self._direction_require_observed_target = bool(require_observed_target)
            # Exclude the host queues and the read already in flight.
            self._direction_after_sequence = max(self._latest_capture_sequence, self._latest_response_sequence) + 1
            self._direction_frames = []
            self._direction_reason = (
                "Seçili kanalda doğrulanmış sinyal bekleniyor."
                if self._direction_require_observed_target
                else "Kilitli kanalın yeni güç kareleri bekleniyor."
            )

    def cancel_direction_capture(self) -> None:
        with self._measurement_lock:
            self._direction_span = None
            self._direction_frames = []

    def direction_capture(self) -> tuple[tuple[LiveEDSnapshot, ...], str]:
        with self._measurement_lock:
            return tuple(self._direction_frames), self._direction_reason

    @staticmethod
    def direction_channel_owner(snapshot: LiveEDSnapshot, lower: int, upper: int):
        # A nearby second candidate is ambiguous, even if only one is confirmed.
        matches = [event for event in snapshot.response.active
                   if event.observed_this_frame
                   and event.end_shifted_bin >= lower - 4
                   and event.start_shifted_bin <= upper + 4]
        if len(matches) != 1:
            return None
        event = matches[0]
        return event if (event.state == "confirmed"
                         and lower <= event.start_shifted_bin <= event.peak_shifted_bin
                         <= event.end_shifted_bin <= upper) else None

    def _record_direction_snapshot(self, snapshot: LiveEDSnapshot) -> None:
        # Caller holds _measurement_lock. Latch the first complete fresh window
        # so GUI pacing cannot make the operator miss its availability.
        if self._direction_span is None or len(self._direction_frames) == 4:
            return
        if snapshot.sequence_number <= self._direction_after_sequence:
            return
        lower, upper = self._direction_span
        owner = self.direction_channel_owner(snapshot, lower, upper)
        nearby = [
            event
            for event in snapshot.response.active
            if event.observed_this_frame
            and event.end_shifted_bin >= lower - 4
            and event.start_shifted_bin <= upper + 4
        ]
        if owner is None and (self._direction_require_observed_target or nearby):
            self._direction_frames.clear()
            self._direction_reason = (
                "Hedef kanalda tek ve doğrulanmış sinyal bekleniyor; sinyal zayıf, "
                "kesintili veya komşu sinyal var."
                if self._direction_require_observed_target
                else "Kilitli kanalın yakınında başka veya sınırı taşan bir sinyal var; temiz güç penceresi bekleniyor."
            )
            return
        if self._direction_frames and snapshot.sequence_number != self._direction_frames[-1].sequence_number + 1:
            self._direction_frames.clear()
        self._direction_frames.append(snapshot)
        self._direction_reason = (
            f"Yeni kanal gözlemi toplanıyor: {len(self._direction_frames)}/4 kare."
            if self._direction_require_observed_target
            else f"Kilitli kanal gücü toplanıyor: {len(self._direction_frames)}/4 kare."
        )

    def _record_parameter_snapshot(self, snapshot: LiveEDSnapshot) -> None:
        # Caller holds _measurement_lock. Event IDs may change while the one
        # operator-selected, isolated channel remains continuous.
        if self._parameter_span is None or len(self._parameter_frames) == self.parameter_measurement_frame_count:
            return
        if snapshot.sequence_number <= self._parameter_after_sequence:
            return
        lower, upper = self._parameter_span
        if self.direction_channel_owner(snapshot, lower, upper) is None:
            self._parameter_frames.clear()
            self._parameter_reason = (
                "Hedef kanalda tek ve doğrulanmış sinyal bekleniyor; "
                "sinyal zayıf, kesintili veya komşu sinyal var."
            )
            return
        if (
            self._parameter_frames
            and snapshot.sequence_number != self._parameter_frames[-1].sequence_number + 1
        ):
            self._parameter_frames.clear()
        self._parameter_frames.append(snapshot)
        self._parameter_reason = (
            f"Yeni kanal gözlemi toplanıyor: {len(self._parameter_frames)}/{self.parameter_measurement_frame_count} kare."
        )

    def audio_window_frame_count(self, event_id: int | None = None) -> int:
        with self._audio_lock:
            if event_id is None:
                return len(self._audio_frames)
            observations = self._audio_event_observations.get(event_id)
            return min(len(self._audio_frames), len(observations) if observations is not None else 0)

    def _audio_channel_evidence(
        self, snapshot: LiveEDSnapshot, target_frequency_hz: float
    ) -> tuple[object | None, bool, bool]:
        """Resolve the one *currently observed* confirmed FPGA event at a channel.

        ``response.active`` is a lifecycle table, not only the detections seen in
        the current frame.  Ended-soon confirmed records can overlap a new event
        after an event-ID handoff.  Counting those retained records as concurrent
        emitters made a continuous RF channel look ambiguous and reset the audio
        buffer.  Only simultaneous observations are ambiguous; retained records
        are continuity evidence for a brief detector miss.
        """
        spacing_hz = LIVE_OUTPUT_SAMPLE_RATE_HZ / self.configuration.fpga_fft_size
        center_hz = float(self.configuration.output_center_frequency_hz)
        matches = []
        for event in snapshot.response.active:
            lower_hz = center_hz + (event.start_shifted_bin - 2048.0) * spacing_hz
            upper_hz = center_hz + (event.end_shifted_bin - 2048.0) * spacing_hz
            if (
                lower_hz - LIVE_AUDIO_TARGET_MARGIN_HZ
                <= target_frequency_hz
                <= upper_hz + LIVE_AUDIO_TARGET_MARGIN_HZ
            ):
                if event.state == "confirmed":
                    matches.append(event)
        observed_matches = [event for event in matches if event.observed_this_frame]
        if len(observed_matches) > 1:
            return None, False, False
        if observed_matches:
            return observed_matches[0], True, True
        if matches:
            event = max(matches, key=lambda item: int(item.last_seen_frame_id))
            return event, False, True
        # Channel-bound continuity already applies a bounded missed-frame gate.
        # A momentary absence is therefore a miss, not structural ambiguity.
        return None, False, True

    def _audio_channel_observations(
        self, target_frequency_hz: float
    ) -> tuple[tuple[bool, ...], tuple[int, ...], tuple[bool, ...]]:
        observations: list[bool] = []
        owner_ids: list[int] = []
        validities: list[bool] = []
        for snapshot in self._audio_snapshots:
            owner, observed, valid = (
                (None, False, False)
                if snapshot is None
                else self._audio_channel_evidence(snapshot, target_frequency_hz)
            )
            observations.append(observed)
            validities.append(valid)
            if owner is not None:
                owner_ids.append(int(owner.event_id))
        return tuple(observations), tuple(owner_ids), tuple(validities)

    @staticmethod
    def _audio_continuity(
        observations: tuple[bool, ...], *, complete: bool
    ) -> dict[str, int | float | bool]:
        total_frames = len(observations)
        observed_frames = sum(observations)
        maximum_misses = 0
        current_misses = 0
        for observed in observations:
            if observed:
                current_misses = 0
            else:
                current_misses += 1
                maximum_misses = max(maximum_misses, current_misses)
        fraction = observed_frames / total_frames if total_frames else 0.0
        return {
            "total_frames": total_frames,
            "observed_frames": observed_frames,
            "observed_fraction": fraction,
            "max_consecutive_misses": maximum_misses,
            "acceptable": bool(
                complete
                and total_frames == LIVE_AUDIO_WINDOW_FRAMES
                and fraction >= LIVE_AUDIO_MIN_OBSERVED_FRACTION
                and maximum_misses <= LIVE_AUDIO_MAX_CONSECUTIVE_MISSES
            ),
        }

    def audio_channel_frame_count(self, target_frequency_hz: float) -> int:
        """Report the current continuous channel-bound buffer length."""
        with self._audio_lock:
            observations, _, validities = self._audio_channel_observations(
                float(target_frequency_hz)
            )
            start = 1 + max(
                (index for index, valid in enumerate(validities) if not valid),
                default=-1,
            )
            current_misses = 0
            for index, observed in enumerate(observations[start:], start=start):
                if observed:
                    current_misses = 0
                else:
                    current_misses += 1
                    if current_misses > LIVE_AUDIO_MAX_CONSECUTIVE_MISSES:
                        start = index + 1
                        current_misses = 0
            return len(observations) - start

    def audio_channel_quality(
        self, target_frequency_hz: float
    ) -> dict[str, int | float | bool]:
        """Report continuity without binding the operator channel to an event ID."""
        with self._audio_lock:
            observations, owner_ids, validities = self._audio_channel_observations(
                float(target_frequency_hz)
            )
            quality = self._audio_continuity(
                observations,
                complete=(
                    len(self._audio_frames) == LIVE_AUDIO_WINDOW_FRAMES
                    and len(self._audio_snapshots) == LIVE_AUDIO_WINDOW_FRAMES
                    and all(validities)
                ),
            )
            quality["invalid_frames"] = sum(not valid for valid in validities)
            quality["distinct_event_ids"] = len(set(owner_ids))
            quality["event_id_changes"] = sum(
                current != previous
                for previous, current in zip(owner_ids, owner_ids[1:])
            )
            return quality

    def audio_channel_ready(self, target_frequency_hz: float) -> bool:
        return bool(
            self.audio_channel_quality(target_frequency_hz).get("acceptable", False)
        )

    def audio_channel_window_snapshot(
        self, target_frequency_hz: float
    ) -> tuple[tuple[IQFrame, ...], dict[str, int | float | bool]]:
        """Atomically snapshot I/Q for one stable RF channel across event-ID churn."""
        with self._audio_lock:
            quality = self.audio_channel_quality(float(target_frequency_hz))
            if not quality.get("acceptable", False):
                return (), quality
            return tuple(self._audio_frames), quality

    def audio_window_ready(self, event_id: int | None = None) -> bool:
        if event_id is None:
            return self.audio_window_frame_count() == LIVE_AUDIO_WINDOW_FRAMES
        return bool(self.audio_window_quality(event_id).get("acceptable", False))

    def audio_window_quality(self, event_id: int) -> dict[str, int | float | bool]:
        """Report bounded detector continuity for the selected confirmed event."""
        with self._audio_lock:
            observations = tuple(self._audio_event_observations.get(int(event_id), ()))
            total_frames = len(observations)
            observed_frames = sum(observations)
            maximum_misses = 0
            current_misses = 0
            for observed in observations:
                if observed:
                    current_misses = 0
                else:
                    current_misses += 1
                    maximum_misses = max(maximum_misses, current_misses)
            fraction = observed_frames / total_frames if total_frames else 0.0
            acceptable = (
                len(self._audio_frames) == LIVE_AUDIO_WINDOW_FRAMES
                and total_frames == LIVE_AUDIO_WINDOW_FRAMES
                and fraction >= LIVE_AUDIO_MIN_OBSERVED_FRACTION
                and maximum_misses <= LIVE_AUDIO_MAX_CONSECUTIVE_MISSES
            )
            return {
                "total_frames": total_frames,
                "observed_frames": observed_frames,
                "observed_fraction": fraction,
                "max_consecutive_misses": maximum_misses,
                "acceptable": acceptable,
            }

    def audio_window(self, event_id: int | None = None) -> tuple[IQFrame, ...]:
        """Snapshot contiguous submitted I/Q whose FPGA responses were validated."""
        return self.audio_window_snapshot(event_id)[0]

    def audio_window_snapshot(
        self, event_id: int | None = None
    ) -> tuple[tuple[IQFrame, ...], dict[str, int | float | bool] | None]:
        """Atomically snapshot I/Q and the selected event's continuity evidence."""
        with self._audio_lock:
            if len(self._audio_frames) != LIVE_AUDIO_WINDOW_FRAMES:
                return (), None if event_id is None else self.audio_window_quality(event_id)
            quality = None if event_id is None else self.audio_window_quality(event_id)
            if quality is not None and not quality.get("acceptable", False):
                return (), quality
            return tuple(self._audio_frames), quality

    def _record_audio_frame(
        self,
        frame: IQFrame,
        observed_ids: tuple[int, ...] = (),
        active_confirmed_ids: tuple[int, ...] | None = None,
        snapshot: LiveEDSnapshot | None = None,
    ) -> None:
        observed = set(observed_ids)
        active = observed if active_confirmed_ids is None else set(active_confirmed_ids)
        with self._audio_lock:
            if self._audio_frames and frame.sequence_number != self._audio_frames[-1].sequence_number + 1:
                self._audio_frames.clear()
                self._audio_event_observations.clear()
                self._audio_snapshots.clear()
            self._audio_frames.append(frame)
            self._audio_snapshots.append(snapshot)
            for event_id in tuple(self._audio_event_observations):
                if event_id not in active:
                    del self._audio_event_observations[event_id]
            for event_id in active:
                history = self._audio_event_observations.setdefault(
                    event_id, deque(maxlen=LIVE_AUDIO_WINDOW_FRAMES)
                )
                history.append(event_id in observed)

    def _record_measurement_snapshot(self, snapshot: LiveEDSnapshot) -> None:
        observed_ids: set[int] = set()
        with self._measurement_lock:
            self._latest_response_sequence = snapshot.sequence_number
            self._record_parameter_snapshot(snapshot)
            self._record_direction_snapshot(snapshot)
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
        if config.direct_fpga_input:
            channelizer = DirectP0FrameAdapter(
                DirectP0Profile(
                    input_samples_per_frame=config.fpga_fft_size,
                    output_samples_per_frame=config.fpga_fft_size,
                )
            )
        else:
            channelizer_profile = P0ChannelizerProfile(
                input_samples_per_frame=4 * config.fpga_fft_size,
                output_samples_per_frame=config.fpga_fft_size,
            )
            channelizer = (self._channelizer_factory()
                           if config.fpga_fft_size == 4096
                           else self._channelizer_factory(channelizer_profile))
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
        if (
            self._stream_factory is HackRFContinuousRX
            and channelizer_backend not in {"native-cpp", "direct-ci8"}
        ):
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
        startup_input_saturated = 0
        startup_output_saturated = 0
        capture_queue_high_watermark = 0
        channel_queue_high_watermark = 0
        preview_frames = 0
        timing_samples = {name: deque(maxlen=4096) for name in ("capture_queue_age_ms", "channelizer_ms", "preview_callback_ms")}
        raw_candidate_total = 0
        maximum_active = 0
        completed = 0
        first_response_at: float | None = None
        last_response_at: float | None = None
        automatic_parameter_outcome_count = 0
        automatic_scheduler: AutomaticParameterScheduler | None = None
        latest_snapshot: LiveEDSnapshot | None = None
        # Queue occupancy and stage timings are diagnostics; sampling them on
        # every 2 ms frame adds avoidable lock/clock work to the real-time
        # path. Keep exact per-frame diagnostics for short test sessions, and
        # use a bounded stride for production-length captures.
        diagnostic_stride = 1 if config.frame_count <= 128 else 16
        stream_statistics: HackRFStreamStatistics | None = None
        run_started = time.perf_counter()
        stream_started: float | None = None

        def capture(stream: _ContinuousStream) -> None:
            nonlocal capture_queue_high_watermark, stream_statistics
            try:
                for capture_index, payload in enumerate(stream):
                    sequence_number = capture_index - config.startup_settling_frames
                    if sequence_number >= 0:
                        self._latest_capture_sequence = sequence_number
                    preview_needed = self._preview_handler is not None and sequence_number >= 0 and (
                        sequence_number == 0
                        or sequence_number + 1 == config.frame_count
                        or (sequence_number + 1) % config.display_interval_frames == 0
                    )
                    received = (
                        time.perf_counter()
                        if sequence_number >= 0 and (
                            sequence_number % diagnostic_stride == 0 or preview_needed
                        )
                        else 0.0
                    )
                    if self._cancellation.is_set():
                        raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")
                    while not self._cancellation.is_set():
                        try:
                            capture_queue.put((capture_index, payload, received), timeout=0.1)
                            if sequence_number >= 0 and sequence_number % diagnostic_stride == 0:
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
            nonlocal startup_input_saturated, startup_output_saturated
            for _ in range(config.capture_frame_count):
                if self._cancellation.is_set():
                    raise AcquisitionError("operation_cancelled", "Canlı ED oturumu iptal edildi.")
                item = take_work(capture_queue, "Alım", "live_capture_timeout")
                if item is end_of_stream:
                    if producer_error:
                        raise producer_error[0]
                    raise AcquisitionError(
                        "live_pipeline_short_stream",
                        "Alım üreticisi hata bildirmeden erken sonlandı.",
                    )
                capture_index, payload, received = item
                sequence_number = capture_index - config.startup_settling_frames
                sampled = sequence_number >= 0 and sequence_number % diagnostic_stride == 0
                if sampled:
                    timing_samples["capture_queue_age_ms"].append((time.perf_counter() - received) * 1000)
                processing_started = time.perf_counter() if sampled else 0.0
                channelized, frame_input_saturated = channelizer.process_ci8(
                    payload,
                    sequence_number=(
                        sequence_number if sequence_number >= 0 else capture_index
                    ),
                    frame_id=(sequence_number if sequence_number >= 0 else capture_index),
                    input_sample_rate_hz=config.rx_config.sample_rate_hz,
                    input_center_frequency_hz=config.input_center_frequency_hz,
                    output_center_frequency_hz=config.output_center_frequency_hz,
                    require_dc_safe_tuning=not config.direct_fpga_input,
                )
                if sequence_number < 0:
                    startup_input_saturated += frame_input_saturated
                    startup_output_saturated += channelized.saturated_components
                    continue
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
                            sample_rate_hz=config.rx_config.sample_rate_hz,
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
                    raise AcquisitionError(
                        "live_pipeline_short_stream",
                        "Kanal seçici hata bildirmeden erken sonlandı.",
                    )
                submitted_frame = (
                    automatic_scheduler.decorate(frame)
                    if automatic_scheduler is not None
                    else frame
                )
                pending_frames[frame.sequence_number] = submitted_frame
                yield submitted_frame

        def handle_response(response: IQResponse) -> None:
            nonlocal completed, raw_candidate_total, maximum_active
            nonlocal automatic_parameter_outcome_count, latest_snapshot
            nonlocal first_response_at, last_response_at
            response_at = time.perf_counter()
            if first_response_at is None:
                first_response_at = response_at
            last_response_at = response_at
            decoded = decode_live_ed_response(response.payload, response.sequence_number)
            if decoded.dma_status_flags != 7:
                raise TransportError("dma_status", "Canlı FPGA DMA durumu geçersizdir.")
            if decoded.dropped_candidates != 0:
                raise TransportError(
                    "candidate_drop",
                    "FPGA tespit kapasitesi aşıldı: "
                    f"kare {response.sequence_number + 1}, "
                    f"ham aday {decoded.raw_candidate_count}, "
                    f"etkin olay {len(decoded.active)}, "
                    f"izlemeye alınamayan aday {decoded.dropped_candidates}. "
                    "Bu bağlantı hatası değildir. LNA/VGA kazançlarını azaltıp yeniden deneyin.",
                )
            output_frame = pending_frames.pop(response.sequence_number)
            outcomes: tuple[AutomaticParameterOutcome, ...] = ()
            if automatic_scheduler is not None:
                outcomes = automatic_scheduler.observe_response(
                    response.sequence_number, decoded.parameter
                )
                automatic_scheduler.observe_events(decoded.active, decoded.ended)
                automatic_parameter_outcome_count += len(outcomes)
            snapshot = LiveEDSnapshot(
                response.sequence_number, output_frame, decoded, outcomes
            )
            latest_snapshot = snapshot
            if output_frame.complex_sample_count == 4096 and not config.direct_fpga_input:
                confirmed_ids = tuple(
                    event.event_id for event in decoded.active if event.state == "confirmed"
                )
                self._record_audio_frame(
                    output_frame,
                    tuple(
                        event.event_id for event in decoded.active
                        if event.state == "confirmed" and event.observed_this_frame
                    ),
                    confirmed_ids,
                    snapshot,
                )
                self._record_measurement_snapshot(snapshot)
            completed += 1
            raw_candidate_total += decoded.raw_candidate_count
            maximum_active = max(maximum_active, len(decoded.active))
            if snapshot_handler is not None and (outcomes or
                completed == 1
                or completed == config.frame_count
                or completed % config.display_interval_frames == 0
            ):
                snapshot_handler(snapshot)

        producer: threading.Thread | None = None
        channel_worker: threading.Thread | None = None
        try:
            if config.fpga_enabled:
                capabilities = None
                probe = getattr(self._transport, "probe_capabilities", None)
                if callable(probe):
                    capabilities = probe(
                        config.board_host, config.board_port, timeout_seconds=2.0
                    )
                else:
                    capabilities = getattr(self._transport, "capabilities", None)
                if (
                    config.direct_fpga_input
                    and (
                        capabilities is None
                        or not bool(getattr(capabilities, "wideband_burst", False))
                    )
                ):
                    raise AcquisitionError(
                        "wideband_profile_unavailable",
                        "Kart ağ köprüsü 10 MS/s geniş bant burst yeteneğini doğrulamadı.",
                    )
                if (
                    config.automatic_parameters_enabled
                    and config.fpga_fft_size == 4096
                    and capabilities is not None
                    and bool(getattr(capabilities, "inline_parameter_observation", False))
                    and int(getattr(capabilities, "maximum_parameter_span_bins", 0)) >= 512
                    and int(getattr(capabilities, "parameter_contexts", 0)) == 1
                ):
                    automatic_scheduler = AutomaticParameterScheduler(
                        center_frequency_hz=config.output_center_frequency_hz,
                        fft_size=config.fpga_fft_size,
                    )
                    self.automatic_parameter_status = (
                        "Etkin · tespit sürerken tek bağlamlı dört kare PL/ARM ölçümü"
                    )
                elif config.automatic_parameters_enabled:
                    self.automatic_parameter_status = (
                        "Kapalı · kart ağ köprüsü canlı parametre yeteneğini doğrulamadı"
                    )
                else:
                    self.automatic_parameter_status = "Operatör ayarıyla kapalı"
                self._transport.connect(config.board_host, config.board_port, timeout_seconds=3.0)
            else:
                self.automatic_parameter_status = "Kapalı · FPGA tespiti kullanılmıyor"
            stream = self._stream_factory(
                self.executable,
                config.rx_config,
                config.capture_frame_count,
                cancellation=self._cancellation,
            )
            with self._lock:
                self._active_stream = stream
            with stream:
                stream_started = time.perf_counter()
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
                    raise AcquisitionError(
                        "fpga_short_stream",
                        "FPGA alışverişi tam kare sayısına ulaşmadı: "
                        f"istenen={config.frame_count}, alışveriş={exchanged}, yanıt={completed}.",
                    )
                if automatic_scheduler is not None:
                    final_outcomes = automatic_scheduler.finish()
                    automatic_parameter_outcome_count += len(final_outcomes)
                    if final_outcomes and latest_snapshot is not None and snapshot_handler is not None:
                        snapshot_handler(
                            replace(
                                latest_snapshot,
                                automatic_parameter_outcomes=final_outcomes,
                            )
                        )
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
                "startup_settling_frames": config.startup_settling_frames,
                "startup_input_saturated_components": startup_input_saturated,
                "startup_output_saturated_components": startup_output_saturated,
                "capture_queue_high_watermark": capture_queue_high_watermark,
                "channel_queue_high_watermark": channel_queue_high_watermark,
                "channelizer_backend": channelizer_backend,
                "automatic_parameter_status": self.automatic_parameter_status,
                "automatic_parameter_outcomes": automatic_parameter_outcome_count,
                "automatic_parameter_expired_before_measurement": (
                    automatic_scheduler.expired_before_measurement_count
                    if automatic_scheduler is not None else 0
                ),
                "setup_seconds": (
                    stream_started - run_started
                    if stream_started is not None else time.perf_counter() - run_started
                ),
                "response_interval_seconds": (
                    last_response_at - first_response_at
                    if first_response_at is not None and last_response_at is not None
                    else 0.0
                ),
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
            stream_statistics.frames_received != config.capture_frame_count
            or stream_statistics.bytes_received
            != config.capture_frame_count * config.rx_config.sample_count * 2
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
        if stream_started is None:
            raise AcquisitionError(
                "stream_timing_missing", "Canlı veri akışı süre başlangıcı oluşmadı."
            )
        elapsed = time.perf_counter() - stream_started
        response_interval = (
            last_response_at - first_response_at
            if first_response_at is not None and last_response_at is not None
            else 0.0
        )
        frames_per_second = (
            (completed - 1) / response_interval
            if completed > 1 and response_interval > 0.0
            else completed / elapsed
        )
        self.last_diagnostics["stream_elapsed_seconds"] = elapsed
        self.last_diagnostics["frames_per_second_scope"] = (
            "first_to_last_fpga_response_interval"
            if completed > 1 and response_interval > 0.0
            else "complete_stream_interval"
        )
        return LiveEDSessionResult(
            completed_frames=completed,
            elapsed_seconds=elapsed,
            frames_per_second=frames_per_second,
            real_time_margin=frames_per_second /
                (config.processing_sample_rate_hz / config.fpga_fft_size),
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
                "frames_per_second_scope": self.last_diagnostics[
                    "frames_per_second_scope"
                ],
                "stages": {name: {"samples": len(values),
                    "p50_ms": float(np.percentile(values, 50)) if values else 0.0,
                    "p95_ms": float(np.percentile(values, 95)) if values else 0.0,
                    "maximum_ms": max(values, default=0.0)} for name, values in timing_samples.items()},
            },
            fpga_enabled=config.fpga_enabled,
        )
