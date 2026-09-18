from __future__ import annotations

from dataclasses import replace
import struct
import threading
import time
import zlib

import pytest

from algorithms.p0 import (
    IQFrame, IQResponse, P0Channelizer, TransportCapabilities, TransportError,
    TransportStats,
)
from algorithms.p0.parameter_client import MAXIMUM_BOARD_SPAN_BINS
from app.operator_console.live_ed import (
    LIVE_AUDIO_MAX_CONSECUTIVE_MISSES,
    LIVE_AUDIO_WINDOW_FRAMES,
    LIVE_STARTUP_SETTLING_FRAMES,
    LiveEDConfiguration,
    LiveEDSession,
    LiveEDSnapshot,
    decode_live_ed_response,
)
from platforms.acquisition import AcquisitionError, HackRFContinuousRX, HackRFStreamStatistics


SERIAL = "0000000000000000a32868dc35138247"


def _direction_snapshot(index, *, event_id=17, observed=True):
    response = decode_live_ed_response(_response(index), index)
    event = replace(response.active[0], event_id=event_id, observed_this_frame=observed)
    return LiveEDSnapshot(index, IQFrame(index, 2_000_000, 104_650_000, bytes(8192), frame_id=index),
                          replace(response, active=(event,)))


def test_direction_capture_excludes_host_backlog_and_latches_changed_ids():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session._latest_capture_sequence = 20
    session.begin_direction_capture(2290, 2320)
    for index in range(30):
        session._record_measurement_snapshot(_direction_snapshot(index, event_id=100 + index))
    frames, _ = session.direction_capture()
    assert [frame.sequence_number for frame in frames] == [22, 23, 24, 25]
    assert [frame.response.active[0].event_id for frame in frames] == [122, 123, 124, 125]
    session._record_measurement_snapshot(_direction_snapshot(30, observed=False))
    assert session.direction_capture()[0] == frames
    session.begin_direction_capture(2290, 2320)
    assert session.direction_capture()[0] == ()
    session.cancel_direction_capture()
    for index in range(32, 40):
        session._record_measurement_snapshot(_direction_snapshot(index))
    assert session.direction_capture()[0] == ()


def test_locked_direction_capture_keeps_fresh_frames_when_target_falls_below_detection():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session.begin_direction_capture(2290, 2320, require_observed_target=False)
    for index in range(2, 6):
        snapshot = _direction_snapshot(index, observed=False)
        session._record_measurement_snapshot(
            replace(snapshot, response=replace(snapshot.response, active=()))
        )
    frames, reason = session.direction_capture()
    assert [frame.sequence_number for frame in frames] == [2, 3, 4, 5]
    assert reason == "Kilitli kanal gücü toplanıyor: 4/4 kare."


def test_locked_direction_capture_still_rejects_nearby_observed_candidate():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session.begin_direction_capture(2290, 2320, require_observed_target=False)
    snapshot = _direction_snapshot(2)
    event = snapshot.response.active[0]
    session._record_measurement_snapshot(
        replace(
            snapshot,
            response=replace(
                snapshot.response,
                active=(event, replace(event, event_id=99)),
            ),
        )
    )
    assert session.direction_capture()[0] == ()
    assert "başka veya sınırı taşan" in session.direction_capture()[1]


def test_parameter_capture_binds_fresh_channel_when_event_ids_change():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session._latest_capture_sequence = 20
    session.begin_parameter_capture(2290, 2320)
    for index in range(30):
        session._record_measurement_snapshot(
            _direction_snapshot(index, event_id=100 + index)
        )
        # The GUI polls after every response; the same request must not reset
        # the partially collected channel-bound window.
        session.begin_parameter_capture(2290, 2320)
    frames, reason = session.parameter_capture()
    assert [frame.sequence_number for frame in frames] == [22, 23, 24, 25]
    assert [frame.response.active[0].event_id for frame in frames] == [122, 123, 124, 125]
    assert "4/4" in reason
    session.cancel_parameter_capture()
    assert session.parameter_capture()[0] == ()


def test_extended_parameter_capture_requires_all_fresh_contiguous_frames():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session._transport._capabilities = TransportCapabilities(extended_parameter=True)
    assert session.parameter_measurement_frame_count == 16
    session._latest_capture_sequence = 20
    session.begin_parameter_capture(2290, 2320)
    for index in range(37):
        session._record_measurement_snapshot(_direction_snapshot(index, event_id=100 + index))
    assert len(session.parameter_capture()[0]) == 15
    session._record_measurement_snapshot(_direction_snapshot(38))  # 37 kayıp
    assert len(session.parameter_capture()[0]) == 1
    for index in range(39, 54):
        session._record_measurement_snapshot(_direction_snapshot(index, event_id=100 + index))
    frames, _ = session.parameter_capture()
    assert [frame.sequence_number for frame in frames] == list(range(38,54))
    session._record_measurement_snapshot(_direction_snapshot(54, observed=False))
    assert session.parameter_capture()[0] == frames
    session.cancel_parameter_capture()
    assert session.parameter_capture()[0] == ()


@pytest.mark.parametrize("problem", ["missing", "neighbour", "outside", "tentative", "gap"])
def test_direction_capture_rejects_ambiguous_or_discontinuous_windows(problem):
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session.begin_direction_capture(2290, 2320)
    for index in (2, 3):
        session._record_measurement_snapshot(_direction_snapshot(index))
    snapshot = _direction_snapshot(4)
    event = snapshot.response.active[0]
    if problem == "missing":
        snapshot = _direction_snapshot(4, observed=False)
    elif problem == "neighbour":
        snapshot = replace(snapshot, response=replace(snapshot.response, active=(event, replace(event, event_id=99))))
    elif problem == "outside":
        snapshot = replace(snapshot, response=replace(snapshot.response, active=(replace(event, end_shifted_bin=2330),)))
    elif problem == "tentative":
        snapshot = replace(snapshot, response=replace(snapshot.response, active=(replace(event, state="tentative"),)))
    else:
        snapshot = _direction_snapshot(5)
    session._record_measurement_snapshot(snapshot)
    assert len(session.direction_capture()[0]) < 4
    for index in range(6, 10):
        session._record_measurement_snapshot(_direction_snapshot(index))
    assert len(session.direction_capture()[0]) == 4


def test_direction_capture_rejects_unsupported_fft():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL, fpga_fft_size=8192))
    with pytest.raises(ValueError, match="4096"):
        session.begin_direction_capture(2290, 2320)


def test_direction_capture_accepts_full_p0pm_v2_span():
    session = LiveEDSession("unused", LiveEDConfiguration(104_650_000, SERIAL))
    session.begin_direction_capture(56, 4039)
    assert session._direction_span == (56, 4039)
    assert session._direction_span[1] - session._direction_span[0] + 1 == MAXIMUM_BOARD_SPAN_BINS
    session.cancel_direction_capture()
    with pytest.raises(ValueError, match="geçerli hedef kanalı"):
        session.begin_direction_capture(55, 4039)


def _response(
    frame_id: int,
    *,
    event_state: int = 2,
    event_flags: int = 1,
    dropped_candidates: int = 0,
) -> bytes:
    event = bytearray(68)
    struct.pack_into("<QIIQBB", event, 0, 17, max(0, frame_id - 2), frame_id, 3, event_state, 1)
    struct.pack_into("<HHHHBB", event, 28, 2299, 2308, 2304, 10, 1, event_flags)
    struct.pack_into("<QQQ", event, 40, 300 << 30, 3 << 30, 20 << 30)
    result = bytearray(20) + event
    struct.pack_into(
        "<IHHHBBQ", result, 0, frame_id, 1, 0, dropped_candidates, 0, 0, 9
    )
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


def _response_v2(frame_id: int) -> bytes:
    event = bytearray(68)
    struct.pack_into("<QIIQBB", event, 0, 17, frame_id - 2, frame_id, 3, 2, 1)
    struct.pack_into("<HHHHBB", event, 28, 2299, 2308, 2304, 10, 1, 1)
    struct.pack_into("<QQQ", event, 40, 300 << 30, 3 << 30, 20 << 30)
    result = bytearray(8_724)
    struct.pack_into("<IHHHBBQ", result, 0, frame_id, 1, 0, 0, 0, 0, 9)
    result[20:88] = event
    parameter = bytearray(128)
    struct.pack_into("<QQIB", parameter, 0, 91, 17, frame_id, 4)
    for offset, value in zip(
        range(24, 96, 12),
        (104_775_000.0, 104_770_000.0, 104_780_000.0, 10_000.0, -31.0, 18.0),
    ):
        struct.pack_into("<BBHd", parameter, offset, 1, 0, 0, value)
    struct.pack_into("<dddd", parameter, 96, 1.0, 10.0, 0.1, 0.2)
    header = bytearray(64)
    struct.pack_into(
        "<IHHIIIIIIIII",
        header,
        0,
        0x31534550,
        2,
        64,
        64 + len(result) + len(parameter),
        frame_id,
        0,
        len(result),
        5,
        7,
        zlib.crc32(result) & 0xFFFFFFFF,
        len(parameter),
        zlib.crc32(parameter) & 0xFFFFFFFF,
    )
    struct.pack_into("<I", header, 44, 1)
    struct.pack_into("<I", header, 60, zlib.crc32(header[:60]) & 0xFFFFFFFF)
    return bytes(header + result + parameter)


def test_full_abi_v2_response_keeps_detection_and_parameter_together():
    decoded = decode_live_ed_response(_response_v2(42), 42)
    assert [event.event_id for event in decoded.active] == [17]
    assert decoded.ended == ()
    assert decoded.parameter is not None
    assert decoded.parameter.intent_id == 91
    assert decoded.parameter.channel_power_dbfs.value == -31.0


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


class _ProfileSizedFakeStream(_FakeStream):
    def __init__(self, executable, config, frame_count, *, cancellation):
        super().__init__(executable, config, frame_count, cancellation=cancellation)
        self.sample_count = config.sample_count

    def __iter__(self):
        payload = bytes(self.sample_count * 2)
        for _ in range(self.frame_count):
            yield payload
        self.statistics = HackRFStreamStatistics(
            self.frame_count, self.frame_count * len(payload), .01, 0, 0, 0,
            "0 overruns, longest 0 bytes")


class _FakeTransport:
    def __init__(self):
        self.stats = TransportStats()
        self.capabilities = TransportCapabilities(wideband_burst=True)

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


class _IncompleteExchangeTransport(_FakeTransport):
    def exchange_stream(self, frames, response_handler):
        completed = super().exchange_stream(frames, response_handler)
        return completed - 1


class _CandidateDropTransport(_FakeTransport):
    def exchange_stream(self, frames, response_handler):
        frame = next(iter(frames))
        self.stats = replace(self.stats, frames_sent=1, frames_received=1)
        response_handler(
            IQResponse(
                frame.sequence_number,
                _response(frame.frame_id, dropped_candidates=3),
            )
        )
        return 1


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


class _StartupTransientStream(_FakeStream):
    def __iter__(self):
        saturated = bytes([127, 127]) * 16_384
        clean = bytes(16_384 * 2)
        for index in range(self.frame_count):
            yield saturated if index < LIVE_STARTUP_SETTLING_FRAMES else clean
        self.statistics = HackRFStreamStatistics(
            self.frame_count,
            self.frame_count * len(clean),
            0.01,
            0,
            0,
            0,
            "0 overruns, longest 0 bytes",
        )


class _PostSettlingSaturatedStream(_FakeStream):
    def __iter__(self):
        saturated = bytes([127, 127]) * 16_384
        clean = bytes(16_384 * 2)
        for index in range(self.frame_count):
            yield clean if index < LIVE_STARTUP_SETTLING_FRAMES else saturated
        self.statistics = HackRFStreamStatistics(
            self.frame_count,
            self.frame_count * len(clean),
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


@pytest.mark.parametrize("fft_size", (4096, 8192, 16384))
def test_runtime_fpga_fft_sizes_drive_capture_channelizer_and_transport(fft_size) -> None:
    configuration = LiveEDConfiguration(
        104_650_000, SERIAL, frame_count=1, fpga_fft_size=fft_size)
    assert configuration.rx_config.sample_count == 4 * fft_size
    factory = (lambda: P0Channelizer()) if fft_size == 4096 else (
        lambda profile: P0Channelizer(profile))
    session = LiveEDSession(
        "hackrf_transfer", configuration,
        stream_factory=_ProfileSizedFakeStream,
        transport_factory=_FakeTransport,
        channelizer_factory=factory,
    )
    snapshots = []
    result = session.run(snapshots.append)
    assert result.completed_frames == 1
    assert snapshots[0].output_frame.complex_sample_count == fft_size
    assert result.hackrf_statistics.bytes_received == 8 * fft_size
    if fft_size == 4096:
        assert session.current_measurement_window(17) == ()
    else:
        assert session.audio_window_frame_count() == 0


def test_buffered_10msps_burst_reaches_fpga_without_host_decimation() -> None:
    configuration = LiveEDConfiguration(
        820_000_000,
        SERIAL,
        frame_count=4,
        direct_fpga_input=True,
        automatic_parameters_enabled=False,
    )
    assert configuration.input_center_frequency_hz == 820_000_000
    assert configuration.rx_config.sample_rate_hz == 10_000_000
    assert configuration.rx_config.sample_count == 4096
    session = LiveEDSession(
        "hackrf_transfer",
        configuration,
        stream_factory=_ProfileSizedFakeStream,
        transport_factory=_FakeTransport,
    )
    snapshots = []

    result = session.run(snapshots.append)

    assert result.completed_frames == 4
    assert result.hackrf_statistics.bytes_received == 4 * 4096 * 2
    assert result.transport_statistics.frames_received == 4
    assert all(item.output_frame.sample_rate_hz == 10_000_000 for item in snapshots)
    assert all(item.output_frame.center_frequency_hz == 820_000_000 for item in snapshots)
    assert session.measurement_channelizer["backend"] == "direct-ci8"
    assert session.audio_window_frame_count() == 0


def test_direct_10msps_burst_disables_unvalidated_parameter_path() -> None:
    with pytest.raises(AcquisitionError, match="parametre"):
        LiveEDConfiguration(820_000_000, SERIAL, direct_fpga_input=True)
    with pytest.raises(AcquisitionError, match="aynı"):
        LiveEDConfiguration(
            820_000_000,
            SERIAL,
            frame_count=4,
            direct_fpga_input=True,
            automatic_parameters_enabled=False,
            input_center_frequency_hz_override=819_000_000,
        )


def test_direct_10msps_burst_requires_explicit_board_capability() -> None:
    class LegacyTransport(_FakeTransport):
        def __init__(self):
            super().__init__()
            self.capabilities = TransportCapabilities()

    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(
            820_000_000,
            SERIAL,
            frame_count=4,
            direct_fpga_input=True,
            automatic_parameters_enabled=False,
        ),
        stream_factory=_ProfileSizedFakeStream,
        transport_factory=LegacyTransport,
    )

    with pytest.raises(AcquisitionError, match="geniş bant burst") as failure:
        session.run()

    assert failure.value.code == "wideband_profile_unavailable"
    assert session._transport.stats.frames_sent == 0

    with pytest.raises(AcquisitionError, match="en fazla 256"):
        LiveEDConfiguration(
            820_000_000,
            SERIAL,
            frame_count=257,
            direct_fpga_input=True,
            automatic_parameters_enabled=False,
        )


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


def test_incomplete_fpga_exchange_is_not_reported_as_usb_short_stream() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=4),
        stream_factory=_FakeStream,
        transport_factory=_IncompleteExchangeTransport,
    )

    with pytest.raises(AcquisitionError) as failure:
        session.run()

    assert failure.value.code == "fpga_short_stream"
    assert "istenen=4" in str(failure.value)


def test_candidate_capacity_error_preserves_frame_and_drop_counts() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(104_650_000, SERIAL, frame_count=1),
        stream_factory=_FakeStream,
        transport_factory=_CandidateDropTransport,
    )

    with pytest.raises(TransportError) as failure:
        session.run()

    assert failure.value.code == "candidate_drop"
    assert "kare 1" in str(failure.value)
    assert "ham aday 5" in str(failure.value)
    assert "izlemeye alınamayan aday 3" in str(failure.value)
    assert "bağlantı hatası değildir" in str(failure.value)


def test_startup_transient_is_discarded_before_strict_saturation_check() -> None:
    configuration = LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        frame_count=2,
        device_serial=SERIAL,
        startup_settling_frames=LIVE_STARTUP_SETTLING_FRAMES,
    )
    session = LiveEDSession(
        "hackrf_transfer",
        configuration,
        stream_factory=_StartupTransientStream,
        transport_factory=_FakeTransport,
    )
    snapshots = []

    result = session.run(snapshots.append)

    assert result.completed_frames == 2
    assert result.hackrf_statistics.frames_received == 2 + LIVE_STARTUP_SETTLING_FRAMES
    assert result.transport_statistics.frames_sent == 2
    assert result.input_saturated_components == 0
    assert result.output_saturated_components == 0
    assert [snapshot.sequence_number for snapshot in snapshots] == [0, 1]
    assert session.last_diagnostics["startup_settling_frames"] == LIVE_STARTUP_SETTLING_FRAMES
    assert session.last_diagnostics["startup_input_saturated_components"] > 0


def test_saturation_after_startup_settling_still_fails_closed() -> None:
    session = LiveEDSession(
        "hackrf_transfer",
        LiveEDConfiguration(
            104_650_000,
            SERIAL,
            frame_count=2,
            startup_settling_frames=LIVE_STARTUP_SETTLING_FRAMES,
        ),
        stream_factory=_PostSettlingSaturatedStream,
        transport_factory=_FakeTransport,
    )

    with pytest.raises(AcquisitionError) as failure:
        session.run()

    assert failure.value.code == "iq_saturation"
    assert session._transport.stats.frames_sent == 0


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


def test_live_audio_allows_only_bounded_detector_misses_for_confirmed_event() -> None:
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
    # A brief detector miss is tolerated only while the ARM event remains confirmed.
    sequence = LIVE_AUDIO_WINDOW_FRAMES
    session._record_audio_frame(
        IQFrame(sequence, 2_000_000, 104_650_000, payload), (), (17,)
    )
    assert session.audio_window_ready()
    assert session.audio_window_ready(17)
    assert session.audio_window_quality(17)["observed_frames"] == LIVE_AUDIO_WINDOW_FRAMES - 1

    for offset in range(1, LIVE_AUDIO_MAX_CONSECUTIVE_MISSES):
        session._record_audio_frame(
            IQFrame(sequence + offset, 2_000_000, 104_650_000, payload), (), (17,)
        )
    assert session.audio_window_ready(17)
    assert session.audio_window_quality(17)["max_consecutive_misses"] == LIVE_AUDIO_MAX_CONSECUTIVE_MISSES

    session._record_audio_frame(
        IQFrame(
            sequence + LIVE_AUDIO_MAX_CONSECUTIVE_MISSES,
            2_000_000,
            104_650_000,
            payload,
        ),
        (),
        (17,),
    )
    assert not session.audio_window_ready(17)
    assert session.audio_window(17) == ()

    # Losing the confirmed ARM event invalidates the event-bound window immediately.
    session._record_audio_frame(
        IQFrame(sequence + LIVE_AUDIO_MAX_CONSECUTIVE_MISSES + 1, 2_000_000, 104_650_000, payload),
        (),
        (),
    )
    assert session.audio_window_frame_count(17) == 0


def test_live_audio_channel_survives_event_id_churn_and_rejects_ambiguity() -> None:
    session = LiveEDSession(
        "hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL),
        stream_factory=_FakeStream, transport_factory=_FakeTransport,
    )
    target_frequency_hz = 104_775_000.0
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        snapshot = _direction_snapshot(sequence, event_id=17 + sequence // 250)
        event_id = int(snapshot.response.active[0].event_id)
        session._record_audio_frame(
            snapshot.output_frame,
            (event_id,),
            (event_id,),
            snapshot,
        )

    assert not session.audio_window_ready(event_id)
    assert session.audio_channel_ready(target_frequency_hz)
    assert session.audio_channel_frame_count(target_frequency_hz) == LIVE_AUDIO_WINDOW_FRAMES
    window, quality = session.audio_channel_window_snapshot(target_frequency_hz)
    assert len(window) == LIVE_AUDIO_WINDOW_FRAMES
    assert quality["distinct_event_ids"] > 1
    assert quality["event_id_changes"] > 0
    assert quality["invalid_frames"] == 0

    ambiguous = _direction_snapshot(LIVE_AUDIO_WINDOW_FRAMES, event_id=999)
    event = ambiguous.response.active[0]
    ambiguous = replace(
        ambiguous,
        response=replace(
            ambiguous.response,
            active=(event, replace(event, event_id=1_000)),
        ),
    )
    session._record_audio_frame(
        ambiguous.output_frame,
        (999, 1_000),
        (999, 1_000),
        ambiguous,
    )
    assert session.audio_channel_frame_count(target_frequency_hz) == 0
    assert not session.audio_channel_ready(target_frequency_hz)


def test_live_audio_channel_ignores_retained_overlapping_event_and_tolerates_brief_gap() -> None:
    session = LiveEDSession(
        "hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL),
        stream_factory=_FakeStream, transport_factory=_FakeTransport,
    )
    target_frequency_hz = 104_775_000.0
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        snapshot = _direction_snapshot(sequence, event_id=17)
        observed = snapshot.response.active[0]
        retained = replace(
            observed,
            event_id=16,
            observed_this_frame=False,
            last_seen_frame_id=max(0, sequence - 1),
        )
        active = (retained,) if sequence == 10 else (retained, observed)
        snapshot = replace(
            snapshot,
            response=replace(snapshot.response, active=active),
        )
        session._record_audio_frame(
            snapshot.output_frame,
            tuple(event.event_id for event in active if event.observed_this_frame),
            tuple(event.event_id for event in active),
            snapshot,
        )

    assert session.audio_channel_ready(target_frequency_hz)
    window, quality = session.audio_channel_window_snapshot(target_frequency_hz)
    assert len(window) == LIVE_AUDIO_WINDOW_FRAMES
    assert quality["observed_frames"] == LIVE_AUDIO_WINDOW_FRAMES - 1
    assert quality["max_consecutive_misses"] == 1
    assert quality["invalid_frames"] == 0


def test_live_audio_stream_returns_only_new_frames_and_reports_consumer_gap() -> None:
    session = LiveEDSession(
        "hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL),
        stream_factory=_FakeStream, transport_factory=_FakeTransport,
    )
    target_frequency_hz = 104_775_000.0
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        snapshot = _direction_snapshot(sequence, event_id=17)
        session._record_audio_frame(snapshot.output_frame, (17,), (17,), snapshot)
    initial, quality = session.audio_channel_frames_after(target_frequency_hz, None)
    assert len(initial) == LIVE_AUDIO_WINDOW_FRAMES
    assert quality["acceptable"]
    last = int(initial[-1].sequence_number)

    for sequence in range(last + 1, last + 123):
        snapshot = _direction_snapshot(sequence, event_id=17)
        session._record_audio_frame(snapshot.output_frame, (17,), (17,), snapshot)
    fresh, quality = session.audio_channel_frames_after(target_frequency_hz, last)
    assert len(fresh) == 122
    assert int(fresh[0].sequence_number) == last + 1
    assert quality["acceptable"]

    stale_last = int(fresh[-1].sequence_number)
    for sequence in range(stale_last + 1, stale_last + LIVE_AUDIO_WINDOW_FRAMES + 2):
        snapshot = _direction_snapshot(sequence, event_id=17)
        session._record_audio_frame(snapshot.output_frame, (17,), (17,), snapshot)
    missing, quality = session.audio_channel_frames_after(target_frequency_hz, stale_last)
    assert not missing
    assert quality["sequence_gap"]


def test_live_audio_rejects_low_observation_coverage_even_without_long_gap() -> None:
    session = LiveEDSession(
        "hackrf_transfer", LiveEDConfiguration(104_650_000, SERIAL),
        stream_factory=_FakeStream, transport_factory=_FakeTransport,
    )
    payload = bytes(8192)
    for sequence in range(LIVE_AUDIO_WINDOW_FRAMES):
        observed_ids = () if sequence % 10 == 0 else (17,)
        session._record_audio_frame(
            IQFrame(sequence, 2_000_000, 104_650_000, payload), observed_ids, (17,)
        )

    quality = session.audio_window_quality(17)
    assert quality["observed_fraction"] < 0.95
    assert quality["max_consecutive_misses"] == 1
    assert not quality["acceptable"]
    assert session.audio_window(17) == ()
