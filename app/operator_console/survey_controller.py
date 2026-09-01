"""Bounded Qt presentation of a receive survey and historical observations."""

from pathlib import Path
import json
import math
import time
from uuid import uuid4
from dataclasses import asdict, replace
from collections import deque
import threading

from PySide6.QtCore import QObject, Property, QRunnable, QTimer, Signal, Slot

from .detection_model import DetectionListModel
from .rx_survey import ROOT, RXSurvey, SurveyConfig, SurveyResult, SurveyUpdate
from .survey_evidence import (
    BROAD_MINIMUM_HZ,
    POWER_CHANGE_THRESHOLD_DB,
    channel_power_delta_db,
    classify_against_reference,
    compare_completed_surveys,
    load_completed_survey,
    single_survey_energy_regions,
)
from algorithms.spectrum import SpectrumProcessor
from platforms.acquisition.source import decode_ci8


MAX_DISPLAY_OBSERVATIONS = 4096


class _SurveyMailbox:
    """Coalesce previews only; bounded control updates preserve coverage order."""

    def __init__(self):
        self.condition = threading.Condition()
        self.items = deque()
        self.pending = False

    def publish(self, update, cancelled):
        with self.condition:
            if (update.state == "preview" and self.items and self.items[-1].state == "preview"
                    and self.items[-1].window == update.window):
                self.items[-1] = update
                return False
            while len(self.items) >= 64:
                if cancelled():
                    return False
                self.condition.wait(.1)
            self.items.append(update)
            notify = not self.pending
            self.pending = True
            return notify

    def take(self):
        with self.condition:
            items = tuple(self.items)
            self.items.clear()
            self.pending = False
            self.condition.notify_all()
            return items


class _Signals(QObject):
    update = Signal(object)
    complete = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, survey):
        super().__init__()
        self.survey = survey
        self.signals = _Signals()
        self.mailbox = _SurveyMailbox()
        self.processor = SpectrumProcessor()

    def _publish(self, update):
        if update.state == "preview" and update.snapshot is not None:
            frame = update.snapshot.output_frame
            spectrum = self.processor.process(decode_ci8(frame.payload, expected_complex_samples=4096),
                sample_rate_hz=frame.sample_rate_hz, center_frequency_hz=frame.center_frequency_hz)
            update = replace(update, prepared_spectrum=spectrum)
        cancelled = lambda: bool(getattr(self.survey, "_cancel", threading.Event()).is_set())
        if self.mailbox.publish(update, cancelled):
            self.signals.update.emit(self.mailbox)

    def run(self):
        try:
            result = self.survey.run(self._publish)
        except Exception as exc:
            self.signals.failed.emit(str(getattr(exc, "code", type(exc).__name__)))
        else:
            self.signals.complete.emit(result)


class SurveyController(QObject):
    changed = Signal()
    preview = Signal(object)
    finished = Signal(str)

    def __init__(self, parent=None, *, factory=RXSurvey):
        super().__init__(parent)
        self._factory = factory
        self._survey = None
        self._config = SurveyConfig()
        self._windows = self._config.windows()
        self._states = [0] * len(self._windows)
        self._current = -1
        self._good = self._bad = self._observed = 0
        self._rows = []
        self._current_observations = []
        self._current_window_metrics = {}
        self._current_observation_count = 0
        self._current_energy_count = 0
        self._single_survey_energy_count = 0
        self._completed_window_records = []
        self._energy_changes = 0
        self._tx_correlated = 0
        self._background = 0
        self._model = DetectionListModel(self)
        self._selected = ""
        self._state = "Hazır"
        self._detail = "Frekansı bilinmeyen yayın için sırayla alım."
        self._audit = ""
        self._comparison_audit = ""
        self._reference_audit = ""
        self._reference_observations = ()
        self._reference_window_metrics = {}
        self._reference_by_window = {}
        self._reference_serial = ""
        self._reference_config_key = None
        self._run_condition = "unspecified"
        self._started = 0.0
        self._elapsed = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

    @Property(bool, notify=changed)
    def running(self):
        return self._survey is not None

    @Property(str, notify=changed)
    def state(self):
        return self._state

    @Property(str, notify=changed)
    def detail(self):
        return self._detail

    @Property(str, notify=changed)
    def coverageText(self):
        return f"{self._good} / {len(self._states)} pencere tarandı · {self._bad} hata"

    @Property(float, notify=changed)
    def progress(self):
        return self._good / max(1, len(self._states))

    @Property("QVariantList", notify=changed)
    def coverage(self):
        return self._states

    @Property(int, notify=changed)
    def currentIndex(self):
        return self._current

    @Property(str, notify=changed)
    def currentRange(self):
        if self._current < 0:
            return "Pencere bekleniyor"
        item = self._windows[self._current]
        return f"{item.lower_hz / 1e6:.3f}–{item.upper_hz / 1e6:.3f} MHz"

    @Property(str, notify=changed)
    def timeText(self):
        elapsed = f"{int(self._elapsed) // 60:02d}:{int(self._elapsed) % 60:02d}"
        count = self._good + self._bad
        if not self.running or count < 3:
            return f"Geçen {elapsed}"
        remaining = self._elapsed / count * (len(self._states) - count)
        return f"Geçen {elapsed} · kalan yaklaşık {remaining / 60:.0f} dk"

    @Property(str, notify=changed)
    def auditPath(self):
        return self._audit

    @Property(str, notify=changed)
    def comparisonAuditPath(self):
        return self._comparison_audit

    @Property(bool, notify=changed)
    def referenceReady(self):
        return bool(self._reference_audit and self._reference_config_key is not None)

    @Property(str, notify=changed)
    def referenceText(self):
        if not self.referenceReady:
            return "TX kapalı referans henüz alınmadı."
        lower, upper, *_ = self._reference_config_key
        return (
            f"TX kapalı referans hazır · {len(self._reference_observations)} gözlem · "
            f"{lower / 1e6:g}–{upper / 1e6:g} MHz"
        )

    @Property(str, notify=changed)
    def runConditionText(self):
        return {
            "tx_off_reference": "TX KAPALI REFERANS",
            "tx_on_comparison": "TX AÇIK KARŞILAŞTIRMA",
        }.get(self._run_condition, "TEK TARAMA")

    @Property(str, notify=changed)
    def observationText(self):
        if self._run_condition == "tx_on_comparison":
            return (f"{self._tx_correlated} değişen RF adayı · {self._energy_changes} güç artışı penceresi "
                    f"· {self._background} referans/belirsiz · verici sayısı değildir")
        if self._run_condition == "tx_off_reference":
            return f"{self._observed} TX kapalı referans gözlemi"
        if self._single_survey_energy_count:
            return (
                f"{self._observed} iki ayarlı RF adayı · "
                f"{self._single_survey_energy_count} öne çıkan enerji bölgesi · "
                "dış verici kanıtı değildir"
            )
        if self._observed > len(self._rows):
            return f"{len(self._rows)} gösteriliyor / {self._observed} iki ayarlı RF adayı · tamamı kayıtta"
        return f"{self._observed} iki ayarlı RF adayı · dış verici kanıtı değildir"

    @Property(str, notify=changed)
    def currentObservationText(self):
        if self._current < 0:
            return "Aktif pencere bekleniyor"
        if self._current_energy_count:
            return f"Son pencerede {self._current_observation_count} iki ayarlı aday ve kanal gücü artışı"
        if self._current_observation_count == 0:
            return "Son pencerede iki ayarda doğrulanan RF adayı yok"
        return f"Son pencerede {self._current_observation_count} iki ayarlı RF adayı"

    @Property(QObject, constant=True)
    def observationModel(self):
        return self._model

    @Property(str, notify=changed)
    def selectedKey(self):
        return self._selected

    @Property(float, notify=changed)
    def selectedFrequency(self):
        return next((row["frequencyHz"] for row in self._rows if row["eventId"] == self._selected), 0.0)

    @Slot(str)
    def selectObservation(self, key):
        if any(row["eventId"] == key for row in self._rows):
            self._selected = key
            self.changed.emit()

    @staticmethod
    def _config_key(config):
        return (
            config.lower_hz, config.upper_hz, config.lna_gain_db, config.vga_gain_db,
            config.frames_per_window, config.guard_frames,
        )

    def reference_matches(self, config, serial=None):
        return (self.referenceReady and self._reference_config_key == self._config_key(config)
                and (serial is None or self._reference_serial == serial))

    @Slot()
    def clearReference(self):
        if self.running:
            return
        self._reference_audit = ""
        self._reference_observations = ()
        self._reference_window_metrics = {}
        self._reference_by_window = {}
        self._reference_serial = ""
        self._reference_config_key = None
        self._comparison_audit = ""
        self.changed.emit()

    def start(self, executable, serial, config, pool, *, audit_path=None):
        if self.running:
            return False
        if config.operator_condition == "tx_on_comparison" and not self.reference_matches(config, serial):
            raise ValueError("Aynı alıcı ve ayarlarla tamamlanmış TX kapalı referans gerekir.")
        if config.operator_condition == "tx_off_reference":
            self.clearReference()
        self._serial = serial
        self._config = config
        self._windows = config.windows()
        self._states = [0] * len(self._windows)
        self._current = -1
        self._good = self._bad = self._observed = 0
        self._rows = []
        self._current_observations = []
        self._current_window_metrics = {}
        self._current_observation_count = 0
        self._current_energy_count = self._energy_changes = 0
        self._single_survey_energy_count = 0
        self._completed_window_records = []
        self._tx_correlated = self._background = 0
        self._model.set_rows([])
        self._selected = ""
        self._elapsed = 0.0
        self._run_condition = config.operator_condition
        self._comparison_audit = ""
        self._started = time.monotonic()
        self._audit = str(audit_path or (ROOT / "build" / "acceptance" / "rx-survey" / f"{uuid4().hex}.jsonl"))
        self._survey = self._factory(executable, serial, config, Path(self._audit))
        task = _Task(self._survey)
        task.signals.update.connect(self._update)
        task.signals.complete.connect(self._complete)
        task.signals.failed.connect(self._failed)
        self._state = "Taranıyor"
        self._detail = {
            "tx_off_reference": "Harici test vericisi kapalı kabulüyle referans alınıyor.",
            "tx_on_comparison": "Aynı ayarlarda TX kapalı referansla karşılaştırılacak.",
        }.get(config.operator_condition, "Her pencere kart yanıtı ve alım bütünlüğü denetlenerek işlenir.")
        self._timer.start()
        self.changed.emit()
        pool.start(task)
        return True

    @Slot()
    def cancel(self):
        if self._survey is not None:
            self._state = "Durduruluyor"
            self._survey.cancel()
            self.changed.emit()

    def _tick(self):
        if self.running:
            self._elapsed = time.monotonic() - self._started
            self.changed.emit()

    @Slot(object)
    def _update(self, update: SurveyUpdate):
        if isinstance(update, _SurveyMailbox):
            for item in update.take():
                self._update(item)
            return
        self._current = update.window.index
        self._elapsed = update.elapsed_seconds
        if update.state == "preview":
            if update.prepared_spectrum is not None:
                self.preview.emit((update.snapshot, update.prepared_spectrum))
            return
        if update.state == "running":
            self.preview.emit(None)
            self._detail = "Alım önizlemesi · pencere bütünlüğü henüz doğrulanmadı."
        if update.state == "complete":
            self._states[self._current] = 1
            self._good += 1
            newest = []
            if update.window_metrics:
                self._current_window_metrics[self._current] = dict(update.window_metrics)
                self._completed_window_records.append({
                    "window": asdict(update.window),
                    "window_metrics": dict(update.window_metrics),
                })
            for item in update.observations:
                self._observed += 1
                self._current_observations.append(item)
                event = item.get("event") or {}
                peak, noise = float(event.get("peak_power", 0.0)), float(event.get("noise_power", 0.0))
                ratio = 10.0 * math.log10(peak / noise) if peak > 0.0 and noise > 0.0 else float("nan")
                verification = item.get("verification") or {}
                details = [
                    f"P/N {ratio:.1f} dB" if math.isfinite(ratio) else "P/N ölçülemedi",
                    f"{item['observed_frames']} kare",
                ]
                bandwidth_hz = float(item.get("bandwidth_hz", 0.0))
                if bandwidth_hz >= 1_000_000:
                    details.append(f"kaba aralık {bandwidth_hz / 1e6:.2f} MHz")
                elif bandwidth_hz > 0.0:
                    details.append(f"kaba aralık {bandwidth_hz / 1e3:.1f} kHz")
                if verification:
                    details.append(f"2. ayar {verification.get('observed_frames', 0)} kare")
                    broad = bandwidth_hz >= BROAD_MINIMUM_HZ
                    primary_frequency = float(item.get(
                        "frequency_hz" if broad else "peak_frequency_hz", item["frequency_hz"]
                    ))
                    verification_frequency = float(verification.get(
                        "frequency_hz" if broad else "peak_frequency_hz", primary_frequency
                    ))
                    if "frequency_hz" in verification or "peak_frequency_hz" in verification:
                        delta_hz = abs(verification_frequency - primary_frequency)
                        details.append(
                            f"RF farkı {delta_hz / 1e3:.1f} kHz" if delta_hz >= 1_000.0
                            else f"RF farkı {delta_hz:.0f} Hz"
                        )
                evidence_key = "dual_tune"
                evidence_text = "2 AYARDA"
                evidence_detail = "İki farklı LO ayarında aynı RF adayı"
                if self._run_condition == "tx_off_reference":
                    evidence_key, evidence_text = "reference", "REFERANS"
                    evidence_detail = "TX kapalı koşulunda görüldü"
                elif self._run_condition == "tx_on_comparison":
                    reference_record = self._reference_by_window.get(self._current, {})
                    evidence = classify_against_reference(
                        item, self._reference_observations,
                        active_window=update.window_metrics or {},
                        reference_window=reference_record.get("window_metrics", {}),
                        screened_references=(item for record in self._reference_by_window.values()
                                             for item in record.get("screened_observations", ())),
                    )
                    if evidence.state == "appeared_with_tx":
                        evidence_key, evidence_text = "ab_candidate", "A/B: YENİ ADAY"
                        evidence_detail = "Referansta görülmedi; TX açık turda iki LO'da var. Kaynak henüz doğrulanmadı."
                        self._tx_correlated += 1
                    elif evidence.state == "strengthened_with_tx":
                        evidence_key, evidence_text = "ab_candidate", "A/B: GÜÇLENDİ"
                        evidence_detail = "İki LO'da ortalama tepe gücü en az 6 dB arttı. Kaynak henüz doğrulanmadı."
                        self._tx_correlated += 1
                    elif evidence.state in {"incomparable_settings", "reference_candidate"}:
                        evidence_key, evidence_text = "uncertain", "A/B: BELİRSİZ"
                        evidence_detail = ("Gerçek kazanç/ölçüm ayarları farklı; tekrar referans alın."
                                           if evidence.state == "incomparable_settings" else
                                           "Referansta kısa/ikinci LO'da doğrulanmamış aday da var; yeni yayın denemez.")
                        self._background += 1
                    else:
                        evidence_key, evidence_text = "reference", "REFERANSTA VAR"
                        evidence_detail = "TX kapalı turda da görüldü; test vericisine bağlanmadı"
                        self._background += 1
                newest.append({
                    "eventId": item["key"], "frequencyHz": item["frequency_hz"],
                    "frequency": f"{item['frequency_hz'] / 1e6:.6f} MHz",
                    "detail": " · ".join(details),
                    "window": f"Pencere {self._current + 1}",
                    "latestWindow": True,
                    "evidenceKey": evidence_key,
                    "evidence": evidence_text,
                    "evidenceDetail": evidence_detail,
                })
            if self._run_condition == "tx_on_comparison":
                delta_db = channel_power_delta_db(
                    update.window_metrics or {}, self._reference_window_metrics.get(self._current, {})
                )
                if delta_db is not None and delta_db >= POWER_CHANGE_THRESHOLD_DB:
                    newest.append({
                        "eventId": f"energy:{self._current}",
                        "frequencyHz": update.window.center_hz,
                        "frequency": (
                            f"{(update.window.center_hz - 1e6) / 1e6:.3f}–"
                            f"{(update.window.center_hz + 1e6) / 1e6:.3f} MHz"
                        ),
                        "detail": f"Pencere gücü referansa göre +{delta_db:.1f} dB",
                        "window": f"Pencere {self._current + 1}",
                        "latestWindow": True,
                        "evidenceKey": "ab_candidate",
                        "evidence": "A/B: KANAL GÜCÜ",
                        "evidenceDetail": (
                            "Host güç ölçümü; ikinci LO veya yayın sınırı doğrulaması değildir"
                        ),
                    })
                    self._energy_changes += 1
            self._current_observation_count = len(update.observations)
            self._current_energy_count = len(newest) - len(update.observations)
            for row in self._rows:
                row["latestWindow"] = False
            if newest:
                # New detections must remain visible during a long survey instead of
                # being buried below thousands of historical observations.
                self._rows = (newest + self._rows)[:MAX_DISPLAY_OBSERVATIONS]
            self._model.set_rows(self._rows)
            self._detail = "Pencere ve ikinci LO kontrolü tamamlandı; sonuç geçmiş RF gözlemidir."
        elif update.state == "failed":
            self.preview.emit(None)
            self._states[self._current] = 2
            self._bad += 1
            self._current_observation_count = 0
            self._current_energy_count = 0
            self._detail = f"Pencere işlenemedi: {update.error_code}"
        self.changed.emit()

    @Slot(object)
    def _complete(self, result: SurveyResult):
        self._timer.stop()
        self._survey = None
        self._elapsed = result.elapsed_seconds
        self._state = {"completed": "Tur tamamlandı", "cancelled": "Durduruldu",
                       "partial": "Eksik kapsam", "failed": "Tarama hatası"}[result.state]
        if result.error_code:
            self._detail = f"Tarama durdu: {result.error_code}"
            self._invalidate_comparison()
        elif result.state == "completed" and self._run_condition == "tx_off_reference":
            try:
                begin, observations, windows, _ = load_completed_survey(Path(result.audit_path))
                if begin.get("operator_declared_external_tx") != "tx_off_reference" or begin.get("serial") != self._serial:
                    raise ValueError("Referansın deney koşulu veya alıcı kimliği uyuşmuyor.")
                self._reference_observations = observations
                self._reference_by_window = {item["window"]["index"]: item for item in windows}
                self._reference_window_metrics = {i: item.get("window_metrics", {}) for i, item in self._reference_by_window.items()}
                self._reference_config_key = self._config_key(self._config)
                self._reference_serial = self._serial
                self._reference_audit = result.audit_path
                self._detail = "TX kapalı referans hazır. Vericiyi açıp aynı ayarlarla karşılaştırma turunu başlatın."
            except (OSError, ValueError) as exc:
                self.clearReference()
                self._detail = f"Referans doğrulanamadı: {exc}"
        elif result.state == "completed" and self._run_condition == "tx_on_comparison":
            try:
                payload = compare_completed_surveys(Path(self._reference_audit), Path(result.audit_path))
                comparison_path = Path(result.audit_path).with_suffix(".ab.json")
                with comparison_path.open("x", encoding="utf-8") as stream:
                    json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
                    stream.write("\n")
                self._comparison_audit = str(comparison_path.resolve())
                self._detail = (
                    f"A/B tamamlandı: {payload['tx_correlated_observation_count']} değişen RF adayı, "
                    f"{payload['tx_correlated_energy_window_count']} güç artışı penceresi. "
                    "Farklar verici kimliğini kanıtlamaz; kapalı/açık tekrarı gerekir."
                )
            except (OSError, ValueError) as exc:
                self._invalidate_comparison()
                self._detail = f"Tarama tamamlandı; A/B kanıt dosyası üretilemedi: {exc}"
        else:
            self._invalidate_comparison()
            if result.state == "completed" and self._run_condition == "unspecified":
                regions = single_survey_energy_regions(self._completed_window_records)
                energy_rows = []
                for index, region in enumerate(regions):
                    energy_rows.append({
                        "eventId": f"local-energy:{index}",
                        "frequencyHz": region["peak_center_hz"],
                        "frequency": (
                            f"{region['lower_hz'] / 1e6:.3f}–"
                            f"{region['upper_hz'] / 1e6:.3f} MHz"
                        ),
                        "detail": (
                            f"Yerel tabandan +{region['peak_local_delta_db']:.1f} dB · "
                            f"{region['window_count']} komşu pencere"
                        ),
                        "window": (
                            f"Pencereler {region['first_window_index'] + 1}–"
                            f"{region['last_window_index'] + 1}"
                        ),
                        "latestWindow": False,
                        "evidenceKey": "energy_candidate",
                        "evidence": "ÖNE ÇIKAN ENERJİ",
                        "evidenceDetail": (
                            "Tek tur yerel kanal gücü; ikinci LO ve dış verici kanıtı değildir"
                        ),
                    })
                self._single_survey_energy_count = len(energy_rows)
                if energy_rows:
                    existing_ids = {row["eventId"] for row in energy_rows}
                    self._rows = energy_rows + [
                        row for row in self._rows if row["eventId"] not in existing_ids
                    ]
                    self._model.set_rows(self._rows)
            self._detail = "Bu turdaki geçmiş gözlemler; şu anda yayın yapıldığını göstermez."
        self.changed.emit()
        self.finished.emit(result.state)

    def _invalidate_comparison(self):
        if self._run_condition != "tx_on_comparison":
            return
        self._tx_correlated = self._energy_changes = self._current_energy_count = 0
        self._background = len(self._rows)
        self._comparison_audit = ""
        for row in self._rows:
            row.update(evidenceKey="uncertain", evidence="A/B: TAMAMLANMADI",
                       evidenceDetail="Tam tur bütünlüğü doğrulanamadı; bu satır A/B sonucu sayılamaz.")
        self._model.set_rows(self._rows)

    @Slot(str)
    def _failed(self, code):
        self._timer.stop()
        self._survey = None
        self._state = "Tarama hatası"
        self._invalidate_comparison()
        self._detail = f"Tarama tamamlanamadı: {code}"
        self.changed.emit()
        self.finished.emit("failed")
