"""Operator actions for the PHASE-10 single-band ET task."""

from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np
from PySide6.QtCore import Property, Signal, Slot

from algorithms.transmission import SingleBandNoiseEngine, SingleBandNoisePlan
from platforms.transmission import ETTransmitError, discover_hackrf_serials, load_tx_safety_profile


ET_ERROR_TEXT = {
    "tx_gate_locked": "Fiziksel ET güvenlik kapısı açık değil.",
    "connection_unapproved": "Kablolu-zayıflatıcılı veya RF ekranlı düzen doğrulanmadı.",
    "device_serial_unassigned": "ET_TX HackRF seri kimliği atanmadı.",
    "frequency_not_allowed": "Seçilen bant izin listesinde değil.",
    "attenuation_unverified": "Kapalı düzen zayıflatması doğrulanmadı.",
    "approval_incomplete": "Fiziksel kapı onay kaydı eksik.",
    "approval_expired": "Fiziksel kapı onayının süresi doldu.",
    "tools_unavailable": "hackrf_transfer bulunamadı.",
    "device_probe_failed": "ET_TX HackRF aygıt denetimi tamamlanamadı.",
    "configured_serial_not_found": "Yapılandırılmış ET_TX HackRF bağlı değil.",
    "emergency_stop_latched": "Acil durdurma kilidi etkin; uygulamayı yeniden başlatın.",
}


class QuickETActionsMixin:
    """Preview one bounded band and start TX only through the physical gate."""

    etChanged = Signal()

    @Property(str, notify=etChanged)
    def etTask(self) -> str:
        return self._et_task

    @Property(str, notify=etChanged)
    def etStatus(self) -> str:
        return self._et_status

    @Property(str, notify=etChanged)
    def etResultTitle(self) -> str:
        return self._et_result_title

    @Property(str, notify=etChanged)
    def etResultDetail(self) -> str:
        return self._et_result_detail

    @Property("QVariantList", notify=etChanged)
    def etMetricRows(self) -> list[dict[str, str]]:
        return self._et_metric_rows

    @Property("QVariantList", notify=etChanged)
    def etPrimaryValues(self) -> list[float | None]:
        return self._et_primary_values

    @Property("QVariantList", notify=etChanged)
    def etSecondaryValues(self) -> list[float]:
        return self._et_secondary_values

    @Property("QVariantList", notify=etChanged)
    def etTimeline(self) -> list[dict[str, str]]:
        return self._et_timeline

    @Property(str, notify=etChanged)
    def etPrimaryTitle(self) -> str:
        return self._et_primary_title

    @Property(str, notify=etChanged)
    def etSecondaryTitle(self) -> str:
        return self._et_secondary_title

    @Property(bool, notify=etChanged)
    def etTransmitting(self) -> bool:
        return self._et_transmitting

    @Property(bool, notify=etChanged)
    def etCanTransmit(self) -> bool:
        profile = self._et_tx_profile
        return bool(
            profile is not None
            and profile.enabled
            and profile.physical_gate_approved
            and profile.device_serial
            and profile.allowed_frequency_ranges_hz
            and not self._et_tx_runner.emergency_latched
        )

    @Property(str, notify=etChanged)
    def etTxGateState(self) -> str:
        if self._et_tx_profile_error:
            return "Güvenlik profili okunamadı"
        if self.etCanTransmit:
            return "Kapalı RF düzeni profili etkin"
        return "Fiziksel güvenlik kapısı kapalı"

    @Property("QVariantList", constant=True)
    def etTaskCards(self) -> list[dict[str, str]]:
        return [
            {"id": "continuous", "name": "Tekli Görev", "detail": "Tek hedef bant · süreli", "maturity": "PHASE-10"},
        ]

    @Slot(str)
    def selectETTask(self, task: str) -> None:
        if task != "continuous" or task == self._et_task:
            return
        self._et_task = task
        self._et_status = "TX KİLİTLİ"
        self._et_result_title = "Tekli Görev"
        self._et_result_detail = "Önce seçilen bandı iletimsiz doğrulayın."
        self._et_metric_rows = []
        self._et_primary_values = []
        self._et_secondary_values = []
        self._et_timeline = []
        self.etChanged.emit()

    @staticmethod
    def _single_plan(lower_mhz: str, upper_mhz: str, duration_seconds: str) -> SingleBandNoisePlan:
        try:
            lower = int(round(float(lower_mhz.strip().replace(",", ".")) * 1_000_000.0))
            upper = int(round(float(upper_mhz.strip().replace(",", ".")) * 1_000_000.0))
            duration = float(duration_seconds.strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError("Frekans ve süre alanları sayısal olmalıdır.") from exc
        return SingleBandNoisePlan(lower, upper, duration)

    @Slot(str, str, str)
    def previewETSingle(self, lower_mhz: str, upper_mhz: str, duration_seconds: str) -> None:
        if self._et_transmitting or self._busy:
            return
        try:
            plan = self._single_plan(lower_mhz, upper_mhz, duration_seconds)
            engine = SingleBandNoiseEngine()
            tile = engine.generate_tile(plan)
            summary = engine.summarize(plan, tile)
        except (ValueError, OSError) as exc:
            self._et_status = "GİRDİ HATASI"
            self._et_result_title = "Tekli görev doğrulanamadı"
            self._et_result_detail = str(exc)
            self._et_metric_rows = []
            self.etChanged.emit()
            return
        power = np.abs(np.fft.fftshift(np.fft.fft(tile))) ** 2
        power = 10.0 * np.log10(np.maximum(power, np.max(power) * 1e-12))
        indices = np.linspace(0, power.size - 1, 512, dtype=np.int64)
        self._et_primary_values = []
        self._et_secondary_values = [float(power[index]) for index in indices]
        self._et_status = "İLETİMSİZ DOĞRULANDI"
        self._et_result_title = "Tekli bant hazır"
        self._et_result_detail = "Sayısal I/Q ve spektrum doğrulandı. Bu işlem RF gönderimi yapmadı."
        self._et_metric_rows = [
            {"label": "Alt frekans", "value": f"{plan.lower_frequency_hz / 1_000_000.0:.6f} MHz"},
            {"label": "Üst frekans", "value": f"{plan.upper_frequency_hz / 1_000_000.0:.6f} MHz"},
            {"label": "Merkez", "value": f"{plan.center_frequency_hz / 1_000_000.0:.6f} MHz"},
            {"label": "Bant genişliği", "value": f"{plan.bandwidth_hz / 1_000.0:.3f} kHz"},
            {"label": "Süre", "value": f"{plan.duration_seconds:.3f} s"},
            {"label": "OBW %99", "value": f"{summary.measured_obw99_hz / 1_000.0:.3f} kHz"},
            {"label": "Örnekleme", "value": "8 MS/s · CI8"},
        ]
        self._et_secondary_title = "İletimsiz Spektrum"
        self._add_log("ET Tekli Görev", "Seçilen bant iletimsiz olarak doğrulandı; TX çalıştırılmadı.")
        self.etChanged.emit()

    @Slot(str, str, str)
    def startETSingle(self, lower_mhz: str, upper_mhz: str, duration_seconds: str) -> None:
        if self._et_transmitting or self._busy:
            return
        try:
            plan = self._single_plan(lower_mhz, upper_mhz, duration_seconds)
            profile = load_tx_safety_profile(Path(self._et_tx_profile_path))
            profile.authorize(plan, txvga_db=0)
            executable = shutil.which("hackrf_transfer")
            info_executable = shutil.which("hackrf_info")
            if not executable or not info_executable:
                raise ETTransmitError("tools_unavailable", "hackrf_transfer bulunamadı.")
            if profile.device_serial.casefold() not in discover_hackrf_serials(info_executable):
                raise ETTransmitError("configured_serial_not_found", "Yapılandırılmış ET_TX HackRF bağlı değil.")
        except (ValueError, ETTransmitError) as exc:
            code = str(getattr(exc, "code", "invalid_task"))
            self._et_status = "TX KİLİTLİ"
            self._et_result_title = "Gönderim başlatılmadı"
            self._et_result_detail = ET_ERROR_TEXT.get(code, str(exc))
            self._add_log("ET güvenlik kapısı", self._et_result_detail)
            self.etChanged.emit()
            return
        self._et_tx_profile = profile
        self._et_transmitting = True
        self._et_status = "GÖNDERİM HAZIRLANIYOR"
        self._et_result_title = "Tekli görev başlatılıyor"
        self._et_result_detail = "Sonlu CI8 görev dosyası hazırlanıyor."
        self.etChanged.emit()
        generation = self._generation
        self._submit(
            generation,
            "et_tx",
            lambda: self._et_tx_runner.run(executable, plan, profile, txvga_db=0),
        )

    @Slot()
    def stopETSingle(self) -> None:
        if not self._et_transmitting:
            return
        self._et_status = "DURDURULUYOR"
        self._et_result_detail = "HackRF TX süreci sonlandırılıyor."
        self._et_tx_runner.request_stop()
        self.etChanged.emit()

    @Slot()
    def emergencyStopETSingle(self) -> None:
        self._et_tx_runner.emergency_stop()
        self._et_transmitting = False
        self._et_status = "ACİL DURDURMA"
        self._et_result_title = "Gönderim kilitlendi"
        self._et_result_detail = "HackRF TX sonlandırıldı. Yeniden başlatmak için uygulamayı kapatıp açın."
        self._add_log("ET acil durdurma", self._et_result_detail)
        self.etChanged.emit()
