"""Reproducible evidence levels for receive-only survey observations.

The FPGA temporal detector or explicitly labelled integrated-RX path, followed
by the survey's second-LO check, establishes that a spectral feature is stable
and is not tied to one zero-IF tuning.  Neither path identifies the external
transmitter.  A controlled TX-off/TX-on comparison provides that evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Mapping


NARROW_MATCH_TOLERANCE_HZ = 25_000.0
BROAD_MINIMUM_HZ = 257 * 2_000_000.0 / 4096.0
POWER_CHANGE_THRESHOLD_DB = 6.0
ENERGY_BASELINE_RADIUS_WINDOWS = 10
ENERGY_BASELINE_GUARD_WINDOWS = 2
ENERGY_MINIMUM_REFERENCE_WINDOWS = 6
ENERGY_MINIMUM_ADJACENT_WINDOWS = 2


def _number(item: Mapping[str, object], key: str, default: float = 0.0) -> float:
    value = item.get(key, default)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else default


def observation_peak_hz(item: Mapping[str, object]) -> float:
    return _number(item, "peak_frequency_hz", _number(item, "frequency_hz"))


def observation_interval_hz(item: Mapping[str, object]) -> tuple[float, float]:
    center = _number(item, "frequency_hz")
    lower = _number(item, "lower_frequency_hz", center)
    upper = _number(item, "upper_frequency_hz", center)
    return (min(lower, upper), max(lower, upper))


def observation_contrast_db(item: Mapping[str, object]) -> float | None:
    event = item.get("event")
    if not isinstance(event, Mapping):
        contrast = item.get("peak_to_noise_db")
        return (
            float(contrast)
            if isinstance(contrast, (int, float)) and math.isfinite(float(contrast))
            else None
        )
    peak = _number(event, "peak_power")
    noise = _number(event, "noise_power")
    if peak <= 0.0 or noise <= 0.0:
        return None
    return 10.0 * math.log10(peak / noise)


def observation_peak_db(item: Mapping[str, object]) -> float | None:
    # An individual last-frame maximum is too variable for an A/B power claim.
    peak = _number(item, "mean_peak_power")
    return 10.0 * math.log10(peak) if peak > 0.0 else None


def same_gain(first: Mapping[str, object], second: Mapping[str, object]) -> bool:
    return all(
        isinstance(first.get(key), int) and not isinstance(first[key], bool)
        and first[key] == second.get(key)
        for key in ("lna_gain_db", "vga_gain_db")
    )


def comparable_window(first: Mapping[str, object], second: Mapping[str, object]) -> bool:
    return same_gain(first, second) and all(
        first.get(key) is not None and first[key] == second.get(key)
        for key in ("input_center_hz", "output_center_hz", "sample_rate_hz", "power_reference",
                    "power_frame_count", "power_component_count")
    )


def _require_clean_result(result: Mapping[str, object], frames: int) -> None:
    rx = result.get("hackrf_statistics", {})
    transport = result.get("transport_statistics", {})
    if (result.get("completed_frames") != frames or result.get("fpga_enabled") is not True
            or any(result.get(key) != 0 for key in ("input_saturated_components", "output_saturated_components"))
            or rx.get("frames_received") != frames
            or any(rx.get(key) != 0 for key in ("overruns", "longest_overrun_bytes", "process_returncode"))
            or transport.get("frames_sent") != frames or transport.get("frames_received") != frames
            or any(transport.get(key) != 0 for key in ("crc_errors", "sequence_errors", "queue_drops"))
            or transport.get("last_error") is not None):
        raise ValueError("Taramanın alım/kart bütünlüğü doğrulanamadı.")


def channel_power_delta_db(active: Mapping[str, object], reference: Mapping[str, object]) -> float | None:
    if not comparable_window(active, reference):
        return None
    values = [item.get("channel_power_dbfs") for item in (active, reference)]
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        return None
    return float(values[0]) - float(values[1])


def single_survey_energy_regions(
    windows: Iterable[Mapping[str, object]],
) -> tuple[dict, ...]:
    """Rank local channel-power elevations without claiming an external emitter.

    The FPGA candidate path remains responsible for narrow, low-total-power
    signals.  This complementary path catches broad emissions that raise the
    CFAR reference cells together.  A guarded local median removes slow HackRF
    passband/gain variation; two adjacent 600 kHz responsibility windows and a
    6 dB (four-times-power) rise are required before a region is presented.
    """
    records = sorted(
        (record for record in windows if isinstance(record.get("window"), Mapping)),
        key=lambda record: int(record["window"]["index"]),
    )
    if not records:
        return ()
    powers = []
    for record in records:
        metrics = record.get("window_metrics", {})
        value = metrics.get("channel_power_dbfs") if isinstance(metrics, Mapping) else None
        powers.append(float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None)
    elevations: list[float | None] = []
    for index, power in enumerate(powers):
        references = [
            value
            for other, value in enumerate(powers)
            if value is not None
            and abs(other - index) > ENERGY_BASELINE_GUARD_WINDOWS
            and abs(other - index) <= ENERGY_BASELINE_RADIUS_WINDOWS
        ]
        if power is None or len(references) < ENERGY_MINIMUM_REFERENCE_WINDOWS:
            elevations.append(None)
            continue
        references.sort()
        middle = len(references) // 2
        baseline = (
            references[middle]
            if len(references) % 2 else 0.5 * (references[middle - 1] + references[middle])
        )
        elevations.append(power - baseline)

    groups: list[list[int]] = []
    for index, elevation in enumerate(elevations):
        if elevation is None or elevation < POWER_CHANGE_THRESHOLD_DB:
            continue
        if not groups or index != groups[-1][-1] + 1:
            groups.append([])
        groups[-1].append(index)

    regions = []
    for group in groups:
        if len(group) < ENERGY_MINIMUM_ADJACENT_WINDOWS:
            continue
        peak_index = max(group, key=lambda index: elevations[index] or float("-inf"))
        first_window = records[group[0]]["window"]
        last_window = records[group[-1]]["window"]
        peak_window = records[peak_index]["window"]
        regions.append({
            "first_window_index": int(first_window["index"]),
            "last_window_index": int(last_window["index"]),
            "window_count": len(group),
            "lower_hz": int(first_window["center_hz"]) - 1_000_000,
            "upper_hz": int(last_window["center_hz"]) + 1_000_000,
            "peak_center_hz": int(peak_window["center_hz"]),
            "peak_channel_power_dbfs": float(powers[peak_index]),
            "peak_local_delta_db": float(elevations[peak_index]),
            "threshold_db": POWER_CHANGE_THRESHOLD_DB,
            "state": "single_survey_local_energy_candidate",
        })
    return tuple(sorted(regions, key=lambda item: -item["peak_local_delta_db"]))


def observations_match(first: Mapping[str, object], second: Mapping[str, object]) -> bool:
    """Match the same RF feature across complete, independently tuned surveys."""
    first_lower, first_upper = observation_interval_hz(first)
    second_lower, second_upper = observation_interval_hz(second)
    first_width = first_upper - first_lower
    second_width = second_upper - second_lower
    if max(first_width, second_width) < BROAD_MINIMUM_HZ:
        return abs(observation_peak_hz(first) - observation_peak_hz(second)) <= NARROW_MATCH_TOLERANCE_HZ
    overlap = max(0.0, min(first_upper, second_upper) - max(first_lower, second_lower))
    smaller = min(first_width, second_width)
    if smaller <= 0.0 or overlap / smaller < 0.5:
        return False
    first_center = 0.5 * (first_lower + first_upper)
    second_center = 0.5 * (second_lower + second_upper)
    return abs(first_center - second_center) <= max(
        NARROW_MATCH_TOLERANCE_HZ, 0.5 * max(first_width, second_width)
    )


@dataclass(frozen=True)
class EvidenceClassification:
    state: str
    reference_frequency_hz: float | None = None
    frequency_delta_hz: float | None = None
    peak_delta_db: float | None = None
    contrast_delta_db: float | None = None

    @property
    def tx_correlated(self) -> bool:
        return self.state in {"appeared_with_tx", "strengthened_with_tx"}


def classify_against_reference(
    observation: Mapping[str, object],
    references: Iterable[Mapping[str, object]],
    *,
    active_window: Mapping[str, object],
    reference_window: Mapping[str, object],
    screened_references: Iterable[Mapping[str, object]] = (),
) -> EvidenceClassification:
    if not comparable_window(active_window, reference_window):
        return EvidenceClassification("incomparable_settings")
    matches = [item for item in references if observations_match(observation, item)]
    if not matches:
        if any(observations_match(observation, item) for item in screened_references):
            return EvidenceClassification("reference_candidate")
        return EvidenceClassification("appeared_with_tx")
    # Overlap can yield duplicate observations.  Do not choose a weaker copy to
    # manufacture a positive power change.
    reference = max(matches, key=lambda item: _number(item, "mean_peak_power"))
    frequency_delta = observation_peak_hz(observation) - observation_peak_hz(reference)
    peak = observation_peak_db(observation)
    reference_peak = observation_peak_db(reference)
    contrast = observation_contrast_db(observation)
    reference_contrast = observation_contrast_db(reference)
    peak_delta = peak - reference_peak if same_gain(observation, reference) and peak is not None and reference_peak is not None else None
    contrast_delta = contrast - reference_contrast if contrast is not None and reference_contrast is not None else None
    verification = observation.get("verification", {})
    reference_verification = reference.get("verification", {})
    verified_power = observation_peak_db(verification)
    reference_verified_power = observation_peak_db(reference_verification)
    strengthened = (
        peak_delta is not None and peak_delta >= POWER_CHANGE_THRESHOLD_DB
        and all(observation.get(key) is not None and observation[key] == reference.get(key)
                for key in ("input_center_hz", "output_center_hz"))
        and same_gain(verification, reference_verification)
        and verified_power is not None and reference_verified_power is not None
        and verified_power - reference_verified_power >= POWER_CHANGE_THRESHOLD_DB
    )
    return EvidenceClassification(
        "strengthened_with_tx" if strengthened else "present_in_reference",
        reference_frequency_hz=_number(reference, "frequency_hz"),
        frequency_delta_hz=frequency_delta,
        peak_delta_db=peak_delta,
        contrast_delta_db=contrast_delta,
    )


def load_completed_survey(path: Path) -> tuple[dict, tuple[dict, ...], tuple[dict, ...], dict]:
    from dataclasses import asdict
    from .rx_survey import SurveyConfig

    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records or records[0].get("type") != "begin" or records[-1].get("type") != "end":
        raise ValueError("Tarama kaydı eksik.")
    if records[-1].get("state") != "completed" or records[-1].get("error_code"):
        raise ValueError("Karşılaştırma için iki taramanın da tamamlanmış olması gerekir.")
    if sum(record.get("type") == "begin" for record in records) != 1 or sum(record.get("type") == "end" for record in records) != 1:
        raise ValueError("Tarama başlangıç/bitiş kaydı yinelenmiş.")
    if any(record.get("type") in {"window_failed", "window_cancelled"} for record in records):
        raise ValueError("Hatalı veya iptal edilen pencere karşılaştırılamaz.")
    try:
        config = SurveyConfig(**records[0]["config"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Tarama yapılandırması geçerli değil.") from exc
    expected = config.windows()
    windows = tuple(record for record in records if record.get("type") == "window_complete")
    end = records[-1]
    if (len(windows) != len(expected) or end.get("completed_windows") != len(expected)
            or end.get("total_windows") != len(expected) or end.get("failed_windows") != 0):
        raise ValueError("Taramanın tamamlanan pencere kapsamı eksik.")
    for record, window in zip(windows, expected):
        if record.get("window") != asdict(window):
            raise ValueError("Tarama pencere sırası veya frekans kapsamı değişmiş.")
        if record.get("result", {}).get("completed_frames") != config.frames_per_window:
            raise ValueError("Taramanın tamamlanan kare sayısı eksik.")
        _require_clean_result(record.get("result", {}), config.frames_per_window)
        metrics = record.get("window_metrics", {})
        power_frames = config.frames_per_window - config.guard_frames
        if (metrics.get("power_frame_count") != power_frames
                or metrics.get("power_component_count") != power_frames * 8192
                or metrics.get("output_center_hz") != window.center_hz
                or metrics.get("sample_rate_hz") != 2_000_000
                or metrics.get("power_reference") != "mean_abs_iq_squared_ci8_div128"
                or not comparable_window(metrics, metrics)):
            raise ValueError("Pencere güç ölçümünün kapsamı veya ayar kaydı eksik.")
        for item in record.get("observations", ()):
            verification = item.get("verification", {})
            if item.get("observed_frames", 0) < 8 or verification.get("observed_frames", 0) < 8:
                raise ValueError("Adayın iki LO gözlem kanıtı eksik.")
            _require_clean_result(verification.get("result", {}), 48)
    observations = tuple(
        observation
        for record in records
        if record.get("type") == "window_complete"
        for observation in record.get("observations", ())
    )
    return records[0], observations, windows, records[-1]


def comparable_config(begin: Mapping[str, object]) -> tuple[object, ...]:
    config = begin.get("config")
    if not isinstance(config, Mapping):
        raise ValueError("Tarama yapılandırması bulunamadı.")
    return tuple(config.get(key) for key in (
        "lower_hz", "upper_hz", "lna_gain_db", "vga_gain_db", "frames_per_window", "guard_frames"
    ))


def compare_completed_surveys(reference_path: Path, active_path: Path) -> dict:
    reference_begin, references, reference_windows, reference_end = load_completed_survey(reference_path)
    active_begin, active, active_windows, active_end = load_completed_survey(active_path)
    if comparable_config(reference_begin) != comparable_config(active_begin):
        raise ValueError("TX kapalı ve TX açık taramalar aynı ayarlarla yapılmalıdır.")
    if (reference_begin.get("operator_declared_external_tx") != "tx_off_reference"
            or active_begin.get("operator_declared_external_tx") != "tx_on_comparison"):
        raise ValueError("Harici verici koşulu beyan edilmemiş; eski turlar A/B kanıtı sayılamaz.")
    if not reference_begin.get("serial") or reference_begin["serial"] != active_begin.get("serial"):
        raise ValueError("İki tur aynı alıcıyla yapılmalıdır.")
    if not reference_begin.get("source_sha256") or reference_begin["source_sha256"] != active_begin.get("source_sha256"):
        raise ValueError("İki tur arasında yazılım kaynağı değişmiş.")
    classified = []
    reference_by_index = {int(record["window"]["index"]): record for record in reference_windows}
    screened_references = tuple(item for row in reference_windows for item in row.get("screened_observations", ()))
    for record in active_windows:
        reference_record = reference_by_index[int(record["window"]["index"])]
        for item in record.get("observations", ()):
            evidence = classify_against_reference(
                item, references,
                active_window=record.get("window_metrics", {}),
                reference_window=reference_record.get("window_metrics", {}),
                screened_references=screened_references,
            )
            classified.append({
                "key": item.get("key"),
                "frequency_hz": _number(item, "frequency_hz"),
                "peak_frequency_hz": observation_peak_hz(item),
                "state": evidence.state,
                "reference_frequency_hz": evidence.reference_frequency_hz,
                "frequency_delta_hz": evidence.frequency_delta_hz,
                "peak_delta_db": evidence.peak_delta_db,
                "contrast_delta_db": evidence.contrast_delta_db,
                "observed_frames": int(_number(item, "observed_frames")),
                "verification_frames": int(_number(item.get("verification", {}), "observed_frames")),
            })
    energy_windows = []
    incomparable_windows = []
    for record in active_windows:
        window = record.get("window")
        if not isinstance(window, Mapping):
            continue
        reference_record = reference_by_index.get(int(window["index"]))
        if reference_record is None:
            continue
        active_metrics = record.get("window_metrics")
        reference_metrics = reference_record.get("window_metrics")
        if not isinstance(active_metrics, Mapping) or not isinstance(reference_metrics, Mapping):
            continue
        delta_db = channel_power_delta_db(active_metrics, reference_metrics)
        if delta_db is None:
            incomparable_windows.append(int(window["index"]))
            continue
        if delta_db < POWER_CHANGE_THRESHOLD_DB:
            continue
        energy_windows.append({
            "window_index": int(window["index"]),
            "lower_hz": int(window["center_hz"]) - 1_000_000,
            "upper_hz": int(window["center_hz"]) + 1_000_000,
            "center_hz": int(window["center_hz"]),
            "reference_channel_power_dbfs": float(reference_metrics["channel_power_dbfs"]),
            "active_channel_power_dbfs": float(active_metrics["channel_power_dbfs"]),
            "delta_db": delta_db,
            "state": "channel_power_increased_with_tx",
        })
    correlated_observations = sum(
        item["state"] in {"appeared_with_tx", "strengthened_with_tx"} for item in classified
    )
    return {
        "schema": "phase08-rx-survey-ab-v1",
        "reference_audit": str(Path(reference_path).resolve()),
        "active_audit": str(Path(active_path).resolve()),
        "reference_sha256": hashlib.sha256(Path(reference_path).read_bytes()).hexdigest(),
        "active_sha256": hashlib.sha256(Path(active_path).read_bytes()).hexdigest(),
        "external_emitter_confirmed": False,
        "scope": "Operator-declared off/on comparison; changes are candidates, not emitter identification.",
        "configuration": dict(reference_begin["config"]),
        "reference_completed_windows": reference_end["completed_windows"],
        "active_completed_windows": active_end["completed_windows"],
        "reference_observation_count": len(references),
        "active_observation_count": len(active),
        "tx_correlated_count": correlated_observations + len(energy_windows),
        "tx_correlated_observation_count": correlated_observations,
        "tx_correlated_energy_window_count": len(energy_windows),
        "observations": classified,
        "energy_windows": energy_windows,
        "incomparable_energy_windows": incomparable_windows,
    }
