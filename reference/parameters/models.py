"""Typed, calibration-honest PHASE-04 parameter result models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FieldState = Literal[
    "valid",
    "not_observed",
    "not_applicable",
    "insufficient_quality",
    "uncertain",
]
ParameterInvalidReason = Literal[
    "analysis_candidate_overflow",
    "reference_cells_unavailable",
    "anchor_not_significant",
    "support_component_overflow",
    "support_empty",
    "invalid_noise",
]
SignalDomain = Literal["Analog", "Sayısal", "Belirsiz"]


@dataclass(frozen=True)
class AnalysisCandidate:
    """One bounded PHASE-04 analysis window owned by a confirmed event."""

    owner_event_id: int
    source_event_ids: tuple[int, ...]
    source_region_count: int
    hull_start_bin: int
    hull_end_bin: int
    search_start_bin: int
    search_end_bin: int
    left_reference_start_bin: int
    left_reference_end_bin: int
    right_reference_start_bin: int
    right_reference_end_bin: int
    peak_bin: int
    state: FieldState
    invalid_reason: ParameterInvalidReason | None = None


@dataclass(frozen=True)
class BandSupportResult:
    """Explainable inclusive-bin support returned by one bandwidth method."""

    lower_shifted_bin: int | None
    upper_shifted_bin: int | None
    state: FieldState
    invalid_reason: ParameterInvalidReason | None = None
    component_count: int = 0
    retained_component_count: int = 0
    expansion_order: tuple[str, ...] = ()
    retained_component_indices: tuple[int, ...] = ()


@dataclass(frozen=True)
class FrequencyEstimate:
    spectral_center_frequency_hz: float | None
    spectral_center_state: FieldState
    observed_carrier_frequency_hz: float | None
    observed_carrier_state: FieldState


@dataclass(frozen=True)
class BandwidthEstimate:
    lower_edge_frequency_hz: float | None
    lower_edge_state: FieldState
    upper_edge_frequency_hz: float | None
    upper_edge_state: FieldState
    bandwidth_hz: float | None
    bandwidth_state: FieldState
    lower_shifted_bin: int | None
    upper_shifted_bin: int | None
    invalid_reason: ParameterInvalidReason | None = None


@dataclass(frozen=True)
class RelativePowerEstimate:
    signal_power_fs2: float | None
    signal_power_dbfs: float | None
    noise_power_fs2: float | None
    snr_db: float | None
    relative_power_state: FieldState
    snr_state: FieldState
    calibrated: bool = False


@dataclass(frozen=True)
class SignalDomainEstimate:
    value: SignalDomain
    state: FieldState
    observed_frame_count: int


@dataclass(frozen=True)
class EventParameterEstimate:
    event_id: int
    frame_index: int
    frequency: FrequencyEstimate
    bandwidth: BandwidthEstimate
    power: RelativePowerEstimate
    signal_domain: SignalDomainEstimate
    invalid_reason: ParameterInvalidReason | None = None


@dataclass(frozen=True)
class ParameterFrameResult:
    frame_index: int
    events: tuple[EventParameterEstimate, ...]
    history_payload_bytes: int
    transient_guard_samples_per_side: int
    feature_sample_count: int
    frame_local_filtering: bool = True
    analysis_candidates: tuple[AnalysisCandidate, ...] = ()
    dropped_owner_candidate_count: int = 0
