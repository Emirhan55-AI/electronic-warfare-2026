from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from app.operator_console.rx_survey import SurveyConfig
from app.operator_console.survey_evidence import (
    channel_power_delta_db, classify_against_reference,
    compare_completed_surveys, observations_match, single_survey_energy_regions,
)


def _result(frames):
    return {
        "completed_frames": frames, "fpga_enabled": True,
        "input_saturated_components": 0, "output_saturated_components": 0,
        "hackrf_statistics": {"frames_received": frames, "overruns": 0,
                              "longest_overrun_bytes": 0, "process_returncode": 0},
        "transport_statistics": {"frames_sent": frames, "frames_received": frames,
                                 "crc_errors": 0, "sequence_errors": 0,
                                 "queue_drops": 0, "last_error": None},
    }


def _metrics(center=1_299_700_000, power=-60.0):
    return {
        "channel_power_dbfs": power, "power_frame_count": 120,
        "power_component_count": 120 * 8192, "lna_gain_db": 32, "vga_gain_db": 32,
        "input_center_hz": center - 1_500_000, "output_center_hz": center,
        "sample_rate_hz": 2_000_000, "power_reference": "mean_abs_iq_squared_ci8_div128",
    }


def _observation(frequency_hz, *, peak_power=100.0, noise_power=1.0, width_hz=1_500.0):
    return {
        "key": str(frequency_hz), "frequency_hz": frequency_hz, "peak_frequency_hz": frequency_hz,
        "lower_frequency_hz": frequency_hz - width_hz / 2,
        "upper_frequency_hz": frequency_hz + width_hz / 2,
        "bandwidth_hz": width_hz, "observed_frames": 80,
        "lna_gain_db": 32, "vga_gain_db": 32, "mean_peak_power": peak_power,
        "input_center_hz": 1_298_200_000, "output_center_hz": 1_299_700_000,
        "event": {"peak_power": peak_power, "noise_power": noise_power},
        "verification": {"observed_frames": 30, "mean_peak_power": peak_power,
                         "lna_gain_db": 32, "vga_gain_db": 32,
                         "input_center_hz": frequency_hz + 2_500_000,
                         "output_center_hz": frequency_hz, "result": _result(48)},
    }


def _classify(observation, references, **kwargs):
    return classify_against_reference(observation, references, active_window=_metrics(),
                                      reference_window=_metrics(), **kwargs)


def _write(tmp_path, name, observations=(), *, power=-60.0, mutate=None):
    condition = "tx_off_reference" if name.startswith("off") else "tx_on_comparison"
    config = SurveyConfig(1_299_400_000, 1_300_600_000, operator_condition=condition)
    records = [{"type": "begin", "schema": 1, "config": asdict(config),
                "operator_declared_external_tx": condition, "serial": "receiver-1",
                "source_sha256": {"detector.py": "a" * 64}}]
    for window in config.windows():
        records.append({"type": "window_complete", "window": asdict(window),
                        "observations": list(observations) if window.index == 0 else [],
                        "screened_observations": [], "result": _result(128),
                        "window_metrics": _metrics(window.center_hz, power)})
    records.append({"type": "end", "state": "completed", "error_code": "",
                    "completed_windows": 2, "total_windows": 2, "failed_windows": 0})
    if mutate:
        mutate(records)
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
    return path


def test_narrow_observation_needs_close_absolute_rf_frequency():
    reference = _observation(1_300_000_000.0)
    assert observations_match(reference, _observation(1_300_020_000.0))
    assert not observations_match(reference, _observation(1_300_030_000.0))


def test_controlled_reference_separates_persistent_appearing_and_strengthened_features():
    reference = _observation(1_300_000_000.0, peak_power=10.0)
    persistent = _classify(_observation(1_300_001_000.0, peak_power=20.0), [reference])
    appeared = _classify(_observation(1_301_000_000.0), [reference])
    strengthened = _classify(_observation(1_300_001_000.0, peak_power=100.0), [reference])
    assert persistent.state == "present_in_reference"
    assert appeared.state == "appeared_with_tx" and appeared.tx_correlated
    assert strengthened.state == "strengthened_with_tx" and strengthened.tx_correlated
    assert strengthened.peak_delta_db == pytest.approx(10.0)


def test_broad_observations_match_by_support_overlap_even_when_peak_moves():
    first = _observation(100_000_000.0, width_hz=1_000_000.0)
    first["peak_frequency_hz"] = 99_600_000.0
    second = _observation(100_050_000.0, width_hz=900_000.0)
    second["peak_frequency_hz"] = 100_400_000.0
    assert observations_match(first, second)
    assert not observations_match(first, _observation(101_000_000.0, width_hz=900_000.0))


def test_last_frame_spike_or_falling_noise_does_not_prove_power_increase():
    reference = _observation(1_300_000_000.0)
    active = _observation(1_300_000_000.0, noise_power=0.01)
    active["event"]["peak_power"] = 100_000.0
    evidence = _classify(active, [reference])
    assert evidence.state == "present_in_reference"
    assert evidence.contrast_delta_db > 6
    assert evidence.peak_delta_db == 0
    active["mean_peak_power"] = 10_000.0
    assert _classify(active, [reference]).state == "present_in_reference"  # second LO did not rise


def test_gain_change_or_unverified_reference_cannot_be_called_new_signal():
    active = _observation(1_300_000_000.0)
    different_gain = dict(_metrics(), lna_gain_db=24)
    evidence = classify_against_reference(active, [], active_window=different_gain,
                                          reference_window=_metrics())
    assert evidence.state == "incomparable_settings"
    assert channel_power_delta_db(different_gain, _metrics()) is None
    assert _classify(active, [], screened_references=[active]).state == "reference_candidate"


def test_shifted_primary_tuning_cannot_be_called_strengthened():
    reference = _observation(1_300_000_000.0, peak_power=1.0)
    active = _observation(1_300_000_000.0)
    active["input_center_hz"] += 600_000
    active["output_center_hz"] += 600_000
    assert _classify(active, [reference]).state == "present_in_reference"


def test_duplicate_reference_uses_strongest_not_weakest_power():
    active = _observation(1_300_000_000.0)
    refs = [_observation(1_300_000_000.0, peak_power=1), _observation(1_300_000_100.0)]
    assert _classify(active, refs).state == "present_in_reference"


def test_comparison_binds_complete_audits_without_claiming_emitter_identification(tmp_path):
    reference = _write(tmp_path, "off.jsonl", [_observation(1_296_000_000.0)])
    active = _write(tmp_path, "on.jsonl", [_observation(1_296_001_000.0), _observation(1_300_000_000.0)])
    result = compare_completed_surveys(reference, active)
    assert result["tx_correlated_observation_count"] == 1
    assert result["external_emitter_confirmed"] is False
    assert len(result["reference_sha256"]) == len(result["active_sha256"]) == 64
    assert [item["state"] for item in result["observations"]] == ["present_in_reference", "appeared_with_tx"]


def test_channel_power_increase_is_diagnostic_even_without_fpga_candidates(tmp_path):
    result = compare_completed_surveys(_write(tmp_path, "off.jsonl"),
                                        _write(tmp_path, "on.jsonl", power=-51.5))
    assert result["tx_correlated_observation_count"] == 0
    assert result["tx_correlated_energy_window_count"] == 2
    energy = result["energy_windows"][0]
    assert energy["delta_db"] == pytest.approx(8.5)
    assert energy["upper_hz"] - energy["lower_hz"] == 2_000_000
    assert result["external_emitter_confirmed"] is False


def test_single_survey_energy_ranking_requires_local_repeat_support():
    records = []
    for index in range(30):
        center = 1_500_300_000 + index * 600_000
        power = -31.0 if index in {12, 13, 14} else -40.0
        if index == 4:
            power = -30.0  # An isolated transient/window artifact is not ranked.
        records.append({
            "window": {"index": index, "center_hz": center},
            "window_metrics": {"channel_power_dbfs": power},
        })
    regions = single_survey_energy_regions(records)
    assert len(regions) == 1
    assert regions[0]["window_count"] == 3
    assert regions[0]["peak_local_delta_db"] == pytest.approx(9.0)
    assert regions[0]["peak_center_hz"] in {
        records[index]["window"]["center_hz"] for index in (12, 13, 14)
    }


@pytest.mark.parametrize("fault", ["unfinished", "missing_window", "duplicate_window", "missing_frames",
                                  "overrun", "secondary_overrun", "missing_secondary", "condition",
                                  "serial", "source", "config", "power_frames"])
def test_incomplete_or_incompatible_measurements_are_rejected(tmp_path, fault):
    reference = _write(tmp_path, "off.jsonl", [_observation(1_300_000_000.0)])

    def mutate(records):
        if fault == "unfinished":
            records[-1]["state"] = "cancelled"
        elif fault == "missing_window":
            records.pop(2)
        elif fault == "duplicate_window":
            records[2] = records[1]
        elif fault == "missing_frames":
            records[1]["result"]["completed_frames"] = 127
        elif fault == "overrun":
            records[1]["result"]["hackrf_statistics"]["overruns"] = 1
        elif fault == "secondary_overrun":
            records[1]["observations"][0]["verification"]["result"]["hackrf_statistics"]["overruns"] = 1
        elif fault == "missing_secondary":
            records[1]["observations"][0]["verification"].pop("result")
        elif fault == "condition":
            records[0]["operator_declared_external_tx"] = "unspecified"
        elif fault == "serial":
            records[0]["serial"] = "other-receiver"
        elif fault == "source":
            records[0]["source_sha256"]["detector.py"] = "b" * 64
        elif fault == "config":
            records[0]["config"]["lna_gain_db"] = 24
        elif fault == "power_frames":
            records[1]["window_metrics"]["power_component_count"] -= 8192

    active = _write(tmp_path, "on.jsonl", [_observation(1_300_000_000.0)], mutate=mutate)
    with pytest.raises(ValueError):
        compare_completed_surveys(reference, active)


@pytest.mark.parametrize("cancelled", [False, True])
def test_controller_uses_validated_audits_and_demotes_incomplete_comparison(tmp_path, cancelled):
    from PySide6.QtGui import QGuiApplication
    from app.operator_console.rx_survey import SurveyResult, SurveyUpdate
    from app.operator_console.survey_controller import SurveyController
    from app.operator_console.detection_model import DetectionListModel
    app = QGuiApplication.instance() or QGuiApplication(['ab-controller-test'])
    controller = SurveyController()
    reference = _write(tmp_path, 'off.jsonl')
    controller._config = SurveyConfig(1_299_400_000, 1_300_600_000, operator_condition='tx_off_reference')
    controller._serial = 'receiver-1'
    controller._run_condition = 'tx_off_reference'
    controller._complete(SurveyResult('completed',2,2,0,1.0,str(reference)))
    assert controller.referenceReady
    assert controller.reference_matches(controller._config, 'receiver-1')
    assert not controller.reference_matches(controller._config, 'other-receiver')
    controller._run_condition = 'tx_on_comparison'
    controller._windows = controller._config.windows()
    controller._states = [0,0]
    item = _observation(1_300_000_000.0)
    controller._update(SurveyUpdate(controller._windows[0], 'complete', .5, (item,),
                                    window_metrics=_metrics()))
    row = controller.observationModel.data(controller.observationModel.index(0), DetectionListModel.RowRole)
    assert row['evidenceKey'] == 'ab_candidate'
    active = _write(tmp_path,'on.jsonl',[item])
    controller._complete(SurveyResult('cancelled' if cancelled else 'completed',2,2,0,1.0,str(active)))
    if cancelled:
        assert not controller.comparisonAuditPath
        row = controller.observationModel.data(controller.observationModel.index(0), DetectionListModel.RowRole)
        assert row['evidenceKey'] == 'uncertain'
        assert controller.referenceReady  # A retry can reuse the intact off reference.
    else:
        assert controller.comparisonAuditPath
        payload = json.loads(__import__('pathlib').Path(controller.comparisonAuditPath).read_text(encoding='utf-8'))
        assert payload['tx_correlated_observation_count'] == 1
        assert not payload['external_emitter_confirmed']
