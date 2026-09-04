from scripts.evaluate_p0_persistent_weak import evaluate


def test_small_repeatable_evaluation_rejects_noise_and_finds_all_injections() -> None:
    result = evaluate(trials=2, seed=4040)
    assert result["implementation_status"] == "top8_reference_model_passed"
    assert result["profile"]["maximum_tracked_nominations_per_frame"] == 8
    assert all(row["false_confirmed_windows"] == 0 for row in result["noise_scenarios"])
    assert all(row["confirmed"] for row in result["frequency_invariance"])
    assert all(
        abs(row["detected_shifted_bin"] - row["injected_shifted_bin"]) <= 2
        for row in result["frequency_invariance"]
    )
