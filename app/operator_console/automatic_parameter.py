"""Bounded strongest-first scheduling for inline PL/ARM parameter observations."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Iterable

from algorithms.p0.transport import (
    IQFrame,
    InlineParameterResult,
    ParameterObservationRequest,
    TransportError,
)


AUTOMATIC_PARAMETER_QUEUE_CAPACITY = 8
AUTOMATIC_PARAMETER_REQUIRED_FRAMES = 4
AUTOMATIC_PARAMETER_MAXIMUM_RETRIES = 2
AUTOMATIC_PARAMETER_MINIMUM_BIN = 56
AUTOMATIC_PARAMETER_MAXIMUM_BIN = 4039
AUTOMATIC_PARAMETER_MINIMUM_SPAN = 8
AUTOMATIC_PARAMETER_MAXIMUM_SPAN = 512
AUTOMATIC_PARAMETER_REFERENCE_GUARD = 36


@dataclass(frozen=True)
class AutomaticParameterOutcome:
    event_id: int
    intent_id: int
    detected_frequency_hz: float
    detected_peak_power: float
    lower_shifted_bin: int
    upper_shifted_bin: int
    status: str
    reason: str | None
    result: InlineParameterResult | None = None

    @property
    def channel_power_dbfs(self) -> float | None:
        return (
            self.result.channel_power_dbfs.value
            if self.result is not None
            and self.result.channel_power_dbfs.state == "valid"
            else None
        )


@dataclass
class _ActiveObservation:
    event_id: int
    intent_id: int
    detected_frequency_hz: float
    detected_peak_power: float
    lower_shifted_bin: int
    upper_shifted_bin: int
    submitted_frames: int = 0


class AutomaticParameterScheduler:
    """Schedule at most one four-frame card observation context at a time."""

    def __init__(self, *, center_frequency_hz: int, fft_size: int = 4096) -> None:
        if fft_size != 4096 or center_frequency_hz <= 0:
            raise ValueError("Canlı otomatik parametre zamanlayıcısı 4096 FFT bağlamı gerektirir.")
        self._center_frequency_hz = center_frequency_hz
        self._bin_spacing_hz = 2_000_000.0 / fft_size
        self._candidates: dict[int, object] = {}
        self._completed: set[int] = set()
        self._retry_counts: dict[int, int] = {}
        self._active: _ActiveObservation | None = None
        self._submitted: dict[int, int] = {}
        self._draining_intent: int | None = None
        self._pending_outcomes: list[AutomaticParameterOutcome] = []
        self._next_intent_id = 1
        self._expired_before_measurement_count = 0

    @property
    def completed_event_count(self) -> int:
        return len(self._completed)

    @property
    def active_event_id(self) -> int | None:
        return self._active.event_id if self._active is not None else None

    @property
    def expired_before_measurement_count(self) -> int:
        """Confirmed events that ended without ever becoming a measurement."""
        return self._expired_before_measurement_count

    def _frequency(self, event: object) -> float:
        return self._center_frequency_hz + (
            int(getattr(event, "peak_shifted_bin")) - 2048
        ) * self._bin_spacing_hz

    @staticmethod
    def _expanded_span(event: object) -> tuple[int, int]:
        lower = int(getattr(event, "start_shifted_bin"))
        upper = int(getattr(event, "end_shifted_bin"))
        missing = max(0, AUTOMATIC_PARAMETER_MINIMUM_SPAN - (upper - lower + 1))
        lower -= missing // 2
        upper += missing - missing // 2
        return lower, upper

    def observe_events(
        self, events: Iterable[object], ended_events: Iterable[object] = ()
    ) -> None:
        current: dict[int, object] = {}
        for event in events:
            if (
                getattr(event, "state", "") == "confirmed"
                and bool(getattr(event, "observed_this_frame", False))
                and int(getattr(event, "event_id", 0)) > 0
                and math.isfinite(float(getattr(event, "peak_power", float("nan"))))
            ):
                current[int(getattr(event, "event_id"))] = event
        self._candidates = current
        active_event_id = self._active.event_id if self._active is not None else None
        for event in ended_events:
            event_id = int(getattr(event, "event_id", 0))
            if event_id <= 0 or event_id in self._completed or event_id == active_event_id:
                continue
            # An event that never received a parameter intent is queue telemetry,
            # not a measurement outcome. Publishing every short-lived detector
            # event can flood the GUI/catalog under a strong modulated signal.
            self._completed.add(event_id)
            self._expired_before_measurement_count += 1

    def _skip(self, event: object, lower: int, upper: int, reason: str) -> None:
        event_id = int(getattr(event, "event_id"))
        self._completed.add(event_id)
        self._pending_outcomes.append(
            AutomaticParameterOutcome(
                event_id,
                0,
                self._frequency(event),
                float(getattr(event, "peak_power")),
                lower,
                upper,
                "not_measurable",
                reason,
            )
        )

    def _select(self) -> None:
        if self._active is not None or self._draining_intent is not None:
            return
        ranked = sorted(
            (
                event for event_id, event in self._candidates.items()
                if event_id not in self._completed
            ),
            key=lambda item: (-float(getattr(item, "peak_power")), int(getattr(item, "event_id"))),
        )[:AUTOMATIC_PARAMETER_QUEUE_CAPACITY]
        while ranked:
            event = ranked.pop(0)
            event_id = int(getattr(event, "event_id"))
            lower, upper = self._expanded_span(event)
            if upper - lower + 1 > AUTOMATIC_PARAMETER_MAXIMUM_SPAN:
                self._skip(event, lower, upper, "live_span_exceeds_512_bins")
                continue
            if lower < AUTOMATIC_PARAMETER_MINIMUM_BIN or upper > AUTOMATIC_PARAMETER_MAXIMUM_BIN:
                self._skip(event, lower, upper, "reference_window_outside_fft")
                continue
            ambiguous = any(
                int(getattr(other, "event_id")) != event_id
                and int(getattr(other, "end_shifted_bin")) >= lower - AUTOMATIC_PARAMETER_REFERENCE_GUARD
                and int(getattr(other, "start_shifted_bin")) <= upper + AUTOMATIC_PARAMETER_REFERENCE_GUARD
                for other in self._candidates.values()
            )
            if ambiguous:
                self._skip(event, lower, upper, "neighbor_in_reference_window")
                continue
            intent_id = self._next_intent_id
            self._next_intent_id += 1
            self._active = _ActiveObservation(
                event_id,
                intent_id,
                self._frequency(event),
                float(getattr(event, "peak_power")),
                lower,
                upper,
            )
            return

    def decorate(self, frame: IQFrame) -> IQFrame:
        self._select()
        active = self._active
        if active is None or active.submitted_frames >= AUTOMATIC_PARAMETER_REQUIRED_FRAMES:
            return frame
        request = ParameterObservationRequest(
            active.intent_id,
            active.event_id,
            active.lower_shifted_bin,
            active.upper_shifted_bin,
            active.submitted_frames == 0,
        )
        active.submitted_frames += 1
        self._submitted[frame.sequence_number] = active.intent_id
        return replace(frame, parameter_request=request)

    @staticmethod
    def _result_state(result: InlineParameterResult) -> tuple[str, str | None]:
        fields = (
            result.emission_center_frequency_hz,
            result.lower_occupied_edge_hz,
            result.upper_occupied_edge_hz,
            result.occupied_bandwidth_hz,
            result.channel_power_dbfs,
            result.snr_estimate_db,
        )
        invalid = next((field for field in fields if field.state != "valid"), None)
        return ("valid", None) if invalid is None else (invalid.state, invalid.reason)

    def observe_response(
        self, sequence_number: int, parameter: InlineParameterResult | None
    ) -> tuple[AutomaticParameterOutcome, ...]:
        expected_intent = self._submitted.pop(sequence_number, None)
        if expected_intent is None:
            if parameter is not None:
                raise TransportError(
                    "unexpected_parameter_result", "İsteksiz kart parametre sonucu alındı."
                )
            return self.drain_outcomes()
        if parameter is None or parameter.intent_id != expected_intent:
            raise TransportError(
                "parameter_result_missing", "Kart otomatik parametre isteğini yanıtlamadı."
            )
        active = self._active
        if active is None or parameter.event_id != active.event_id:
            if self._draining_intent == expected_intent:
                if not any(intent == expected_intent for intent in self._submitted.values()):
                    self._draining_intent = None
                return self.drain_outcomes()
            raise TransportError(
                "parameter_result_mismatch", "Kart parametre sonucu hedef olayla eşleşmiyor."
            )
        reasons = {
            field.reason
            for field in (
                parameter.emission_center_frequency_hz,
                parameter.lower_occupied_edge_hz,
                parameter.upper_occupied_edge_hz,
                parameter.occupied_bandwidth_hz,
                parameter.channel_power_dbfs,
                parameter.snr_estimate_db,
            )
        }
        if "event_ownership_lost" in reasons:
            retries = self._retry_counts.get(active.event_id, 0) + 1
            self._retry_counts[active.event_id] = retries
            self._active = None
            self._draining_intent = expected_intent
            if retries > AUTOMATIC_PARAMETER_MAXIMUM_RETRIES:
                self._completed.add(active.event_id)
                self._pending_outcomes.append(
                    AutomaticParameterOutcome(
                        active.event_id,
                        active.intent_id,
                        active.detected_frequency_hz,
                        active.detected_peak_power,
                        active.lower_shifted_bin,
                        active.upper_shifted_bin,
                        "not_observed",
                        "event_ownership_lost",
                        parameter,
                    )
                )
            if not any(intent == expected_intent for intent in self._submitted.values()):
                self._draining_intent = None
            return self.drain_outcomes()
        if parameter.observation_count == AUTOMATIC_PARAMETER_REQUIRED_FRAMES:
            status, reason = self._result_state(parameter)
            self._completed.add(active.event_id)
            self._pending_outcomes.append(
                AutomaticParameterOutcome(
                    active.event_id,
                    active.intent_id,
                    active.detected_frequency_hz,
                    active.detected_peak_power,
                    active.lower_shifted_bin,
                    active.upper_shifted_bin,
                    status,
                    reason,
                    parameter,
                )
            )
            self._active = None
        return self.drain_outcomes()

    def drain_outcomes(self) -> tuple[AutomaticParameterOutcome, ...]:
        outcomes = tuple(self._pending_outcomes)
        self._pending_outcomes.clear()
        return outcomes

    def finish(self) -> tuple[AutomaticParameterOutcome, ...]:
        active = self._active
        if active is not None and active.event_id not in self._completed:
            self._completed.add(active.event_id)
            self._pending_outcomes.append(
                AutomaticParameterOutcome(
                    active.event_id,
                    active.intent_id,
                    active.detected_frequency_hz,
                    active.detected_peak_power,
                    active.lower_shifted_bin,
                    active.upper_shifted_bin,
                    "not_observed",
                    "session_ended_before_four_observations",
                )
            )
            self._active = None
        return self.drain_outcomes()
