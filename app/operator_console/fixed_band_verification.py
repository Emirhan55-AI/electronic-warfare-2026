"""Bounded two-LO verification for fixed-band FPGA candidates.

The verifier never identifies an external transmitter.  It only checks that the
same absolute-RF feature survives two independent HackRF tuning centres while
the FPGA detector and transport integrity checks remain in the loop.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import threading
from typing import Callable

import numpy as np

from algorithms.p0.coarse_detection import CoarseSpectrumDetector
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from platforms.acquisition import decode_ci8
from platforms.acquisition.contracts import AcquisitionError

from .live_ed import (
    LIVE_MAX_TUNING_OFFSET_HZ,
    LIVE_MIN_TUNING_OFFSET_HZ,
    LIVE_OUTPUT_SAMPLE_RATE_HZ,
    LIVE_OUTPUT_SAMPLES_PER_FRAME,
    LIVE_STARTUP_SETTLING_FRAMES,
    LiveEDConfiguration,
    LiveEDSession,
)
from .integrated_spectrum import integrated_candidate_near


FIXED_VERIFY_FRAMES = 96
FIXED_VERIFY_GUARD_FRAMES = 16
FIXED_VERIFY_MIN_OBSERVED_FRAMES = 24
FIXED_VERIFY_MATCH_HZ = 50_000.0
FIXED_VERIFY_RX_MATCH_HZ = 100_000.0
FIXED_VERIFY_RX_MIN_OBSERVED_FRAMES = 48
FIXED_VERIFY_OUTPUT_OFFSETS_HZ = (-300_000, 300_000, -600_000, 600_000)
FIXED_VERIFY_BROAD_MINIMUM_BINS = 257
FIXED_VERIFY_BROAD_MINIMUM_HZ = (
    FIXED_VERIFY_BROAD_MINIMUM_BINS
    * LIVE_OUTPUT_SAMPLE_RATE_HZ
    / LIVE_OUTPUT_SAMPLES_PER_FRAME
)
FIXED_SPUR_MATCH_HZ = 5_000.0
FIXED_SPUR_SHOULDER_INNER_HZ = 2_000.0
FIXED_SPUR_SHOULDER_OUTER_HZ = 25_000.0
FIXED_SPUR_NOISE_INNER_HZ = 50_000.0
FIXED_SPUR_NOISE_OUTER_HZ = 250_000.0
FIXED_SPUR_SHOULDER_THRESHOLD_DB = 3.0
FIXED_SPUR_MIN_SHOULDER_BINS = 8
FIXED_SPUR_NARROW_THRESHOLD_DB = 8.0
FIXED_SPUR_NARROW_MINIMUM_BINS = 2
FIXED_SPUR_NARROW_OCCUPANCY_THRESHOLD_DB = 6.0
FIXED_SPUR_NARROW_MINIMUM_OCCUPANCY = 0.75
# The primary FPGA event only nominates a frequency.  The expensive multi-LO
# check below makes the final decision, so keeping this gate high needlessly
# delays weak but persistent emissions at the edge of the selected channel.
FIXED_PRIMARY_MIN_SEEN_FRAMES = 8
FIXED_PRESENTATION_HOLD_FRAMES = 128
_DEVICE_MIN_HZ = 1_000_000
_DEVICE_MAX_HZ = 6_000_000_000
_PREFERRED_OFFSETS_HZ = (-1_500_000, 2_500_000, 1_500_000, -2_500_000)


@dataclass(frozen=True)
class FixedBandCandidate:
    frequency_hz: float
    peak_frequency_hz: float
    lower_frequency_hz: float
    upper_frequency_hz: float
    peak_to_noise_db: float
    source: str

    def __post_init__(self) -> None:
        values = (
            self.frequency_hz,
            self.peak_frequency_hz,
            self.lower_frequency_hz,
            self.upper_frequency_hz,
            self.peak_to_noise_db,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Sabit bant adayı sonlu sayısal alanlar ister.")
        if not _DEVICE_MIN_HZ <= self.frequency_hz <= _DEVICE_MAX_HZ:
            raise ValueError("Sabit bant adayı alıcı frekans sınırının dışında.")
        if not self.lower_frequency_hz <= self.frequency_hz <= self.upper_frequency_hz:
            raise ValueError("Sabit bant aday desteği merkez frekansını kapsamıyor.")
        if self.source not in {"fpga", "coarse_rx"}:
            raise ValueError("Sabit bant aday kaynağı geçerli değil.")


@dataclass(frozen=True)
class FixedLOObservation:
    input_center_hz: int
    output_center_hz: int
    observed_frames: int
    frequency_hz: float | None
    peak_frequency_hz: float | None
    lower_frequency_hz: float | None
    upper_frequency_hz: float | None
    peak_to_noise_db: float | None
    receiver_observed_frames: int = 0
    receiver_frequency_hz: float | None = None
    receiver_peak_to_noise_db: float | None = None
    receiver_lower_frequency_hz: float | None = None
    receiver_upper_frequency_hz: float | None = None
    spur_guard_required: bool = False
    spur_guard_passed: bool = True
    spur_shoulder_bins: int = 0
    spur_shoulder_peak_to_noise_db: float | None = None


@dataclass(frozen=True)
class FixedBandVerification:
    candidate: FixedBandCandidate
    state: str
    observations: tuple[FixedLOObservation, ...]

    @property
    def verified(self) -> bool:
        return self.state == "verified_two_lo"

    @property
    def verification_method(self) -> str:
        if not self.verified:
            return "none"
        if sum(item.observed_frames >= FIXED_VERIFY_MIN_OBSERVED_FRAMES for item in self.observations) >= 2:
            return "fpga"
        return "receiver"


def _verification_tunings(target_hz: int) -> tuple[tuple[int, int], ...]:
    output_candidates = tuple(
        target_hz + offset_hz for offset_hz in FIXED_VERIFY_OUTPUT_OFFSETS_HZ
    )
    tunings: list[tuple[int, int]] = []
    for output_center_hz in output_candidates:
        if not _DEVICE_MIN_HZ <= output_center_hz <= _DEVICE_MAX_HZ:
            continue
        input_candidates = []
        for offset_hz in _PREFERRED_OFFSETS_HZ:
            input_center_hz = output_center_hz + offset_hz
            distance = abs(offset_hz)
            if not (
                _DEVICE_MIN_HZ <= input_center_hz <= _DEVICE_MAX_HZ
                and LIVE_MIN_TUNING_OFFSET_HZ <= distance <= LIVE_MAX_TUNING_OFFSET_HZ
                and all(input_center_hz != existing[0] for existing in tunings)
            ):
                continue
            input_candidates.append(input_center_hz)
        if input_candidates:
            # Each observation must use a different FPGA output centre as well
            # as a different physical receiver tuning.  Otherwise a spur
            # created after the RF tuner can remain at one absolute output
            # coordinate and falsely pass a nominal "two LO" check.
            input_center_hz = max(
                input_candidates,
                key=lambda value: min(
                    (abs(value - existing[0]) for existing in tunings),
                    default=0,
                ),
            )
            tunings.append((input_center_hz, output_center_hz))
    if len(tunings) < 2:
        raise AcquisitionError(
            "fixed_verification_tuning",
            "Aday için iki bağımsız alıcı ayarı oluşturulamadı.",
        )
    return tuple(tunings)


def known_spur_shoulder_evidence(
    frequencies_hz,
    mean_power,
    spur_frequency_hz: float,
    *,
    power_rows=None,
) -> tuple[bool, int, float]:
    """Qualify persistent modulated energy around a calibrated receiver spur.

    Wide modulation passes through occupied shoulder bins in the averaged
    spectrum.  A narrow emission beside the spur must additionally form a
    contiguous two-bin peak and remain above the per-frame noise estimate in
    at least 75% of the observation window.  The temporal condition prevents a
    single impulse from opening the known-spur guard.
    """

    frequencies = np.asarray(frequencies_hz, dtype=np.float64)
    power = np.asarray(mean_power, dtype=np.float64)
    if frequencies.ndim != 1 or power.shape != frequencies.shape or frequencies.size < 2:
        raise ValueError("Spur yan bant doğrulaması eş boyutlu spektrum dizileri ister.")
    if not np.all(np.isfinite(frequencies)) or not np.all(np.isfinite(power)) or np.any(power < 0.0):
        raise ValueError("Spur yan bant doğrulaması sonlu ve negatif olmayan güç ister.")
    offset = np.abs(frequencies - float(spur_frequency_hz))
    shoulder = (
        (offset > FIXED_SPUR_SHOULDER_INNER_HZ)
        & (offset <= FIXED_SPUR_SHOULDER_OUTER_HZ)
    )
    reference = (
        (offset >= FIXED_SPUR_NOISE_INNER_HZ)
        & (offset <= FIXED_SPUR_NOISE_OUTER_HZ)
    )
    if not np.any(shoulder) or not np.any(reference):
        return False, 0, float("nan")
    noise_power = float(np.median(power[reference]))
    if noise_power <= 0.0:
        return False, 0, float("nan")
    contrast_db = 10.0 * np.log10(np.maximum(power[shoulder], 1e-30) / noise_power)
    qualifying_bins = int(np.count_nonzero(contrast_db > FIXED_SPUR_SHOULDER_THRESHOLD_DB))
    peak_contrast_db = float(np.max(contrast_db))
    if qualifying_bins >= FIXED_SPUR_MIN_SHOULDER_BINS:
        return True, qualifying_bins, peak_contrast_db
    if power_rows is None or peak_contrast_db < FIXED_SPUR_NARROW_THRESHOLD_DB:
        return False, qualifying_bins, peak_contrast_db

    rows = np.asarray(power_rows, dtype=np.float64)
    if (
        rows.ndim != 2
        or rows.shape[1] != power.size
        or rows.shape[0] == 0
        or not np.all(np.isfinite(rows))
        or np.any(rows < 0.0)
    ):
        raise ValueError("Spur zaman doğrulaması sonlu ve eş boyutlu güç kareleri ister.")
    shoulder_indices = np.flatnonzero(shoulder)
    narrow_indices = shoulder_indices[
        contrast_db > FIXED_SPUR_SHOULDER_THRESHOLD_DB
    ]
    if narrow_indices.size < FIXED_SPUR_NARROW_MINIMUM_BINS:
        return False, qualifying_bins, peak_contrast_db
    contiguous = np.split(narrow_indices, np.flatnonzero(np.diff(narrow_indices) > 1) + 1)
    clusters = [
        cluster for cluster in contiguous
        if cluster.size >= FIXED_SPUR_NARROW_MINIMUM_BINS
    ]
    if not clusters:
        return False, qualifying_bins, peak_contrast_db
    frame_noise = np.median(rows[:, reference], axis=1)
    if np.any(frame_noise <= 0.0):
        return False, qualifying_bins, peak_contrast_db
    for cluster in clusters:
        cluster_mean_contrast = 10.0 * np.log10(
            np.maximum(power[cluster], 1e-30) / noise_power
        )
        if float(np.max(cluster_mean_contrast)) < FIXED_SPUR_NARROW_THRESHOLD_DB:
            continue
        cluster_power = np.max(rows[:, cluster], axis=1)
        frame_contrast_db = 10.0 * np.log10(
            np.maximum(cluster_power, 1e-30) / frame_noise
        )
        occupancy = float(np.mean(
            frame_contrast_db >= FIXED_SPUR_NARROW_OCCUPANCY_THRESHOLD_DB
        ))
        if occupancy >= FIXED_SPUR_NARROW_MINIMUM_OCCUPANCY:
            return True, qualifying_bins, peak_contrast_db
    return False, qualifying_bins, peak_contrast_db


def _coarse_matches(candidate: FixedBandCandidate, item) -> bool:
    candidate_broad = _is_broad_support(
        candidate.lower_frequency_hz,
        candidate.upper_frequency_hz,
    )
    item_broad = _is_broad_support(item.lower_frequency_hz, item.upper_frequency_hz)
    if not candidate_broad:
        return abs(item.peak_frequency_hz - candidate.peak_frequency_hz) <= FIXED_VERIFY_RX_MATCH_HZ
    if not item_broad:
        return False
    overlap = max(
        0.0,
        min(candidate.upper_frequency_hz, item.upper_frequency_hz)
        - max(candidate.lower_frequency_hz, item.lower_frequency_hz),
    )
    candidate_width = candidate.upper_frequency_hz - candidate.lower_frequency_hz
    item_width = item.upper_frequency_hz - item.lower_frequency_hz
    smaller = min(candidate_width, item_width)
    return smaller > 0.0 and overlap / smaller >= 0.5


def _is_broad_support(lower_hz: float, upper_hz: float) -> bool:
    return upper_hz - lower_hz >= FIXED_VERIFY_BROAD_MINIMUM_HZ


def fixed_candidate_reference_frequency(
    lower_hz: float,
    upper_hz: float,
    peak_hz: float,
) -> float:
    """Use support centre for broad emissions and the spectral peak for narrow ones."""
    if _is_broad_support(lower_hz, upper_hz):
        return 0.5 * (lower_hz + upper_hz)
    return peak_hz


def _event_geometry(output_center_hz: int, event) -> tuple[float, float, float, float]:
    spacing = LIVE_OUTPUT_SAMPLE_RATE_HZ / LIVE_OUTPUT_SAMPLES_PER_FRAME
    origin = LIVE_OUTPUT_SAMPLES_PER_FRAME // 2
    lower = output_center_hz + (event.start_shifted_bin - origin - 0.5) * spacing
    upper = output_center_hz + (event.end_shifted_bin - origin + 0.5) * spacing
    center = 0.5 * (lower + upper)
    peak = output_center_hz + (event.peak_shifted_bin - origin) * spacing
    return lower, upper, center, peak


def _matches(candidate: FixedBandCandidate, geometry: tuple[float, float, float, float]) -> bool:
    lower, upper, center, peak = geometry
    first_width = candidate.upper_frequency_hz - candidate.lower_frequency_hz
    second_width = upper - lower
    first_broad = first_width >= FIXED_VERIFY_BROAD_MINIMUM_HZ
    second_broad = second_width >= FIXED_VERIFY_BROAD_MINIMUM_HZ
    if not first_broad:
        return abs(peak - candidate.peak_frequency_hz) <= FIXED_VERIFY_MATCH_HZ
    if not second_broad:
        return False
    overlap = max(
        0.0,
        min(candidate.upper_frequency_hz, upper)
        - max(candidate.lower_frequency_hz, lower),
    )
    smaller = min(first_width, second_width)
    return (
        smaller > 0.0
        and overlap / smaller >= 0.5
        and abs(center - candidate.frequency_hz)
        <= max(FIXED_VERIFY_MATCH_HZ, 0.5 * max(first_width, second_width))
    )


def _observation_pair_matches(
    candidate: FixedBandCandidate,
    first: FixedLOObservation,
    second: FixedLOObservation,
    *,
    receiver: bool,
) -> bool:
    if receiver:
        first_frequency = first.receiver_frequency_hz
        second_frequency = second.receiver_frequency_hz
        first_lower = first.receiver_lower_frequency_hz
        first_upper = first.receiver_upper_frequency_hz
        second_lower = second.receiver_lower_frequency_hz
        second_upper = second.receiver_upper_frequency_hz
        tolerance_hz = FIXED_VERIFY_RX_MATCH_HZ
    else:
        first_frequency = first.peak_frequency_hz
        second_frequency = second.peak_frequency_hz
        first_lower = first.lower_frequency_hz
        first_upper = first.upper_frequency_hz
        second_lower = second.lower_frequency_hz
        second_upper = second.upper_frequency_hz
        tolerance_hz = FIXED_VERIFY_MATCH_HZ
    values = (
        first_frequency,
        second_frequency,
        first_lower,
        first_upper,
        second_lower,
        second_upper,
    )
    if any(value is None for value in values):
        return False
    if not _is_broad_support(candidate.lower_frequency_hz, candidate.upper_frequency_hz):
        return abs(float(first_frequency) - float(second_frequency)) <= tolerance_hz
    overlap = max(
        0.0,
        min(float(first_upper), float(second_upper))
        - max(float(first_lower), float(second_lower)),
    )
    smaller_width = min(
        float(first_upper) - float(first_lower),
        float(second_upper) - float(second_lower),
    )
    return smaller_width > 0.0 and overlap / smaller_width >= 0.5


class FixedBandVerifier:
    """Run two short FPGA sessions at distinct physical tuning centres."""

    def __init__(
        self,
        executable: str,
        serial: str,
        lna_gain_db: int,
        vga_gain_db: int,
        *,
        session_factory: Callable = LiveEDSession,
        known_spurs_hz: tuple[int, ...] = (),
        rf_amplifier: bool = False,
    ) -> None:
        self.executable = executable
        self.serial = serial
        self.lna_gain_db = int(lna_gain_db)
        self.vga_gain_db = int(vga_gain_db)
        self.rf_amplifier = rf_amplifier
        self._session_factory = session_factory
        self.known_spurs_hz = tuple(int(value) for value in known_spurs_hz)
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._active = None

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            active = self._active
        if active is not None:
            active.cancel()

    def _observe(
        self,
        candidate: FixedBandCandidate,
        input_center_hz: int,
        output_center_hz: int,
    ) -> FixedLOObservation:
        geometries: list[tuple[float, float, float, float]] = []
        contrasts: list[float] = []
        receiver_frequencies: list[float] = []
        receiver_contrasts: list[float] = []
        receiver_lowers: list[float] = []
        receiver_uppers: list[float] = []
        receiver_power_sum: np.ndarray | None = None
        receiver_power_rows: list[np.ndarray] = []
        receiver_power_frames = 0
        receiver_frequencies_hz: np.ndarray | None = None
        receiver_processor = SpectrumProcessor(SpectrumConfig(frame_length=16_384))
        receiver_detector = CoarseSpectrumDetector()

        def accept(snapshot) -> None:
            if snapshot.sequence_number < FIXED_VERIFY_GUARD_FRAMES:
                return
            matches = []
            for event in snapshot.response.active:
                if event.state != "confirmed" or not event.observed_this_frame:
                    continue
                geometry = _event_geometry(output_center_hz, event)
                if _matches(candidate, geometry):
                    matches.append((abs(geometry[2] - candidate.frequency_hz), geometry, event))
            if not matches:
                return
            _, geometry, event = min(matches, key=lambda item: item[0])
            geometries.append(geometry)
            if math.isfinite(event.peak_to_noise_db):
                contrasts.append(float(event.peak_to_noise_db))

        def accept_preview(preview) -> None:
            nonlocal receiver_power_sum, receiver_power_frames, receiver_frequencies_hz
            if preview.sequence_number < FIXED_VERIFY_GUARD_FRAMES or preview.display_frame is None:
                return
            frame = preview.display_frame
            spectrum = receiver_processor.process(
                decode_ci8(frame.payload, expected_complex_samples=16_384),
                sample_rate_hz=frame.sample_rate_hz,
                center_frequency_hz=frame.center_frequency_hz,
            )
            power = np.asarray(spectrum.display.bin_power_fs2, dtype=np.float64)
            receiver_power_sum = power.copy() if receiver_power_sum is None else receiver_power_sum + power
            receiver_power_rows.append(power.copy())
            receiver_power_frames += 1
            receiver_frequencies_hz = np.asarray(
                spectrum.display.frequency_absolute_hz,
                dtype=np.float64,
            )
            coarse = receiver_detector.process(
                spectrum.display.bin_power_fs2,
                center_frequency_hz=spectrum.center_frequency_hz,
                sample_rate_hz=spectrum.sample_rate_hz,
                sequence_number=preview.sequence_number,
            )
            matches = [
                item for item in coarse.candidates
                if item.state == "confirmed"
                and item.observed_this_frame
                and _coarse_matches(candidate, item)
            ]
            if not matches:
                return
            item = min(matches, key=lambda row: abs(row.peak_frequency_hz - candidate.peak_frequency_hz))
            receiver_frequencies.append(
                fixed_candidate_reference_frequency(
                    float(item.lower_frequency_hz),
                    float(item.upper_frequency_hz),
                    float(item.peak_frequency_hz),
                )
                if _is_broad_support(
                    candidate.lower_frequency_hz,
                    candidate.upper_frequency_hz,
                )
                else float(item.peak_frequency_hz)
            )
            receiver_lowers.append(float(item.lower_frequency_hz))
            receiver_uppers.append(float(item.upper_frequency_hz))
            if math.isfinite(item.peak_to_noise_db):
                receiver_contrasts.append(float(item.peak_to_noise_db))

        config = LiveEDConfiguration(
            output_center_hz,
            self.serial,
            self.lna_gain_db,
            self.vga_gain_db,
            frame_count=FIXED_VERIFY_FRAMES,
            display_interval_frames=1,
            startup_settling_frames=LIVE_STARTUP_SETTLING_FRAMES,
            input_center_frequency_hz_override=input_center_hz,
            rf_amplifier=self.rf_amplifier,
        )
        session = self._session_factory(self.executable, config)
        if hasattr(session, "set_preview_handler"):
            session.set_preview_handler(accept_preview)
        with self._lock:
            self._active = session
        if self._cancelled.is_set():
            session.cancel()
        try:
            result = session.run(accept)
        finally:
            with self._lock:
                self._active = None
        if self._cancelled.is_set():
            raise AcquisitionError("operation_cancelled", "Sabit bant doğrulaması durduruldu.")
        if result.completed_frames != FIXED_VERIFY_FRAMES:
            raise AcquisitionError(
                "fixed_verification_incomplete",
                "Sabit bant doğrulama penceresi eksik işlendi.",
            )
        guarded_spur = next(
            (
                float(spur_hz)
                for spur_hz in self.known_spurs_hz
                if abs(candidate.frequency_hz - spur_hz) <= FIXED_SPUR_MATCH_HZ
            ),
            None,
        )
        spur_guard_required = guarded_spur is not None
        spur_guard_passed = not spur_guard_required
        spur_shoulder_bins = 0
        spur_shoulder_peak_to_noise_db = None
        if (
            guarded_spur is not None
            and receiver_power_sum is not None
            and receiver_power_frames > 0
            and receiver_frequencies_hz is not None
        ):
            (
                spur_guard_passed,
                spur_shoulder_bins,
                spur_shoulder_peak_to_noise_db,
            ) = known_spur_shoulder_evidence(
                receiver_frequencies_hz,
                receiver_power_sum / receiver_power_frames,
                guarded_spur,
                power_rows=np.stack(receiver_power_rows),
            )
        integrated = None
        if receiver_frequencies_hz is not None and receiver_power_rows:
            integrated = integrated_candidate_near(
                receiver_frequencies_hz,
                np.stack(receiver_power_rows),
                candidate.peak_frequency_hz,
                tolerance_hz=FIXED_VERIFY_RX_MATCH_HZ,
            )
        receiver_observed_frames = len(receiver_frequencies)
        receiver_frequency = (
            sum(receiver_frequencies) / len(receiver_frequencies)
            if receiver_frequencies else None
        )
        receiver_contrast = (
            sum(receiver_contrasts) / len(receiver_contrasts)
            if receiver_contrasts else None
        )
        receiver_lower = (
            sum(receiver_lowers) / len(receiver_lowers)
            if receiver_lowers else None
        )
        receiver_upper = (
            sum(receiver_uppers) / len(receiver_uppers)
            if receiver_uppers else None
        )
        if integrated is not None and integrated.observed_frames > receiver_observed_frames:
            receiver_observed_frames = integrated.observed_frames
            receiver_frequency = integrated.frequency_hz
            receiver_contrast = integrated.peak_to_noise_db
            receiver_lower = integrated.lower_frequency_hz
            receiver_upper = integrated.upper_frequency_hz
        if len(geometries) < FIXED_VERIFY_MIN_OBSERVED_FRAMES:
            return FixedLOObservation(
                input_center_hz,
                output_center_hz,
                len(geometries),
                None,
                None,
                None,
                None,
                None,
                receiver_observed_frames,
                receiver_frequency,
                receiver_contrast,
                receiver_lower,
                receiver_upper,
                spur_guard_required,
                spur_guard_passed,
                spur_shoulder_bins,
                spur_shoulder_peak_to_noise_db,
            )
        lower = sum(item[0] for item in geometries) / len(geometries)
        upper = sum(item[1] for item in geometries) / len(geometries)
        center = sum(item[2] for item in geometries) / len(geometries)
        peak = sum(item[3] for item in geometries) / len(geometries)
        contrast = sum(contrasts) / len(contrasts) if contrasts else None
        return FixedLOObservation(
            input_center_hz,
            output_center_hz,
            len(geometries),
            center,
            peak,
            lower,
            upper,
            contrast,
            receiver_observed_frames,
            receiver_frequency,
            receiver_contrast,
            receiver_lower,
            receiver_upper,
            spur_guard_required,
            spur_guard_passed,
            spur_shoulder_bins,
            spur_shoulder_peak_to_noise_db,
        )

    def run(self, candidate: FixedBandCandidate) -> FixedBandVerification:
        target_hz = int(round(candidate.frequency_hz))
        observations = []
        fpga_reproduced: list[FixedLOObservation] = []
        receiver_reproduced: list[FixedLOObservation] = []
        for input_center_hz, output_center_hz in _verification_tunings(target_hz):
            observation = self._observe(candidate, input_center_hz, output_center_hz)
            observations.append(observation)
            if (
                observation.observed_frames >= FIXED_VERIFY_MIN_OBSERVED_FRAMES
                and observation.spur_guard_passed
            ):
                fpga_reproduced.append(observation)
            if (
                observation.receiver_observed_frames >= FIXED_VERIFY_RX_MIN_OBSERVED_FRAMES
                and observation.spur_guard_passed
            ):
                receiver_reproduced.append(observation)
            fpga_pair = any(
                _observation_pair_matches(candidate, previous, observation, receiver=False)
                for previous in fpga_reproduced[:-1]
            ) if fpga_reproduced and fpga_reproduced[-1] is observation else False
            receiver_pair = any(
                _observation_pair_matches(candidate, previous, observation, receiver=True)
                for previous in receiver_reproduced[:-1]
            ) if receiver_reproduced and receiver_reproduced[-1] is observation else False
            if fpga_pair or receiver_pair:
                return FixedBandVerification(candidate, "verified_two_lo", tuple(observations))
        return FixedBandVerification(candidate, "not_reproduced", tuple(observations))
