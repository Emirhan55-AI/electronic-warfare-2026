from app.operator_console.survey_presentation import merge_signal_rows, signal_fields


def row(key, window, peak=826e6, verified_peak=None, width=14000, detected=True):
    return dict(eventId=key, memberIds=[key], windowIndex=window, peakHz=peak,
                verificationPeakHz=peak if verified_peak is None else verified_peak,
                bandwidthHz=width, signalDetected=detected, evidenceKey="dual_tune",
                latestWindow=False, qualityScore=80)


def test_neighbor_duplicates_merge_without_mutating_raw_rows():
    previous = row("a", 209)
    result = merge_signal_rows([row("b", 210, peak=826e6 + 135)], [previous])
    assert len(result) == 1
    assert result[0]["memberIds"] == ["a", "b"]
    assert result[0]["eventId"] == "a"
    assert previous["memberIds"] == ["a"]


def test_close_signals_in_same_window_stay_separate():
    assert len(merge_signal_rows([row("b", 209, peak=826e6 + 400)], [row("a", 209)])) == 2


def test_different_verification_peak_or_wide_energy_cannot_merge():
    for candidate in [row("b", 210, verified_peak=826e6 + 2000),
                      row("b", 210, width=100000), row("b", 210, detected=False),
                      row("b", 213), row("b", 210, peak=826e6 + 2000)]:
        assert len(merge_signal_rows([candidate], [row("a", 209)])) == 2


def test_anchor_prevents_transitive_frequency_drift():
    rows = merge_signal_rows([row("b", 210, peak=826e6 + 700)], [row("a", 209)])
    assert len(merge_signal_rows([row("c", 211, peak=826e6 + 1400)], rows)) == 2


def test_missing_verification_is_not_presented_as_detected():
    fields = signal_fields(dict(key="x", frequency_hz=826e6), 1)
    assert not fields["signalDetected"]
    assert fields["rangeText"] == ""
