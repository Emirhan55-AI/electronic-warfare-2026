"""Safe GPS L1 C/A scenario metadata validation; no RF waveform is created."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
    waveform_source_contract_valid: bool
    tx_state: str = "KİLİTLİ"
    provenance: str = "OFFLINE SENARYO DOĞRULAMA"


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
        if len(set(scenario.satellite_ids)) != len(scenario.satellite_ids) or any(not 1 <= item <= 32 for item in scenario.satellite_ids):
            errors.append("GPS uydu kimlikleri 1..32 ve benzersiz olmalıdır")
        try:
            parsed = datetime.fromisoformat(scenario.scenario_time_utc.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("senaryo zamanı UTC zaman dilimi içermelidir")
        except ValueError:
            errors.append("senaryo zamanı ISO-8601 UTC biçiminde değil")
        available = bool(scenario.metadata_source.strip() and scenario.satellite_ids)
        position_time_consistent = not any("enlem" in error or "boylam" in error or "zamanı" in error for error in errors)
        valid = not errors and available
        return GNSSValidationResult(
            valid=valid,
            errors=tuple(errors),
            service=scenario.service,
            position_time_consistent=position_time_consistent,
            scenario_data_available=available,
            # This is intentionally a source/metadata contract; no GPS RF
            # samples or transmitter operation is represented here.
            waveform_source_contract_valid=valid,
        )
