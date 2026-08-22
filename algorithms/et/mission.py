"""Fail-closed P0 ET mission state machine with no hardware TX implementation."""

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
    """Only OFFLINE/LOOPBACK/REPLAY can run; there is no transmit method."""

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
        if self.mode not in {SafetyMode.OFFLINE, SafetyMode.LOOPBACK, SafetyMode.REPLAY}:
            self.state = "GÜVENLİK KİLİDİ"
            self._record("RED", duration_seconds, "Donanım TX P0 kabulünde kilitlidir")
            raise PermissionError("yalnız OFFLINE, LOOPBACK veya REPLAY göreve izin verilir")
        self.state = "ÇALIŞIYOR"
        self._record("BAŞLAT", duration_seconds, detail)

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
