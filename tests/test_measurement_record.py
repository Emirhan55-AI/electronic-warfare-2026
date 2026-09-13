"""Input integrity, bounded persistence and same-runtime F5 reproduction."""

from dataclasses import replace
import json
from unittest.mock import patch
import zipfile

import numpy as np
import pytest

from algorithms.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.spectrum import SpectrumConfig
from app.operator_console import measurement_record as records


def inputs():
    rng = np.random.default_rng(72026)
    index = np.arange(4096)
    frames = tuple(
        .3 * np.exp(2j * np.pi * 160.25 * index / 4096)
        + .005 * (rng.standard_normal(4096) + 1j * rng.standard_normal(4096))
        for _ in range(4)
    )
    span = AnalysisSpan(2180, 2238, "operator_adjusted", 3)
    candidate = MeasurementCandidate(31, 4, 2205, 2211)
    context = MeasurementContext(5, 5, 5, 31, 4, (True,) * 4, (candidate,))
    return MeasurementIntent(5, 5, 5, 31, 4, 0, span, context), frames


def record(directory, *, frames=None, intent=None):
    default_intent, default_frames = inputs()
    return records.measure_and_record(
        intent or default_intent, frames if frames is not None else default_frames,
        sample_rate_hz=2_000_000, center_frequency_hz=900_000_000,
        spectrum_config=SpectrumConfig(), source={"kind": "test", "session_id": "isolated-test"},
        requested_utc="2026-09-07T00:00:00+00:00", directory=directory,
    )


@pytest.mark.parametrize("mutation", [None, "stale", "mask", "outside", "generation", "ids"])
def test_direction_record_preserves_real_observation_ownership(mutation):
    intent, _ = inputs()
    events = [dict(event_id=event_id, seen_count=4, state="confirmed", observed_this_frame=True,
                   start_shifted_bin=2205, peak_shifted_bin=2208, end_shifted_bin=2211)
              for event_id in (28, 29, 30, 31)]
    intent = replace(intent, context=replace(intent.context, owner_observed_frames=(False, False, False, True)))
    source = {"sequence_numbers": [0, 1, 2, 3], "owner_observations": events,
              "direction_capture": {"binding": "operator_selected_channel_v1", "span": [2180, 2238],
                                    "emitter_identity_verified": False, "fresh_after_operator_request": True,
                                    "host_capture_sequence_floor": -1, "event_ids": [28, 29, 30, 31]}}
    if mutation == "stale":
        source["direction_capture"]["host_capture_sequence_floor"] = 0
    elif mutation == "mask":
        intent = replace(intent, context=replace(intent.context, owner_observed_frames=(True,) * 4))
    elif mutation == "outside":
        events[0]["start_shifted_bin"] = 2000
    elif mutation == "generation":
        intent = replace(intent, source_generation=99)
    elif mutation == "ids":
        source["direction_capture"]["event_ids"] = [31] * 4
    if mutation is None:
        records.validate_measurement_ownership(intent, source)
    else:
        with pytest.raises(ValueError):
            records.validate_measurement_ownership(intent, source)


def test_parameter_record_accepts_changed_ids_only_with_fresh_channel_binding():
    intent, _ = inputs()
    events = [dict(event_id=event_id, seen_count=4, state="confirmed", observed_this_frame=True,
                   start_shifted_bin=2205, peak_shifted_bin=2208, end_shifted_bin=2211)
              for event_id in (28, 29, 30, 31)]
    intent = replace(
        intent,
        context=replace(intent.context, owner_observed_frames=(False, False, False, True)),
    )
    source = {
        "sequence_numbers": [0, 1, 2, 3],
        "owner_observations": events,
        "channel_capture": {
            "binding": "operator_selected_channel_v1",
            "span": [2180, 2238],
            "emitter_identity_verified": False,
            "fresh_after_operator_request": True,
            "host_capture_sequence_floor": -1,
            "event_ids": [28, 29, 30, 31],
        },
    }
    records.validate_measurement_ownership(intent, source)
    source["direction_capture"] = dict(source["channel_capture"])
    with pytest.raises(ValueError, match="birden fazla"):
        records.validate_measurement_ownership(intent, source)


def rewrite(source, target, *, alter_document=None, alter_iq=None):
    with zipfile.ZipFile(source) as archive:
        document = json.loads(archive.read("measurement.json"))
        iq = archive.read("iq.cf64_le")
    if alter_document:
        alter_document(document)
    if alter_iq:
        iq = alter_iq(iq)
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("measurement.json", records.json_bytes(document))
        archive.writestr("iq.cf64_le", iq)


def test_record_preserves_exact_input_units_methods_and_reproduces_fields(tmp_path):
    saved = record(tmp_path)
    document, frames = records.read_measurement(saved.path)
    _, original = inputs()
    for expected, actual in zip(original, frames, strict=True):
        np.testing.assert_array_equal(actual, expected)
        assert not actual.flags.writeable
    assert saved.sha256 == records.digest(saved.path.read_bytes())
    assert document["processing_location"] == "host"
    assert document["observation_duration_s"] == .008192
    assert document["bin_spacing_hz"] == 488.28125
    assert document["acquisition_utc"] is None
    assert document["calibration"]["dbm_available"] is False
    assert document["fields"]["channel_power_dbfs"]["unit"] == "dBFS"
    assert document["fields"]["carrier_line_frequency"]["unit"] == "Hz"
    assert len(document["fields"]) == 8
    assert all(field["method_id"] for field in document["fields"].values())
    assert records.replay_measurement(saved.path) == saved.result


def test_no_signal_still_records_quality_reasons_without_numeric_fallback(tmp_path):
    saved = record(tmp_path, frames=tuple(np.zeros(4096, complex) for _ in range(4)))
    document, _ = records.read_measurement(saved.path)
    assert all(field["state"] != "valid" for field in document["fields"].values())
    assert all(field["value"] is None for field in document["fields"].values())
    assert all(field["reason"] for field in document["fields"].values())
    assert records.replay_measurement(saved.path) == saved.result


def test_changed_iq_is_rejected(tmp_path):
    saved = record(tmp_path)
    altered = tmp_path / "altered.zip"
    rewrite(saved.path, altered, alter_iq=lambda data: bytes([data[0] ^ 1]) + data[1:])
    with pytest.raises(ValueError, match="bütünlük"):
        records.replay_measurement(altered)


def test_changed_result_is_rejected_by_independent_recomputation(tmp_path):
    saved = record(tmp_path)
    altered = tmp_path / "altered.zip"
    rewrite(saved.path, altered, alter_document=lambda doc: doc["fields"]["channel_power_dbfs"].update(value=999))
    with pytest.raises(ValueError, match="yeniden üretilemedi"):
        records.replay_measurement(altered)


def test_outer_hash_detects_receiver_metadata_change(tmp_path):
    saved = record(tmp_path)
    altered = tmp_path / "altered.zip"
    rewrite(saved.path, altered, alter_document=lambda doc: doc["source"].update(session_id="another-session"))
    with pytest.raises(ValueError, match="dış özeti"):
        records.replay_measurement(altered, expected_sha256=saved.sha256)


def test_archive_reader_rejects_oversized_uncompressed_input(tmp_path):
    path = tmp_path / "oversized.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("measurement.json", "{}")
        archive.writestr("iq.cf64_le", bytes(records.IQ_BYTES + 1))
    with pytest.raises(ValueError, match="açılmış boyutları"):
        records.read_measurement(path)


def test_historical_runtime_is_not_relabelled_as_current(tmp_path):
    saved = record(tmp_path)
    altered = tmp_path / "altered.zip"
    rewrite(saved.path, altered, alter_document=lambda doc: doc["runtime"].update(profile_sha256="0" * 64))
    with pytest.raises(ValueError, match="farklı kaynak"):
        records.replay_measurement(altered)


def test_write_failure_does_not_return_measurement_or_leave_partial_archive(tmp_path):
    with patch.object(zipfile.ZipFile, "writestr", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            record(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_id_collision_cannot_replace_a_previous_record(tmp_path):
    saved = record(tmp_path)
    before = saved.path.read_bytes()
    with patch.object(records, "uuid4", return_value=type("ID", (), {"hex": saved.path.stem})()):
        with pytest.raises(FileExistsError):
            record(tmp_path)
    assert saved.path.read_bytes() == before


def test_rejects_nonfinite_input_before_creating_any_record(tmp_path):
    _, frames = inputs()
    frames[0][0] = complex(float("nan"), 0)
    with pytest.raises(ValueError, match="sonlu olmayan"):
        record(tmp_path, frames=frames)
    assert not list(tmp_path.iterdir())


def test_runtime_change_during_measurement_prevents_publication(tmp_path):
    binding = records.runtime_binding()
    with patch.object(records, "runtime_binding", side_effect=[binding, {**binding, "numpy_version": "different"}]):
        with pytest.raises(ValueError, match="sırasında"):
            record(tmp_path)
    assert not list(tmp_path.iterdir())


def test_missing_event_ownership_does_not_publish_valid_fields(tmp_path):
    intent, _ = inputs()
    saved = record(tmp_path, intent=replace(intent, context=None))
    document, _ = records.read_measurement(saved.path)
    assert all(field["state"] != "valid" for field in document["fields"].values())
    assert records.replay_measurement(saved.path) == saved.result
