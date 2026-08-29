from __future__ import annotations

import math

import numpy as np
import pytest

from algorithms.p0 import MultiscaleDetector
from algorithms.ps.candidate_transport import decode_packet, encode_packet
from algorithms.rtl.candidate_grouping import CandidateRecord
from algorithms.rtl.p0_candidate_reducer import (
    FIXED_COEFFICIENT_BITS,
    INTEGRATED_THRESHOLD_Q48,
    NOISE_Q48,
    OS_THRESHOLD_Q48,
    REGIONAL_THRESHOLD_Q48,
    architecture_study,
    reduce_candidates,
)
from algorithms.rtl.p0_os_cfar_vectors import p0_os_cfar_vectors


POWER_SCALE = 1 << 30


def _quantize(value: float) -> int:
    return int(math.floor(value * POWER_SCALE + 0.5))


def _floating_candidates(natural_power: tuple[int, ...]) -> tuple[CandidateRecord, ...]:
    shifted = np.asarray(
        [natural_power[index ^ 0x800] for index in range(4096)], dtype=np.float64
    ) / POWER_SCALE
    result = MultiscaleDetector().process(shifted, frame_id=0)
    return tuple(
        CandidateRecord(
            start_shifted_bin=candidate.start_bin,
            end_shifted_bin=candidate.end_bin,
            peak_shifted_bin=candidate.peak_bin,
            peak_power=_quantize(candidate.peak_power),
            regional_noise=_quantize(candidate.noise_power_per_bin),
            threshold=_quantize(candidate.threshold_power),
            pfa_select=1,
            evaluate_center=False,
        )
        for candidate in result.candidates
    )


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    return tuple(shifted[index ^ 0x800] for index in range(4096))


def test_fixed_coefficients_preserve_the_locked_real_values() -> None:
    scale = 1 << FIXED_COEFFICIENT_BITS

    assert abs(OS_THRESHOLD_Q48 / scale - 8.58014304069906) <= 0.5 / scale
    assert abs(NOISE_Q48 / scale - 1.0 / (2.0 * math.log(2.0))) <= 0.5 / scale
    assert abs(REGIONAL_THRESHOLD_Q48 / scale - 5.0 / (4.0 * math.log(2.0))) <= 0.5 / scale
    assert abs(INTEGRATED_THRESHOLD_Q48 / scale - 40.0 / math.log(2.0)) <= 0.5 / scale


def test_reducer_matches_all_locked_os_cfar_frames_and_candidate_metadata() -> None:
    for vector in p0_os_cfar_vectors():
        observed = reduce_candidates(vector.natural_power)

        assert observed.candidates == _floating_candidates(vector.natural_power), vector.vector_id


def test_reducer_recovers_wideband_support_and_reuses_phase06i_packet() -> None:
    baseline = 1 << 30
    shifted = [baseline + ((index * 17) % 101) * 1000 for index in range(4096)]
    for index in range(1200, 1450):
        shifted[index] = 8 << 30
    natural = _natural_from_shifted(shifted)

    result = reduce_candidates(natural)

    assert result.candidates == _floating_candidates(natural)
    assert len(result.recovery_candidates) == 1
    packet = encode_packet(73, result.candidates)
    decoded = decode_packet(packet)
    assert decoded.frame_id == 73
    assert decoded.candidates == result.candidates


def test_reducer_rejects_frames_outside_the_fixed_contract() -> None:
    with pytest.raises(ValueError, match="4096"):
        reduce_candidates([0] * 4095)
    with pytest.raises(ValueError, match="58-bit"):
        reduce_candidates([0] * 4095 + [1 << 58])


def test_architecture_keeps_detection_and_measurement_payloads_separate() -> None:
    study = architecture_study()

    assert study["selected"] == "sparse final-candidate packet for detection frames"
    assert study["full_power_policy"] == "retained only for explicit parameter-measurement frames"
    assert study["requires_dma_overlap"] is True
    assert study["physical_acceptance"] is False
