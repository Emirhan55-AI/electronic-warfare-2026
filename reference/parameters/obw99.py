"""Single bounded PHASE-04-D1 occupied-bandwidth reference estimator."""

from __future__ import annotations

import math
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from reference.detection import DetectionEvent, DetectionFrameResult
from reference.spectrum import SpectrumResult


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_CONTRACT_PATH = ROOT / "datasets" / "fixtures" / "phase04d1" / "reference-contract.json"
METHOD_LOCK_PATH = ROOT / "datasets" / "fixtures" / "phase04d1" / "method-lock.json"


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return document


OccupiedBandwidthState = Literal[
    "valid",
    "not_observed",
    "not_applicable",
    "insufficient_quality",
    "uncertain",
]


@dataclass(frozen=True)
class OccupiedBandwidthEstimate:
    event_id: int
    frame_index: int
    occupied_bandwidth_hz: float | None
    lower_occupied_edge_hz: float | None
    upper_occupied_edge_hz: float | None
    occupied_power_fraction: float
    state: OccupiedBandwidthState
    observation_count: int
    temporal_state: str
    quality_reasons: tuple[str, ...]
    analysis_clipped: bool
    candidate_isolated: bool
    lower_shifted_bin: float | None = None
    upper_shifted_bin: float | None = None


@dataclass(frozen=True)
class OccupiedBandwidthFrameResult:
    frame_index: int
    events: tuple[OccupiedBandwidthEstimate, ...]
    active_history_count: int
    history_payload_bytes: int
    dropped_event_count: int


@dataclass(frozen=True)
class _FrameMeasurement:
    lower: int
    upper: int
    psd: np.ndarray
    noise: float
    lower_edge: float
    upper_edge: float


@dataclass
class _EventHistory:
    frames: deque[_FrameMeasurement]
    last_frame: int


def _overlap(first: DetectionEvent, second: DetectionEvent) -> bool:
    return first.region.start_bin <= second.region.end_bin and second.region.start_bin <= first.region.end_bin


def _fractional_edge(excess: np.ndarray, lower: int, fraction: float) -> float:
    total = float(np.sum(excess))
    if total <= 0.0:
        raise ValueError("empty excess")
    target = fraction * total
    cumulative = np.cumsum(excess)
    index = min(int(np.searchsorted(cumulative, target, side="left")), excess.size - 1)
    before = 0.0 if index == 0 else float(cumulative[index - 1])
    position = index - 0.5 + (target - before) / max(float(excess[index]), np.finfo(np.float64).tiny)
    return float(lower + position)


class OccupiedBandwidthEstimator:
    """Estimate OBW99 without labels, truth data, or a second method path."""

    METHOD_ID = "obw.direct-cumulative-99-v1"
    BLOCK_ID = "analysis.occupied-bandwidth/v1"
    OUTPUT_TYPE = "parameters.occupied-bandwidth/v1"

    def __init__(self, *, noise_correction: float | None = None) -> None:
        contract = _load_json(REFERENCE_CONTRACT_PATH)
        self.contract = contract
        span = contract["analysis_span"]
        quality = contract["quality"]
        temporal = contract["temporal_state"]
        memory = contract["bounded_memory"]
        self.safe_lower = int(span["shifted_safe_lower_bin_inclusive"])
        self.safe_upper = int(span["shifted_safe_upper_bin_inclusive"])
        self.initial_margin = int(span["initial_margin_bins_per_side"])
        self.expansion_step = int(span["expansion_step_bins_per_side"])
        self.maximum_width = int(span["maximum_analysis_width_bins"])
        self.edge_guard = int(span["analysis_edge_guard_bins"])
        self.reference_guard = int(span["reference_guard_bins"])
        self.reference_cells = int(span["reference_cells_per_side"])
        self.neighbor_reserve = int(span["neighbor_policy"]["reserved_bins"])
        self.edge_excess_fraction = float(span["expansion_trigger"]["edge_guard_excess_fraction_greater_than"])
        self.minimum_excess_ratio = float(quality["minimum_integrated_excess_to_noise_ratio"])
        self.stability_limit = float(quality["temporal_edge_stability"]["maximum_native_bins"])
        self.depth = int(temporal["minimum_consecutive_confirmed_observed_frames"])
        self.maximum_events = int(memory["maximum_active_events"])
        if noise_correction is None:
            method_lock = _load_json(METHOD_LOCK_PATH)
            calibration = method_lock.get("noise_calibration", {})
            if method_lock.get("status") != "locked-pre-binding" or calibration.get("status") != "passed":
                raise ValueError("a passing pre-binding method lock is required")
            noise_correction = calibration.get("correction_factor")
        self.noise_correction = float(noise_correction)
        if not math.isfinite(self.noise_correction) or self.noise_correction <= 0.0:
            raise ValueError("noise correction must be positive and finite")
        self._history: dict[int, _EventHistory] = {}
        self._previous_events: dict[int, DetectionEvent] = {}
        self._last_frame: int | None = None
        self._generation: Any = None

    @property
    def active_history_count(self) -> int:
        return len(self._history)

    @property
    def history_payload_bytes(self) -> int:
        return self.maximum_events * int(self.contract["bounded_memory"]["total_bytes_per_event"])

    def reset(self) -> None:
        self._history.clear()
        self._previous_events.clear()
        self._last_frame = None
        self._generation = None

    def notify_seek(self) -> None:
        self.reset()

    def notify_source_change(self, generation: Any) -> None:
        if generation != self._generation:
            self.reset()
            self._generation = generation

    def _reset_topology_changes(self, current: dict[int, DetectionEvent]) -> None:
        previous = self._previous_events
        current_to_previous = {
            event_id: {old_id for old_id, old in previous.items() if _overlap(event, old)}
            for event_id, event in current.items()
        }
        previous_to_current = {
            event_id: {new_id for new_id, new in current.items() if _overlap(event, new)}
            for event_id, event in previous.items()
        }
        reset_ids: set[int] = set(previous) - set(current)
        for event_id, linked in current_to_previous.items():
            if len(linked) != 1 or (linked and event_id not in linked):
                reset_ids.add(event_id)
                reset_ids.update(linked)
        for event_id, linked in previous_to_current.items():
            if len(linked) != 1:
                reset_ids.add(event_id)
                reset_ids.update(linked)
        for event_id in reset_ids:
            self._history.pop(event_id, None)

    def _territory(self, event: DetectionEvent, others: tuple[DetectionEvent, ...]) -> tuple[int, int]:
        lower = self.safe_lower
        upper = self.safe_upper
        for other in others:
            if other.event_id == event.event_id:
                continue
            midpoint = 0.5 * (event.region.peak_bin + other.region.peak_bin)
            if other.region.peak_bin < event.region.peak_bin:
                lower = max(lower, int(math.ceil(midpoint)) + self.neighbor_reserve)
            else:
                upper = min(upper, int(math.floor(midpoint)) - self.neighbor_reserve)
        return lower, upper

    def _noise(self, psd: np.ndarray, lower: int, upper: int, territory: tuple[int, int]) -> float | None:
        left_end = lower - self.reference_guard - 1
        left_start = left_end - self.reference_cells + 1
        right_start = upper + self.reference_guard + 1
        right_end = right_start + self.reference_cells - 1
        if left_start < territory[0] or right_end > territory[1]:
            return None
        values = np.concatenate((psd[left_start : left_end + 1], psd[right_start : right_end + 1]))
        estimate = float(np.median(values) / math.log(2.0) * self.noise_correction)
        return estimate if math.isfinite(estimate) and estimate > 0.0 else None

    def _measure_frame(
        self,
        event: DetectionEvent,
        others: tuple[DetectionEvent, ...],
        psd: np.ndarray,
    ) -> tuple[_FrameMeasurement | None, tuple[str, ...], bool, bool]:
        territory = self._territory(event, others)
        reference_reserve = self.reference_guard + self.reference_cells
        analysis_lower_limit = territory[0] + reference_reserve
        analysis_upper_limit = territory[1] - reference_reserve
        lower = max(event.region.start_bin - self.initial_margin, analysis_lower_limit)
        upper = min(event.region.end_bin + self.initial_margin, analysis_upper_limit)
        isolated = lower <= event.region.start_bin <= event.region.end_bin <= upper
        if not isolated or lower > upper:
            return None, ("candidate_not_isolated",), True, False
        while True:
            if upper - lower + 1 > self.maximum_width:
                return None, ("analysis_window_clipped",), True, isolated
            noise = self._noise(psd, lower, upper, territory)
            if noise is None:
                return None, ("reference_cells_unavailable", "analysis_window_clipped"), True, isolated
            excess = np.maximum(psd[lower : upper + 1] - noise, 0.0)
            total = float(np.sum(excess))
            if total <= 0.0:
                return None, ("insufficient_excess_power",), False, isolated
            lower_edge = _fractional_edge(excess, lower, 0.005)
            upper_edge = _fractional_edge(excess, lower, 0.995)
            left_trigger = (
                lower_edge <= lower + self.edge_guard
                or float(np.sum(excess[: self.edge_guard])) / total > self.edge_excess_fraction
            )
            right_trigger = (
                upper_edge >= upper - self.edge_guard
                or float(np.sum(excess[-self.edge_guard :])) / total > self.edge_excess_fraction
            )
            if not left_trigger and not right_trigger:
                ratio = total / (noise * excess.size)
                if ratio < self.minimum_excess_ratio:
                    return None, ("insufficient_excess_power",), False, isolated
                readonly = np.asarray(psd[lower : upper + 1], dtype=np.float64).copy()
                readonly.setflags(write=False)
                return _FrameMeasurement(lower, upper, readonly, noise, lower_edge, upper_edge), (), False, isolated
            next_lower = lower
            next_upper = upper
            if left_trigger:
                next_lower = max(analysis_lower_limit, lower - self.expansion_step)
            if right_trigger:
                next_upper = min(analysis_upper_limit, upper + self.expansion_step)
            if next_upper - next_lower + 1 > self.maximum_width:
                available = self.maximum_width - (upper - lower + 1)
                if left_trigger and right_trigger:
                    left_add = min(lower - analysis_lower_limit, available // 2)
                    right_add = min(analysis_upper_limit - upper, available - left_add)
                    next_lower, next_upper = lower - left_add, upper + right_add
                elif left_trigger:
                    next_lower = lower - min(lower - analysis_lower_limit, available)
                else:
                    next_upper = upper + min(analysis_upper_limit - upper, available)
            if next_lower == lower and next_upper == upper:
                return None, ("analysis_window_clipped",), True, isolated
            lower, upper = next_lower, next_upper

    def process(
        self,
        spectrum: SpectrumResult,
        detection: DetectionFrameResult,
        *,
        frame_index: int,
        generation: Any = 0,
    ) -> OccupiedBandwidthFrameResult:
        if detection.frame_index != frame_index:
            raise ValueError("detection and estimator frame indices differ")
        if self._generation is None:
            self._generation = generation
        elif generation != self._generation:
            self.reset()
            self._generation = generation
        if self._last_frame is not None and frame_index != self._last_frame + 1:
            self._history.clear()
            self._previous_events.clear()
        observed = tuple(
            event
            for event in detection.active_events
            if event.state == "confirmed" and event.observed_this_frame
        )
        current = {event.event_id: event for event in observed}
        self._reset_topology_changes(current)
        for event_id in set(self._history) - set(current):
            self._history.pop(event_id, None)
        psd = np.asarray(spectrum.display.psd_fs2_per_hz, dtype=np.float64)
        outputs: list[OccupiedBandwidthEstimate] = []
        dropped = max(0, len(observed) - self.maximum_events)
        for event in sorted(observed, key=lambda item: item.event_id)[: self.maximum_events]:
            measured, reasons, clipped, isolated = self._measure_frame(event, observed, psd)
            if measured is None:
                self._history.pop(event.event_id, None)
                state: OccupiedBandwidthState = "uncertain" if clipped or not isolated else "insufficient_quality"
                outputs.append(
                    OccupiedBandwidthEstimate(
                        event.event_id,
                        frame_index,
                        None,
                        None,
                        None,
                        0.99,
                        state,
                        0,
                        "reset",
                        reasons,
                        clipped,
                        isolated,
                    )
                )
                continue
            history = self._history.get(event.event_id)
            if (
                history is None
                or history.last_frame != frame_index - 1
                or not history.frames
                or (history.frames[-1].lower, history.frames[-1].upper) != (measured.lower, measured.upper)
            ):
                history = _EventHistory(deque(maxlen=self.depth), frame_index)
                self._history[event.event_id] = history
            history.frames.append(measured)
            history.last_frame = frame_index
            observation_count = len(history.frames)
            if observation_count < self.depth:
                outputs.append(
                    OccupiedBandwidthEstimate(
                        event.event_id,
                        frame_index,
                        None,
                        None,
                        None,
                        0.99,
                        "insufficient_quality",
                        observation_count,
                        "warming_up",
                        ("temporal_warmup",),
                        False,
                        isolated,
                    )
                )
                continue
            averaged = np.mean(np.stack([item.psd for item in history.frames], axis=0), axis=0)
            noise = float(np.mean([item.noise for item in history.frames]))
            excess = np.maximum(averaged - noise, 0.0)
            total = float(np.sum(excess))
            if total <= 0.0 or total / (noise * excess.size) < self.minimum_excess_ratio:
                outputs.append(
                    OccupiedBandwidthEstimate(
                        event.event_id,
                        frame_index,
                        None,
                        None,
                        None,
                        0.99,
                        "insufficient_quality",
                        observation_count,
                        "observed",
                        ("insufficient_excess_power",),
                        False,
                        isolated,
                    )
                )
                continue
            lower_edge = _fractional_edge(excess, measured.lower, 0.005)
            upper_edge = _fractional_edge(excess, measured.lower, 0.995)
            frame_lowers = np.asarray([item.lower_edge for item in history.frames], dtype=np.float64)
            frame_uppers = np.asarray([item.upper_edge for item in history.frames], dtype=np.float64)
            deviation = max(
                float(np.max(np.abs(frame_lowers - np.median(frame_lowers)))),
                float(np.max(np.abs(frame_uppers - np.median(frame_uppers)))),
            )
            if deviation > self.stability_limit:
                outputs.append(
                    OccupiedBandwidthEstimate(
                        event.event_id,
                        frame_index,
                        None,
                        None,
                        None,
                        0.99,
                        "insufficient_quality",
                        observation_count,
                        "unstable",
                        ("temporal_edges_unstable",),
                        False,
                        isolated,
                    )
                )
                continue
            bin_hz = spectrum.bin_spacing_hz
            lower_hz = spectrum.center_frequency_hz + (lower_edge - spectrum.frame_length / 2.0) * bin_hz
            upper_hz = spectrum.center_frequency_hz + (upper_edge - spectrum.frame_length / 2.0) * bin_hz
            outputs.append(
                OccupiedBandwidthEstimate(
                    event.event_id,
                    frame_index,
                    upper_hz - lower_hz,
                    lower_hz,
                    upper_hz,
                    0.99,
                    "valid",
                    observation_count,
                    "stable",
                    (),
                    False,
                    isolated,
                    lower_edge,
                    upper_edge,
                )
            )
        self._previous_events = current
        self._last_frame = frame_index
        return OccupiedBandwidthFrameResult(
            frame_index,
            tuple(outputs),
            len(self._history),
            self.history_payload_bytes,
            dropped,
        )
