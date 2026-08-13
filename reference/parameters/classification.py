"""Bounded frame-feature history and limited Analog/Digital separation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .models import SignalDomainEstimate


FEATURE_COUNT = 32
MAX_TRACKS = 64
HISTORY_DEPTH = 4
FEATURE_HISTORY_BYTES = MAX_TRACKS * HISTORY_DEPTH * FEATURE_COUNT * 8 + MAX_TRACKS * HISTORY_DEPTH * 8 + MAX_TRACKS * HISTORY_DEPTH
assert FEATURE_HISTORY_BYTES == 67_840


@dataclass
class _Slot:
    row: int
    last_frame: int


class FeatureHistoryStore:
    """Preallocated four-record history; it never retains raw or filtered I/Q."""

    def __init__(self) -> None:
        self.features = np.zeros((MAX_TRACKS, HISTORY_DEPTH, FEATURE_COUNT), dtype=np.float64)
        self.frame_indices = np.full((MAX_TRACKS, HISTORY_DEPTH), -1, dtype=np.int64)
        self.valid = np.zeros((MAX_TRACKS, HISTORY_DEPTH), dtype=np.bool_)
        self._slots: dict[int, _Slot] = {}

    @property
    def payload_bytes(self) -> int:
        return self.features.nbytes + self.frame_indices.nbytes + self.valid.nbytes

    def reset(self) -> None:
        self.features.fill(0.0)
        self.frame_indices.fill(-1)
        self.valid.fill(False)
        self._slots.clear()

    def remove_missing(self, active_event_ids: set[int]) -> None:
        for event_id in sorted(set(self._slots) - active_event_ids):
            self._clear_slot(event_id)

    def contains(self, event_id: int) -> bool:
        """Return whether an event owns one bounded feature-history slot."""
        return event_id in self._slots

    def last_frame(self, event_id: int) -> int | None:
        """Return the last genuinely observed feature frame for an event."""
        slot = self._slots.get(event_id)
        return None if slot is None else slot.last_frame

    def discard(self, event_id: int) -> None:
        """Drop one losing merge/split owner without disturbing other tracks."""
        if event_id in self._slots:
            self._clear_slot(event_id)

    def append(self, event_id: int, frame_index: int, features: npt.ArrayLike) -> npt.NDArray[np.float64]:
        vector = np.asarray(features, dtype=np.float64)
        if vector.shape != (FEATURE_COUNT,) or not np.all(np.isfinite(vector)):
            raise ValueError("feature record must contain 32 finite float64 values")
        slot = self._slots.get(event_id)
        if slot is None:
            free_rows = sorted(set(range(MAX_TRACKS)) - {item.row for item in self._slots.values()})
            if not free_rows:
                raise ValueError("feature history track capacity exceeded")
            slot = _Slot(free_rows[0], frame_index - 1)
            self._slots[event_id] = slot
        if frame_index != slot.last_frame + 1:
            self.features[slot.row].fill(0.0)
            self.frame_indices[slot.row].fill(-1)
            self.valid[slot.row].fill(False)
        row = slot.row
        self.features[row, :-1] = self.features[row, 1:]
        self.frame_indices[row, :-1] = self.frame_indices[row, 1:]
        self.valid[row, :-1] = self.valid[row, 1:]
        self.features[row, -1] = vector
        self.frame_indices[row, -1] = frame_index
        self.valid[row, -1] = True
        slot.last_frame = frame_index
        return self.features[row, self.valid[row]].copy()

    def _clear_slot(self, event_id: int) -> None:
        slot = self._slots.pop(event_id)
        self.features[slot.row].fill(0.0)
        self.frame_indices[slot.row].fill(-1)
        self.valid[slot.row].fill(False)


def _feature_summary(history: npt.NDArray[np.float64]) -> dict[str, float]:
    mean = np.mean(np.asarray(history, dtype=np.float64), axis=0)
    return {
        "envelope_cv": float(mean[4]),
        "off_fraction": float(mean[5]),
        "two_level": float(mean[7]),
        "constant_modulus": float(mean[8]),
        "phase_jump_rate": float(np.sum(history[:, 9]) / max(1.0, np.sum(history[:, 10]))),
        "mode_separation": float(mean[20]),
        "valley_ratio": float(mean[21]),
        "spectral_flatness": float(mean[22]),
        "snr_db": float(mean[31]),
    }


def _rules(values: dict[str, float]) -> tuple[float, float]:
    analog = 0.0
    digital = 0.0
    jump = values["phase_jump_rate"]
    cv = values["envelope_cv"]
    if jump < 0.005 and 0.05 <= cv <= 0.55:
        analog += 3.0
    if jump < 0.005 and values["constant_modulus"] <= 0.20:
        analog += 2.0
    if values["two_level"] >= 0.75 or values["off_fraction"] >= 0.20:
        digital += 3.0
    if 0.005 <= jump <= 0.25:
        digital += 3.0
    if values["mode_separation"] >= 4.0 and values["valley_ratio"] <= 0.50:
        digital += 3.0
    return analog, digital


def classify_features(method: str, history: npt.NDArray[np.float64]) -> SignalDomainEstimate:
    records = np.asarray(history, dtype=np.float64)
    count = int(records.shape[0])
    if count < 3:
        return SignalDomainEstimate("Belirsiz", "uncertain", count)
    values = _feature_summary(records)
    if values["snr_db"] < 6.0:
        return SignalDomainEstimate("Belirsiz", "uncertain", count)
    analog, digital = _rules(values)
    if method == "domain.normalized-feature-score":
        analog += max(0.0, 0.55 - values["envelope_cv"])
        digital += max(0.0, 0.25 - abs(values["phase_jump_rate"] - 0.125))
    elif method == "domain.conservative-consensus":
        rule_decision = "Analog" if analog - digital >= 2.0 else "Sayısal" if digital - analog >= 2.0 else "Belirsiz"
        score_analog = analog + max(0.0, 0.55 - values["envelope_cv"])
        score_digital = digital + max(0.0, 0.25 - abs(values["phase_jump_rate"] - 0.125))
        score_decision = "Analog" if score_analog - score_digital >= 2.0 else "Sayısal" if score_digital - score_analog >= 2.0 else "Belirsiz"
        if rule_decision != score_decision:
            return SignalDomainEstimate("Belirsiz", "uncertain", count)
        analog, digital = score_analog, score_digital
    elif method != "domain.explainable-rules":
        raise ValueError(f"unsupported signal-domain method: {method}")
    if analog - digital >= 2.0:
        return SignalDomainEstimate("Analog", "valid", count)
    if digital - analog >= 2.0:
        return SignalDomainEstimate("Sayısal", "valid", count)
    return SignalDomainEstimate("Belirsiz", "uncertain", count)
