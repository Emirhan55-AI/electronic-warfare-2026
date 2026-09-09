"""Fail-closed ET mission state machine with controlled Faraday-lab admission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class SafetyMode(str, Enum):
    OFFLINE = "OFFLINE"
    LOOPBACK = "LOOPBACK"
    REPLAY = "REPLAY"
    CABLED_LAB = "CABLED_LAB"
    HARDWARE_TX_LOCKED = "HARDWARE_TX_LOCKED"


@dataclass(frozen=True)
class MissionLogEntry:
    timestamp_utc: str
    action: str
    mode: str
    state: str
    duration_seconds: float
    detail: str


class ETMissionController:
    """Admit offline work and the approved Faraday-lab mode.

    Admission to ``CABLED_LAB`` records the approved test context but does not
    itself transmit: this controller intentionally has no device/TX method.
    General hardware or open-air transmission remains fail-closed.
    """

    def __init__(self, mode: SafetyMode = SafetyMode.OFFLINE, *, maximum_duration_seconds: float = 30.0) -> None:
        self.mode = mode
        self.maximum_duration_seconds = maximum_duration_seconds
        self.state = "HAZIR"
        self.emergency_stop_latched = False
        self.log: list[MissionLogEntry] = []

    def set_mode(self, mode: SafetyMode) -> None:
        if self.state == "ÇALIŞIYOR":
            raise RuntimeError("çalışan görev sırasında güvenlik modu değiştirilemez")
        self.mode = mode
        self._record("MOD", 0.0, mode.value)

    def start(self, *, duration_seconds: float, detail: str) -> None:
        if self.state == "ÇALIŞIYOR":
            raise RuntimeError("görev zaten çalışıyor")
        if self.emergency_stop_latched:
            raise RuntimeError("acil durdurma kilidi sıfırlanmadan görev başlatılamaz")
        if not 0 < duration_seconds <= self.maximum_duration_seconds:
            raise ValueError("görev süresi bounded sınırı aşıyor")
        if self.mode is SafetyMode.HARDWARE_TX_LOCKED:
            self.state = "GÜVENLİK KİLİDİ"
            self._record("RED", duration_seconds, "Genel veya açık alan donanım TX kilitlidir")
            raise PermissionError("yalnız OFFLINE, LOOPBACK, REPLAY veya onaylı FARADAY LAB göreve izin verilir")
        self.state = "ÇALIŞIYOR"
        recorded_detail = f"FARADAY LAB · {detail}" if self.mode is SafetyMode.CABLED_LAB else detail
        self._record("BAŞLAT", duration_seconds, recorded_detail)

    def stop(self) -> None:
        self.state = "DURDURULDU"
        self._record("DURDUR", 0.0, "Operatör durdurması")

    def complete(self, *, detail: str) -> None:
        """Close a synchronous offline task without implying an RF emission."""

        if self.state != "ÇALIŞIYOR":
            raise RuntimeError("tamamlanacak çalışan görev yok")
        self.state = "TAMAMLANDI"
        self._record("TAMAMLA", 0.0, detail)

    def emergency_stop(self) -> None:
        self.emergency_stop_latched = True
        self.state = "ACİL DURDURMA"
        self._record("ACİL DURDUR", 0.0, "Fail-closed kilit")

    def reset_emergency_stop(self) -> None:
        if self.state == "ÇALIŞIYOR":
            raise RuntimeError("çalışan görevde acil durdurma sıfırlanamaz")
        self.emergency_stop_latched = False
        self.state = "HAZIR"
        self._record("KİLİT SIFIRLA", 0.0, "Yazılım kilidi sıfırlandı")

    def _record(self, action: str, duration_seconds: float, detail: str) -> None:
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.log.append(MissionLogEntry(stamp, action, self.mode.value, self.state, duration_seconds, detail))
