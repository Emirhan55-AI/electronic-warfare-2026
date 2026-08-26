"""Safe GPS L1 C/A scenario metadata validation; no RF waveform is created."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class GNSSScenario:
    latitude_deg: float
    longitude_deg: float
    scenario_time_utc: str
    satellite_ids: tuple[int, ...]
    duration_seconds: float = 30.0
    service: str = "GPS L1 C/A"
    metadata_source: str = "OFFLINE SCENARIO METADATA"


@dataclass(frozen=True)
class GNSSValidationResult:
    valid: bool
    errors: tuple[str, ...]
    service: str
    position_time_consistent: bool
    scenario_data_available: bool
    metadata_contract_valid: bool
    waveform_available: bool = False
    tx_state: str = "KİLİTLİ"
    provenance: str = "OFFLINE SENARYO DOĞRULAMA"

    @property
    def waveform_source_contract_valid(self) -> bool:
        """Compatibility view that must remain false until samples exist."""

        return False


class GNSSScenarioValidator:
    """Validate only the bounded metadata contract for an offline scenario."""

    @staticmethod
    def validate(scenario: GNSSScenario) -> GNSSValidationResult:
        errors: list[str] = []
        if scenario.service != "GPS L1 C/A":
            errors.append("yalnız GPS L1 C/A senaryosu kabul edilir")
        if not -90.0 <= scenario.latitude_deg <= 90.0:
            errors.append("sanal enlem geçersiz")
        if not -180.0 <= scenario.longitude_deg <= 180.0:
            errors.append("sanal boylam geçersiz")
        if not 0 < scenario.duration_seconds <= 3_600.0:
            errors.append("senaryo süresi sınır dışında")
        if not scenario.satellite_ids:
            errors.append("en az bir GPS uydu kimliği gerekir")
        prn_types_valid = all(type(item) is int for item in scenario.satellite_ids)
        prn_values_valid = prn_types_valid and all(1 <= item <= 63 for item in scenario.satellite_ids)
        prn_values_unique = prn_types_valid and len(set(scenario.satellite_ids)) == len(scenario.satellite_ids)
        if not prn_values_valid or not prn_values_unique:
            errors.append("GPS L1 C/A PRN kodları 1..63 ve benzersiz olmalıdır")
        try:
            parsed = datetime.fromisoformat(scenario.scenario_time_utc.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
                errors.append("senaryo zamanı Z veya +00:00 biçiminde UTC olmalıdır")
        except ValueError:
            errors.append("senaryo zamanı ISO-8601 UTC biçiminde değil")
        if not scenario.metadata_source.strip():
            errors.append("senaryo metadata kaynağı boş olamaz")
        available = bool(scenario.metadata_source.strip() and scenario.satellite_ids)
        position_time_consistent = not any("enlem" in error or "boylam" in error or "zamanı" in error for error in errors)
        valid = not errors and available
        return GNSSValidationResult(
            valid=valid,
            errors=tuple(errors),
            service=scenario.service,
            position_time_consistent=position_time_consistent,
            scenario_data_available=available,
            metadata_contract_valid=valid,
        )
