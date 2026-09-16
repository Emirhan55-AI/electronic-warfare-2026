from datetime import datetime, timezone
from contextlib import contextmanager
import json
import sqlite3

import pytest

from algorithms.p0.transport import InlineParameterField, InlineParameterResult
from app.operator_console.automatic_parameter import AutomaticParameterOutcome
from app.operator_console.parameter_catalog import ParameterCatalog, PowerCalibrationRegistry


@pytest.mark.parametrize("profiles", [None, 7, True, "invalid", {}])
def test_invalid_calibration_profile_container_does_not_crash(tmp_path, profiles):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"schema": "rx-power-calibration-v1", "profiles": profiles}), encoding="utf-8")
    registry = PowerCalibrationRegistry(path)
    assert not registry.valid_document
    catalog = ParameterCatalog(tmp_path / "catalog.sqlite3", path)
    assert catalog.rows() == []


def test_missing_calibration_is_not_a_valid_document(tmp_path):
    assert not PowerCalibrationRegistry(tmp_path / "missing.json").valid_document


def test_catalog_connections_close_and_failed_transaction_rolls_back(tmp_path, monkeypatch):
    connections = []
    connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    catalog = ParameterCatalog(tmp_path / "catalog.sqlite3", tmp_path / "missing.json")
    catalog.rows()
    catalog.export_csv(tmp_path / "export.csv")
    with pytest.raises(RuntimeError):
        with catalog._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS rollback_probe (value INTEGER)")
            connection.execute("INSERT INTO rollback_probe VALUES (1)")
            raise RuntimeError("abort")
    with catalog._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM rollback_probe").fetchone()[0] == 0
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def outcome(event_id: int, power: float) -> AutomaticParameterOutcome:
    field = lambda value: InlineParameterField("valid", value, None)
    result = InlineParameterResult(
        event_id,
        event_id,
        10,
        4,
        field(820_000_000.0 + event_id),
        field(819_990_000.0),
        field(820_010_000.0),
        field(20_000.0),
        field(power),
        field(18.0),
        1.0,
        10.0,
        0.1,
        0.2,
    )
    return AutomaticParameterOutcome(
        event_id,
        event_id,
        820_000_000.0,
        1.0,
        2000,
        2020,
        "valid",
        None,
        result,
    )


def test_catalog_persists_deduplicates_and_sorts_by_dbfs(tmp_path):
    calibration = tmp_path / "calibration.json"
    calibration.write_text('{"schema":"rx-power-calibration-v1","profiles":[]}', encoding="utf-8")
    catalog = ParameterCatalog(tmp_path / "catalog.sqlite3", calibration)
    common = dict(
        session_id="session-a",
        receiver_role="ED_RX_PRIMARY",
        receiver_serial="abcdef1234567890",
        sample_rate_hz=2_000_000,
        lna_gain_db=16,
        vga_gain_db=16,
        output_amplitude_scale=1.0,
    )
    assert catalog.add(outcome(1, -45.0), **common)
    assert catalog.add(outcome(2, -20.0), **common)
    assert not catalog.add(outcome(1, -10.0), **common)
    rows = catalog.rows()
    assert [row["dbfs"] for row in rows] == ["-20.00 dBFS", "-45.00 dBFS"]
    assert rows[0]["lowerEdge"] == "819.990000 MHz"
    assert rows[0]["upperEdge"] == "820.010000 MHz"
    assert rows[0]["snr"] == "18.00 dB"
    assert all(row["dbm"] == "Kalibre değil" for row in rows)
    exported = catalog.export_csv(tmp_path / "export.csv")
    assert exported.read_text(encoding="utf-8-sig").startswith("id,")


def test_catalog_batches_one_gui_delivery_in_one_transaction(tmp_path, monkeypatch):
    catalog = ParameterCatalog(tmp_path / "catalog.sqlite3", tmp_path / "missing.json")
    common = dict(
        session_id="session-batch",
        receiver_role="ED_RX_PRIMARY",
        receiver_serial="abcdef1234567890",
        sample_rate_hz=2_000_000,
        lna_gain_db=16,
        vga_gain_db=16,
        output_amplitude_scale=1.0,
    )
    connections = 0
    connect = catalog._connect

    @contextmanager
    def tracked_connect():
        nonlocal connections
        connections += 1
        with connect() as connection:
            yield connection

    monkeypatch.setattr(catalog, "_connect", tracked_connect)
    assert catalog.add_many((outcome(1, -45.0), outcome(2, -20.0), outcome(1, -10.0)), **common) == 2
    assert connections == 1
    assert [row["dbfs"] for row in catalog.rows()] == ["-20.00 dBFS", "-45.00 dBFS"]


def test_calibration_is_exact_context_and_expiry_bound(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(
        json.dumps(
            {
                "schema": "rx-power-calibration-v1",
                "profiles": [
                    {
                        "profile_id": "lab-1",
                        "receiver_serial": "abcdef1234567890",
                        "sample_rate_hz": 2_000_000,
                        "lna_gain_db": 16,
                        "vga_gain_db": 16,
                        "output_amplitude_scale": 1.0,
                        "minimum_frequency_hz": 800_000_000,
                        "maximum_frequency_hz": 900_000_000,
                        "dbm_minus_dbfs": -12.0,
                        "uncertainty_db": 1.5,
                        "measured_utc": "2026-01-01T00:00:00+00:00",
                        "valid_until_utc": "2027-01-01T00:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    registry = PowerCalibrationRegistry(path)
    valid = registry.apply(
        -30.0,
        receiver_serial="ABCDEF1234567890",
        sample_rate_hz=2_000_000,
        lna_gain_db=16,
        vga_gain_db=16,
        output_amplitude_scale=1.0,
        frequency_hz=820_000_000.0,
        now=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )
    assert valid.status == "calibrated"
    assert valid.power_dbm == -42.0
    amplified = registry.apply(
        -30.0, receiver_serial="abcdef1234567890", sample_rate_hz=2_000_000,
        lna_gain_db=16, vga_gain_db=16, output_amplitude_scale=1.0,
        frequency_hz=820_000_000.0, rf_amplifier=True,
        now=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )
    assert amplified.status == "unavailable"
    assert amplified.power_dbm is None
    mismatch = registry.apply(
        -30.0,
        receiver_serial="abcdef1234567890",
        sample_rate_hz=2_000_000,
        lna_gain_db=24,
        vga_gain_db=16,
        output_amplitude_scale=1.0,
        frequency_hz=820_000_000.0,
        now=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )
    assert mismatch.status == "unavailable"
    assert mismatch.power_dbm is None

    context = dict(receiver_serial="abcdef1234567890", sample_rate_hz=2_000_000,
                   lna_gain_db=16, vga_gain_db=16, output_amplitude_scale=1.0,
                   frequency_hz=820_000_000.0,
                   now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    original = json.loads(path.read_text(encoding="utf-8"))
    for key, value in (("output_amplitude_scale", True), ("profile_id", " "),
                       ("minimum_frequency_hz", -(10 ** 400)),
                       ("dbm_minus_dbfs", 10 ** 400)):
        changed = json.loads(json.dumps(original))
        changed["profiles"][0][key] = value
        path.write_text(json.dumps(changed), encoding="utf-8")
        assert PowerCalibrationRegistry(path).apply(-30.0, **context).power_dbm is None
    original["profiles"].append({**original["profiles"][0], "profile_id": "other",
                                 "dbm_minus_dbfs": 10.0})
    path.write_text(json.dumps(original), encoding="utf-8")
    ambiguous = PowerCalibrationRegistry(path).apply(-30.0, **context)
    assert ambiguous.power_dbm is None
    assert ambiguous.reason == "ambiguous_matching_profiles"
