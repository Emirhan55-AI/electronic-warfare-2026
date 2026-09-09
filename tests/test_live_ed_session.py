from __future__ import annotations

from dataclasses import replace
import struct
import threading
import time
import zlib

import pytest

from algorithms.p0 import IQFrame, IQResponse, P0Channelizer, TransportError, TransportStats
from app.operator_console.live_ed import (
    LIVE_AUDIO_WINDOW_FRAMES,
    LiveEDConfiguration,
    LiveEDSession,
    decode_live_ed_response,
)
from platforms.acquisition import AcquisitionError, HackRFContinuousRX, HackRFStreamStatistics


SERIAL = "0000000000000000a32868dc35138247"


def _response(frame_id: int, *, event_state: int = 2, event_flags: int = 1) -> bytes:
    event = bytearray(68)
    struct.pack_into("<QIIQBB", event, 0, 17, max(0, frame_id - 2), frame_id, 3, event_state, 1)
    struct.pack_into("<HHHHBB", event, 28, 2299, 2308, 2304, 10, 1, event_flags)
    struct.pack_into("<QQQ", event, 40, 300 << 30, 3 << 30, 20 << 30)
    result = bytearray(20) + event
    struct.pack_into("<IHHHBBQ", result, 0, frame_id, 1, 0, 0, 0, 0, 9)
    header = bytearray(48)
    struct.pack_into(
        "<IHHIIIIII",
        header,
        0,
        0x31534550,
        3,
        48,
        len(header) + len(result),
        frame_id,
        0,
        len(result),
        5,
        7,
    )
    struct.pack_into("<I", header, 44, zlib.crc32(header[:44]) & 0xFFFFFFFF)
    return bytes(header + result)


class _FakeStream:
    def __init__(self, executable, config, frame_count, *, cancellation):
        del executable, config
        self.frame_count = frame_count
        self.cancellation = cancellation
        self.statistics = None

    def __enter__(self):
        return self

    def __iter__(self):
        payload = bytes(16_384 * 2)
        for _ in range(self.frame_count):
            yield payload
        self.statistics = HackRFStreamStatistics(
            frames_received=self.frame_count,
            bytes_received=self.frame_count * len(payload),
            elapsed_seconds=0.01,
            overruns=0,
            longest_overrun_bytes=0,
            process_returncode=0,
            stderr_text="0 overruns, longest 0 bytes",
        )

    def close(self):
        self.cancellation.set()

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback


class _FakeTransport:
    def __init__(self):
        self.stats = TransportStats()

    def connect(self, host, port, *, timeout_seconds):
        del host, port, timeout_seconds
        self.stats = replace(self.stats, state="CONNECTED")

    def exchange_stream(self, frames, response_handler):
        count = 0
        for frame in frames:
            count += 1
            self.stats = replace(
                self.stats,
                frames_sent=count,
                frames_received=count,
                bytes_sent=self.stats.bytes_sent + len(frame.payload),
            )
            response_handler(IQResponse(frame.sequence_number, _response(frame.frame_id)))
        return count

    def close(self):
        self.stats = replace(self.stats, state="DISCONNECTED")


class _SaturatedStream(_FakeStream):
    def __iter__(self):
        payload = bytes([127, 127]) * 16_384
        for _ in range(self.frame_count):
            yield payload
        self.statistics = HackRFStreamStatistics(
            self.frame_count,
            self.frame_count * len(payload),
            0.01,
            0,
            0,
            0,
            "0 overruns, longest 0 bytes",
        )


class _BlockingSaturatedStream(_FakeStream):
    def __iter__(self):
        payload = bytes([127, 127]) * 16_384
        yield payload
        self.cancellation.wait(10.0)
        self.statistics = HackRFStreamStatistics(
            1,
            len(payload),
            0.01,
            0,
            0,
            0,
            "0 overruns, longest 0 bytes",
        )


class _DrainingStream(_FakeStream):
    drained = threading.Event()

    def __iter__(self):
        type(self).drained.clear()
        yield from super().__iter__()
        type(self).drained.set()


class _WaitForCaptureTransport(_FakeTransport):
    def exchange_stream(self, frames, response_handler):
        assert _DrainingStream.drained.wait(1.0), "USB okuma işi taşıma başlamadan akışı boşaltamadı."
        return super().exchange_stream(frames, response_handler)


def test_live_response_decoder_exposes_fpga_event_fields() -> None:
    decoded = decode_live_ed_response(_response(42), 42)
    assert decoded.dma_status_flags == 7
    assert decoded.raw_candidate_count == 5
    assert decoded.evicted_history_count == 9
    assert len(decoded.active) == 1
    event = decoded.active[0]
    assert event.event_id == 17
    assert event.state == "confirmed"
    assert event.observed_this_frame
    assert event.peak_shifted_bin == 2304
    assert event.peak_to_noise_db == 20.0
    assert not event.weak_evidence
    assert not event.single_frame_confident


def test_live_response_decoder_exposes_persistent_weak_class() -> None:
    decoded = decode_live_ed_response(_response(42, event_flags=0x05), 42)

    event = decoded.active[0]
    assert event.weak_evidence
    assert not event.single_frame_confident


def test_live_response_decoder_exposes_wideband_class() -> None:
    decoded = decode_live_ed_response(_response(42, event_flags=0x11), 42)

    event = decoded.active[0]
    assert event.wideband_evidence
    assert not event.weak_evidence


@pytest.mark.parametrize("event_flags", (0x00, 0x08, 0x21))
def test_live_response_decoder_rejects_invalid_candidate_class_flags(event_flags: int) -> None:
    with pytest.raises(TransportError) as failure:
        decode_live_ed_response(_response(42, event_flags=event_flags), 42)

    assert getattr(failure.value, "code", "") == "local_response_event"


def test_live_configuration_rejects_non_integer_center_with_product_error() -> None:
    with pytest.raises(AcquisitionError) as failure:
        LiveEDConfiguration(  # type: ignore[arg-type]
            output_center_frequency_hz="104650000",
            device_serial=SERIAL,
        )

    assert failure.value.code == "invalid_center_frequency"


def test_physical_live_session_fails_closed_without_native_channelizer() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=1, fpga_enabled=False),
        stream_factory=HackRFContinuousRX,
        channelizer_factory=P0Channelizer,
    )

    with pytest.raises(AcquisitionError) as failure:
        session.run()

    assert failure.value.code == "native_channelizer_required"


def test_live_session_channelizes_and_publishes_bounded_fpga_snapshots() -> None:
    snapshots = []
    configuration = LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        frame_count=4,
        display_interval_frames=2,
        device_serial=SERIAL,
    )
    session = LiveEDSession(
        "hackrf_transfer",
        configuration,
        stream_factory=_FakeStream,
        transport_factory=_FakeTransport,
    )

    result = session.run(snapshots.append)

    assert result.completed_frames == 4
    assert result.raw_candidate_total == 20
    assert result.maximum_active_events == 1
    assert result.input_saturated_components == 0
    assert result.output_saturated_components == 0
    assert 1 <= result.capture_queue_high_watermark <= 4
    assert result.hackrf_statistics.overruns == 0
    assert result.transport_statistics.frames_received == 4
    assert [item.sequence_number for item in snapshots] == [0, 1, 3]
    assert all(item.output_frame.sample_rate_hz == 2_000_000 for item in snapshots)
    assert all(item.output_frame.center_frequency_hz == 104_650_000 for item in snapshots)
    window = session.measurement_window(17)
    assert [item.sequence_number for item in window] == [0, 1, 2, 3]
    assert all(item.response.active[0].event_id == 17 for item in window)
    assert session.current_measurement_window(17) == window
    # A stored snapshot is still available for display, but cannot start a new measurement.
    last = window[-1]
    session._record_measurement_snapshot(replace(last, sequence_number=4,
        response=replace(last.response, active=())))
    assert session.measurement_window(17) == window
    assert session.current_measurement_window(17) == ()
    for sequence in (5, 6, 7):
        session._record_measurement_snapshot(replace(last, sequence_number=sequence))
        assert session.current_measurement_window(17) == ()
    session._record_measurement_snapshot(replace(last, sequence_number=8))
    assert [item.sequence_number for item in session.current_measurement_window(17)] == [5, 6, 7, 8]
    session._record_measurement_snapshot(replace(last, sequence_number=10))
    assert session.current_measurement_window(17) == ()


def test_live_session_rejects_clipped_iq_instead_of_presenting_it_as_valid() -> None:
    configuration = LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        frame_count=2,
        device_serial=SERIAL,
    )
    session = LiveEDSession(
        "hackrf_transfer",
        configuration,
        stream_factory=_SaturatedStream,
        transport_factory=_FakeTransport,
    )

    snapshots = []
    with pytest.raises(AcquisitionError, match="kırpılan") as failure:
        session.run(snapshots.append)

    assert failure.value.code == "iq_saturation"
    assert snapshots == []
    assert session._transport.stats.frames_sent == 0
    assert session.last_diagnostics["hackrf_statistics"]["frames_received"] == 2


def test_optional_receive_level_assessment_uses_consecutive_startup_window() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=64, assess_receive_level=True),
        stream_factory=_FakeStream,
        transport_factory=_FakeTransport,
    )
    with pytest.raises(AcquisitionError) as failure:
        session.run()
    assert failure.value.code == "rx_level_low"
    # The rejected decision frame and remaining frames cannot be sent as
    # if they belonged to a completed, correctly levelled capture.
    assert session._transport.stats.frames_sent <= 47


def test_saturation_is_reported_before_a_long_capture_can_mask_it_as_queue_timeout() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=878_906),
        stream_factory=_BlockingSaturatedStream,
        transport_factory=_FakeTransport,
    )

    started = time.perf_counter()
    with pytest.raises(AcquisitionError) as failure:
        session.run()

    assert failure.value.code == "iq_saturation"
    assert time.perf_counter() - started < 1.0


def test_live_session_decouples_bounded_usb_capture_from_transport() -> None:
    configuration = LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        frame_count=4,
        display_interval_frames=2,
        device_serial=SERIAL,
    )
    session = LiveEDSession(
        "hackrf_transfer",
        configuration,
        stream_factory=_DrainingStream,
        transport_factory=_WaitForCaptureTransport,
    )

    result = session.run()

    assert result.completed_frames == 4
    assert result.capture_queue_high_watermark == 4
    assert 1 <= result.channelized_queue_high_watermark <= 4


def test_receive_preview_precedes_any_fpga_response_and_has_no_detection_fields():
    preview_ready = threading.Event()
    previews, responses = [], []

    class DelayedTransport(_FakeTransport):
        def exchange_stream(self, frames, response_handler):
            assert preview_ready.wait(2), "RX önizlemesi ilk FPGA yanıtını bekledi."
            assert responses == []
            return super().exchange_stream(frames, response_handler)

    session = LiveEDSession("hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL, frame_count=32),
        stream_factory=_FakeStream, transport_factory=DelayedTransport)

    def preview(item):
        previews.append(item)
        assert not hasattr(item, "response")
        preview_ready.set()

    session.set_preview_handler(preview)
    result = session.run(responses.append)
    assert [item.sequence_number for item in previews] == [0, 14, 29, 31]
    assert result.preview_frames == 4
    assert result.completed_frames == 32
    assert result.transport_statistics.frames_received == 32
    assert all(item.received_monotonic > 0 for item in previews)
    assert all(item.display_frame is not None for item in previews)
    assert all(item.display_frame.sample_rate_hz == 8_000_000 for item in previews)
    assert all(item.display_frame.center_frequency_hz == session.configuration.input_center_frequency_hz for item in previews)
    assert all(len(item.display_frame.payload) == 16_384 * 2 for item in previews)
    assert all(item.output_frame.sample_rate_hz == 2_000_000 for item in previews)
    assert all(len(item.output_frame.payload) == 4_096 * 2 for item in previews)


def test_explicit_receive_only_mode_never_connects_or_manufactures_fpga_results():
    class NoBoard(_FakeTransport):
        def connect(self, *args, **kwargs):
            raise AssertionError("RX önizleme kart bağlantısı denememeli.")
        def exchange_stream(self, *args, **kwargs):
            raise AssertionError("RX önizleme FPGA sonucu üretmemeli.")

    session = LiveEDSession("hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=32, fpga_enabled=False),
        stream_factory=_FakeStream, transport_factory=NoBoard)
    previews, responses = [], []
    session.set_preview_handler(previews.append)
    result = session.run(responses.append)
    assert result.completed_frames == 32
    assert result.fpga_enabled is False
    assert result.transport_statistics.frames_sent == result.transport_statistics.frames_received == 0
    assert result.raw_candidate_total == 0
    assert responses == []
    assert len(previews) == 4


def test_live_audio_window_is_bounded_and_resets_on_sequence_gap() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(
            output_center_frequency_hz=104_650_000,
            frame_count=LIVE_AUDIO_WINDOW_FRAMES,
            device_serial=SERIAL,
        ),
        stream_factory=_FakeStream,
        transport_factory=_FakeTransport,
    )
    payload = bytes(8192)
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        session._record_audio_frame(
            IQFrame(sequence, 2_000_000, 104_650_000, payload, frame_id=sequence)
        )

    window = session.audio_window()
    assert session.audio_window_ready()
    assert session.audio_window_frame_count() == LIVE_AUDIO_WINDOW_FRAMES
    assert len(window) == LIVE_AUDIO_WINDOW_FRAMES
    assert window[0].sequence_number == 0
    assert window[-1].sequence_number == LIVE_AUDIO_WINDOW_FRAMES - 1

    session._record_audio_frame(
        IQFrame(3_000, 2_000_000, 104_650_000, payload, frame_id=3_000)
    )
    assert not session.audio_window_ready()
    assert session.audio_window_frame_count() == 1
    assert session.audio_window() == ()


def test_live_audio_requires_consecutive_confirmed_observations_for_selected_event() -> None:
    session = LiveEDSession(
        "hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL),
        stream_factory=_FakeStream, transport_factory=_FakeTransport,
    )
    payload = bytes(8192)
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        session._record_audio_frame(
            IQFrame(sequence, 2_000_000, 104_650_000, payload, frame_id=sequence), (17,)
        )
    assert session.audio_window_ready(17)
    assert len(session.audio_window(17)) == LIVE_AUDIO_WINDOW_FRAMES
    assert not session.audio_window_ready(18)
    assert session.audio_window(18) == ()
    # A single missed observation invalidates event continuity even while IQ is contiguous.
    sequence = LIVE_AUDIO_WINDOW_FRAMES
    session._record_audio_frame(IQFrame(sequence, 2_000_000, 104_650_000, payload), ())
    assert session.audio_window_ready()
    assert not session.audio_window_ready(17)
    assert session.audio_window(17) == ()
    session._record_audio_frame(IQFrame(sequence + 1, 2_000_000, 104_650_000, payload), (17,))
    assert session.audio_window_frame_count(17) == 1
