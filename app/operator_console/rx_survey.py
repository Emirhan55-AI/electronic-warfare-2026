"""Receive-only frequency survey using the existing, validated card transport."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from typing import Callable

import numpy as np

from algorithms.p0.channelizer import P0ChannelizerProfile
from platforms.acquisition.contracts import AcquisitionError
from .live_ed import (
    LIVE_DEFAULT_LNA_GAIN_DB,
    LIVE_DEFAULT_VGA_GAIN_DB,
    LIVE_OUTPUT_SAMPLE_RATE_HZ,
    LIVE_OUTPUT_SAMPLES_PER_FRAME,
    LiveEDConfiguration,
    LiveEDSession,
    LiveEDSnapshot,
)


MIN_FREQUENCY_HZ = 1_000_000
MAX_FREQUENCY_HZ = 6_000_000_000
# A 1 MHz support can be at most 300 kHz from one tuning center while remaining
# inside the validated +/-800 kHz channelizer passband. Responsibility cells
# therefore advance by 600 kHz; the actual 2 MHz detector windows overlap.
SURVEY_MAX_FULL_SUPPORT_HZ = 1_000_000
SURVEY_CHANNELIZER_PASSBAND_HALF_HZ = P0ChannelizerProfile().passband_edge_hz
SURVEY_RESPONSIBILITY_WIDTH_HZ = 2 * (
    SURVEY_CHANNELIZER_PASSBAND_HALF_HZ - SURVEY_MAX_FULL_SUPPORT_HZ // 2
)
SURVEY_CLUSTER_HZ = 50_000
SURVEY_BROAD_MINIMUM_SPAN_BINS = 257
SURVEY_MIN_OBSERVED_FRAMES = 8
SURVEY_VERIFY_FRAMES = 48
SURVEY_VERIFY_GUARD_FRAMES = 8
SURVEY_VERIFY_MIN_OBSERVED_FRAMES = 8
SURVEY_VERIFY_TUNING_OFFSET_HZ = 2_500_000
SURVEY_MONITOR_CENTER_OFFSET_HZ = 100_000
MAX_WINDOW_OBSERVATIONS = 128
SURVEY_TRANSPORT_ATTEMPTS = 3
ROOT = Path(__file__).resolve().parents[2]
SURVEY_SOURCES = (
    "app/operator_console/rx_survey.py", "app/operator_console/live_ed.py",
    "algorithms/p0/channelizer.py", "algorithms/p0/transport.py",
    "platforms/acquisition/continuous.py",
    "platforms/acquisition/windows_pipe.py", "app/operator_console/survey_controller.py",
    "app/operator_console/quick_view_model.py", "app/operator_console/qml/RxSurveyView.qml",
    "app/operator_console/qml/Main.qml", "scripts/check_rx_survey.py",
    "app/operator_console/spectral_display.py", "app/operator_console/survey_evidence.py",
    "scripts/compare_rx_surveys.py",
    "algorithms/p0/native_channelizer.py", "algorithms/p0/native/channelizer_native.cpp",
)


def survey_gain_profiles(lna_gain_db: int, vga_gain_db: int) -> tuple[tuple[int, int], ...]:
    """Return the requested receive gain followed by conservative fallbacks."""
    profiles = []
    lna, vga = lna_gain_db, vga_gain_db
    while True:
        profile = (lna, vga)
        if not profiles or profiles[-1] != profile:
            profiles.append(profile)
        if profile == (0, 0):
            return tuple(profiles)
        lna = max(0, lna - 8)
        vga = max(0, vga - 8)
        vga -= vga % 2


@dataclass(frozen=True)
class SurveyWindow:
    index: int
    lower_hz: int
    upper_hz: int
    center_hz: int
    include_upper: bool


@dataclass(frozen=True)
class SurveyConfig:
    lower_hz: int = MIN_FREQUENCY_HZ
    upper_hz: int = MAX_FREQUENCY_HZ
    lna_gain_db: int = LIVE_DEFAULT_LNA_GAIN_DB
    vga_gain_db: int = LIVE_DEFAULT_VGA_GAIN_DB
    frames_per_window: int = 128
    guard_frames: int = 8
    operator_condition: str = "unspecified"

    def __post_init__(self):
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (
            self.lower_hz, self.upper_hz, self.frames_per_window, self.guard_frames,
        )):
            raise ValueError("Tarama sınırları tam sayı Hz olmalıdır.")
        if not MIN_FREQUENCY_HZ <= self.lower_hz < self.upper_hz <= MAX_FREQUENCY_HZ:
            raise ValueError("Tarama aralığı 1 MHz–6 GHz içinde olmalıdır.")
        if not 16 <= self.frames_per_window <= 512 or not 8 <= self.guard_frames < self.frames_per_window - 3:
            raise ValueError("Tarama gözlem süresi güvenli sınırların dışında.")
        if self.operator_condition not in {"unspecified", "tx_off_reference", "tx_on_comparison"}:
            raise ValueError("Tarama deney koşulu geçerli değil.")
        # Reuse the actual receive configuration's gain validation.
        LiveEDConfiguration(self.lower_hz, "0" * 32, self.lna_gain_db, self.vga_gain_db)

    def windows(self) -> tuple[SurveyWindow, ...]:
        return tuple(
            SurveyWindow(
                index,
                lower,
                min(lower + SURVEY_RESPONSIBILITY_WIDTH_HZ, self.upper_hz),
                (lower + min(lower + SURVEY_RESPONSIBILITY_WIDTH_HZ, self.upper_hz)) // 2,
                lower + SURVEY_RESPONSIBILITY_WIDTH_HZ >= self.upper_hz,
            )
            for index, lower in enumerate(
                range(self.lower_hz, self.upper_hz, SURVEY_RESPONSIBILITY_WIDTH_HZ)
            )
        )


def _event_frequency_geometry(center_hz: int, event) -> tuple[float, float, float, float]:
    """Return half-bin support bounds, support center and peak in absolute Hz."""
    spacing = LIVE_OUTPUT_SAMPLE_RATE_HZ / LIVE_OUTPUT_SAMPLES_PER_FRAME
    shifted_origin = LIVE_OUTPUT_SAMPLES_PER_FRAME // 2
    lower = center_hz + (event.start_shifted_bin - shifted_origin - 0.5) * spacing
    upper = center_hz + (event.end_shifted_bin - shifted_origin + 0.5) * spacing
    support_center = 0.5 * (lower + upper)
    peak = center_hz + (event.peak_shifted_bin - shifted_origin) * spacing
    return lower, upper, support_center, peak


def _interval_gap_hz(first_lower: float, first_upper: float,
                     second_lower: float, second_upper: float) -> float:
    return max(0.0, first_lower - second_upper, second_lower - first_upper)


def _verification_matches(observation: dict, lower: float, upper: float,
                          support_center: float, peak: float) -> bool:
    """Match narrow candidates by frequency and broad candidates by RF support."""
    observed_lower = float(observation["lower_frequency_hz"])
    observed_upper = float(observation["upper_frequency_hz"])
    observed_width = observed_upper - observed_lower
    candidate_width = upper - lower
    broad_minimum_hz = (
        SURVEY_BROAD_MINIMUM_SPAN_BINS
        * LIVE_OUTPUT_SAMPLE_RATE_HZ
        / LIVE_OUTPUT_SAMPLES_PER_FRAME
    )
    if max(observed_width, candidate_width) < broad_minimum_hz:
        return abs(peak - float(observation["peak_frequency_hz"])) <= SURVEY_CLUSTER_HZ
    overlap = max(0.0, min(observed_upper, upper) - max(observed_lower, lower))
    smaller_width = min(observed_width, candidate_width)
    if smaller_width <= 0.0 or overlap / smaller_width < 0.5:
        return False
    return abs(support_center - float(observation["frequency_hz"])) <= max(
        SURVEY_CLUSTER_HZ, 0.5 * max(observed_width, candidate_width)
    )


@dataclass(frozen=True)
class SurveyUpdate:
    window: SurveyWindow
    state: str
    elapsed_seconds: float
    observations: tuple[dict, ...] = ()
    snapshot: LiveEDSnapshot | None = None
    error_code: str = ""
    display_snapshots: tuple[LiveEDSnapshot, ...] = ()
    prepared_spectrum: object | None = None
    window_metrics: dict | None = None
    screened_observations: tuple[dict, ...] = ()


@dataclass(frozen=True)
class SurveyResult:
    state: str
    total_windows: int
    completed_windows: int
    failed_windows: int
    elapsed_seconds: float
    audit_path: str
    error_code: str = ""


class RXSurvey:
    """One pass; an RF window counts only after its complete RX/card run passes.

    Each window has a fresh channelizer and TCP connection. The existing board
    bridge resets temporal state on the first request of every connection. RF
    observations are historical, not an assertion of continuously active emitters.
    """

    def __init__(self, executable: str, serial: str, config: SurveyConfig, audit_path: Path,
                 *, session_factory=LiveEDSession):
        self.executable = executable
        self.serial = serial
        self.config = config
        self.audit_path = Path(audit_path)
        self._session_factory = session_factory
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._active = None

    def cancel(self):
        self._cancel.set()
        with self._lock:
            active = self._active
        if active is not None:
            active.cancel()

    def _verify_observation(self, observation: dict) -> dict | None:
        target_hz = int(round(observation["frequency_hz"]))
        input_center_hz = target_hz + SURVEY_VERIFY_TUNING_OFFSET_HZ
        if input_center_hz > MAX_FREQUENCY_HZ:
            input_center_hz = target_hz - SURVEY_VERIFY_TUNING_OFFSET_HZ
        requested_lna = int(observation.get("lna_gain_db", self.config.lna_gain_db))
        requested_vga = int(observation.get("vga_gain_db", self.config.vga_gain_db))
        last_gain_error = None
        retry_evidence = []
        for lna_gain_db, vga_gain_db in survey_gain_profiles(requested_lna, requested_vga):
            gain_saturated = False
            for transport_attempt in range(1, SURVEY_TRANSPORT_ATTEMPTS + 1):
                snapshot_count = 0
                observed_centers = []
                observed_peaks = []
                observed_lowers = []
                observed_uppers = []
                observed_peak_powers = []
                latest_event = None
                latest_iq_sha256 = ""

                def accept(snapshot):
                    nonlocal snapshot_count, latest_event, latest_iq_sha256
                    if snapshot.sequence_number != snapshot_count:
                        raise AcquisitionError("survey_sequence", "Doğrulama kare sırası bozuldu.")
                    if snapshot.output_frame.center_frequency_hz != target_hz:
                        raise AcquisitionError("survey_frequency", "Doğrulama karesi başka frekansa ait.")
                    snapshot_count += 1
                    if snapshot.sequence_number < SURVEY_VERIFY_GUARD_FRAMES:
                        return
                    candidates = []
                    for event in snapshot.response.active:
                        if event.state != "confirmed" or not event.observed_this_frame:
                            continue
                        lower, upper, center, peak = _event_frequency_geometry(target_hz, event)
                        if _verification_matches(observation, lower, upper, center, peak):
                            candidates.append((abs(center - observation["frequency_hz"]),
                                               lower, upper, center, peak, event))
                    if not candidates:
                        return
                    _, lower, upper, center, peak, latest_event = min(
                        candidates, key=lambda item: item[0]
                    )
                    observed_lowers.append(lower)
                    observed_uppers.append(upper)
                    observed_centers.append(center)
                    observed_peaks.append(peak)
                    observed_peak_powers.append(float(latest_event.peak_power))
                    latest_iq_sha256 = hashlib.sha256(snapshot.output_frame.payload).hexdigest()

                config = LiveEDConfiguration(
                    target_hz,
                    self.serial,
                    lna_gain_db,
                    vga_gain_db,
                    frame_count=SURVEY_VERIFY_FRAMES,
                    display_interval_frames=1,
                    input_center_frequency_hz_override=input_center_hz,
                )
                session = self._session_factory(self.executable, config)
                with self._lock:
                    self._active = session
                if self._cancel.is_set():
                    session.cancel()
                try:
                    result = session.run(accept)
                except Exception as exc:
                    code = str(getattr(exc, "code", ""))
                    if code == "usb_overrun" and transport_attempt < SURVEY_TRANSPORT_ATTEMPTS:
                        retry_evidence.append({"error_code": code, "attempt": transport_attempt,
                                               "lna_gain_db": lna_gain_db, "vga_gain_db": vga_gain_db})
                        continue
                    if code == "iq_saturation":
                        last_gain_error = exc
                        gain_saturated = True
                        retry_evidence.append({"error_code": code, "attempt": transport_attempt,
                                               "lna_gain_db": lna_gain_db, "vga_gain_db": vga_gain_db})
                        break
                    raise
                if snapshot_count != SURVEY_VERIFY_FRAMES or result.completed_frames != snapshot_count:
                    raise AcquisitionError("survey_incomplete_window", "Aday doğrulama penceresi eksik işlendi.")
                if self._cancel.is_set():
                    raise AcquisitionError("operation_cancelled", "Tarama durduruldu.")
                if len(observed_centers) < SURVEY_VERIFY_MIN_OBSERVED_FRAMES:
                    return None
                verified = dict(observation)
                verified["verification"] = {
                    "input_center_hz": input_center_hz,
                    "output_center_hz": target_hz,
                    "observed_frames": len(observed_centers),
                    "frequency_hz": sum(observed_centers) / len(observed_centers),
                    "peak_frequency_hz": sum(observed_peaks) / len(observed_peaks),
                    "mean_peak_power": sum(observed_peak_powers) / len(observed_peak_powers),
                    "lower_frequency_hz": sum(observed_lowers) / len(observed_lowers),
                    "upper_frequency_hz": sum(observed_uppers) / len(observed_uppers),
                    "bandwidth_hz": (
                        sum(observed_uppers) / len(observed_uppers)
                        - sum(observed_lowers) / len(observed_lowers)
                    ),
                    "lna_gain_db": lna_gain_db,
                    "vga_gain_db": vga_gain_db,
                    "retries": retry_evidence,
                    "event": asdict(latest_event) if latest_event is not None else None,
                    "iq_sha256": latest_iq_sha256,
                    "result": asdict(result),
                }
                return verified
            if not gain_saturated:
                break
        if last_gain_error is not None:
            raise last_gain_error
        return None

    def run(self, callback: Callable[[SurveyUpdate], None] | None = None) -> SurveyResult:
        windows = self.config.windows()
        started = time.monotonic()
        good = bad = 0
        final_state, final_error = "completed", ""
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite another physical observation.
        with self.audit_path.open("x", encoding="utf-8") as audit:
            def record(document):
                audit.write(json.dumps(document, ensure_ascii=False, allow_nan=False) + "\n")
                audit.flush()

            record({"type": "begin", "schema": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "config": asdict(self.config), "serial": self.serial,
                    # This application never transmits.  The separate operator
                    # condition records the state of an external lab transmitter.
                    "transmit_enabled": False, "receiver_transmit_enabled": False,
                    "operator_declared_external_tx": self.config.operator_condition,
                    "total_windows": len(windows), "source_sha256": {
                        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SURVEY_SOURCES
                    }})
            for window in windows:
                if self._cancel.is_set():
                    final_state = "cancelled"
                    break
                observations: dict[int, dict] = {}
                latest = None
                snapshot_count = 0
                channel_power_sum = 0
                channel_power_components = 0
                window_started = time.monotonic()
                record({"type": "window_start", "window": asdict(window)})
                if callback:
                    callback(SurveyUpdate(window, "running", time.monotonic() - started))

                def accept(snapshot):
                    nonlocal latest, snapshot_count, channel_power_sum, channel_power_components
                    if snapshot.sequence_number != snapshot_count:
                        raise AcquisitionError("survey_sequence", "Tarama kare sırası bozuldu.")
                    if snapshot.output_frame.center_frequency_hz != window.center_hz:
                        raise AcquisitionError("survey_frequency", "Tarama karesi başka frekansa ait.")
                    snapshot_count += 1
                    latest = snapshot
                    if snapshot.sequence_number < self.config.guard_frames:
                        return
                    components = np.frombuffer(snapshot.output_frame.payload, dtype=np.int8).astype(np.int16)
                    channel_power_sum += int(np.square(components, dtype=np.int32).sum(dtype=np.int64))
                    channel_power_components += int(components.size)
                    if snapshot.sequence_number % 16 == 15 or snapshot_count == self.config.frames_per_window:
                        display_snapshots.append(snapshot)
                        if callback:
                            callback(SurveyUpdate(window, "preview", time.monotonic() - started, snapshot=snapshot))
                    frame_candidates = []
                    for event in snapshot.response.active:
                        if event.state != "confirmed" or not event.observed_this_frame:
                            continue
                        lower, upper, center, peak = _event_frequency_geometry(window.center_hz, event)
                        if center < window.lower_hz or center > window.upper_hz or (
                            center == window.upper_hz and not window.include_upper
                        ):
                            continue
                        frame_candidates.append((lower, upper, center, peak, event))

                    groups = []
                    for candidate in sorted(frame_candidates, key=lambda item: item[0]):
                        if not groups or candidate[0] - max(item[1] for item in groups[-1]) > SURVEY_CLUSTER_HZ:
                            groups.append([])
                        groups[-1].append(candidate)

                    for group in groups:
                        group_lower = min(item[0] for item in group)
                        group_upper = max(item[1] for item in group)
                        group_frequency = 0.5 * (group_lower + group_upper)
                        representative = max(
                            (item[4] for item in group),
                            key=lambda event: (
                                event.peak_to_noise_db if event.peak_to_noise_db == event.peak_to_noise_db else -1.0,
                                event.seen_count,
                            ),
                        )
                        group_peak = next(item[3] for item in group if item[4] is representative)
                        matching = [
                            (_interval_gap_hz(
                                float(row["lower_frequency_hz"]),
                                float(row["upper_frequency_hz"]),
                                group_lower,
                                group_upper,
                            ), key)
                            for key, row in observations.items()
                            if _interval_gap_hz(
                                float(row["lower_frequency_hz"]),
                                float(row["upper_frequency_hz"]),
                                group_lower,
                                group_upper,
                            ) <= SURVEY_CLUSTER_HZ
                        ]
                        key = min(matching)[1] if matching else len(observations)
                        if key not in observations:
                            if len(observations) >= MAX_WINDOW_OBSERVATIONS:
                                raise AcquisitionError("survey_observation_limit", "Pencere gözlem sınırı aşıldı.")
                            observations[key] = {
                                "key": f"{window.index}:{key}", "frequency_hz": group_frequency,
                                "peak_frequency_hz": group_peak,
                                "lower_frequency_hz": group_lower,
                                "upper_frequency_hz": group_upper,
                                "bandwidth_hz": group_upper - group_lower,
                                "first_frame": snapshot.sequence_number, "observed_frames": 0,
                            }
                        row = observations[key]
                        count = row["observed_frames"]
                        lower_average = (row["lower_frequency_hz"] * count + group_lower) / (count + 1)
                        upper_average = (row["upper_frequency_hz"] * count + group_upper) / (count + 1)
                        row.update(
                            frequency_hz=0.5 * (lower_average + upper_average),
                            peak_frequency_hz=(row["peak_frequency_hz"] * count + group_peak) / (count + 1),
                            lower_frequency_hz=lower_average,
                            upper_frequency_hz=upper_average,
                            bandwidth_hz=upper_average - lower_average,
                            mean_peak_power=(row.get("mean_peak_power", 0.0) * count
                                             + float(representative.peak_power)) / (count + 1),
                            last_frame=snapshot.sequence_number,
                            event=asdict(representative),
                            iq_sha256=hashlib.sha256(snapshot.output_frame.payload).hexdigest(),
                        )
                        row["observed_frames"] = count + 1

                try:
                    result = None
                    selected_lna = self.config.lna_gain_db
                    selected_vga = self.config.vga_gain_db
                    profiles = survey_gain_profiles(selected_lna, selected_vga)
                    for gain_attempt, (lna_gain_db, vga_gain_db) in enumerate(profiles, start=1):
                        gain_saturated = False
                        for transport_attempt in range(1, SURVEY_TRANSPORT_ATTEMPTS + 1):
                            observations = {}
                            latest = None
                            snapshot_count = 0
                            channel_power_sum = 0
                            channel_power_components = 0
                            display_snapshots = []
                            if callback and (gain_attempt > 1 or transport_attempt > 1):
                                callback(SurveyUpdate(window, "running", time.monotonic() - started))
                            config = LiveEDConfiguration(window.center_hz, self.serial,
                                lna_gain_db, vga_gain_db,
                                frame_count=self.config.frames_per_window, display_interval_frames=1)
                            session = self._session_factory(self.executable, config)
                            with self._lock:
                                self._active = session
                            if self._cancel.is_set():
                                session.cancel()
                            try:
                                result = session.run(accept)
                            except Exception as exc:
                                code = str(getattr(exc, "code", "survey_failed"))
                                if code == "usb_overrun" and transport_attempt < SURVEY_TRANSPORT_ATTEMPTS:
                                    record({"type": "window_transport_retry", "window": asdict(window),
                                            "attempt": transport_attempt, "error_code": code,
                                            "lna_gain_db": lna_gain_db, "vga_gain_db": vga_gain_db})
                                    continue
                                if code == "iq_saturation" and gain_attempt < len(profiles):
                                    record({"type": "window_gain_retry", "window": asdict(window),
                                            "attempt": gain_attempt, "error_code": code,
                                            "lna_gain_db": lna_gain_db, "vga_gain_db": vga_gain_db})
                                    gain_saturated = True
                                    break
                                raise
                            selected_lna, selected_vga = lna_gain_db, vga_gain_db
                            break
                        if result is not None and not gain_saturated:
                            break
                    if result is None or snapshot_count != self.config.frames_per_window or result.completed_frames != snapshot_count:
                        raise AcquisitionError("survey_incomplete_window", "Tarama penceresi eksik işlendi.")
                    if self._cancel.is_set():
                        raise AcquisitionError("operation_cancelled", "Tarama durduruldu.")
                    screened = tuple(sorted(
                        (
                            {**item, "lna_gain_db": selected_lna, "vga_gain_db": selected_vga,
                             "input_center_hz": config.input_center_frequency_hz,
                             "output_center_hz": window.center_hz}
                            for item in observations.values()
                        ),
                        key=lambda item: (-item["observed_frames"], item["frequency_hz"]),
                    ))
                    items = tuple(
                        verified
                        for item in screened
                        if item["observed_frames"] >= SURVEY_MIN_OBSERVED_FRAMES
                        for verified in (self._verify_observation(item),)
                        if verified is not None
                    )
                    channel_power_dbfs = (
                        10.0 * math.log10(
                            2.0 * channel_power_sum / channel_power_components / (128.0 * 128.0)
                        )
                        if channel_power_sum > 0 and channel_power_components > 0 else None
                    )
                    window_metrics = {
                        "channel_power_dbfs": channel_power_dbfs,
                        "power_frame_count": self.config.frames_per_window - self.config.guard_frames,
                        "power_component_count": channel_power_components,
                        "lna_gain_db": selected_lna,
                        "vga_gain_db": selected_vga,
                        "input_center_hz": config.input_center_frequency_hz,
                        "output_center_hz": window.center_hz,
                        "sample_rate_hz": LIVE_OUTPUT_SAMPLE_RATE_HZ,
                        "power_reference": "mean_abs_iq_squared_ci8_div128",
                    }
                    # Persist before advertising coverage or observations to the UI.
                    record({"type": "window_complete", "window": asdict(window),
                            "elapsed_seconds": time.monotonic() - window_started,
                            "gain": {"lna_gain_db": selected_lna, "vga_gain_db": selected_vga},
                            "observations": items, "screened_observations": screened,
                            "window_metrics": window_metrics,
                            "result": asdict(result)})
                    good += 1
                    if callback:
                        callback(SurveyUpdate(window, "complete", time.monotonic() - started, items, latest,
                                              display_snapshots=tuple(display_snapshots),
                                              window_metrics=window_metrics,
                                              screened_observations=screened))
                except Exception as exc:
                    code = str(getattr(exc, "code", "survey_failed"))
                    if self._cancel.is_set() or code == "operation_cancelled":
                        final_state = "cancelled"
                        record({"type": "window_cancelled", "window": asdict(window), "error_code": code})
                        break
                    bad += 1
                    record({"type": "window_failed", "window": asdict(window), "error_code": code,
                            "error_type": type(exc).__name__, "error_detail": str(exc)})
                    if callback:
                        callback(SurveyUpdate(window, "failed", time.monotonic() - started, error_code=code))
                    # Clipping invalidates this window, never proves an empty band.
                    # Device/transport/storage faults stop instead of skipping a whole spectrum.
                    if code not in {"iq_saturation", "survey_observation_limit"}:
                        final_state, final_error = "failed", code
                        break
                finally:
                    with self._lock:
                        self._active = None
            if final_state == "completed" and bad:
                final_state = "partial"
            summary = SurveyResult(final_state, len(windows), good, bad, time.monotonic() - started,
                                   str(self.audit_path.resolve()), final_error)
            record({"type": "end", **asdict(summary)})
        return summary
