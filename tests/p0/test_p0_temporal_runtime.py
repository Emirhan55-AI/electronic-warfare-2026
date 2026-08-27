from scripts.verify_p0_temporal_runtime import verify


def test_os_cfar_to_temporal_runtime_bridge() -> None:
    result = verify()

    assert result["status"] == "passed"
    assert result["frames"] == 5
    assert result["first_confirmation_frame"] == 1
    assert result["expiry_frame"] == 4
    assert result["peak_shifted_bin"] == 2304
    assert result["dropped_candidates"] == 0
    assert result["failure_preserves_previous_result"] is True
