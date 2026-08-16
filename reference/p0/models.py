"""Immutable result objects used by P0 ED runtime owners and the UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Provenance = Literal["REPLAY", "HOST REFERENCE", "FUTURE ZEDBOARD HARDWARE"]
SignalDomain = Literal["Analog", "Sayısal", "Belirsiz"]


@dataclass(frozen=True)
class CandidateRegion:
    start_bin: int
    end_bin: int
    peak_bin: int
    peak_power: float
    noise_power_per_bin: float
    threshold_power: float

    @property
    def bin_count(self) -> int:
        return self.end_bin - self.start_bin + 1


@dataclass(frozen=True)
class P0ParameterResult:
    frame_id: int
    candidate: CandidateRegion
    confirmed: bool
    carrier_frequency_hz: float
    lower_frequency_hz: float
    upper_frequency_hz: float
    bandwidth_hz: float
    relative_power_linear: float
    relative_power_dbfs: float
    snr_db: float
    signal_domain: SignalDomain
    classification_reasons: tuple[str, ...]
    spectral_flatness: float
    envelope_variation: float
    instantaneous_frequency_discontinuity: float
    time_frequency_variation: float
    calibration_state: Literal["KALİBRASYON BEKLİYOR"]
    provenance: Provenance
    backend: str
