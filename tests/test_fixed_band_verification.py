from types import SimpleNamespace

import numpy as np

from app.operator_console.fixed_band_verification import (
    FIXED_VERIFY_FRAMES,
    FixedBandCandidate,
    FixedLOObservation,
    FixedBandVerifier,
    _observation_pair_matches,
    fixed_candidate_reference_frequency,
    known_spur_shoulder_evidence,
)
from app.operator_console.live_ed import LiveEDEvent, LiveEDPreview, LiveEDResponse, LiveEDSnapshot
from app.operator_console.integrated_spectrum import IntegratedSpectrumCandidate
from algorithms.p0.transport import IQFrame


SERIAL = "0000000000000000a32868dc35138247"


def _snapshot(config, index, peak_bin, *, half_span_bins=2):
    event = LiveEDEvent(
        17,
        0,
        index,
        index + 1,
        "confirmed",
        True,
        peak_bin - half_span_bins,
        peak_bin + half_span_bins,
        peak_bin,
        5,
        1,
        0,
        100.0,
        1.0,
        10.0,
    )
    frame = IQFrame(
        index,
        2_000_000,
        config.output_center_frequency_hz,
        bytes(8192),
        frame_id=index,
    )
    return LiveEDSnapshot(
        index,
        frame,
        LiveEDResponse(index, 1, 7, 0, False, 0, (event,), (), 136),
    )


class _StableSession:
    configurations = []
    target_frequency_hz = 2_900_000_000.0

    def __init__(self, executable, config):
        assert executable == "hackrf_transfer"
        self.config = config
        self.cancelled = False
        self.configurations.append(config)

    def cancel(self):
        self.cancelled = True

    def run(self, callback):
        assert not self.cancelled
        peak_bin = 2048 + round(
            (self.target_frequency_hz - self.config.output_center_frequency_hz)
            / (2_000_000 / 4096)
        )
        for index in range(self.config.frame_count):
            callback(_snapshot(self.config, index, peak_bin))
        return SimpleNamespace(completed_frames=self.config.frame_count)


def _candidate(frequency=2_900_000_000.0):
    return FixedBandCandidate(
        frequency,
        frequency,
        frequency - 1_500.0,
        frequency + 1_500.0,
        20.0,
        "fpga",
    )


def test_fixed_candidate_must_survive_two_distinct_physical_tunings():
    _StableSession.configurations = []
    _StableSession.target_frequency_hz = 2_900_000_000.0
    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=_StableSession,
    ).run(_candidate())
    assert result.verified
    assert len(result.observations) == 2
    assert all(
        item.observed_frames == FIXED_VERIFY_FRAMES - 16 for item in result.observations
    ), result.observations
    centres = [item.input_center_hz for item in result.observations]
    assert centres == [2_898_200_000, 2_902_800_000]
    assert [
        config.output_center_frequency_hz for config in _StableSession.configurations
    ] == [2_899_700_000, 2_900_300_000]


def test_fixed_output_spur_cannot_pass_two_output_centres():
    class OutputLockedSpurSession(_StableSession):
        def run(self, callback):
            peak_bin = 2048 + round(300_000 / (2_000_000 / 4096))
            for index in range(self.config.frame_count):
                callback(_snapshot(self.config, index, peak_bin))
            return SimpleNamespace(completed_frames=self.config.frame_count)

    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=OutputLockedSpurSession,
    ).run(_candidate())

    assert not result.verified
    assert len(result.observations) == 4
    assert len({item.output_center_hz for item in result.observations}) == 4


def test_candidate_seen_at_only_one_receiver_tuning_is_rejected():
    class MovingSession(_StableSession):
        def run(self, callback):
            expected = 2048 + round(
                (self.target_frequency_hz - self.config.output_center_frequency_hz)
                / (2_000_000 / 4096)
            )
            first_center = self.target_frequency_hz - 1_800_000
            peak = expected if self.config.input_center_frequency_hz == first_center else 2400
            for index in range(self.config.frame_count):
                callback(_snapshot(self.config, index, peak))
            return SimpleNamespace(completed_frames=self.config.frame_count)

    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=MovingSession,
    ).run(_candidate())
    assert not result.verified
    assert result.state == "not_reproduced"
    assert len(result.observations) == 4
    assert sum(item.observed_frames > 0 for item in result.observations) == 1


def test_two_successful_tunings_can_follow_a_rejected_receiver_side():
    class AsymmetricSession(_StableSession):
        def run(self, callback):
            output = self.config.output_center_frequency_hz
            good = self.config.input_center_frequency_hz > output
            expected = 2048 + round(
                (self.target_frequency_hz - output) / (2_000_000 / 4096)
            )
            for index in range(self.config.frame_count):
                callback(_snapshot(self.config, index, expected if good else 2400))
            return SimpleNamespace(completed_frames=self.config.frame_count)

    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=AsymmetricSession,
    ).run(_candidate())
    assert result.verified
    assert len(result.observations) == 3
    assert result.observations[0].observed_frames == 0
    assert all(item.observed_frames > 0 for item in result.observations[1:])


def test_upper_hardware_edge_uses_two_valid_lower_tunings():
    _StableSession.configurations = []
    _StableSession.target_frequency_hz = 6_000_000_000.0
    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=_StableSession,
    ).run(_candidate(6_000_000_000.0))
    assert result.verified
    assert [item.input_center_hz for item in result.observations] == [5_998_200_000, 5_996_900_000]
    assert [item.output_center_hz for item in result.observations] == [5_999_700_000, 5_999_400_000]


def test_receiver_two_lo_fallback_verifies_when_fpga_temporal_events_are_sparse():
    class ReceiverOnlySession:
        def __init__(self, executable, config):
            self.config = config
            self.preview_handler = None

        def set_preview_handler(self, handler):
            self.preview_handler = handler

        def cancel(self):
            pass

        def run(self, callback):
            offset = 2_900_000_000.0 - self.config.input_center_frequency_hz
            phase = 2.0 * np.pi * offset / 8_000_000.0 * np.arange(16_384)
            samples = np.rint(60.0 * np.exp(1j * phase))
            payload = np.column_stack((samples.real, samples.imag)).astype(np.int8).tobytes()
            for index in range(self.config.frame_count):
                display = IQFrame(index, 8_000_000, self.config.input_center_frequency_hz, payload, frame_id=index)
                output = IQFrame(index, 2_000_000, self.config.output_center_frequency_hz, bytes(8192), frame_id=index)
                self.preview_handler(LiveEDPreview(index, output, 0.0, display))
                callback(LiveEDSnapshot(
                    index,
                    output,
                    LiveEDResponse(index, 0, 7, 0, False, 0, (), (), 68),
                ))
            return SimpleNamespace(completed_frames=self.config.frame_count)

    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=ReceiverOnlySession,
    ).run(_candidate())

    assert result.verified
    assert result.verification_method == "receiver"
    assert len(result.observations) == 2
    assert all(item.observed_frames == 0 for item in result.observations)
    assert all(item.receiver_observed_frames >= 48 for item in result.observations)


def test_integrated_receiver_evidence_verifies_below_single_frame_cfar(monkeypatch):
    class IntegratedOnlySession:
        def __init__(self, executable, config):
            self.config = config
            self.preview_handler = None

        def set_preview_handler(self, handler):
            self.preview_handler = handler

        def cancel(self):
            pass

        def run(self, callback):
            payload = bytes(32_768)
            for index in range(self.config.frame_count):
                display = IQFrame(
                    index,
                    8_000_000,
                    self.config.input_center_frequency_hz,
                    payload,
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
            return SimpleNamespace(completed_frames=self.config.frame_count)

    monkeypatch.setattr(
        "app.operator_console.fixed_band_verification.integrated_candidate_near",
        lambda *_args, **_kwargs: IntegratedSpectrumCandidate(
            2_900_000_000.0,
            2_900_000_000.0,
            2_899_999_750.0,
            2_900_000_250.0,
            8.0,
            70,
            80,
            6.3,
            1.0,
        ),
    )
    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        8,
        8,
        session_factory=IntegratedOnlySession,
    ).run(_candidate())

    assert result.verified
    assert result.verification_method == "receiver"
    assert len(result.observations) == 2
    assert all(item.receiver_observed_frames == 70 for item in result.observations)


def test_broad_candidate_uses_support_center_instead_of_single_peak():
    assert fixed_candidate_reference_frequency(100_000_000.0, 101_000_000.0, 100_100_000.0) == 100_500_000.0
    assert fixed_candidate_reference_frequency(100_000_000.0, 100_010_000.0, 100_007_000.0) == 100_007_000.0


def test_unrelated_narrow_lines_inside_broad_support_do_not_verify_broad_emission():
    class NarrowInsideBroadSession(_StableSession):
        def run(self, callback):
            expected = 2048 + round(300_000 / (2_000_000 / 4096))
            for index in range(self.config.frame_count):
                callback(_snapshot(self.config, index, expected))
            return SimpleNamespace(completed_frames=self.config.frame_count)

    frequency = 2_900_000_000.0
    broad = FixedBandCandidate(
        frequency,
        frequency,
        frequency - 500_000.0,
        frequency + 500_000.0,
        12.0,
        "coarse_rx",
    )
    result = FixedBandVerifier(
        "hackrf_transfer",
        SERIAL,
        16,
        16,
        session_factory=NarrowInsideBroadSession,
    ).run(broad)

    assert not result.verified
    assert len(result.observations) == 4
    assert all(item.observed_frames == 0 for item in result.observations)


def test_broad_fragments_must_overlap_across_receiver_tunings():
    frequency = 2_900_000_000.0
    broad = FixedBandCandidate(
        frequency,
        frequency,
        frequency - 600_000.0,
        frequency + 600_000.0,
        12.0,
        "coarse_rx",
    )
    first = FixedLOObservation(
        2_898_000_000,
        2_899_700_000,
        80,
        frequency - 350_000,
        frequency - 350_000,
        frequency - 500_000,
        frequency - 200_000,
        12.0,
    )
    second = FixedLOObservation(
        2_902_000_000,
        2_899_700_000,
        80,
        frequency + 350_000,
        frequency + 350_000,
        frequency + 200_000,
        frequency + 500_000,
        12.0,
    )

    assert not _observation_pair_matches(broad, first, second, receiver=False)


def test_known_spur_requires_repeatable_shoulder_occupancy():
    frequencies = 1_000_000_000.0 + np.arange(-512, 513) * 488.28125
    noise = np.ones(frequencies.size, dtype=np.float64)
    quiet = noise.copy()
    active = noise.copy()
    shoulder = (
        (np.abs(frequencies - 1_000_000_000.0) > 2_000.0)
        & (np.abs(frequencies - 1_000_000_000.0) <= 25_000.0)
    )
    active[np.flatnonzero(shoulder)[:12]] = 3.0

    assert known_spur_shoulder_evidence(frequencies, quiet, 1_000_000_000.0)[0] is False
    passed, bins, peak_db = known_spur_shoulder_evidence(
        frequencies,
        active,
        1_000_000_000.0,
    )
    assert passed
    assert bins == 12
    assert peak_db > 4.7


def test_known_spur_accepts_persistent_narrow_emission_beside_spur():
    frequencies = 1_000_000_000.0 + np.arange(-512, 513) * 488.28125
    rows = np.ones((32, frequencies.size), dtype=np.float64)
    shoulder_indices = np.flatnonzero(
        (frequencies >= 999_986_000.0) & (frequencies <= 999_987_000.0)
    )
    rows[:, shoulder_indices] = 10.0

    passed, bins, peak_db = known_spur_shoulder_evidence(
        frequencies,
        np.mean(rows, axis=0),
        1_000_000_000.0,
        power_rows=rows,
    )

    assert passed
    assert bins == shoulder_indices.size
    assert bins >= 2
    assert peak_db >= 9.9


def test_known_spur_rejects_transient_narrow_peak():
    frequencies = 1_000_000_000.0 + np.arange(-512, 513) * 488.28125
    rows = np.ones((32, frequencies.size), dtype=np.float64)
    shoulder_indices = np.flatnonzero(
        (frequencies >= 999_986_000.0) & (frequencies <= 999_987_000.0)
    )
    rows[:2, shoulder_indices] = 1_000.0

    passed, _, peak_db = known_spur_shoulder_evidence(
        frequencies,
        np.mean(rows, axis=0),
        1_000_000_000.0,
        power_rows=rows,
    )

    assert peak_db >= 10.0
    assert not passed


def test_known_spur_rejects_isolated_narrow_bin_without_spectral_support():
    frequencies = 1_000_000_000.0 + np.arange(-512, 513) * 488.28125
    rows = np.ones((32, frequencies.size), dtype=np.float64)
    isolated = int(np.argmin(np.abs(frequencies - 999_986_500.0)))
    rows[:, isolated] = 10.0

    passed, bins, peak_db = known_spur_shoulder_evidence(
        frequencies,
        np.mean(rows, axis=0),
        1_000_000_000.0,
        power_rows=rows,
    )

    assert bins == 1
    assert peak_db >= 9.9
    assert not passed
