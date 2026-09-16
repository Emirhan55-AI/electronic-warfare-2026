from dataclasses import dataclass, replace
import json

import pytest

from algorithms.p0.channelizer import P0ChannelizerProfile
from algorithms.p0.transport import IQFrame
from app.operator_console.live_ed import (
    LiveEDConfiguration,
    LiveEDEvent,
    LiveEDPreview,
    LiveEDResponse,
    LiveEDSnapshot,
)
from app.operator_console.integrated_spectrum import IntegratedSpectrumCandidate
from app.operator_console.rx_survey import (
    RXSurvey,
    SURVEY_CHANNELIZER_PASSBAND_HALF_HZ,
    SURVEY_MAX_FULL_SUPPORT_HZ,
    SURVEY_WIDEBAND_PASSBAND_HALF_HZ,
    SURVEY_WIDEBAND_RESPONSIBILITY_WIDTH_HZ,
    SURVEY_WIDEBAND_TUNING_OFFSET_HZ,
    SurveyConfig,
    _event_frequency_geometry,
    survey_gain_profiles,
)
from platforms.acquisition.contracts import AcquisitionError


SERIAL = "0" * 32


@dataclass
class _Result:
    completed_frames: int


class _Session:
    def __init__(self, executable, config):
        self.config = config
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self, callback):
        for index in range(self.config.frame_count):
            if self.cancelled:
                raise AcquisitionError("operation_cancelled", "test")
            event = LiveEDEvent(17, 0, index, index + 1, "confirmed", True,
                               2046, 2050, 2048, 5, 1, 0, 100., 1., 10.)
            frame = IQFrame(index, 2_000_000, self.config.output_center_frequency_hz, bytes(8192), frame_id=index)
            callback(LiveEDSnapshot(index, frame, LiveEDResponse(index, 1, 7, 0, False, 0, (event,), (), 136)))
        return _Result(self.config.frame_count)


def _records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_full_device_plan_has_no_gaps_and_uses_passband_not_filter_edges():
    windows = SurveyConfig().windows()
    profile = P0ChannelizerProfile()
    assert len(windows) == 9999
    assert windows[0].lower_hz == 1_000_000
    assert windows[-1].upper_hz == 6_000_000_000
    assert windows[-1].include_upper
    assert all(not item.include_upper for item in windows[:-1])
    for previous, current in zip(windows, windows[1:]):
        assert previous.upper_hz == current.lower_hz
    for item in windows:
        assert item.center_hz - item.lower_hz <= profile.passband_edge_hz
        assert item.upper_hz - item.center_hz <= profile.passband_edge_hz
        config = LiveEDConfiguration(item.center_hz, SERIAL)
        assert 1_000_000 <= config.input_center_frequency_hz <= 6_000_000_000
        assert abs(config.output_center_frequency_hz - config.input_center_frequency_hz) == 1_500_000
        assert not config.rx_config.rf_amplifier


def test_overlapping_tunings_keep_one_mhz_support_inside_validated_passband():
    windows = SurveyConfig(2_400_000_000, 2_500_000_000).windows()
    half_support = SURVEY_MAX_FULL_SUPPORT_HZ / 2
    for item in windows:
        for frequency_hz in (item.lower_hz, (item.lower_hz + item.upper_hz) / 2, item.upper_hz):
            assert abs(frequency_hz - item.center_hz) + half_support <= SURVEY_CHANNELIZER_PASSBAND_HALF_HZ

            first_bin = 2048 + (frequency_hz - half_support - item.center_hz) * 4096 / 2_000_000
            final_bin = 2048 + (frequency_hz + half_support - item.center_hz) * 4096 / 2_000_000
            assert first_bin >= 256
            assert final_bin < 3840


def test_wideband_burst_plan_owns_gap_free_dc_and_edge_safe_intervals():
    windows = SurveyConfig(
        800_000_000,
        840_000_000,
        mode="wideband_burst",
    ).windows()

    assert len(windows) == 16
    assert windows[0].lower_hz == 800_000_000
    assert windows[-1].upper_hz == 840_000_000
    assert all(not item.include_upper for item in windows[:-1])
    assert windows[-1].include_upper
    half_support = SURVEY_MAX_FULL_SUPPORT_HZ / 2
    for previous, current in zip(windows, windows[1:]):
        assert previous.upper_hz == current.lower_hz
    for item in windows:
        relative_lower = item.lower_hz - item.center_hz
        relative_upper = item.upper_hz - item.center_hz
        assert (
            SURVEY_WIDEBAND_TUNING_OFFSET_HZ <= relative_lower <= relative_upper
            or relative_lower <= relative_upper <= -SURVEY_WIDEBAND_TUNING_OFFSET_HZ
        )
        assert max(abs(relative_lower), abs(relative_upper)) + half_support <= (
            SURVEY_WIDEBAND_PASSBAND_HALF_HZ
        )
        assert item.upper_hz - item.lower_hz <= SURVEY_WIDEBAND_RESPONSIBILITY_WIDTH_HZ


def test_wideband_event_geometry_uses_10msps_bin_spacing():
    event = LiveEDEvent(
        17, 0, 2, 3, "confirmed", True,
        2458, 2458, 2458, 1, 1, 0, 100.0, 1.0, 10.0,
    )
    lower, upper, center, peak = _event_frequency_geometry(
        820_000_000,
        event,
        sample_rate_hz=10_000_000,
        fft_size=4096,
    )
    assert peak == pytest.approx(821_000_976.5625)
    assert center == pytest.approx(peak)
    assert upper - lower == pytest.approx(10_000_000 / 4096)


@pytest.mark.parametrize("amplifier", [False, True])
def test_wideband_survey_uses_bounded_direct_fpga_sessions(tmp_path, amplifier):
    seen = []

    class WidebandSession:
        def __init__(self, executable, config):
            del executable
            self.config = config
            seen.append(config)

        def cancel(self):
            pass

        def run(self, callback):
            for index in range(self.config.frame_count):
                frame = IQFrame(
                    index,
                    10_000_000,
                    self.config.output_center_frequency_hz,
                    bytes(8192),
                    frame_id=index,
                )
                callback(LiveEDSnapshot(
                    index,
                    frame,
                    LiveEDResponse(index, 0, 7, 0, False, 0, (), (), 68),
                ))
            return _Result(self.config.frame_count)

    path = tmp_path / "wideband.jsonl"
    result = RXSurvey(
        "hackrf_transfer",
        SERIAL,
        SurveyConfig(
            800_000_000,
            805_000_000,
            frames_per_window=16,
            guard_frames=8,
            mode="wideband_burst",
            rf_amplifier=amplifier,
        ),
        path,
        session_factory=WidebandSession,
    ).run()

    assert result.state == "completed"
    assert result.completed_windows == 2
    assert all(config.direct_fpga_input for config in seen)
    assert all(config.rx_config.rf_amplifier is amplifier for config in seen)
    assert all(not config.automatic_parameters_enabled for config in seen)
    assert all(config.frame_count == 16 for config in seen)
    completed = [row for row in _records(path) if row["type"] == "window_complete"]
    assert [row["window_metrics"]["sample_rate_hz"] for row in completed] == [
        10_000_000,
        10_000_000,
    ]
    assert all(
        row["timing"]["sample_observation_seconds"] == pytest.approx(0.0065536)
        for row in completed
    )

    with pytest.raises(ValueError, match="en fazla 256"):
        SurveyConfig(
            800_000_000,
            805_000_000,
            frames_per_window=257,
            guard_frames=8,
            mode="wideband_burst",
        )


@pytest.mark.parametrize("center,expected", [(1_000_000, 2_500_000), (1_700_000, 3_200_000),
                                            (104_650_000, 103_150_000), (6_000_000_000, 5_998_500_000)])
def test_live_tuning_stays_inside_device_limits_at_both_edges(center, expected):
    assert LiveEDConfiguration(center, SERIAL).input_center_frequency_hz == expected


def test_live_tuning_accepts_only_validated_opposite_side_override():
    config = LiveEDConfiguration(
        104_650_000,
        SERIAL,
        input_center_frequency_hz_override=107_150_000,
    )
    assert config.input_center_frequency_hz == 107_150_000
    with pytest.raises(AcquisitionError) as error:
        LiveEDConfiguration(
            104_650_000,
            SERIAL,
            input_center_frequency_hz_override=105_650_000,
        )
    assert error.value.code == "invalid_tuning_offset"


@pytest.mark.parametrize("bounds", [(0, 6_000_000_000), (1_000_000, 6_000_000_001),
                                     (2_000_000, 1_000_000), (1_000_000., 3_000_000)])
def test_invalid_search_envelopes_are_rejected(bounds):
    with pytest.raises(ValueError):
        SurveyConfig(*bounds)


def test_survey_gain_profiles_reach_zero_without_invalid_steps():
    assert survey_gain_profiles(32, 32) == ((32, 32), (24, 24), (16, 16), (8, 8), (0, 0))
    assert survey_gain_profiles(24, 18) == ((24, 18), (16, 10), (8, 2), (0, 0))


def test_survey_commits_only_complete_windows_and_ignores_guard_frames(tmp_path):
    path = tmp_path / "scan.jsonl"
    updates = []
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 2_200_000), path,
                      session_factory=_Session).run(updates.append)
    assert result.state == "completed"
    assert result.completed_windows == result.total_windows == 2
    previews = [item for item in updates if item.state == "preview"]
    assert previews and all(not item.observations for item in previews)
    assert updates.index(previews[0]) < next(i for i, item in enumerate(updates) if item.state == "complete")
    completed = [item for item in updates if item.state == "complete"]
    assert len(completed) == 2
    assert len(completed[0].display_snapshots) == 8
    assert [snapshot.sequence_number for snapshot in completed[0].display_snapshots] == list(range(15, 128, 16))
    assert all(snapshot.output_frame.center_frequency_hz == completed[0].window.center_hz
               for snapshot in completed[0].display_snapshots)
    first = completed[0].observations[0]
    assert first["first_frame"] == 8
    assert first["last_frame"] == 127
    assert first["observed_frames"] == 120
    assert first["frequency_hz"] == 1_300_000
    assert first["verification"]["observed_frames"] == 40
    assert first["verification"]["input_center_hz"] == 3_800_000
    assert len(first["iq_sha256"]) == 64
    assert first["key"] != completed[1].observations[0]["key"]
    assert _records(path)[0]["transmit_enabled"] is False
    completed_record = next(row for row in _records(path) if row["type"] == "window_complete")
    assert completed_record["window_metrics"] == {
        "channel_power_dbfs": None,
        "power_frame_count": 120,
        "power_component_count": 120 * 8192,
        "lna_gain_db": 32,
        "vga_gain_db": 32,
        "input_center_hz": 2_800_000,
        "output_center_hz": 1_300_000,
        "sample_rate_hz": 2_000_000,
        "power_reference": "mean_abs_iq_squared_ci8_div128",
    }
    assert _records(path)[-1]["state"] == "completed"
    with pytest.raises(FileExistsError):
        RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(), path, session_factory=_Session).run()


def test_known_spur_cannot_be_verified_by_fpga_line_without_receiver_shoulders(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "app.operator_console.rx_survey.load_known_spurs",
        lambda serial: (1_300_000,),
    )
    path = tmp_path / "known-spur.jsonl"
    result = RXSurvey(
        "hackrf_transfer",
        SERIAL,
        SurveyConfig(1_000_000, 1_600_000),
        path,
        session_factory=_Session,
    ).run()

    assert result.state == "completed"
    completed = next(row for row in _records(path) if row["type"] == "window_complete")
    assert completed["observations"] == []
    assert completed["screened_observations"]


def test_blind_integrated_rx_candidate_survives_independent_retune(tmp_path, monkeypatch):
    target_hz = 1_300_000.0
    candidate = IntegratedSpectrumCandidate(
        target_hz,
        target_hz,
        target_hz - 250.0,
        target_hz + 250.0,
        8.0,
        96,
        120,
        6.3,
        1.0,
    )

    monkeypatch.setattr(
        "app.operator_console.rx_survey.integrated_spectrum_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        "app.operator_console.rx_survey.integrated_candidate_near",
        lambda *_args, **_kwargs: replace(candidate, observed_frames=34, total_frames=40),
    )

    class IntegratedSession:
        def __init__(self, executable, config):
            self.config = config
            self.preview_handler = None

        def set_preview_handler(self, handler):
            self.preview_handler = handler

        def cancel(self):
            pass

        def run(self, callback):
            for index in range(self.config.frame_count):
                display = IQFrame(
                    index,
                    8_000_000,
                    self.config.input_center_frequency_hz,
                    bytes(32_768),
                    frame_id=index,
                )
                output = IQFrame(
                    index,
                    2_000_000,
                    self.config.output_center_frequency_hz,
                    bytes(8192),
                    frame_id=index,
                )
                self.preview_handler(LiveEDPreview(index, output, 0.0, display))
                callback(LiveEDSnapshot(
                    index,
                    output,
                    LiveEDResponse(index, 0, 7, 0, False, 0, (), (), 68),
                ))
            return _Result(self.config.frame_count)

    updates = []
    result = RXSurvey(
        "hackrf_transfer",
        SERIAL,
        SurveyConfig(1_000_000, 1_600_000),
        tmp_path / "integrated.jsonl",
        session_factory=IntegratedSession,
    ).run(updates.append)

    assert result.state == "completed"
    observation = next(item for item in updates if item.state == "complete").observations[0]
    assert observation["source"] == "integrated_rx"
    assert observation["peak_frequency_hz"] == target_hz
    assert observation["observed_frames"] == 96
    assert observation["verification"]["method"] == "integrated_rx"
    assert observation["verification"]["observed_frames"] == 34


def test_channel_power_uses_complex_iq_normalization_and_excludes_guard_frames(tmp_path):
    import math

    class PowerSession(_Session):
        def run(self, callback):
            def with_power(snapshot):
                sample = bytes([127, 127]) if snapshot.sequence_number < 8 else bytes([64, 32])
                frame = replace(snapshot.output_frame, payload=sample * 4096)
                callback(replace(snapshot, output_frame=frame))
            return super().run(with_power)

    path = tmp_path / "channel-power.jsonl"
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000), path,
                      session_factory=PowerSession).run()
    assert result.state == "completed"
    record = next(row for row in _records(path) if row["type"] == "window_complete")
    assert record["window_metrics"]["channel_power_dbfs"] == pytest.approx(10 * math.log10(.5**2 + .25**2))
    assert record["observations"][0]["mean_peak_power"] == 100.0
    assert record["observations"][0]["verification"]["mean_peak_power"] == 100.0


def test_preview_is_published_before_session_returns_or_coverage_is_committed(tmp_path):
    updates = []
    class PreviewSession(_Session):
        def run(self, callback):
            result = super().run(callback)
            if self.config.input_center_frequency_hz_override is None:
                assert any(item.state == "preview" for item in updates)
                assert not any(item.state == "complete" for item in updates)
            return result
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000),
        tmp_path / "preview-first.jsonl", session_factory=PreviewSession).run(updates.append)
    assert result.state == "completed"


def test_survey_mailbox_coalesces_only_previews_and_preserves_control_order():
    from app.operator_console.rx_survey import SurveyUpdate
    from app.operator_console.survey_controller import _SurveyMailbox
    mailbox = _SurveyMailbox()
    window = SurveyConfig(1_000_000, 1_600_000).windows()[0]
    assert mailbox.publish(SurveyUpdate(window, "running", 0), lambda: False)
    for index in range(1000):
        assert not mailbox.publish(SurveyUpdate(window, "preview", index), lambda: False)
    assert len(mailbox.items) == 2
    mailbox.publish(SurveyUpdate(window, "failed", 1001), lambda: False)
    items = mailbox.take()
    assert [item.state for item in items] == ["running", "preview", "failed"]
    assert items[1].elapsed_seconds == 999
    for index in range(64):
        mailbox.publish(SurveyUpdate(window, "running", index), lambda: False)
    assert not mailbox.publish(SurveyUpdate(window, "complete", 65), lambda: True)
    assert len(mailbox.items) == 64


def test_survey_clusters_nearby_event_ids_once_per_frame(tmp_path):
    class Fragmented(_Session):
        def run(self, callback):
            for index in range(self.config.frame_count):
                events = (
                    LiveEDEvent(100 + index, 0, index, 2, "confirmed", True,
                                2026, 2030, 2028, 5, 1, 0, 100., 1., 10.),
                    LiveEDEvent(300 + index, 0, index, 2, "confirmed", True,
                                2066, 2070, 2068, 5, 1, 0, 80., 1., 10.),
                )
                frame = IQFrame(index, 2_000_000, self.config.output_center_frequency_hz,
                                bytes(8192), frame_id=index)
                callback(LiveEDSnapshot(index, frame,
                    LiveEDResponse(index, 2, 7, 0, False, 0, events, (), 136)))
            return _Result(self.config.frame_count)

    updates = []
    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000),
        tmp_path / "clustered.jsonl", session_factory=Fragmented,
    ).run(updates.append)
    assert result.state == "completed"
    completed = next(item for item in updates if item.state == "complete")
    assert len(completed.observations) == 1
    assert completed.observations[0]["observed_frames"] == 120


def test_survey_rejects_candidate_that_moves_after_independent_retune(tmp_path):
    class MovingSpur(_Session):
        def run(self, callback):
            peak = 2048 if self.config.input_center_frequency_hz_override is None else 2300
            for index in range(self.config.frame_count):
                event = LiveEDEvent(17, 0, index, index + 1, "confirmed", True,
                                    peak - 2, peak + 2, peak, 5, 1, 0, 100., 1., 10.)
                frame = IQFrame(index, 2_000_000, self.config.output_center_frequency_hz,
                                bytes(8192), frame_id=index)
                callback(LiveEDSnapshot(index, frame,
                    LiveEDResponse(index, 1, 7, 0, False, 0, (event,), (), 136)))
            return _Result(self.config.frame_count)

    updates = []
    RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000),
        tmp_path / "moving-spur.jsonl", session_factory=MovingSpur,
    ).run(updates.append)
    completed = next(item for item in updates if item.state == "complete")
    assert completed.observations == ()


@pytest.mark.parametrize("amplifier", [False, True])
def test_independent_retune_uses_detection_only_session(tmp_path, amplifier):
    class DetectionOnlyVerification(_Session):
        def run(self, callback):
            assert self.config.rx_config.rf_amplifier is amplifier
            if self.config.input_center_frequency_hz_override is not None:
                assert self.config.display_interval_frames == 1
                assert self.config.automatic_parameters_enabled is False
            return super().run(callback)

    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000, rf_amplifier=amplifier),
        tmp_path / "detection-only-verification.jsonl",
        session_factory=DetectionOnlyVerification,
    ).run()
    assert result.state == "completed"


def test_narrow_primary_is_not_verified_by_distant_peak_in_broad_support():
    from app.operator_console.rx_survey import _verification_matches
    observation = {"lower_frequency_hz": 825_999_000,
                   "upper_frequency_hz": 826_001_000,
                   "frequency_hz": 826_000_000, "peak_frequency_hz": 826_000_000}
    assert not _verification_matches(
        observation, 825_800_000, 826_400_000, 826_100_000, 826_300_000)
    assert _verification_matches(
        observation, 825_800_000, 826_400_000, 826_100_000, 826_000_400)


def test_broad_primary_cannot_be_verified_by_tiny_embedded_line():
    from app.operator_console.rx_survey import _verification_matches
    observation = dict(lower_frequency_hz=1499.5e6, upper_frequency_hz=1500.5e6,
                       frequency_hz=1500e6, peak_frequency_hz=1500e6)
    assert not _verification_matches(observation, 1500e6-500, 1500e6+500, 1500e6, 1500e6)
    assert _verification_matches(observation, 1499.6e6, 1500.4e6, 1500e6, 1500e6+40000)


def test_separated_groups_matching_one_old_span_count_each_frame_once(tmp_path):
    class SplitAfterBroad(_Session):
        def run(self, callback):
            def split(snapshot):
                event = snapshot.response.active[0]
                # Most frames establish a broad historical support; the final
                # frame splits into distant groups still inside that support.
                spans = [(1800, 2296)] if snapshot.sequence_number < self.config.frame_count - 1 else [(1800,1804),(2292,2296)]
                events = tuple(replace(event, event_id=i, start_shifted_bin=a,
                                      end_shifted_bin=b, peak_shifted_bin=(a+b)//2,
                                      coarse_span_bins=b-a+1) for i,(a,b) in enumerate(spans))
                callback(replace(snapshot, response=replace(snapshot.response, active=events)))
            return super().run(split)
    path = tmp_path / 'unique-frames.jsonl'
    RXSurvey('hackrf_transfer', SERIAL, SurveyConfig(1_000_000, 1_600_000),
             path, session_factory=SplitAfterBroad).run()
    record = next(r for r in _records(path) if r['type']=='window_complete')
    item = record['observations'][0]
    assert item['observed_frames'] == 120
    assert item['group_observations'] == 121


def test_broad_observation_is_verified_by_absolute_support_when_peak_moves(tmp_path):
    signal_center_hz = 100_001_000
    support_bins = 2048

    class BroadNoiseLike(_Session):
        def run(self, callback):
            spacing = 2_000_000 / 4096
            center_bin = round(2048 + (signal_center_hz - self.config.output_center_frequency_hz) / spacing)
            start = center_bin - support_bins // 2
            end = start + support_bins - 1
            assert 256 <= start <= end < 3840
            peak = start + 100 if self.config.input_center_frequency_hz_override is None else end - 100
            for index in range(self.config.frame_count):
                event = LiveEDEvent(
                    17, 0, index, index + 1, "confirmed", True,
                    start, end, peak, support_bins, 1, 0, 100., 1., 10.,
                )
                frame = IQFrame(
                    index, 2_000_000, self.config.output_center_frequency_hz,
                    bytes(8192), frame_id=index,
                )
                callback(LiveEDSnapshot(
                    index, frame, LiveEDResponse(index, 1, 7, 0, False, 0, (event,), (), 136)
                ))
            return _Result(self.config.frame_count)

    updates = []
    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(100_000_000, 100_600_000),
        tmp_path / "broad-support.jsonl", session_factory=BroadNoiseLike,
    ).run(updates.append)
    assert result.state == "completed"
    observation = next(item for item in updates if item.state == "complete").observations[0]
    assert observation["bandwidth_hz"] == pytest.approx(1_000_000)
    assert observation["verification"]["observed_frames"] == 40
    assert observation["verification"]["bandwidth_hz"] == pytest.approx(1_000_000)
    assert abs(observation["verification"]["frequency_hz"] - observation["frequency_hz"]) < 1_000
    assert abs(observation["verification"]["peak_frequency_hz"] - observation["peak_frequency_hz"]) > 800_000


def test_clipped_window_is_failed_not_empty_or_covered(tmp_path):
    class Clipped(_Session):
        def run(self, callback):
            super().run(callback)
            raise AcquisitionError("iq_saturation", "clipped after observations")
    updates = []
    path = tmp_path / "clipped.jsonl"
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 2_200_000), path,
                      session_factory=Clipped).run(updates.append)
    assert result.state == "partial"
    assert result.completed_windows == 0
    assert result.failed_windows == 2
    assert not any(item.observations for item in updates)
    assert not any(row["type"] == "window_complete" for row in _records(path))


def test_saturated_window_is_retried_at_lower_gain_before_coverage_is_committed(tmp_path):
    class GainSensitive(_Session):
        def run(self, callback):
            if self.config.lna_gain_db > 16 or self.config.vga_gain_db > 16:
                raise AcquisitionError("iq_saturation", "test overload")
            return super().run(callback)

    updates = []
    path = tmp_path / "gain-fallback.jsonl"
    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000), path,
        session_factory=GainSensitive,
    ).run(updates.append)
    assert result.state == "completed"
    assert result.completed_windows == 1
    records = _records(path)
    retries = [row for row in records if row["type"] == "window_gain_retry"]
    assert [(row["lna_gain_db"], row["vga_gain_db"]) for row in retries] == [(32, 32), (24, 24)]
    completed = next(row for row in records if row["type"] == "window_complete")
    assert completed["gain"] == {"lna_gain_db": 16, "vga_gain_db": 16}
    assert completed["observations"][0]["lna_gain_db"] == 16
    assert completed["observations"][0]["verification"]["lna_gain_db"] == 16


def test_candidate_capacity_drop_fails_without_hiding_signals_by_lowering_gain(tmp_path):
    class CandidateLimited(_Session):
        def run(self, callback):
            if self.config.lna_gain_db > 24:
                raise AcquisitionError("candidate_drop", "test candidate capacity")
            return super().run(callback)

    path = tmp_path / "candidate-fallback.jsonl"
    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000), path,
        session_factory=CandidateLimited,
    ).run()
    assert result.state == "failed"
    assert result.error_code == "candidate_drop"
    assert result.completed_windows == 0
    assert not any(row["type"] in {"window_gain_retry", "window_complete"} for row in _records(path))


@pytest.mark.parametrize("error_code", ["usb_overrun", "short_stream"])
def test_transient_transport_fault_retries_same_window_without_creating_a_coverage_gap(
    tmp_path,
    error_code,
):
    class TransientOverrun(_Session):
        attempts = {}

        def run(self, callback):
            key = (self.config.output_center_frequency_hz,
                   self.config.input_center_frequency_hz_override)
            self.attempts[key] = self.attempts.get(key, 0) + 1
            if self.attempts[key] == 1:
                raise AcquisitionError(error_code, "test transient")
            return super().run(callback)

    path = tmp_path / "transport-retry.jsonl"
    result = RXSurvey(
        "hackrf_transfer", SERIAL, SurveyConfig(1_000_000, 1_600_000), path,
        session_factory=TransientOverrun,
    ).run()
    assert result.state == "completed"
    assert result.completed_windows == 1
    records = _records(path)
    retries = [row for row in records if row["type"] == "window_transport_retry"]
    assert len(retries) == 1
    assert retries[0]["error_code"] == error_code
    completed = next(row for row in records if row["type"] == "window_complete")
    assert completed["observations"][0]["verification"]["retries"][0]["error_code"] == error_code


def test_transport_fault_stops_scan_without_pretending_remaining_band_is_empty(tmp_path):
    class Disconnected(_Session):
        def run(self, callback):
            raise AcquisitionError("connection_failed", "no card")
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(), tmp_path / "failed.jsonl",
                      session_factory=Disconnected).run()
    assert result.state == "failed"
    assert result.completed_windows == 0
    assert result.failed_windows == 1
    assert result.total_windows == 9999


def test_operator_stop_preserves_completed_window_and_does_not_visit_next(tmp_path):
    survey = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(), tmp_path / "cancel.jsonl", session_factory=_Session)
    def update(item):
        if item.state == "complete":
            survey.cancel()
    result = survey.run(update)
    assert result.state == "cancelled"
    assert result.completed_windows == 1
    assert result.failed_windows == 0


def test_sequence_or_tuning_mismatch_does_not_commit_a_window(tmp_path):
    class WrongFrequency(_Session):
        def run(self, callback):
            return super().run(lambda snap: callback(replace(snap,
                output_frame=replace(snap.output_frame, center_frequency_hz=100_000_000))))
    result = RXSurvey("hackrf_transfer", SERIAL, SurveyConfig(), tmp_path / "wrong.jsonl", session_factory=WrongFrequency).run()
    assert result.state == "failed"
    assert result.error_code == "survey_frequency"
    assert result.completed_windows == 0
