"""Spectrum, fixed-band verification and detection-state presentation."""

from __future__ import annotations

import math

import numpy as np

from algorithms.p0.coarse_detection import CoarseDetectionFrame
from algorithms.pipeline import RuntimeFrameResult

from .fixed_band_verification import (
    FIXED_PRESENTATION_HOLD_FRAMES,
    FIXED_PRIMARY_MIN_SEEN_FRAMES,
    FIXED_VERIFY_MATCH_HZ,
    FixedBandCandidate,
    FixedBandVerification,
    fixed_candidate_reference_frequency,
    known_spur_shoulder_evidence,
)
from .live_ed import LIVE_USABLE_HALF_BAND_HZ
from .quick_runtime import _reduce_display_max

LIVE_SPUR_GUARD_WINDOW = 8
SUPPRESSED_VERIFICATION_STATES = {"not_reproduced", "live_guard_failed"}
LIVE_PRESENTATION_CLUSTER_HZ = 75_000.0
FIXED_VERIFICATION_QUEUE_CAPACITY = 4


class QuickDetectionStateMixin:
    def _update_spectrum(self, result: RuntimeFrameResult) -> None:
        self._update_spectrum_result(result.spectrum)

    def _update_live_spur_guard(self, spectrum: object) -> None:
        """Continuously revoke a known-spur decision when its RF shoulders vanish."""
        if self._source_mode != "hackrf" or not self._known_spurs_hz:
            return
        display = getattr(spectrum, "display")
        power = np.asarray(display.bin_power_fs2, dtype=np.float64)
        frequencies = np.asarray(display.frequency_absolute_hz, dtype=np.float64)
        if power.ndim != 1 or frequencies.shape != power.shape or power.size == 0:
            return
        binding = (
            float(getattr(spectrum, "center_frequency_hz")),
            float(getattr(spectrum, "sample_rate_hz")),
            int(power.size),
        )
        if binding != self._live_spur_guard_binding:
            self._live_spur_guard_binding = binding
            self._live_spur_guard_power.clear()
            self._live_spur_guard_passed.clear()
        self._live_spur_guard_power.append(power.copy())
        if len(self._live_spur_guard_power) < LIVE_SPUR_GUARD_WINDOW:
            return
        averaged = np.mean(np.stack(tuple(self._live_spur_guard_power)), axis=0)
        power_rows = np.stack(tuple(self._live_spur_guard_power))
        lower_hz = float(frequencies[0])
        upper_hz = float(frequencies[-1])
        changed = False
        for spur_hz in self._known_spurs_hz:
            if not lower_hz <= spur_hz <= upper_hz:
                continue
            passed, _, _ = known_spur_shoulder_evidence(
                frequencies,
                averaged,
                float(spur_hz),
                power_rows=power_rows,
            )
            previous = self._live_spur_guard_passed.get(spur_hz)
            self._live_spur_guard_passed[spur_hz] = passed
            record = self._fixed_verification_record(float(spur_hz))
            if record is not None and not passed and record.get("state") == "verified_two_lo":
                record.update(state="live_guard_failed", result=None)
                changed = True
            elif record is not None and passed and record.get("state") in {
                "live_guard_failed",
                "not_reproduced",
            }:
                key = next(
                    key for key, value in self._fixed_verification_records.items()
                    if value is record
                )
                del self._fixed_verification_records[key]
                changed = True
            elif previous is not None and previous != passed:
                changed = True
        if not changed:
            return
        self._live_detection_rows = [
            self._apply_fixed_verification(row) for row in self._live_detection_rows
        ]
        self._live_detection_history = [
            self._apply_fixed_verification(row) for row in self._live_detection_history
        ]
        self._refresh_live_detection_list(force=True)

    def _update_spectrum_result(self, spectrum: object) -> None:
        display = getattr(spectrum, "display")
        values = np.asarray(display.bin_power_dbfs, dtype=np.float64)
        power_fs2 = np.asarray(display.bin_power_fs2, dtype=np.float64)
        finite_power = power_fs2[np.isfinite(power_fs2) & (power_fs2 > 0.0)]
        self._direction_frame_power_dbfs = (
            None if finite_power.size == 0 else float(10.0 * np.log10(np.mean(finite_power)))
        )
        width = min(self._viewport_points, values.size)
        reduced = _reduce_display_max(values, width)
        self._spectral_display.append(
            values,
            timestamp=self._frame_index * spectrum.frame_length / spectrum.sample_rate_hz,
            binding=(self._generation, spectrum.center_frequency_hz, spectrum.sample_rate_hz),
        )
        self._spectrum_center_frequency_hz = float(spectrum.center_frequency_hz)
        self._spectrum_sample_rate_hz = float(spectrum.sample_rate_hz)
        self._spectrum_values = [float(value) for value in reduced]
        self._update_live_spur_guard(spectrum)
        self.spectrumChanged.emit()

    def _fixed_verification_record(self, frequency_hz: float) -> dict[str, object] | None:
        return next(
            (
                record for record in self._fixed_verification_records.values()
                if abs(float(record["frequency_hz"]) - float(frequency_hz)) <= FIXED_VERIFY_MATCH_HZ
            ),
            None,
        )

    def _fixed_verification_state(self, frequency_hz: float) -> str:
        record = self._fixed_verification_record(frequency_hz)
        return str(record["state"]) if record is not None else "unverified"

    def _apply_fixed_verification(self, row: dict[str, object]) -> dict[str, object]:
        updated = dict(row)
        record = self._fixed_verification_record(float(row["frequencyHz"]))
        state = str(record["state"]) if record is not None else "unverified"
        result = record.get("result") if record is not None else None
        method = result.verification_method if isinstance(result, FixedBandVerification) else "none"
        revision = int(row.get("eventRevision", 0))
        labels = {
            "verified_two_lo": ("Kararlı RF adayı", "2 ayarda kararlı"),
            "pending": ("FPGA adayı", "İkinci alıcı ayarı denetleniyor"),
            "not_reproduced": ("FPGA adayı", "İkinci ayarda görülmedi"),
            "live_guard_failed": ("Donanım çizgisi", "Canlı RF kanıtı yok"),
            "verification_error": ("FPGA adayı", "İkinci ayar tamamlanamadı"),
        }
        title, label = labels.get(
            state,
            (
                "FPGA adayı",
                "Kararlılık ölçülüyor" if revision < FIXED_PRIMARY_MIN_SEEN_FRAMES else "FPGA adayı",
            ),
        )
        updated.update(
            verificationKey=state,
            verificationLabel=label,
            verificationMethod=method,
            title=title,
        )
        return updated

    def _queue_fixed_verification(self, candidate: FixedBandCandidate) -> None:
        if (
            self._live_session is None
            or self._fixed_verification_candidate is not None
            or self._fixed_verifier is not None
            or self._fixed_verification_record(candidate.frequency_hz) is not None
            or not self._hackrf_transfer_executable
            or self._device_config.serial is None
        ):
            return
        key = round(candidate.frequency_hz / FIXED_VERIFY_MATCH_HZ)
        self._fixed_verification_records[key] = {
            "frequency_hz": candidate.frequency_hz,
            "state": "pending",
            "source": candidate.source,
            "result": None,
        }
        self._fixed_verification_candidate = candidate
        self._fixed_verification_stop_requested = False
        self._fixed_resume_settings = {
            "center_hz": int(self._live_receive_settings["center_hz"]),
            "lna_db": int(self._live_receive_settings["lna_db"]),
            "vga_db": int(self._live_receive_settings["vga_db"]),
            "frame_count": int(self._frame_count),
        }
        self._fixed_preserved_history = [dict(row) for row in self._live_detection_history]
        self._fixed_verifier = self._fixed_verifier_factory(
            self._hackrf_transfer_executable,
            self._device_config.serial,
            self._fixed_resume_settings["lna_db"],
            self._fixed_resume_settings["vga_db"],
            session_factory=self._live_session_factory,
            known_spurs_hz=self._known_spurs_hz,
        )
        self._status_message = (
            f"{self._format_precise_rf(candidate.frequency_hz)} adayı iki alıcı ayarında denetleniyor."
        )
        self._add_log("Sabit bant doğrulama", self._status_message)
        self.detectionsChanged.emit()
        self.stateChanged.emit()
        self._live_session.cancel()

    def _fixed_candidate_known(self, frequency_hz: float) -> bool:
        if self._fixed_verification_record(frequency_hz) is not None:
            return True
        if (
            self._fixed_verification_candidate is not None
            and abs(self._fixed_verification_candidate.frequency_hz - frequency_hz)
            <= FIXED_VERIFY_MATCH_HZ
        ):
            return True
        return any(
            abs(item.frequency_hz - frequency_hz) <= FIXED_VERIFY_MATCH_HZ
            for item in self._fixed_verification_queue
        )

    def _offer_fixed_verification_candidates(
        self,
        candidates: list[FixedBandCandidate],
    ) -> None:
        for candidate in sorted(
            candidates,
            key=lambda item: item.peak_to_noise_db,
            reverse=True,
        ):
            if self._fixed_candidate_known(candidate.frequency_hz):
                continue
            self._fixed_verification_queue.append(candidate)
            self._fixed_verification_queue.sort(
                key=lambda item: item.peak_to_noise_db,
                reverse=True,
            )
            del self._fixed_verification_queue[FIXED_VERIFICATION_QUEUE_CAPACITY:]
        self._start_next_fixed_verification()

    def _start_next_fixed_verification(self) -> None:
        if (
            self._live_session is None
            or self._fixed_verification_candidate is not None
            or self._fixed_verifier is not None
        ):
            return
        while self._fixed_verification_queue:
            candidate = self._fixed_verification_queue.pop(0)
            if self._fixed_verification_record(candidate.frequency_hz) is None:
                self._queue_fixed_verification(candidate)
                return

    def _maybe_verify_fpga_candidate(self, detections: list[dict[str, object]]) -> None:
        candidates = [
            row for row in detections
            if row.get("stateKey") == "confirmed"
            and bool(row.get("observed", True))
            and not bool(row.get("held", False))
            and int(row.get("eventRevision", 0)) >= FIXED_PRIMARY_MIN_SEEN_FRAMES
            and int(row.get("eventRevision", 0)) < FIXED_PRIMARY_MIN_SEEN_FRAMES + 30
            and self._fixed_verification_state(float(row["frequencyHz"])) == "unverified"
        ]
        if not candidates:
            return
        self._offer_fixed_verification_candidates([
            FixedBandCandidate(
                fixed_candidate_reference_frequency(
                    float(row["lowerFrequencyHz"]),
                    float(row["upperFrequencyHz"]),
                    float(row.get("peakFrequencyHz", row["frequencyHz"])),
                ),
                float(row.get("peakFrequencyHz", row["frequencyHz"])),
                float(row["lowerFrequencyHz"]),
                float(row["upperFrequencyHz"]),
                float(row["contrastDb"]),
                "fpga",
            )
            for row in candidates
        ])

    def _maybe_verify_coarse_candidate(self, frame: CoarseDetectionFrame) -> None:
        if self._fixed_verification_candidate is not None:
            return
        candidates = [
            item for item in frame.candidates
            if item.state == "confirmed"
            and item.observed_this_frame
            and self._fixed_verification_state(fixed_candidate_reference_frequency(
                item.lower_frequency_hz,
                item.upper_frequency_hz,
                item.peak_frequency_hz,
            )) == "unverified"
        ]
        if not candidates:
            return
        self._offer_fixed_verification_candidates([
            FixedBandCandidate(
                fixed_candidate_reference_frequency(
                    item.lower_frequency_hz,
                    item.upper_frequency_hz,
                    item.peak_frequency_hz,
                ),
                item.peak_frequency_hz,
                item.lower_frequency_hz,
                item.upper_frequency_hz,
                item.peak_to_noise_db,
                "coarse_rx",
            )
            for item in candidates
            if math.isfinite(item.peak_to_noise_db)
        ])

    def _update_live_detections(self, response: object) -> None:
        active = tuple(getattr(response, "active", ()))
        response_frame = int(getattr(response, "frame_id", self._frame_index))
        state_text = {"tentative": "İzleniyor", "confirmed": "Algılanıyor", "ended": "Sona ermiş"}
        spacing = 2_000_000.0 / 4096.0
        center = float(self._live_output_center_frequency_hz)
        detections: list[dict[str, object]] = []
        for item in active:
            peak_frequency = center + (item.peak_shifted_bin - 2048.0) * spacing
            lower_frequency = center + (item.start_shifted_bin - 2048.0) * spacing
            upper_frequency = center + (item.end_shifted_bin - 2048.0) * spacing
            frequency = fixed_candidate_reference_frequency(
                lower_frequency,
                upper_frequency,
                peak_frequency,
            )
            if abs(frequency - center) > LIVE_USABLE_HALF_BAND_HZ:
                continue
            contrast = item.peak_to_noise_db
            detections.append(
                {
                    "eventId": int(item.event_id),
                    "title": "Sinyal tespit edildi",
                    "frequencyHz": float(frequency),
                    "peakFrequencyHz": float(peak_frequency),
                    "lowerFrequencyHz": lower_frequency,
                    "upperFrequencyHz": upper_frequency,
                    "frequency": self._format_precise_rf(frequency),
                    "snr": f"{contrast:.1f} dB" if math.isfinite(contrast) else "—",
                    "contrastDb": float(contrast) if math.isfinite(contrast) else float("-inf"),
                    "state": state_text[item.state] if item.observed_this_frame else "Sinyal yok",
                    "stateKey": item.state if item.observed_this_frame else "stale",
                    "confirmed": item.state == "confirmed",
                    "observed": item.observed_this_frame,
                    "offsetKHz": (frequency - center) / 1_000.0,
                    "startBin": int(item.start_shifted_bin),
                    "endBin": int(item.end_shifted_bin),
                    "peakBin": int(item.peak_shifted_bin),
                    "eventRevision": int(item.seen_count),
                    "lastObservedFrame": response_frame,
                    "held": False,
                    "startNormalized": self._normalized_live_bin(item.start_shifted_bin),
                    "endNormalized": self._normalized_live_bin(item.end_shifted_bin),
                    "peakNormalized": self._normalized_live_bin(item.peak_shifted_bin),
                }
            )
        current_frequencies = [float(row["frequencyHz"]) for row in detections]
        for previous in self._live_detection_rows:
            if previous.get("stateKey") != "confirmed" or not previous.get("observed", True):
                continue
            if any(
                abs(float(previous["frequencyHz"]) - frequency) <= FIXED_VERIFY_MATCH_HZ
                for frequency in current_frequencies
            ):
                continue
            last_observed = int(previous.get("lastObservedFrame", response_frame))
            if response_frame - last_observed <= FIXED_PRESENTATION_HOLD_FRAMES:
                detections.append(dict(
                    previous,
                    state="Kısa süreli izleniyor",
                    stateKey="confirmed",
                    observed=True,
                    held=True,
                ))
        detections = self._cluster_live_detection_rows(detections)
        detections = [self._apply_fixed_verification(row) for row in detections]
        self._live_detection_rows = detections
        self._update_live_detection_history(detections)
        selected = next((row for row in detections if row["eventId"] == self._selected_detection_id and row["observed"]), None)
        if selected is not None:
            self._selected_live_detection = dict(selected)
        elif self._selected_live_detection is not None:
            self._selected_live_detection = self._last_observation(self._selected_live_detection)
        self._refresh_live_detection_list()
        self._maybe_verify_fpga_candidate(detections)

    @staticmethod
    def _last_observation(row: dict[str, object]) -> dict[str, object]:
        return dict(row, state="Sinyal yok", stateKey="stale", observed=False)

    def _cluster_live_detection_rows(
        self, detections: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Collapse peak wander into one operator-visible current emission."""
        confirmed = sorted(
            (
                row for row in detections
                if row["stateKey"] == "confirmed" and bool(row["observed"])
            ),
            key=lambda row: float(row["frequencyHz"]),
        )
        groups: list[list[dict[str, object]]] = []
        for row in confirmed:
            frequency_hz = float(row["frequencyHz"])
            if groups and frequency_hz - float(groups[-1][0]["frequencyHz"]) <= LIVE_PRESENTATION_CLUSTER_HZ:
                groups[-1].append(row)
            else:
                groups.append([row])

        clustered: list[dict[str, object]] = []
        for group in groups:
            representative = max(
                group,
                key=lambda row: (float(row["contrastDb"]), int(row["eventRevision"])),
            )
            merged = dict(representative)
            lower_hz = min(float(row["lowerFrequencyHz"]) for row in group)
            upper_hz = max(float(row["upperFrequencyHz"]) for row in group)
            merged.update(
                lowerFrequencyHz=lower_hz,
                upperFrequencyHz=upper_hz,
                startNormalized=self._normalized_live_frequency(lower_hz),
                endNormalized=self._normalized_live_frequency(upper_hz),
                componentCount=len(group),
            )
            clustered.append(merged)

        clustered.sort(
            key=lambda row: (-float(row["contrastDb"]), -int(row["eventRevision"]), float(row["frequencyHz"]))
        )
        clustered.extend(
            row for row in detections
            if row["stateKey"] != "confirmed" or not bool(row["observed"])
        )
        return clustered

    def _update_live_detection_history(self, detections: list[dict[str, object]]) -> None:
        for retained in self._live_detection_history:
            retained.update(observed=False, state="Son görüldü", stateKey="stale")
        for row in detections:
            if row["stateKey"] != "confirmed" or not row["observed"]:
                continue
            frequency_hz = float(row["frequencyHz"])
            lower_hz = float(row["lowerFrequencyHz"])
            upper_hz = float(row["upperFrequencyHz"])
            matched = None
            for retained in self._live_detection_history:
                retained_lower = float(retained["lowerFrequencyHz"])
                retained_upper = float(retained["upperFrequencyHz"])
                tolerance = LIVE_PRESENTATION_CLUSTER_HZ
                if not (upper_hz < retained_lower or lower_hz > retained_upper) or abs(
                    frequency_hz - float(retained["frequencyHz"])
                ) <= tolerance:
                    matched = retained
                    break
            if matched is None:
                matched = dict(row)
                matched["rowKey"] = f"frequency-{len(self._live_detection_history) + 1}"
                matched["firstSeenFrame"] = self._frame_index
                matched["observationCount"] = 0
                self._live_detection_history.append(matched)
            row_key = matched["rowKey"]
            first_seen = matched["firstSeenFrame"]
            observations = int(matched["observationCount"]) + (0 if row.get("held") else 1)
            state = str(row.get("verificationLabel", "FPGA adayı"))
            if row.get("held"):
                state = "Kısa süreli izleniyor"
            matched.clear()
            matched.update(
                row,
                rowKey=row_key,
                firstSeenFrame=first_seen,
                lastSeenFrame=self._frame_index,
                observationCount=observations,
                state=state,
                stateKey="confirmed",
                observed=True,
            )

    def _refresh_live_detection_list(self, *, force: bool = False) -> None:
        if self._source_mode != "hackrf":
            return
        if self._live_session is None:
            for retained in self._live_detection_history:
                retained.update(observed=False, state="Son görüldü", stateKey="stale")
        current = sorted(
            (
                row for row in self._live_detection_history
                if bool(row["observed"])
                and row.get("verificationKey") not in SUPPRESSED_VERIFICATION_STATES
            ),
            key=lambda row: (-float(row["contrastDb"]), -int(row["lastSeenFrame"])),
        )
        history = sorted(
            (
                row for row in self._live_detection_history
                if not bool(row["observed"])
                and row.get("verificationKey") not in SUPPRESSED_VERIFICATION_STATES
            ),
            key=lambda row: (-int(row["lastSeenFrame"]), -float(row["contrastDb"])),
        )
        ordered = current + history
        for row in ordered:
            row["historyBoundary"] = False
        if history:
            history[0]["historyBoundary"] = True
        self._detections = ordered[:12]
        self._live_list_frame = self._frame_index
        visible_ids = {int(row["eventId"]) for row in self._detections}
        session = self._live_session
        if session is not None and hasattr(session, "measurement_window"):
            for event_id in visible_ids:
                window = tuple(session.measurement_window(event_id))
                if len(window) == 4:
                    self._visible_live_measurement_windows[event_id] = window
                    if event_id == self._selected_detection_id and not self._selected_live_measurement_window:
                        self._selected_live_measurement_window = window
        retained_window_ids = visible_ids | ({self._selected_detection_id} if self._selected_detection_id >= 0 else set())
        self._visible_live_measurement_windows = {
            event_id: window
            for event_id, window in self._visible_live_measurement_windows.items()
            if event_id in retained_window_ids
        }
        self._detection_model.set_rows(self._detections)
        self.detectionsChanged.emit()

    def _update_detections(self, result: RuntimeFrameResult) -> None:
        for event in result.detection.active_events:
            if not event.observed_this_frame:
                continue
            history = self._event_observation_history.setdefault(int(event.event_id), [])
            record = (self._frame_index, True)
            if history and history[-1][0] == self._frame_index:
                history[-1] = record
            else:
                history.append(record)
            del history[:-8]
        visible = sorted(
            result.detection.active_events,
            key=lambda item: (item.state != "confirmed", item.event_id),
        )[:12]
        state_text = {"tentative": "İzleniyor", "confirmed": "Kararlı", "ended": "Sona ermiş"}
        self._detections = [
            {
                "eventId": int(item.event_id),
                "title": f"Tespit #{item.event_id}",
                "frequency": self._format_frequency(item.region.peak_frequency_hz),
                "snr": f"{item.region.peak_to_noise_db:.1f} dB",
                "state": state_text[item.state],
                "stateKey": item.state,
                "offsetKHz": (item.region.peak_frequency_hz - result.spectrum.center_frequency_hz) / 1_000.0,
                "startNormalized": self._normalized_shifted_bin(item.region.start_bin),
                "endNormalized": self._normalized_shifted_bin(item.region.end_bin),
                "peakNormalized": self._normalized_shifted_bin(item.region.peak_bin),
            }
            for item in visible
        ]
        if not any(int(item["eventId"]) == self._selected_detection_id for item in self._detections):
            if self._selected_detection_id >= 0:
                self._clear_listening("Seçili tespit sona erdi; yeni bir tespit seçin.")
            self._selected_detection_id = -1
            self._selected_live_measurement_window = ()
            self._measurement_requested = False
            self._parameter_rows = []
            self._analysis_span = None
            self._analysis_span_draft = None
        self._detection_model.set_rows(self._detections)
        self.detectionsChanged.emit()

    def _clear_results(self, *, keep_source: bool = False) -> None:
        self._last_result = None
        self._direction_frame_power_dbfs = None
        self._spectrum_values = []
        self._spectral_display.clear()
        self._detections = []
        self._detection_model.set_rows([])
        self._live_detection_rows = []
        self._live_detection_history = []
        self._coarse_detection_frame = None
        self._coarse_detection_sequence = -1
        self._coarse_detection_error = ""
        self._selected_live_detection = None
        self._visible_live_measurement_windows.clear()
        self._selected_live_measurement_window = ()
        self._live_list_frame = -1
        self._selected_detection_id = -1
        self._measurement_requested = False
        self._pending_live_measurement = None
        self._pending_live_listening = None
        self._parameter_rows = []
        self._analysis_span = None
        self._analysis_span_draft = None
        self._event_observation_history.clear()
        self._frame_index = 0
        self._reset_direction()
        self._clear_listening("Doğrulanmış bir tespit seçin.")
        if not keep_source:
            self._frame_count = 0
        self.spectrumChanged.emit()
        self.detectionsChanged.emit()
        self.pipelineChanged.emit()
