"""Noncoherent multi-frame evidence for weak, persistent RX candidates.

This host stage nominates and verifies receive candidates.  It never changes
the FPGA OS-CFAR decision and must be presented as RX evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import numpy.typing as npt


INTEGRATED_MIN_FRAMES = 32
INTEGRATED_THRESHOLD_DB = 6.0
INTEGRATED_MIN_OCCUPANCY = 0.75
INTEGRATED_REFERENCE_INNER_HZ = 50_000.0
INTEGRATED_REFERENCE_OUTER_HZ = 250_000.0
INTEGRATED_CLUSTER_HZ = 50_000.0
INTEGRATED_COMPONENT_GAP_HZ = 5_000.0
INTEGRATED_COMPONENT_THRESHOLD_DB = 1.5


@dataclass(frozen=True)
class IntegratedSpectrumCandidate:
    frequency_hz: float
    peak_frequency_hz: float
    lower_frequency_hz: float
    upper_frequency_hz: float
    peak_to_noise_db: float
    observed_frames: int
    total_frames: int
    mean_peak_power: float
    mean_noise_power: float
    component_count: int = 1
    center_method: str = "spectral_peak"

    @property
    def occupancy(self) -> float:
        return self.observed_frames / self.total_frames


def integrated_spectrum_candidates(
    frequencies_hz: npt.ArrayLike,
    frame_power: npt.ArrayLike,
    *,
    lower_hz: float,
    upper_hz: float,
    maximum_candidates: int = 16,
) -> tuple[IntegratedSpectrumCandidate, ...]:
    """Return persistent local maxima from a stack of linear-power spectra."""

    frequencies = np.asarray(frequencies_hz, dtype=np.float64)
    power = np.asarray(frame_power, dtype=np.float64)
    if frequencies.ndim != 1 or power.ndim != 2 or power.shape[1:] != frequencies.shape:
        raise ValueError("Bütünleşik spektrum eş boyutlu frekans ve kare gücü ister.")
    if power.shape[0] < INTEGRATED_MIN_FRAMES:
        return ()
    if not np.all(np.isfinite(frequencies)) or not np.all(np.isfinite(power)) or np.any(power < 0.0):
        raise ValueError("Bütünleşik spektrum sonlu ve negatif olmayan güç ister.")
    if frequencies.size < 3 or np.any(np.diff(frequencies) <= 0.0):
        raise ValueError("Bütünleşik spektrum artan bir frekans ekseni ister.")
    if not math.isfinite(lower_hz) or not math.isfinite(upper_hz) or lower_hz >= upper_hz:
        raise ValueError("Bütünleşik spektrum aralığı geçersizdir.")
    if maximum_candidates < 1:
        raise ValueError("Bütünleşik spektrum aday sınırı pozitif olmalıdır.")

    mean_power = np.mean(power, axis=0)
    in_scope = (frequencies >= lower_hz) & (frequencies <= upper_hz)
    local_maximum = np.zeros(frequencies.size, dtype=np.bool_)
    local_maximum[1:-1] = (
        (mean_power[1:-1] >= mean_power[:-2])
        & (mean_power[1:-1] > mean_power[2:])
    )
    peak_indices = np.flatnonzero(in_scope & local_maximum)
    threshold_ratio = 10.0 ** (INTEGRATED_THRESHOLD_DB / 10.0)
    spacing = float(np.median(np.diff(frequencies)))
    local_noise: dict[int, float] = {}
    seed_indices: set[int] = set()
    for peak_index in peak_indices:
        offset = np.abs(frequencies - frequencies[peak_index])
        reference = (
            (offset >= INTEGRATED_REFERENCE_INNER_HZ)
            & (offset <= INTEGRATED_REFERENCE_OUTER_HZ)
        )
        if np.count_nonzero(reference) < 32:
            continue
        mean_noise = float(np.median(mean_power[reference]))
        local_noise[int(peak_index)] = mean_noise
        mean_peak = float(mean_power[peak_index])
        if mean_noise <= 0.0 or mean_peak < mean_noise * threshold_ratio:
            continue
        frame_noise = np.median(power[:, reference], axis=1)
        observed = int(np.count_nonzero(power[:, peak_index] > frame_noise * threshold_ratio))
        if observed < math.ceil(INTEGRATED_MIN_OCCUPANCY * power.shape[0]):
            continue
        seed_indices.add(int(peak_index))

    if not seed_indices:
        return ()

    # Nomination remains strict: at least one component must cross the 6 dB,
    # 75 % occupancy gate above.  Once nominated, lower-energy persistent
    # side components may describe that emission's geometry.  They cannot
    # create a candidate on their own.  A 5 kHz adjacency rule prevents two
    # unrelated nearby carriers from being averaged into a fabricated centre;
    # the 50 kHz cap bounds the narrow-emission interpretation.
    component_ratio = 10.0 ** (INTEGRATED_COMPONENT_THRESHOLD_DB / 10.0)
    component_indices = [
        int(index) for index in peak_indices
        if local_noise.get(int(index), 0.0) > 0.0
        and mean_power[index] > local_noise[int(index)] * component_ratio
    ]
    clusters: list[list[int]] = []
    for index in component_indices:
        if (
            not clusters
            or frequencies[index] - frequencies[clusters[-1][-1]] > INTEGRATED_COMPONENT_GAP_HZ
            or frequencies[index] - frequencies[clusters[-1][0]] > INTEGRATED_CLUSTER_HZ
        ):
            clusters.append([])
        clusters[-1].append(index)

    merged: list[IntegratedSpectrumCandidate] = []
    for cluster in clusters:
        cluster_seeds = [index for index in cluster if index in seed_indices]
        if not cluster_seeds:
            continue
        strongest_index = max(
            cluster_seeds,
            key=lambda index: mean_power[index] / local_noise[index],
        )
        strongest_noise = local_noise[strongest_index]
        strongest_power = float(mean_power[strongest_index])
        frame_offset = np.abs(frequencies - frequencies[strongest_index])
        frame_reference = (
            (frame_offset >= INTEGRATED_REFERENCE_INNER_HZ)
            & (frame_offset <= INTEGRATED_REFERENCE_OUTER_HZ)
        )
        frame_noise = np.median(power[:, frame_reference], axis=1)
        observed = int(np.count_nonzero(
            power[:, strongest_index] > frame_noise * threshold_ratio
        ))
        weights = np.asarray([
            max(float(mean_power[index]) - local_noise[index], 0.0)
            for index in cluster
        ], dtype=np.float64)
        peaks = frequencies[np.asarray(cluster, dtype=np.int64)]
        if len(cluster) == 1:
            center = float(peaks[0])
        else:
            center = (
                float(np.average(peaks, weights=weights))
                if float(weights.sum()) > 0.0 else float(np.mean(peaks))
            )
        merged.append(IntegratedSpectrumCandidate(
            frequency_hz=center,
            peak_frequency_hz=float(frequencies[strongest_index]),
            lower_frequency_hz=float(frequencies[cluster[0]] - spacing / 2.0),
            upper_frequency_hz=float(frequencies[cluster[-1]] + spacing / 2.0),
            peak_to_noise_db=10.0 * math.log10(strongest_power / strongest_noise),
            observed_frames=observed,
            total_frames=int(power.shape[0]),
            mean_peak_power=strongest_power,
            mean_noise_power=strongest_noise,
            component_count=len(cluster),
            center_method=(
                "persistent_component_centroid" if len(cluster) > 1
                else "spectral_peak"
            ),
        ))

    retained = sorted(
        merged,
        key=lambda row: (-row.peak_to_noise_db, -row.component_count, row.frequency_hz),
    )[:maximum_candidates]
    return tuple(sorted(retained, key=lambda row: row.frequency_hz))


def integrated_candidate_near(
    frequencies_hz: npt.ArrayLike,
    frame_power: npt.ArrayLike,
    target_hz: float,
    *,
    tolerance_hz: float = 50_000.0,
) -> IntegratedSpectrumCandidate | None:
    candidates = integrated_spectrum_candidates(
        frequencies_hz,
        frame_power,
        lower_hz=target_hz - tolerance_hz,
        upper_hz=target_hz + tolerance_hz,
        maximum_candidates=4,
    )
    return min(
        candidates,
        key=lambda item: min(
            abs(item.frequency_hz - target_hz),
            abs(item.peak_frequency_hz - target_hz),
        ),
        default=None,
    )
