from datetime import datetime, timezone
import json

from algorithms.p0.transport import InlineParameterField, InlineParameterResult
from app.operator_console.automatic_parameter import AutomaticParameterOutcome
from app.operator_console.parameter_catalog import ParameterCatalog, PowerCalibrationRegistry


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
