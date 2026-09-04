from app.operator_console.known_spurs import load_known_spurs


def test_physical_receiver_profiles_load_only_their_own_calibrated_spurs():
    assert load_known_spurs("0000000000000000a32868dc35138247") == (
        1_000_000_000,
    )
    assert load_known_spurs("0000000000000000a32868dc36877e47") == (
        720_000_000,
        760_000_000,
        832_000_000,
        840_000_000,
        1_000_000_000,
        1_040_000_000,
        1_080_000_000,
    )
    assert load_known_spurs("unknown-receiver") == ()
