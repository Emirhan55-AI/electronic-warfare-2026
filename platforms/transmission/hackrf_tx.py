"""HackRF TX process boundary for one approved, closed laboratory band.

The boundary is fail-closed: an unapproved or expired physical profile, an
unassigned serial number, an out-of-list RF band, or an excessive gain blocks
command construction before a process can start.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from typing import Callable

from algorithms.transmission import SingleBandNoiseEngine, SingleBandNoisePlan


SERIAL_PATTERN = re.compile(r"^[0-9a-fA-F]{16,64}$")
APPROVED_CONNECTIONS = frozenset({"CABLED_ATTENUATED", "RF_SHIELDED"})
BASEBAND_FILTER_HZ = 5_000_000


class ETTransmitError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TxSafetyProfile:
    enabled: bool
    device_serial: str
    allowed_frequency_ranges_hz: tuple[tuple[int, int], ...]
    maximum_duration_seconds: float
    maximum_txvga_db: int
    connection: str
    physical_gate_approved: bool
    minimum_attenuation_db: float
    measured_attenuation_db: float | None
    reviewed_at_utc: str | None
    expires_at_utc: str | None
    approved_by: str

    def authorize(self, plan: SingleBandNoisePlan, *, txvga_db: int, now: datetime | None = None) -> None:
        if not self.enabled or not self.physical_gate_approved:
            raise ETTransmitError("tx_gate_locked", "Fiziksel ET güvenlik kapısı onaylanmamış.")
        if self.connection not in APPROVED_CONNECTIONS:
            raise ETTransmitError("connection_unapproved", "Yalnız kablolu-zayıflatıcılı veya RF ekranlı düzen kullanılabilir.")
        if not SERIAL_PATTERN.fullmatch(self.device_serial):
            raise ETTransmitError("device_serial_unassigned", "ET_TX HackRF seri kimliği atanmamış.")
        if not 0 <= txvga_db <= self.maximum_txvga_db:
            raise ETTransmitError("tx_gain_rejected", "TX kazancı onaylı profil sınırını aşıyor.")
        if plan.duration_seconds > self.maximum_duration_seconds:
            raise ETTransmitError("duration_rejected", "Görev süresi onaylı profil sınırını aşıyor.")
        if not any(
            lower <= plan.lower_frequency_hz and plan.upper_frequency_hz <= upper
            for lower, upper in self.allowed_frequency_ranges_hz
        ):
            raise ETTransmitError("frequency_not_allowed", "Seçilen frekans aralığı ET izin listesinde değil.")
        if self.measured_attenuation_db is None or self.measured_attenuation_db < self.minimum_attenuation_db:
            raise ETTransmitError("attenuation_unverified", "Kapalı düzen zayıflatması doğrulanmamış.")
        if not self.approved_by.strip() or self.reviewed_at_utc is None or self.expires_at_utc is None:
            raise ETTransmitError("approval_incomplete", "Fiziksel kapı onay kaydı eksik.")
        current = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
        try:
            expiry = datetime.fromisoformat(self.expires_at_utc.replace("Z", "+00:00"))
            reviewed = datetime.fromisoformat(self.reviewed_at_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ETTransmitError("approval_time_invalid", "Fiziksel kapı zaman kaydı geçersiz.") from exc
        if expiry.tzinfo is None or reviewed.tzinfo is None:
            raise ETTransmitError("approval_time_invalid", "Fiziksel kapı zaman kaydı UTC ofseti içermelidir.")
        expiry = expiry.astimezone(timezone.utc)
        reviewed = reviewed.astimezone(timezone.utc)
        if reviewed > current or expiry <= current:
            raise ETTransmitError("approval_expired", "Fiziksel ET güvenlik kapısı süresi dolmuş veya henüz geçerli değil.")


@dataclass(frozen=True)
class TxRunResult:
    status: str
    started_at_utc: str
    finished_at_utc: str
    stop_reason: str
    return_code: int
    sample_count: int
    stderr_tail: str


def load_tx_safety_profile(path: Path) -> TxSafetyProfile:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ETTransmitError("profile_unreadable", "ET_TX güvenlik profili okunamadı.") from exc
    if payload.get("schema_version") != 1 or payload.get("role") != "ET_TX":
        raise ETTransmitError("profile_invalid", "ET_TX güvenlik profili sözleşmeyle uyumlu değil.")
    gate = payload.get("physical_gate", {})
    ranges = payload.get("allowed_frequency_ranges_hz", [])
    try:
        parsed_ranges = tuple((int(item[0]), int(item[1])) for item in ranges)
        if any(lower >= upper for lower, upper in parsed_ranges):
            raise ValueError
        profile = TxSafetyProfile(
            enabled=bool(payload.get("enabled", False)),
            device_serial=str(payload.get("device_serial", "")).strip(),
            allowed_frequency_ranges_hz=parsed_ranges,
            maximum_duration_seconds=float(payload.get("maximum_duration_seconds", 0.0)),
            maximum_txvga_db=int(payload.get("maximum_txvga_db", -1)),
            connection=str(gate.get("connection", "UNVERIFIED")),
            physical_gate_approved=bool(gate.get("approved", False)),
            minimum_attenuation_db=float(gate.get("minimum_attenuation_db", 0.0)),
            measured_attenuation_db=(None if gate.get("measured_attenuation_db") is None else float(gate["measured_attenuation_db"])),
            reviewed_at_utc=gate.get("reviewed_at_utc"),
            expires_at_utc=gate.get("expires_at_utc"),
            approved_by=str(gate.get("approved_by", "")),
        )
        if not 0 < profile.maximum_duration_seconds <= 30.0:
            raise ValueError
        if not 0 <= profile.maximum_txvga_db <= 47:
            raise ValueError
        if profile.minimum_attenuation_db < 0:
            raise ValueError
        if any(lower < 1_000_000 or upper > 6_000_000_000 for lower, upper in parsed_ranges):
            raise ValueError
        return profile
    except (KeyError, TypeError, ValueError) as exc:
        raise ETTransmitError("profile_invalid", "ET_TX güvenlik profili alanları geçersiz.") from exc


def discover_hackrf_serials(
    executable: str,
    *,
    run_factory: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[str, ...]:
    if Path(executable).name.casefold().removesuffix(".exe") != "hackrf_info":
        raise ETTransmitError("command_not_allowed", "ET_TX aygıt denetimi yalnız hackrf_info kullanabilir.")
    try:
        completed = run_factory(
            [executable],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ETTransmitError("device_probe_failed", "ET_TX HackRF aygıt denetimi tamamlanamadı.") from exc
    output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    serials = tuple(
        dict.fromkeys(
            match.lower()
            for match in re.findall(r"Serial number:\s*([0-9a-fA-F]{16,64})", output, flags=re.IGNORECASE)
        )
    )
    return serials


def build_hackrf_tx_argv(
    executable: str,
    iq_path: Path,
    plan: SingleBandNoisePlan,
    profile: TxSafetyProfile,
    *,
    txvga_db: int = 0,
    now: datetime | None = None,
) -> list[str]:
    if Path(executable).name.casefold().removesuffix(".exe") != "hackrf_transfer":
        raise ETTransmitError("command_not_allowed", "ET TX yalnız hackrf_transfer kullanabilir.")
    if not iq_path.is_file() or iq_path.stat().st_size != plan.sample_count * 2:
        raise ETTransmitError("iq_file_invalid", "Görev I/Q dosyası eksik veya yanlış uzunlukta.")
    profile.authorize(plan, txvga_db=txvga_db, now=now)
    return [
        executable,
        "-d", profile.device_serial,
        "-t", str(iq_path),
        "-f", str(plan.center_frequency_hz),
        "-s", str(plan.sample_rate_hz),
        "-b", str(BASEBAND_FILTER_HZ),
        "-a", "0",
        "-p", "0",
        "-x", str(txvga_db),
        "-n", str(plan.sample_count),
        "-B",
    ]


class HackRFTxRunner:
    """Run one finite TX process with an independent stop latch and deadline."""

    def __init__(
        self,
        *,
        popen_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
        audit_path: Path | None = None,
    ) -> None:
        self._popen_factory = popen_factory
        self._audit_path = audit_path
        self._process: subprocess.Popen[str] | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._stop_reason = "Operatör durdurması"
        self._emergency_latched = False

    @property
    def emergency_latched(self) -> bool:
        return self._emergency_latched

    def request_stop(self) -> None:
        self._stop_reason = "Operatör durdurması"
        self._stop.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def emergency_stop(self) -> None:
        self._emergency_latched = True
        self._stop_reason = "Acil durdurma kilidi"
        self._stop.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def run(
        self,
        executable: str,
        plan: SingleBandNoisePlan,
        profile: TxSafetyProfile,
        *,
        txvga_db: int = 0,
    ) -> TxRunResult:
        if self._emergency_latched:
            raise ETTransmitError("emergency_stop_latched", "Acil durdurma kilidi uygulama yeniden başlatılmadan sıfırlanamaz.")
        self._stop.clear()
        self._stop_reason = "Operatör durdurması"
        engine = SingleBandNoiseEngine()
        started = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory(prefix="baz-et-tx-") as directory:
            iq_path = Path(directory) / "single-band.ci8"
            engine.write_mission_ci8(iq_path, plan)
            argv = build_hackrf_tx_argv(executable, iq_path, plan, profile, txvga_db=txvga_db)
            if self._emergency_latched or self._stop.is_set():
                raise ETTransmitError("emergency_stop_latched", "Görev hazırlanırken durduruldu; HackRF TX başlatılmadı.")
            self._write_audit(
                {
                    "event": "STARTING",
                    "timestamp_utc": started.isoformat().replace("+00:00", "Z"),
                    "device_serial": profile.device_serial,
                    "lower_frequency_hz": plan.lower_frequency_hz,
                    "upper_frequency_hz": plan.upper_frequency_hz,
                    "center_frequency_hz": plan.center_frequency_hz,
                    "bandwidth_hz": plan.bandwidth_hz,
                    "duration_seconds": plan.duration_seconds,
                    "sample_rate_hz": plan.sample_rate_hz,
                    "sample_count": plan.sample_count,
                    "txvga_db": txvga_db,
                    "amplifier_enabled": False,
                    "antenna_power_enabled": False,
                    "connection": profile.connection,
                    "approved_by": profile.approved_by,
                    "software_sha256": self._software_sha256(),
                }
            )
            process = self._popen_factory(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            with self._lock:
                self._process = process
            deadline = time.monotonic() + plan.duration_seconds + 5.0
            stop_reason = "Örnek sınırı tamamlandı"
            while process.poll() is None:
                if self._stop.wait(0.05):
                    stop_reason = self._stop_reason
                    process.terminate()
                    break
                if time.monotonic() >= deadline:
                    stop_reason = "Güvenlik zaman aşımı"
                    process.terminate()
                    break
            try:
                _, stderr = process.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate(timeout=2.0)
                stop_reason = "Zorunlu süreç sonlandırması"
            finally:
                with self._lock:
                    self._process = None
            code = int(process.returncode or 0)
        finished = datetime.now(timezone.utc)
        expected_stop = stop_reason != "Örnek sınırı tamamlandı"
        status = "DURDURULDU" if expected_stop else ("TAMAMLANDI" if code == 0 else "HATA")
        result = TxRunResult(
            status=status,
            started_at_utc=started.isoformat().replace("+00:00", "Z"),
            finished_at_utc=finished.isoformat().replace("+00:00", "Z"),
            stop_reason=stop_reason,
            return_code=code,
            sample_count=plan.sample_count,
            stderr_tail=(stderr or "")[-2000:],
        )
        self._write_audit(
            {
                "event": "FINISHED",
                "timestamp_utc": result.finished_at_utc,
                "device_serial": profile.device_serial,
                "status": result.status,
                "stop_reason": result.stop_reason,
                "return_code": result.return_code,
                "sample_count": result.sample_count,
                "software_sha256": self._software_sha256(),
            }
        )
        return result

    def _write_audit(self, record: dict[str, object]) -> None:
        if self._audit_path is None:
            return
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _software_sha256() -> str:
        digest = hashlib.sha256()
        paths = (
            Path(__file__),
            Path(__file__).resolve().parents[2] / "algorithms" / "transmission" / "single_band_noise.py",
        )
        for path in paths:
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()
