import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

from algorithms.p0 import MultiscaleDetector, P0_WIDEBAND_RECOVERY_PROFILE


ROOT = Path(__file__).resolve().parents[1]


def test_recovery_span_is_derived_from_the_full_os_window() -> None:
    assert P0_WIDEBAND_RECOVERY_PROFILE.integration_bins == 32
    assert P0_WIDEBAND_RECOVERY_PROFILE.noise_multiplier == 2.5
    assert P0_WIDEBAND_RECOVERY_PROFILE.minimum_span_bins == 41
    assert P0_WIDEBAND_RECOVERY_PROFILE.broad_reference_region_rank == 4
    assert P0_WIDEBAND_RECOVERY_PROFILE.broad_minimum_span_bins == 257


def test_short_regional_proposal_does_not_replace_os_cfar() -> None:
    power = np.ones(4096, dtype=np.float64)
    power[2000:2040] = 100.0

    result = MultiscaleDetector().process(power, frame_id=0)

    assert result.recovery_candidates == ()
    assert result.candidates == result.os_cfar.candidates


def test_qualified_recovery_suppresses_overlapping_os_fragments() -> None:
    power = np.ones(4096, dtype=np.float64)
    power[2200:2300] = 100.0

    result = MultiscaleDetector().process(power, frame_id=0)

    assert result.recovery_candidates
    for recovery in result.recovery_candidates:
        assert recovery.bin_count >= 41
        assert all(
            candidate.end_bin < recovery.start_bin or candidate.start_bin > recovery.end_bin
            for candidate in result.candidates
            if candidate not in result.recovery_candidates
        )


def test_integration_support_is_eroded_before_span_qualification() -> None:
    power = np.ones(4096, dtype=np.float64)
    power[2000:2040] = 100.0

    result = MultiscaleDetector().process(power, frame_id=0)

    assert result.recovery_candidates == ()


@pytest.mark.parametrize("width", (512, 1024, 2048))
def test_flanked_region_order_reference_recovers_medium_and_broad_support(width: int) -> None:
    power = np.ones(4096, dtype=np.float64)
    start = (4096 - width) // 2
    power[start : start + width] = 20.0

    recoveries = MultiscaleDetector().recovery_candidates(power)

    assert any(
        max(0, min(start + width, item.end_bin + 1) - max(start, item.start_bin)) / width >= .9
        for item in recoveries
    )


@pytest.mark.parametrize("family", ("slope", "step"))
def test_flanked_region_order_reference_rejects_colored_noise_edges(family: str) -> None:
    if family == "slope":
        power = np.power(10.0, np.linspace(-6.0, 6.0, 4096) / 10.0)
    else:
        power = np.ones(4096, dtype=np.float64)
        power[2048:] = 10 ** 1.2

    assert MultiscaleDetector().recovery_candidates(power) == ()


@pytest.mark.parametrize(
    "power",
    (
        np.zeros(4095, dtype=np.float64),
        np.full(4096, np.nan, dtype=np.float64),
        np.full(4096, -1.0, dtype=np.float64),
    ),
)
def test_recovery_rejects_invalid_power(power: np.ndarray) -> None:
    with pytest.raises(ValueError):
        MultiscaleDetector().recovery_candidates(power)


def test_physical_evidence_passes_locked_wideband_and_noise_gates() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/multiscale-detector-physical-acceptance.json")
        .read_text(encoding="utf-8")
    )
    wideband = evidence["wideband_positive"]
    noise = evidence["noise_negative"]

    assert evidence["status"] == "passed"
    assert evidence["platform"]["fpga_manager_state"] == "operating"
    assert wideband["four_frame_owner_windows"] >= 1
    assert wideband["minimum_coverage"] >= wideband["required_minimum_coverage"]
    assert wideband["minimum_iou"] >= wideband["required_minimum_iou"]
    assert wideband["maximum_overreach"] <= wideband["required_maximum_overreach"]
    assert noise["recovery_observations"] == 0
    assert noise["confirmed_observed_counts"] == [0] * 10
    assert noise["valid_parameter_fields"] == 0
    assert evidence["current_source_status"] == "superseded_by_adr_0030_pending_rebuild_and_physical_retest"
    commit = evidence["source_commit"]
    for name, expected in evidence["source_sha256"].items():
        directory = "include" if name.endswith(".h") else "src"
        historical = subprocess.run(
            ["git", "show", f"{commit}:platforms/embedded/p0/{directory}/{name}"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout
        assert hashlib.sha256(historical).hexdigest() == expected
