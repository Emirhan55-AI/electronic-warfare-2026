"""Bounded deterministic 2-of-3 confirmation for OS-CFAR candidates."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .models import CandidateRegion


@dataclass(frozen=True)
class TrackedCandidate:
    track_id: int
    candidate: CandidateRegion
    state: str
    seen_count: int
    observed_this_frame: bool


@dataclass
class _Track:
    track_id: int
    candidate: CandidateRegion
    history: deque[bool]
    seen_count: int = 1
    misses: int = 0
    confirmed: bool = False
    observed: bool = True


class TemporalConfirmation:
    MAX_ACTIVE = 64

    def __init__(self, *, association_tolerance_bins: int = 2) -> None:
        self.association_tolerance_bins = association_tolerance_bins
        self._tracks: dict[int, _Track] = {}
        self._next_id = 1
        self._last_frame_id: int | None = None

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1
        self._last_frame_id = None

    def update(self, candidates: tuple[CandidateRegion, ...], *, frame_id: int) -> tuple[TrackedCandidate, ...]:
        if self._last_frame_id is not None and frame_id != self._last_frame_id + 1:
            self.reset()
        pairs: list[tuple[int, int, int, int]] = []
        for track in self._tracks.values():
            for candidate_index, candidate in enumerate(candidates):
                overlap = self._overlap(track.candidate, candidate)
                if overlap > 0:
                    pairs.append((-overlap, abs(track.candidate.peak_bin - candidate.peak_bin), track.track_id, candidate_index))
        pairs.sort()
        matched_tracks: set[int] = set()
        matched_candidates: set[int] = set()
        for _, _, track_id, candidate_index in pairs:
            if track_id in matched_tracks or candidate_index in matched_candidates:
                continue
            track = self._tracks[track_id]
            track.candidate = candidates[candidate_index]
            track.history.append(True)
            track.seen_count += 1
            track.misses = 0
            track.observed = True
            track.confirmed = track.confirmed or sum(track.history) >= 2
            matched_tracks.add(track_id)
            matched_candidates.add(candidate_index)
        for track_id in list(self._tracks):
            if track_id in matched_tracks:
                continue
            track = self._tracks[track_id]
            track.history.append(False)
            track.misses += 1
            track.observed = False
            if track.misses >= 2:
                del self._tracks[track_id]
        unmatched = [item for index, item in enumerate(candidates) if index not in matched_candidates]
        unmatched.sort(key=lambda item: (-item.peak_power, item.peak_bin, item.start_bin))
        for candidate in unmatched[: max(0, self.MAX_ACTIVE - len(self._tracks))]:
            track_id = self._next_id
            self._next_id += 1
            self._tracks[track_id] = _Track(track_id, candidate, deque((True,), maxlen=3))
        self._last_frame_id = frame_id
        return tuple(
            TrackedCandidate(track.track_id, track.candidate, "confirmed" if track.confirmed else "tentative", track.seen_count, track.observed)
            for track in sorted(self._tracks.values(), key=lambda item: item.track_id)
        )

    def _overlap(self, previous: CandidateRegion, current: CandidateRegion) -> int:
        start = max(previous.start_bin - self.association_tolerance_bins, current.start_bin)
        end = min(previous.end_bin + self.association_tolerance_bins, current.end_bin)
        return max(0, end - start + 1)
