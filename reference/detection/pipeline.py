"""Grouping and bounded temporal confirmation for PHASE-03 detections."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from reference.spectrum import SpectrumResult

from .cfar import CellDetectionResult, LinearPowerDetector


EventState = Literal["tentative", "confirmed", "ended"]


@dataclass(frozen=True)
class DetectionRegion:
    """A coarse grouped candidate; it is not a precise bandwidth estimate."""

    start_bin: int
    end_bin: int
    start_frequency_hz: float
    end_frequency_hz: float
    peak_bin: int
    peak_frequency_hz: float
    peak_power: float
    local_noise_power: float
    threshold_power: float
    peak_to_noise_db: float


@dataclass(frozen=True)
class DetectionEvent:
    """One bounded temporal track snapshot."""

    event_id: int
    state: EventState
    region: DetectionRegion
    first_frame: int
    last_seen_frame: int
    seen_count: int
    first_sample: int
    last_seen_sample: int
    first_time_seconds: float
    last_seen_time_seconds: float
    observed_this_frame: bool


@dataclass(frozen=True)
class DetectionFrameResult:
    """Complete explainable output for one frame."""

    frame_index: int
    cells: CellDetectionResult
    regions: tuple[DetectionRegion, ...]
    active_events: tuple[DetectionEvent, ...]
    ended_events: tuple[DetectionEvent, ...]
    ended_history: tuple[DetectionEvent, ...]
    dropped_candidates: int
    evicted_history_count: int


@dataclass
class _Track:
    event_id: int
    region: DetectionRegion
    first_frame: int
    last_seen_frame: int
    seen_count: int
    history: deque[bool]
    consecutive_misses: int = 0
    confirmed: bool = False
    observed_this_frame: bool = True


class DetectionPipeline:
    """Run cell detection, grouping, and bounded 2-of-3 temporal confirmation."""

    MAX_ACTIVE_TRACKS = 64
    MAX_ENDED_HISTORY = 128
    MAX_VISIBLE_EVENTS = 12

    def __init__(
        self,
        detector: LinearPowerDetector,
        *,
        max_gap_bins: int = 1,
        association_tolerance_bins: int = 2,
        confirmations_required: int = 2,
        confirmation_window: int = 3,
    ) -> None:
        if (max_gap_bins, association_tolerance_bins, confirmations_required, confirmation_window) != (1, 2, 2, 3):
            raise ValueError("PHASE-03 uses gap=1, tolerance=2, and 2-of-3 confirmation")
        self.detector = detector
        self.max_gap_bins = max_gap_bins
        self.association_tolerance_bins = association_tolerance_bins
        self.confirmations_required = confirmations_required
        self.confirmation_window = confirmation_window
        self._tracks: dict[int, _Track] = {}
        self._ended: deque[DetectionEvent] = deque(maxlen=self.MAX_ENDED_HISTORY)
        self._next_event_id = 1
        self._last_frame_index: int | None = None
        self._evicted_history_count = 0

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)

    @property
    def ended_history_count(self) -> int:
        return len(self._ended)

    def reset(self) -> None:
        self._tracks.clear()
        self._ended.clear()
        self._next_event_id = 1
        self._last_frame_index = None
        self._evicted_history_count = 0

    def process(self, spectrum: SpectrumResult, *, frame_index: int) -> DetectionFrameResult:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if self._last_frame_index is not None and frame_index != self._last_frame_index + 1:
            self.reset()

        cells = self.detector.detect(spectrum.display.bin_power_fs2)
        regions = self._group(cells, spectrum)
        ended_now, dropped = self._update_tracks(regions, frame_index, spectrum.sample_rate_hz, spectrum.frame_length)
        self._last_frame_index = frame_index
        active = tuple(
            self._event_from_track(track, frame_index, spectrum.sample_rate_hz, spectrum.frame_length)
            for track in sorted(self._tracks.values(), key=lambda item: item.event_id)
        )
        return DetectionFrameResult(
            frame_index=frame_index,
            cells=cells,
            regions=regions,
            active_events=active,
            ended_events=tuple(ended_now),
            ended_history=tuple(self._ended),
            dropped_candidates=dropped,
            evicted_history_count=self._evicted_history_count,
        )

    def _group(self, cells: CellDetectionResult, spectrum: SpectrumResult) -> tuple[DetectionRegion, ...]:
        indices = np.flatnonzero(cells.detected_mask)
        if indices.size == 0:
            return ()
        groups: list[list[int]] = [[int(indices[0])]]
        for raw_index in indices[1:]:
            index = int(raw_index)
            if index - groups[-1][-1] <= self.max_gap_bins + 1:
                groups[-1].append(index)
            else:
                groups.append([index])

        power = spectrum.display.bin_power_fs2
        frequencies = spectrum.display.frequency_absolute_hz
        regions: list[DetectionRegion] = []
        for group in groups:
            group_array = np.asarray(group, dtype=np.int64)
            peak = int(group_array[int(np.argmax(power[group_array]))])
            noise = float(cells.noise_power[peak])
            peak_power = float(power[peak])
            if noise > 0.0 and peak_power > 0.0:
                delta = 10.0 * math.log10(peak_power / noise)
            elif peak_power > 0.0:
                delta = math.inf
            else:
                delta = 0.0
            regions.append(
                DetectionRegion(
                    start_bin=group[0],
                    end_bin=group[-1],
                    start_frequency_hz=float(frequencies[group[0]]),
                    end_frequency_hz=float(frequencies[group[-1]]),
                    peak_bin=peak,
                    peak_frequency_hz=float(frequencies[peak]),
                    peak_power=peak_power,
                    local_noise_power=noise,
                    threshold_power=float(cells.threshold_power[peak]),
                    peak_to_noise_db=delta,
                )
            )
        return tuple(regions)

    def _update_tracks(
        self,
        regions: tuple[DetectionRegion, ...],
        frame_index: int,
        sample_rate_hz: float,
        frame_length: int,
    ) -> tuple[list[DetectionEvent], int]:
        pairs: list[tuple[int, int, int, int, int]] = []
        for track in self._tracks.values():
            for region_index, region in enumerate(regions):
                overlap = self._association_overlap(track.region, region)
                if overlap > 0:
                    pairs.append(
                        (
                            -overlap,
                            abs(track.region.peak_bin - region.peak_bin),
                            track.event_id,
                            region.start_bin,
                            region_index,
                        )
                    )
        pairs.sort()
        matched_tracks: set[int] = set()
        matched_regions: set[int] = set()
        for _, _, event_id, _, region_index in pairs:
            if event_id in matched_tracks or region_index in matched_regions:
                continue
            matched_tracks.add(event_id)
            matched_regions.add(region_index)
            track = self._tracks[event_id]
            track.region = regions[region_index]
            track.last_seen_frame = frame_index
            track.seen_count += 1
            track.consecutive_misses = 0
            track.observed_this_frame = True
            track.history.append(True)
            if sum(track.history) >= self.confirmations_required:
                track.confirmed = True

        ended_now: list[DetectionEvent] = []
        for event_id in sorted(set(self._tracks) - matched_tracks):
            track = self._tracks[event_id]
            track.observed_this_frame = False
            track.consecutive_misses += 1
            track.history.append(False)
            if track.consecutive_misses >= 2:
                event = replace(
                    self._event_from_track(track, frame_index, sample_rate_hz, frame_length),
                    state="ended",
                    observed_this_frame=False,
                )
                ended_now.append(event)
                if len(self._ended) == self.MAX_ENDED_HISTORY:
                    self._evicted_history_count += 1
                self._ended.append(event)
                del self._tracks[event_id]

        unmatched = [regions[index] for index in range(len(regions)) if index not in matched_regions]
        unmatched.sort(key=lambda item: (-item.peak_to_noise_db, item.peak_bin, item.start_bin))
        capacity = max(0, self.MAX_ACTIVE_TRACKS - len(self._tracks))
        admitted = unmatched[:capacity]
        for region in admitted:
            event_id = self._next_event_id
            self._next_event_id += 1
            self._tracks[event_id] = _Track(
                event_id=event_id,
                region=region,
                first_frame=frame_index,
                last_seen_frame=frame_index,
                seen_count=1,
                history=deque((True,), maxlen=self.confirmation_window),
            )
        return ended_now, len(unmatched) - len(admitted)

    def _association_overlap(self, previous: DetectionRegion, current: DetectionRegion) -> int:
        tolerance = self.association_tolerance_bins
        start = max(previous.start_bin - tolerance, current.start_bin)
        end = min(previous.end_bin + tolerance, current.end_bin)
        return max(0, end - start + 1)

    @staticmethod
    def _event_from_track(
        track: _Track,
        frame_index: int,
        sample_rate_hz: float,
        frame_length: int,
    ) -> DetectionEvent:
        state: EventState = "confirmed" if track.confirmed else "tentative"
        first_sample = track.first_frame * frame_length
        last_sample = track.last_seen_frame * frame_length
        return DetectionEvent(
            event_id=track.event_id,
            state=state,
            region=track.region,
            first_frame=track.first_frame,
            last_seen_frame=track.last_seen_frame,
            seen_count=track.seen_count,
            first_sample=first_sample,
            last_seen_sample=last_sample,
            first_time_seconds=first_sample / sample_rate_hz,
            last_seen_time_seconds=last_sample / sample_rate_hz,
            observed_this_frame=track.observed_this_frame,
        )
