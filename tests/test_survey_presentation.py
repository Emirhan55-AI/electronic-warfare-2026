from unittest.mock import patch

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


def test_narrow_detection_range_is_visible_with_extra_precision():
    fields = signal_fields(dict(key="x", frequency_hz=1800e6,
                                lower_frequency_hz=1799996643.0664062,
                                upper_frequency_hz=1800003356.9335938,
                                bandwidth_hz=6713.8671875), 1)
    assert fields["rangeText"] == "1799,997–1800,003 MHz"


def test_signal_difference_is_exposed_with_a_user_facing_label():
    fields = signal_fields(dict(key="x", frequency_hz=1800e6,
                                event={"peak_power": 100.0, "noise_power": 1.0}), 1)
    assert fields["signalDifferenceDb"] == 20.0
    assert fields["signalDifferenceText"] == "Sinyal farkı: 20,0 dB"


def test_grouping_retains_suspected_family_and_never_special_cases_target():
    from app.operator_console.survey_presentation import grouped_signal_rows
    rows = [dict(row(str(i), i), frequencyHz=f, continuity=.8)
            for i, f in enumerate([80e6, 120e6, 160e6, 200e6])]
    rows += [dict(row("target", 5, width=800000), frequencyHz=1500e6, continuity=1),
             dict(row("other", 6), frequencyHz=855e6, continuity=.9)]
    result = grouped_signal_rows(rows, {"verified", "candidate", "suspect"})
    headers = {r['groupKey']: r['groupCount'] for r in result if r['isHeader']}
    assert headers == dict(verified=2, candidate=0, suspect=4)
    assert {r['eventId'] for r in result if not r['isHeader']} == {r['eventId'] for r in rows}
    assert [r['eventId'] for r in result if not r['isHeader'] and r['groupKey']=='verified'] == ['target', 'other']
    rows[-1]['continuity'] = 1.1
    result = grouped_signal_rows(rows, {'verified'})
    assert next(r['eventId'] for r in result if not r['isHeader']) == 'other'


def test_three_regular_narrow_lines_are_separated_from_a_broad_candidate():
    from app.operator_console.survey_presentation import grouped_signal_rows
    rows = [dict(row("1800", 1), frequencyHz=1800e6, continuity=.8),
            dict(row("1880", 2), frequencyHz=1880e6, continuity=.8),
            dict(row("1920", 3), frequencyHz=1920e6, continuity=.8),
            dict(row("1863", 4, width=1_006_000), frequencyHz=1863.029e6,
                 continuity=1, signalDifferenceDb=31.47)]
    result = grouped_signal_rows(rows, {"verified", "suspect"})
    headers = {item["groupKey"]: item["groupCount"] for item in result if item["isHeader"]}
    assert headers == {"verified": 1, "candidate": 0, "suspect": 3}
    assert next(item for item in result if item.get("eventId") == "1863")["groupKey"] == "verified"


def test_geometry_and_counter_inconsistency_remain_candidates():
    item = dict(key='x', frequency_hz=1500e6, lower_frequency_hz=1499.5e6,
                upper_frequency_hz=1500.5e6, bandwidth_hz=1e6, observed_frames=120,
                verification=dict(lower_frequency_hz=1499.6e6, upper_frequency_hz=1500.4e6,
                                  bandwidth_hz=.8e6, observed_frames=40))
    assert signal_fields(item, 1)['signalDetected']
    item['observed_frames'] = 121
    assert not signal_fields(item, 1)['signalDetected']
    item['observed_frames'] = 120
    item['verification'].update(lower_frequency_hz=1500e6, upper_frequency_hz=1500e6+1000, bandwidth_hz=1000)
    assert not signal_fields(item, 1)['signalDetected']


def test_user_facing_messages_explain_each_group_without_internal_terms():
    from app.operator_console.survey_presentation import grouped_signal_rows
    base = [dict(row("strong", 1), frequencyHz=1500e6, continuity=1),
            dict(row("candidate", 2, detected=False), frequencyHz=1610e6, continuity=.2),
            dict(row("suspect", 3), frequencyHz=1600e6, continuity=.2),
            dict(row("harm2", 4), frequencyHz=1680e6, continuity=.2),
            dict(row("harm3", 5), frequencyHz=1720e6, continuity=.2),
            dict(row("harm4", 6), frequencyHz=1760e6, continuity=.2)]
    result = grouped_signal_rows(base, {"verified", "candidate", "suspect"})
    headers = {x["groupKey"]: x for x in result if x["isHeader"]}
    assert "İki ayrı alımda görüldü" in headers["verified"]["groupDescription"]
    assert "Tek ölçümde bulundu" in headers["candidate"]["groupDescription"]
    assert "Alıcı kaynaklı olabilir" in headers["suspect"]["groupDescription"]
    rows = [x for x in result if not x["isHeader"]]
    assert next(x for x in rows if x["eventId"] == "strong")["statusText"].startswith("Aynı frekans")
    assert next(x for x in rows if x["eventId"] == "candidate")["statusText"].startswith("Tekrar ölçülmeli")
    assert next(x for x in rows if x["eventId"] == "suspect")["statusText"].startswith("Alıcı kaynaklı")


def test_grouping_sorts_by_signal_difference_without_dropping_weak_rows():
    from app.operator_console.survey_presentation import grouped_signal_rows
    rows = [
        dict(row("weak", 1, detected=False), frequencyHz=1800e6,
             signalDifferenceDb=3.0, signalDifferenceText="Sinyal farkı: 3,0 dB"),
        dict(row("strong", 2, detected=False), frequencyHz=1850e6,
             signalDifferenceDb=22.0, signalDifferenceText="Sinyal farkı: 22,0 dB"),
        dict(row("unknown", 3, detected=False), frequencyHz=1900e6),
    ]
    result = grouped_signal_rows(rows, {"candidate"})
    visible = [item["eventId"] for item in result if not item["isHeader"]]
    assert visible == ["strong", "weak", "unknown"]
    assert next(item for item in result if item["isHeader"] and item["groupKey"] == "candidate")["groupCount"] == 3


def test_running_group_presentation_keeps_first_seen_order() -> None:
    from app.operator_console.survey_presentation import grouped_signal_rows

    rows = [
        dict(row("older", 1), frequencyHz=1850e6, signalDifferenceDb=3.0, displayOrder=0),
        dict(row("stronger", 2), frequencyHz=1800e6, signalDifferenceDb=22.0, displayOrder=1),
    ]
    stable = grouped_signal_rows(rows, {"verified"}, preserve_order=True)
    ranked = grouped_signal_rows(rows, {"verified"})
    assert [item["eventId"] for item in stable if not item["isHeader"]] == ["older", "stronger"]
    assert [item["eventId"] for item in ranked if not item["isHeader"]] == ["stronger", "older"]


def test_running_group_presentation_defers_family_reclassification() -> None:
    from app.operator_console.survey_presentation import grouped_signal_rows

    rows = [
        dict(row(str(index), index), frequencyHz=frequency, displayOrder=index)
        for index, frequency in enumerate([1800e6, 1880e6, 1920e6])
    ]
    running = grouped_signal_rows(rows, {"verified", "suspect"}, preserve_order=True)
    finished = grouped_signal_rows(rows, {"verified", "suspect"})
    assert all(item["groupKey"] == "verified" for item in running if not item["isHeader"])
    assert all(item["groupKey"] == "suspect" for item in finished if not item["isHeader"])


def test_hidden_selection_clears_and_recheck_failure_demotes():
    from app.operator_console.survey_controller import SurveyController
    controller = SurveyController()
    controller._rows = [dict(row('x', 1), frequencyHz=855e6)]
    controller._selected = 'x'
    controller._publish_rows()
    controller.toggleObservationGroup('candidate')
    assert controller.selectedKey == ''
    controller._recheck_update(dict(key='x',state='not_seen',checked_at='now'))
    assert controller.groupedObservationModel.rowCount() == 1
    assert controller.observationGroups[0]['groupCount'] == 0


def test_frequency_export_writes_every_presented_signal_to_project_logs(tmp_path):
    from app.operator_console.survey_controller import SurveyController

    (tmp_path / "app" / "operator_console").mkdir(parents=True)
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").touch()
    controller = SurveyController()
    controller._rows = [
        dict(row("first", 1), frequencyHz=855_123_456.0),
        dict(row("second", 2), frequencyHz=1_500_000_000.0),
    ]

    with (
        patch("app.operator_console.survey_controller.ROOT", tmp_path),
        patch("app.operator_console.survey_controller.datetime") as clock,
    ):
        clock.now.return_value.strftime.return_value = "19_06_08"
        assert controller.exportFrequencies()
        assert controller.exportFrequencies()

    exported = sorted((tmp_path / "Logs").glob("*.txt"))
    assert len(exported) == 2
    assert [path.name for path in exported] == ["19_06_08_1.txt", "19_06_08_2.txt"]
    assert exported[0].read_text(encoding="utf-8").splitlines() == [
        "855,123456 MHz",
        "1500,000000 MHz",
    ]
    assert controller.exportMessage.startswith("2 frekans Logs klasörüne kaydedildi:")


def test_frequency_export_rejects_an_empty_signal_list(tmp_path):
    from app.operator_console.survey_controller import SurveyController

    controller = SurveyController()
    with patch(
        "app.operator_console.survey_controller.QStandardPaths.writableLocation",
        return_value=str(tmp_path),
    ):
        assert not controller.exportFrequencies()

    assert controller.exportMessage == "Aktarılacak frekans bulunamadı."
    assert list(tmp_path.iterdir()) == []
