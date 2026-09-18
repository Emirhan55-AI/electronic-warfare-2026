from __future__ import annotations

import pytest

from algorithms.p0.adaptive_df import AdaptiveDirectionSweep


def test_sweep_brackets_clockwise_then_returns_to_zero_for_counterclockwise_side() -> None:
    sweep = AdaptiveDirectionSweep()
    assert sweep.next_angle() == 0.0

    sweep.record(0.0, -30.0, True)
    for angle, power in ((15.0, -39.0), (30.0, -31.0), (45.0, -29.0)):
        assert sweep.next_angle() == angle
        sweep.record(angle, power, True)

    assert sweep.next_angle() == 60.0
    sweep.record(60.0, -55.0, False)

    assert sweep.phase == "counterclockwise_boundary"
    assert sweep.next_angle() == 345.0
    assert "0° başlangıç yönüne geri" in sweep.instruction_text
    assert "tersine 15°" in sweep.instruction_text


def test_sweep_refines_inside_both_lobe_boundaries_and_checks_opposite() -> None:
    sweep = AdaptiveDirectionSweep()
    for angle, power, observed in (
        (0.0, -30.0, True),
        (15.0, -39.0, True),
        (30.0, -31.0, True),
        (45.0, -29.0, True),
        (60.0, -55.0, False),
        (345.0, -34.0, True),
        (330.0, -42.0, True),
        (315.0, -57.0, False),
    ):
        assert sweep.next_angle() == angle
        sweep.record(angle, power, observed)

    assert sweep.phase == "refinement"
    assert [sweep.next_angle()] == [35.0]
    for angle, power in ((35.0, -30.0), (40.0, -28.0), (50.0, -32.0)):
        assert sweep.next_angle() == angle
        sweep.record(angle, power, True)

    assert sweep.phase == "opposite_check"
    assert sweep.next_angle() == 220.0
    sweep.record(220.0, -60.0, False)
    assert sweep.complete
    assert sweep.next_angle() is None
    assert sweep.progress == 1.0


def test_first_point_must_be_confirmed_zero_and_angles_cannot_repeat() -> None:
    sweep = AdaptiveDirectionSweep()
    with pytest.raises(ValueError, match="0° doğrulanmış"):
        sweep.record(15.0, -30.0, True)
    with pytest.raises(ValueError, match="0° doğrulanmış"):
        sweep.record(0.0, -30.0, False)
    sweep.record(0.0, -30.0, True)
    with pytest.raises(ValueError, match="zaten ölçüldü"):
        sweep.record(360.0, -31.0, True)


def test_all_clockwise_points_seen_fails_closed_without_claiming_completion() -> None:
    sweep = AdaptiveDirectionSweep()
    sweep.record(0.0, -30.0, True)
    for angle in range(15, 360, 15):
        sweep.record(float(angle), -31.0, True)
    assert sweep.phase == "boundary_not_found"
    assert not sweep.complete
    assert sweep.next_angle() is None
    assert "sınır bulunamadı" in sweep.status_text
