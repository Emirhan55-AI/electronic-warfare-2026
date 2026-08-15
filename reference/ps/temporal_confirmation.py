"""PHASE-06J adapter for the authoritative PHASE-03 temporal tracker."""

from __future__ import annotations

import math
from dataclasses import dataclass

from reference.detection.pipeline import DetectionEvent, DetectionPipeline, DetectionRegion
from reference.ps.candidate_transport import CandidatePacket
from reference.rtl.candidate_grouping import CandidateRecord


MAX_ACTIVE_TRACKS = DetectionPipeline.MAX_ACTIVE_TRACKS
MAX_ENDED_HISTORY = DetectionPipeline.MAX_ENDED_HISTORY
ASSOCIATION_TOLERANCE_BINS = 2
CONFIRMATIONS_REQUIRED = 2
CONFIRMATION_WINDOW = 3
EXPIRY_CONSECUTIVE_MISSES = 2


class _UnusedDetector:
    """The adapter invokes only the already-authoritative track update stage."""


@dataclass(frozen=True)
class TemporalEvent:
    event_id: int
    state: str
    first_frame_id: int
    last_seen_frame_id: int
    seen_count: int
    observed_this_frame: bool
    candidate: CandidateRecord

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "state": self.state,
            "first_frame_id": self.first_frame_id,
            "last_seen_frame_id": self.last_seen_frame_id,
            "seen_count": self.seen_count,
            "observed_this_frame": self.observed_this_frame,
            "candidate": {
                "start_shifted_bin": self.candidate.start_shifted_bin,
                "end_shifted_bin": self.candidate.end_shifted_bin,
                "peak_shifted_bin": self.candidate.peak_shifted_bin,
                "coarse_span_bins": self.candidate.coarse_span_bins,
                "peak_power": self.candidate.peak_power,
                "regional_noise": self.candidate.regional_noise,
                "threshold": self.candidate.threshold,
                "pfa_select": self.candidate.pfa_select,
                "evaluate_center": self.candidate.evaluate_center,
            },
        }


@dataclass(frozen=True)
class TemporalFrame:
    frame_id: int
    active_events: tuple[TemporalEvent, ...]
    ended_events: tuple[TemporalEvent, ...]
    dropped_candidates: int
    evicted_history_count: int
    reset_applied: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "active_events": [item.as_dict() for item in self.active_events],
            "ended_events": [item.as_dict() for item in self.ended_events],
            "dropped_candidates": self.dropped_candidates,
            "evicted_history_count": self.evicted_history_count,
            "reset_applied": self.reset_applied,
        }


def _region(candidate: CandidateRecord) -> DetectionRegion:
    power = float(candidate.peak_power)
    noise = float(candidate.regional_noise)
    if power > 0.0 and noise > 0.0:
        peak_to_noise_db = 10.0 * math.log10(power / noise)
    elif power > 0.0:
        peak_to_noise_db = math.inf
    else:
        peak_to_noise_db = 0.0
    return DetectionRegion(
        start_bin=candidate.start_shifted_bin,
        end_bin=candidate.end_shifted_bin,
        start_frequency_hz=0.0,
        end_frequency_hz=0.0,
        peak_bin=candidate.peak_shifted_bin,
        peak_frequency_hz=0.0,
        peak_power=power,
        local_noise_power=noise,
        threshold_power=float(candidate.threshold),
        peak_to_noise_db=peak_to_noise_db,
    )


def _candidate(region: DetectionRegion, source: dict[int, CandidateRecord]) -> CandidateRecord:
    try:
        return source[id(region)]
    except KeyError as exc:
        raise AssertionError("authoritative temporal event cannot be mapped to its candidate") from exc


def _event(event: DetectionEvent, source: dict[int, CandidateRecord]) -> TemporalEvent:
    return TemporalEvent(
        event_id=event.event_id,
        state=event.state,
        first_frame_id=event.first_frame & 0xFFFF_FFFF,
        last_seen_frame_id=event.last_seen_frame & 0xFFFF_FFFF,
        seen_count=event.seen_count,
        observed_this_frame=event.observed_this_frame,
        candidate=_candidate(event.region, source),
    )


class AuthoritativeTemporalOracle:
    """Apply PHASE-03 ``_update_tracks`` to strict PHASE-06I packets.

    PHASE-06I frame IDs are uint32 modulo 2^32. A modulo-successor is
    consecutive, including FFFFFFFF→00000000; every other discontinuity resets
    all temporal state before the current frame is admitted.
    """

    def __init__(self) -> None:
        self._pipeline = DetectionPipeline(_UnusedDetector())  # type: ignore[arg-type]
        self._last_frame_id: int | None = None
        self._regions: dict[int, CandidateRecord] = {}

    def reset(self) -> None:
        self._pipeline.reset()
        self._last_frame_id = None
        self._regions.clear()

    def process(self, packet: CandidatePacket) -> TemporalFrame:
        if packet.status != 0:
            raise ValueError("status-marked PHASE-06I packet is not algorithmic input")
        reset_applied = False
        if self._last_frame_id is not None and packet.frame_id != ((self._last_frame_id + 1) & 0xFFFF_FFFF):
            self.reset()
            reset_applied = True
        regions = tuple(_region(item) for item in packet.candidates)
        self._regions.update({id(region): candidate for region, candidate in zip(regions, packet.candidates, strict=True)})
        ended, dropped = self._pipeline._update_tracks(regions, packet.frame_id, 1.0, 4096)
        self._last_frame_id = packet.frame_id
        retained = {id(track.region) for track in self._pipeline._tracks.values()}
        retained.update(id(item.region) for item in self._pipeline._ended)
        self._regions = {key: value for key, value in self._regions.items() if key in retained}
        source = self._regions
        active = tuple(
            _event(
                self._pipeline._event_from_track(track, packet.frame_id, 1.0, 4096),
                source,
            )
            for track in sorted(self._pipeline._tracks.values(), key=lambda item: item.event_id)
        )
        return TemporalFrame(
            frame_id=packet.frame_id,
            active_events=active,
            ended_events=tuple(_event(item, source) for item in ended),
            dropped_candidates=dropped,
            evicted_history_count=self._pipeline._evicted_history_count,
            reset_applied=reset_applied,
        )
