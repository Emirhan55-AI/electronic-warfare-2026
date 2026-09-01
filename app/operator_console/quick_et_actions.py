"""Offline ET task actions exposed by the Qt Quick view model."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Slot

from algorithms.et import (
    AnalogDeceptionConfig,
    ContinuousJammingConfig,
    GNSSScenario,
    InterleavedConfig,
    SafetyMode,
)


class QuickETActionsMixin:
    """Keep offline ET presentation actions separate from RF detection state."""

    @Slot(str)
    def selectETTask(self, task: str) -> None:
        if task not in {"continuous", "interleaved", "analog", "gnss"} or task == self._et_task:
            return
        self._et_task = task
        self._et_status = "HAZIR"
        self._et_result_title = "Görev seçildi"
        self._et_result_detail = "Çalışma parametrelerini seçip görevi başlatın."
        self._et_metric_rows = []
        self._et_primary_values = []
        self._et_secondary_values = []
        self._et_timeline = []
        self._et_primary_title = "Zaman Alanı"
        self._et_secondary_title = "Spektrum"
        self.etChanged.emit()

    @Slot(str, str)
    def runETTask(self, task: str, option: str) -> None:
        if task not in {"continuous", "interleaved", "analog"}:
            return
        self.selectETTask(task)
        try:
            if self._et_mission.state == "ÇALIŞIYOR":
                self._et_mission.stop()
            self._et_mission.set_mode(SafetyMode.OFFLINE)
            self._et_status = "ÇALIŞIYOR"
            self.etChanged.emit()
            if task == "continuous":
                self._run_continuous_et(option)
            elif task == "interleaved":
                self._run_interleaved_et(option)
            else:
                self._run_analog_et(option)
            self._et_status = "TAMAMLANDI"
            self._add_log("ET", f"{self._et_result_title} · görev tamamlandı")
        except (ValueError, RuntimeError, PermissionError) as exc:
            self._et_status = "HATA"
            self._et_result_title = "Görev tamamlanamadı"
            self._et_result_detail = str(exc)
            self._add_log("Hata", f"ET görevi · {type(exc).__name__}")
        self.etChanged.emit()

    @Slot(float, float, str, str)
    def validateETGNSS(self, latitude: float, longitude: float, utc_text: str, prn_text: str) -> None:
        self.selectETTask("gnss")
        try:
            prns = tuple(int(value.strip()) for value in prn_text.split(",") if value.strip())
        except ValueError:
            prns = (0,)
        scenario = GNSSScenario(float(latitude), float(longitude), utc_text.strip(), prns)
        result = self._et_gnss.validate(scenario)
        self._et_primary_values = []
        self._et_secondary_values = []
        self._et_timeline = []
        self._et_primary_title = "Metadata"
        self._et_secondary_title = "Dalga Şekli Yok"
        self._et_result_title = "GPS L1 C/A senaryo denetimi"
        self._et_status = "TAMAMLANDI" if result.valid else "HATA"
        self._et_result_detail = (
            "Konum, kesin UTC ve PRN sözleşmesi geçerli. Dalga şekli üretilmedi."
            if result.valid
            else " · ".join(result.errors)
        )
        self._et_metric_rows = [
            {"label": "Servis", "value": result.service},
            {"label": "Konum / zaman", "value": "PASS" if result.position_time_consistent else "FAIL"},
            {"label": "Metadata", "value": "PASS" if result.metadata_contract_valid else "FAIL"},
            {"label": "PRN", "value": ", ".join(str(value) for value in prns)},
            {"label": "Dalga şekli", "value": "YOK"},
        ]
        self._add_log("ET", f"GPS L1 C/A metadata · {'PASS' if result.valid else 'FAIL'}")
        self.etChanged.emit()

    def _run_continuous_et(self, family: str) -> None:
        choices = {
            "single": ContinuousJammingConfig("single", 48_000, 0.25, (4_000.0,)),
            "multiple": ContinuousJammingConfig("multiple", 48_000, 0.25, (-8_000.0, 0.0, 8_000.0)),
            "barrage": ContinuousJammingConfig("barrage", 48_000, 0.25, barrage_bandwidth_hz=16_000.0),
            "sweep": ContinuousJammingConfig("sweep", 48_000, 0.50, sweep_start_hz=-9_000.0, sweep_stop_hz=9_000.0),
        }
        config = choices.get(family)
        if config is None:
            raise ValueError("bilinmeyen sürekli görev ailesi")
        self._et_mission.start(duration_seconds=config.duration_seconds, detail=f"continuous/{family}")
        result = self._et_continuous.generate(config)
        self._et_mission.complete(detail=f"continuous/{family} tamamlandı")
        frequencies, power = self._et_continuous.spectrum(result.samples, result.sample_rate_hz)
        self._et_primary_values = self._bounded_series(result.samples.real)
        self._et_secondary_values = self._spectrum_series(power)
        self._et_timeline = []
        self._et_primary_title = "Kompleks Taban Bant · I Bileşeni"
        self._et_secondary_title = "Normalize Spektrum · dB"
        family_name = {"single": "Tekli", "multiple": "Çoklu", "barrage": "Baraj", "sweep": "Doğrusal Süpürme"}[family]
        self._et_result_title = f"{family_name} taban bant analizi"
        self._et_result_detail = "Kompleks örnek tamponu üretildi ve spektral ölçümler tamamlandı."
        self._et_metric_rows = [
            {"label": "Örnek", "value": f"{result.samples.size:,}".replace(",", ".")},
            {"label": "Örnekleme", "value": f"{result.sample_rate_hz / 1000:.0f} kHz"},
            {"label": "Tepe", "value": f"{result.peak_magnitude:.3f}"},
            {"label": "RMS", "value": f"{result.rms_magnitude:.3f}"},
            {"label": "OBW99", "value": f"{result.occupied_bandwidth_hz / 1000:.3f} kHz"},
        ]

    def _run_interleaved_et(self, scenario: str) -> None:
        if scenario not in {"absent", "present", "intermittent", "edge"}:
            raise ValueError("bilinmeyen arabakışlı analiz girdisi")
        config = InterleavedConfig(scenario=scenario)  # type: ignore[arg-type]
        self._et_mission.start(duration_seconds=config.windows * config.window_samples / config.sample_rate_hz, detail=f"interleaved/{scenario}")
        result = self._et_interleaved.run(config)
        self._et_mission.complete(detail=f"interleaved/{scenario} tamamlandı")
        self._et_primary_values = [
            None if item.measured_band_power is None else float(item.measured_band_power)
            for item in result.windows
        ]
        self._et_secondary_values = self._bounded_series(result.task_output_samples.real)
        self._et_timeline = [
            {"index": str(item.index + 1), "state": item.state, "decision": item.decision}
            for item in result.windows
        ]
        self._et_primary_title = "Dinleme Penceresi Bant Gücü"
        self._et_secondary_title = "Maskeli Görev Çıkışı · I Bileşeni"
        scenario_name = {"absent": "Hedef Yok", "present": "Sürekli Hedef", "intermittent": "Kesintili Hedef", "edge": "Eşik Kenarı"}[scenario]
        self._et_result_title = f"Arabakışlı zamanlama · {scenario_name}"
        self._et_result_detail = "Dinleme ve görev pencereleri ayrık; görev dışındaki çıkış örnekleri sıfırdır."
        self._et_metric_rows = [
            {"label": "Dinleme", "value": f"{result.listen_window_count} pencere"},
            {"label": "Gecikme", "value": f"{result.response_delay_window_count} pencere"},
            {"label": "Görev", "value": f"{result.task_window_count} pencere"},
            {"label": "Koruma", "value": f"{result.guard_window_count} pencere"},
            {"label": "Görev çevrimi", "value": f"%{result.task_duty_cycle * 100.0:.1f}"},
        ]

    def _run_analog_et(self, mode: str) -> None:
        normalized_mode = mode.upper()
        if normalized_mode not in {"AM", "FM", "NFM"}:
            raise ValueError("bilinmeyen analog görev modu")
        config = AnalogDeceptionConfig(mode=normalized_mode, duration_seconds=0.25)  # type: ignore[arg-type]
        time_axis = np.arange(config.audio_sample_rate_hz, dtype=np.float64) / config.audio_sample_rate_hz
        audio = np.sin(2.0 * np.pi * 1_000.0 * time_axis)
        self._et_mission.start(duration_seconds=config.duration_seconds, detail=f"analog/{normalized_mode}")
        result = self._et_analog.generate(audio, config)
        self._et_mission.complete(detail=f"analog/{normalized_mode} tamamlandı")
        _, power = self._et_continuous.spectrum(result.samples, result.sample_rate_hz)
        self._et_primary_values = self._bounded_series(result.normalized_audio)
        self._et_secondary_values = self._spectrum_series(power)
        self._et_timeline = []
        self._et_primary_title = "3 kHz Bant Sınırlı Test Sesi"
        self._et_secondary_title = f"{normalized_mode} Normalize Spektrumu · dB"
        self._et_result_title = f"{normalized_mode} yerel döngü analizi"
        self._et_result_detail = "1 kHz sınama sesiyle üretim ve geri çözümleme tamamlandı."
        self._et_metric_rows = [
            {"label": "Örnek", "value": f"{result.samples.size:,}".replace(",", ".")},
            {"label": "Ses bandı", "value": f"{result.audio_bandwidth_hz / 1000:.1f} kHz"},
            {"label": "Tepe", "value": f"{result.peak_magnitude:.3f}"},
            {"label": "Loopback uyumu", "value": f"{result.loopback_correlation:.6f}"},
            {"label": "Örnekleme", "value": f"{result.sample_rate_hz / 1000:.0f} kHz"},
        ]

    @staticmethod
    def _bounded_series(values: np.ndarray, maximum: int = 768) -> list[float]:
        source = np.asarray(values, dtype=np.float64)
        if source.size <= maximum:
            return [float(value) for value in source]
        indices = np.linspace(0, source.size - 1, maximum, dtype=np.int64)
        return [float(value) for value in source[indices]]

    @staticmethod
    def _spectrum_series(power: np.ndarray, maximum: int = 768) -> list[float]:
        values = np.asarray(power, dtype=np.float64)
        peak = max(float(np.max(values)), np.finfo(np.float64).tiny)
        db = 10.0 * np.log10(np.maximum(values / peak, 1e-12))
        return QuickETActionsMixin._bounded_series(db, maximum)
