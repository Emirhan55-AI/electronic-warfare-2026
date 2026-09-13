"""Persistent, bounded catalog for automatic parameter observations."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3

from .automatic_parameter import AutomaticParameterOutcome


CATALOG_SCHEMA = "automatic-parameter-catalog-v1"
CALIBRATION_SCHEMA = "rx-power-calibration-v1"
MAXIMUM_CATALOG_ROWS = 10_000
MAXIMUM_DISPLAY_ROWS = 256
MAXIMUM_DETAILS_BYTES = 16_384
STATUS_TEXT = {
    "valid": "Geçerli",
    "not_measurable": "Ölçülemedi",
    "insufficient_quality": "Kalite yetersiz",
    "uncertain": "Belirsiz",
    "not_observed": "Gözlenmedi",
}
REASON_TEXT = {
    "live_span_exceeds_512_bins": "Canlı ölçüm aralığı 512 hücreyi aşıyor.",
    "reference_window_outside_fft": "Gürültü referans aralığı FFT sınırının dışında.",
    "neighbor_in_reference_window": "Gürültü referans aralığında komşu sinyal var.",
    "event_ownership_lost": "Dört kare sırasında olay sahipliği kayboldu.",
    "session_ended_before_four_observations": "Oturum dört gözlem tamamlanmadan bitti.",
    "event_ended_before_measurement": "Sinyal ölçüm sırası gelmeden sona erdi.",
    "accumulating": "Dört karelik gözlem henüz tamamlanmadı.",
    "reference_power_unavailable": "Gürültü referans gücü kullanılamıyor.",
    "reference_mismatch": "İki gürültü referansı birbiriyle uyuşmuyor.",
    "excess_power_not_significant": "Gürültü üstü sinyal gücü yeterli değil.",
    "center_temporal_uncertainty": "Merkez frekansı kareler arasında kararsız.",
    "span_edge_clipping": "Sinyal analiz aralığının kenarına taşıyor.",
    "obw_temporal_instability": "OBW kenarları kareler arasında kararsız.",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class CalibrationApplication:
    status: str
    profile_id: str | None = None
    power_dbm: float | None = None
    uncertainty_db: float | None = None
    reason: str | None = None


class PowerCalibrationRegistry:
    """Fail closed unless one measured profile matches the full RX context."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            document = {"schema": CALIBRATION_SCHEMA, "profiles": []}
        profiles = document.get("profiles", []) if isinstance(document, dict) else []
        self._profiles = tuple(item for item in profiles if isinstance(item, dict))
        self.valid_document = (
            isinstance(document, dict)
            and document.get("schema") == CALIBRATION_SCHEMA
            and isinstance(profiles, list)
        )

    def apply(
        self,
        power_dbfs: float | None,
        *,
        receiver_serial: str,
        sample_rate_hz: int,
        lna_gain_db: int,
        vga_gain_db: int,
        output_amplitude_scale: float,
        frequency_hz: float,
        now: datetime | None = None,
    ) -> CalibrationApplication:
        if power_dbfs is None or not math.isfinite(power_dbfs):
            return CalibrationApplication("unavailable", reason="dbfs_not_valid")
        if not self.valid_document:
            return CalibrationApplication("unavailable", reason="calibration_file_invalid")
        now = now or datetime.now(timezone.utc)
        for profile in self._profiles:
            measured = _parse_utc(profile.get("measured_utc"))
            valid_until = _parse_utc(profile.get("valid_until_utc"))
            exact = (
                isinstance(profile.get("profile_id"), str)
                and isinstance(profile.get("receiver_serial"), str)
                and profile["receiver_serial"].casefold() == receiver_serial.casefold()
                and profile.get("sample_rate_hz") == sample_rate_hz
                and profile.get("lna_gain_db") == lna_gain_db
                and profile.get("vga_gain_db") == vga_gain_db
                and profile.get("output_amplitude_scale") == output_amplitude_scale
                and _finite_number(profile.get("minimum_frequency_hz"))
                and _finite_number(profile.get("maximum_frequency_hz"))
                and profile["minimum_frequency_hz"] <= frequency_hz <= profile["maximum_frequency_hz"]
                and measured is not None
                and valid_until is not None
                and measured <= now <= valid_until
                and _finite_number(profile.get("dbm_minus_dbfs"))
                and _finite_number(profile.get("uncertainty_db"))
                and float(profile["uncertainty_db"]) >= 0
            )
            if exact:
                return CalibrationApplication(
                    "calibrated",
                    str(profile["profile_id"]),
                    power_dbfs + float(profile["dbm_minus_dbfs"]),
                    float(profile["uncertainty_db"]),
                )
        return CalibrationApplication("unavailable", reason="no_exact_matching_profile")


class ParameterCatalog:
    def __init__(self, database_path: Path, calibration_path: Path) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.calibrations = PowerCalibrationRegistry(calibration_path)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS parameter_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    receiver_role TEXT NOT NULL,
                    receiver_serial TEXT NOT NULL,
                    completed_utc TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    detected_frequency_hz REAL NOT NULL,
                    center_frequency_hz REAL,
                    lower_occupied_edge_hz REAL,
                    upper_occupied_edge_hz REAL,
                    occupied_bandwidth_hz REAL,
                    channel_power_dbfs REAL,
                    channel_power_dbm REAL,
                    snr_db REAL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    calibration_status TEXT NOT NULL,
                    calibration_profile_id TEXT,
                    calibration_uncertainty_db REAL,
                    details_json TEXT NOT NULL,
                    UNIQUE(session_id, event_id)
                );
                CREATE INDEX IF NOT EXISTS parameter_observations_power
                    ON parameter_observations(channel_power_dbfs DESC, id DESC);
                CREATE INDEX IF NOT EXISTS parameter_observations_time
                    ON parameter_observations(id DESC);
                """
            )
            columns = {
                item[1]
                for item in connection.execute("PRAGMA table_info(parameter_observations)")
            }
            for name in ("lower_occupied_edge_hz", "upper_occupied_edge_hz"):
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE parameter_observations ADD COLUMN {name} REAL"
                    )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=2.0)
        connection.execute("PRAGMA busy_timeout=2000")
        return connection

    def add(
        self,
        outcome: AutomaticParameterOutcome,
        *,
        session_id: str,
        receiver_role: str,
        receiver_serial: str,
        sample_rate_hz: int,
        lna_gain_db: int,
        vga_gain_db: int,
        output_amplitude_scale: float,
    ) -> bool:
        result = outcome.result
        power_dbfs = outcome.channel_power_dbfs
        frequency = (
            result.emission_center_frequency_hz.value
            if result is not None and result.emission_center_frequency_hz.state == "valid"
            else outcome.detected_frequency_hz
        )
        bandwidth = (
            result.occupied_bandwidth_hz.value
            if result is not None and result.occupied_bandwidth_hz.state == "valid"
            else None
        )
        lower_edge = (
            result.lower_occupied_edge_hz.value
            if result is not None and result.lower_occupied_edge_hz.state == "valid"
            else None
        )
        upper_edge = (
            result.upper_occupied_edge_hz.value
            if result is not None and result.upper_occupied_edge_hz.state == "valid"
            else None
        )
        snr = (
            result.snr_estimate_db.value
            if result is not None and result.snr_estimate_db.state == "valid"
            else None
        )
        calibration = self.calibrations.apply(
            power_dbfs,
            receiver_serial=receiver_serial,
            sample_rate_hz=sample_rate_hz,
            lna_gain_db=lna_gain_db,
            vga_gain_db=vga_gain_db,
            output_amplitude_scale=output_amplitude_scale,
            frequency_hz=float(frequency),
        )
        details = json.dumps(
            {
                "outcome": {
                    **asdict(outcome),
                    "result": asdict(result) if result is not None else None,
                },
                "calibration_reason": calibration.reason,
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(details.encode("utf-8")) > MAXIMUM_DETAILS_BYTES:
            raise ValueError("Otomatik parametre kayıt ayrıntısı boyut sınırını aştı.")
        with self._connect() as connection:
            before = connection.total_changes
            connection.execute(
                """
                INSERT OR IGNORE INTO parameter_observations (
                    schema_name, session_id, receiver_role, receiver_serial,
                    completed_utc, intent_id, event_id, detected_frequency_hz,
                    center_frequency_hz, lower_occupied_edge_hz,
                    upper_occupied_edge_hz, occupied_bandwidth_hz,
                    channel_power_dbfs, channel_power_dbm, snr_db, status, reason,
                    calibration_status, calibration_profile_id,
                    calibration_uncertainty_db, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    CATALOG_SCHEMA,
                    session_id[:128],
                    receiver_role,
                    receiver_serial,
                    _utc_now(),
                    str(outcome.intent_id),
                    str(outcome.event_id),
                    float(outcome.detected_frequency_hz),
                    float(frequency) if frequency is not None else None,
                    float(lower_edge) if lower_edge is not None else None,
                    float(upper_edge) if upper_edge is not None else None,
                    float(bandwidth) if bandwidth is not None else None,
                    float(power_dbfs) if power_dbfs is not None else None,
                    calibration.power_dbm,
                    float(snr) if snr is not None else None,
                    outcome.status,
                    outcome.reason,
                    calibration.status,
                    calibration.profile_id,
                    calibration.uncertainty_db,
                    details,
                ),
            )
            inserted = connection.total_changes > before
            connection.execute(
                """
                DELETE FROM parameter_observations
                WHERE id NOT IN (
                    SELECT id FROM parameter_observations ORDER BY id DESC LIMIT ?
                )
                """,
                (MAXIMUM_CATALOG_ROWS,),
            )
        return inserted

    def rows(self, limit: int = 128) -> list[dict[str, object]]:
        limit = max(1, min(int(limit), MAXIMUM_DISPLAY_ROWS))
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            records = connection.execute(
                """
                SELECT * FROM parameter_observations
                ORDER BY channel_power_dbfs IS NULL, channel_power_dbfs DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        rows: list[dict[str, object]] = []
        for record in records:
            frequency = record["center_frequency_hz"] or record["detected_frequency_hz"]
            rows.append(
                {
                    "id": record["id"],
                    "frequency": f"{frequency / 1e6:.6f} MHz",
                    "dbfs": (
                        f"{record['channel_power_dbfs']:.2f} dBFS"
                        if record["channel_power_dbfs"] is not None else "—"
                    ),
                    "dbm": (
                        f"{record['channel_power_dbm']:.2f} dBm"
                        if record["channel_power_dbm"] is not None else "Kalibre değil"
                    ),
                    "bandwidth": (
                        f"{record['occupied_bandwidth_hz'] / 1e3:.2f} kHz"
                        if record["occupied_bandwidth_hz"] is not None else "—"
                    ),
                    "lowerEdge": (
                        f"{record['lower_occupied_edge_hz'] / 1e6:.6f} MHz"
                        if record["lower_occupied_edge_hz"] is not None else "—"
                    ),
                    "upperEdge": (
                        f"{record['upper_occupied_edge_hz'] / 1e6:.6f} MHz"
                        if record["upper_occupied_edge_hz"] is not None else "—"
                    ),
                    "snr": (
                        f"{record['snr_db']:.2f} dB"
                        if record["snr_db"] is not None else "—"
                    ),
                    "receiver": (
                        ("Birincil alıcı" if record["receiver_role"] == "ED_RX_PRIMARY" else "İkinci alıcı")
                        + f" · …{record['receiver_serial'][-8:]}"
                    ),
                    "status": STATUS_TEXT.get(record["status"], "Kullanılamıyor"),
                    "statusKey": record["status"],
                    "reason": REASON_TEXT.get(record["reason"], record["reason"] or ""),
                    "completedUtc": record["completed_utc"],
                    "calibrationStatus": record["calibration_status"],
                }
            )
        return rows

    def export_csv(self, destination: Path | None = None) -> Path:
        destination = destination or self.path.parent / (
            "otomatik-parametre-katalogu-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".csv"
        )
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            records = connection.execute(
                "SELECT * FROM parameter_observations ORDER BY id DESC"
            ).fetchall()
        with self._connect() as connection:
            fields = [
                item[1]
                for item in connection.execute("PRAGMA table_info(parameter_observations)")
            ]
        with Path(destination).open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(dict(record) for record in records)
        return Path(destination)
