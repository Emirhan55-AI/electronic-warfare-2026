"""Survey and fixed-frequency scan actions for the Qt Quick view model."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Slot

from algorithms.spectrum import SpectrumConfig, SpectrumProcessor

from .live_ed import (
    LIVE_INPUT_SAMPLE_RATE_HZ,
    LIVE_WIDEBAND_INPUT_SAMPLE_RATE_HZ,
    LIVE_STARTUP_SETTLING_FRAMES,
    LiveEDConfiguration,
)
from .quick_runtime import _LiveTask
from .rx_survey import SURVEY_MONITOR_CENTER_OFFSET_HZ, SurveyConfig


class QuickScanActionsMixin:
    """Coordinate RX scans without owning presentation state or DSP algorithms."""

    @Slot(result=bool)
    def toggleReceiverRFAmplifier(self) -> bool:
        """Toggle RF AMP while the receiver is stopped."""
        if self._closed or self._busy or self._live_session is not None:
            return False
        return self.setReceiverAndAudioSettings(
            not self._receiver_rf_amplifier, self._listening_deemphasis_us
        )

    @Slot(float, float, int, int)
    def startFrequencySurvey(self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db) -> None:
        self._start_frequency_survey(
            lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, "unspecified"
        )

    @Slot(float, float, int, int, str)
    def startSurveyProfile(self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, profile):
        self._start_frequency_survey(lower_mhz, upper_mhz, lna_gain_db, vga_gain_db,
                                     "unspecified", mode=profile)

    @Slot(float, float, int, int)
    def startReferenceSurvey(self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db) -> None:
        self._start_frequency_survey(
            lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, "tx_off_reference"
        )

    @Slot(float, float, int, int)
    def startComparisonSurvey(self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db) -> None:
        self._start_frequency_survey(
            lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, "tx_on_comparison"
        )

    def _start_frequency_survey(
        self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, operator_condition, *, mode="full"
    ) -> None:
        if self._closed:
            return
        if self._receiver_health_in_flight:
            QTimer.singleShot(
                50,
                lambda: self._start_frequency_survey(
                    lower_mhz,
                    upper_mhz,
                    lna_gain_db,
                    vga_gain_db,
                    operator_condition,
                    mode=mode,
                ),
            )
            return
        if (self._busy or self._source_mode != "hackrf"
                or not self._hackrf_ready or not self._hackrf_transfer_executable
                or self._active_receiver_serial is None):
            return
        try:
            config = SurveyConfig(
                round(lower_mhz * 1e6), round(upper_mhz * 1e6),
                lna_gain_db, vga_gain_db, operator_condition=operator_condition,
                frames_per_window=self._detection_settings["survey_frames"],
                guard_frames=self._detection_settings["survey_guard_frames"],
                mode=mode,
                rf_amplifier=self._receiver_rf_amplifier,
            )
        except (ValueError, OverflowError) as exc:
            self._show_error("invalid_survey_config", str(exc))
            return
        self._pending_survey_parameter_frequency_hz = None
        self._pending_survey_handoff = None
        if operator_condition == "tx_on_comparison" and not self._survey_controller.reference_matches(config, self._active_receiver_serial):
            self._show_error(
                "survey_reference_required",
                "Frekans sınırları, kazançlar ve gözlem süreleri TX kapalı referansla aynı değil.",
            )
            return
        self.stop()
        self._generation += 1
        self._close_source()
        self._clear_results()
        self._live_has_data = False
        self._live_frames_per_second = 0.0
        self._live_sample_rate_hz = 10_000_000 if mode == "wideband_burst" else 2_000_000
        self._receiver_sample_rate_hz = (
            LIVE_WIDEBAND_INPUT_SAMPLE_RATE_HZ if mode == "wideband_burst"
            else LIVE_INPUT_SAMPLE_RATE_HZ
        )
        self._source_name = "Alıcı ve FPGA"
        self._live_fpga_enabled = True
        self._live_response_at = self._live_received_at = 0.0
        self._source_state = "Çalışıyor"
        self._active_task_kind = "survey"
        self._playing = True
        condition_text = {
            "tx_off_reference": "TX kapalı referans taraması başlatılıyor.",
            "tx_on_comparison": "TX açık karşılaştırma taraması başlatılıyor.",
        }.get(
            operator_condition,
            "10 MS/s hızlı FPGA/ARM taraması başlatılıyor."
            if mode == "wideband_burst" else "Frekans taraması başlatılıyor.",
        )
        self._set_busy(True, condition_text)
        try:
            self._survey_controller.start(self._hackrf_transfer_executable, self._active_receiver_serial, config, self._pool)
        except Exception as exc:
            self._playing = False
            self._active_task_kind = ""
            self._set_busy(False, "Tarama başlatılamadı.")
            self._show_error("survey_start_failed", f"Tarama başlatılamadı: {exc}")
            return
        self._add_log("Tarama", f"{lower_mhz:g}–{upper_mhz:g} MHz · {condition_text}")

    @Slot(object)
    def _survey_preview(self, prepared):
        if self._closed or self._active_task_kind != "survey":
            return
        if prepared is None:
            self._spectral_display.clear()
            self._spectrum_values = []
            self.spectrumChanged.emit()
            return
        snapshot, spectrum = prepared
        self._live_response_at = time.perf_counter()
        self._live_has_data = True
        self._live_output_center_frequency_hz = snapshot.output_frame.center_frequency_hz
        self._frame_count = self._survey_controller._config.frames_per_window
        self._frame_index = snapshot.sequence_number
        self._update_spectrum_result(spectrum)
        self._status_message = self._survey_controller.coverageText
        self.pipelineChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def _survey_finished(self, state):
        if self._closed or self._active_task_kind != "survey":
            return
        self._busy = self._playing = False
        self._active_task_kind = ""
        self._source_state = "Hata" if state == "failed" else "Hazır" if self._live_has_data else "Kullanılmıyor"
        self._status_message = self._survey_controller.state + " · " + self._survey_controller.coverageText
        self._add_log("Tarama", self._status_message)
        self.pipelineChanged.emit()
        self.stateChanged.emit()
        handoff = self._pending_survey_handoff
        self._pending_survey_handoff = None
        if handoff is not None:
            kind, target_hz = handoff
            QTimer.singleShot(0, lambda: self._complete_survey_handoff(kind, target_hz))

    def _complete_survey_handoff(self, kind: str, target_hz: int) -> None:
        if self._closed or self._busy or self._survey_controller.running:
            if kind == "parameters":
                self._pending_survey_parameter_frequency_hz = None
            return
        if not self._start_survey_observation_monitoring(target_hz):
            if kind == "parameters":
                self._pending_survey_parameter_frequency_hz = None
            self._show_error(
                "survey_handoff_failed",
                "Seçili sinyal için sabit frekans alımı başlatılamadı.",
            )
            return
        if kind == "parameters":
            self._status_message = (
                "Parametre çıkarımı için seçilen sinyal 8 MS/s sabit alımda "
                "yeniden doğrulanıyor."
            )
            self._add_log("Parametre", self._status_message)
            self.stateChanged.emit()

    @Slot(result=bool)
    def monitorSurveyObservation(self):
        self._pending_survey_parameter_frequency_hz = None
        return self._request_survey_handoff("monitor")

    @Slot(result=bool)
    def openSurveyObservationParameters(self):
        frequency = self._survey_controller.selectedFrequency
        if frequency <= 0:
            return False
        self._pending_survey_parameter_frequency_hz = round(frequency)
        if self._request_survey_handoff("parameters"):
            if self._survey_controller.running:
                return True
            self._status_message = (
                "Parametre çıkarımı için seçilen sinyal 8 MS/s sabit alımda "
                "yeniden doğrulanıyor."
            )
            self._add_log("Parametre", self._status_message)
            self.stateChanged.emit()
            return True
        self._pending_survey_parameter_frequency_hz = None
        return False

    def _request_survey_handoff(self, kind: str) -> bool:
        frequency = self._survey_controller.selectedFrequency
        if frequency <= 0 or kind not in {"monitor", "parameters"}:
            return False
        target_hz = round(frequency)
        if self._survey_controller.running:
            if self._pending_survey_handoff is not None or self._survey_controller.state == "Durduruluyor":
                return False
            self._pending_survey_handoff = (kind, target_hz)
            self._status_message = (
                "Tarama güvenli biçimde durduruluyor; seçili sinyal sabit frekansta yeniden alınacak."
            )
            self._add_log("Tarama", self._status_message)
            self._survey_controller.cancel()
            self.stateChanged.emit()
            return True
        if self._busy:
            return False
        return self._start_survey_observation_monitoring(target_hz)

    def _monitor_survey_observation(self) -> bool:
        frequency = self._survey_controller.selectedFrequency
        if self._busy or frequency <= 0:
            return False
        return self._start_survey_observation_monitoring(round(frequency))

    def _start_survey_observation_monitoring(self, target_hz: int) -> bool:
        if self._busy or target_hz <= 0:
            return False
        config = self._survey_controller._config
        analysis_center_hz = target_hz - SURVEY_MONITOR_CENTER_OFFSET_HZ
        if analysis_center_hz < 1_000_000:
            analysis_center_hz = target_hz + SURVEY_MONITOR_CENTER_OFFSET_HZ
        self.startLiveEDSession(analysis_center_hz, config.lna_gain_db, config.vga_gain_db, 878_906)
        return self.liveSessionActive

    def _select_pending_survey_parameter_target(self) -> None:
        target_hz = self._pending_survey_parameter_frequency_hz
        if target_hz is None or self._live_session is None:
            return
        matches = [
            row for row in self._detections
            if row.get("stateKey") == "confirmed"
            and bool(row.get("observed", True))
            and (
                float(row.get("lowerFrequencyHz", row["frequencyHz"])) - 50_000.0
                <= target_hz
                <= float(row.get("upperFrequencyHz", row["frequencyHz"])) + 50_000.0
            )
        ]
        if not matches:
            return
        selected = min(matches, key=lambda row: abs(float(row["frequencyHz"]) - target_hz))
        event_id = int(selected["eventId"])
        if self._selected_detection_id != event_id:
            self.selectDetection(event_id)
        if self.measurementSelectionReady:
            self._pending_survey_parameter_frequency_hz = None
            self.surveyParameterReady.emit()

    def _select_pending_listening_target(self) -> None:
        target_hz = self._pending_listening_frequency_hz
        if target_hz is None or self._live_session is None:
            return
        matches = [
            row for row in self._detections
            if row.get("stateKey") == "confirmed"
            and bool(row.get("observed", True))
            and (
                float(row.get("lowerFrequencyHz", row["frequencyHz"])) - 50_000.0
                <= target_hz
                <= float(row.get("upperFrequencyHz", row["frequencyHz"])) + 50_000.0
            )
        ]
        if not matches:
            return
        selected = min(matches, key=lambda row: abs(float(row["frequencyHz"]) - target_hz))
        event_id = int(selected["eventId"])
        if self._selected_detection_id != event_id:
            self.selectDetection(event_id)
        self._pending_listening_frequency_hz = None
        self._status_message = "Ölçülen sinyal yeniden doğrulandı; dinleme tamponu dolduruluyor."
        self._add_log("Dinleme", self._status_message)
        self.stateChanged.emit()

    @Slot(float, int, int, int)
    def startRXPreview(self, center_hz, lna_gain_db, vga_gain_db, frame_count):
        self.startLiveEDSession(center_hz, lna_gain_db, vga_gain_db, frame_count, fpga_enabled=False)

    @Slot(float, int, int, int)
    def startLiveEDSession(
        self,
        output_center_frequency_hz: float,
        lna_gain_db: int,
        vga_gain_db: int,
        frame_count: int,
        *,
        fpga_enabled: bool = True,
        preserve_fixed_context: bool = False,
        preserve_direction: bool = False,
    ) -> None:
        if self._closed:
            return
        if self._receiver_health_in_flight:
            QTimer.singleShot(
                50,
                lambda: self.startLiveEDSession(
                    output_center_frequency_hz,
                    lna_gain_db,
                    vga_gain_db,
                    frame_count,
                    fpga_enabled=fpga_enabled,
                    preserve_fixed_context=preserve_fixed_context,
                    preserve_direction=preserve_direction,
                ),
            )
            return
        if (
            self._source_mode != "hackrf"
            or not self._hackrf_ready
            or not self._hackrf_transfer_executable
            or self._busy
            or self._live_session is not None
            or self._active_receiver_serial is None
        ):
            return
        try:
            configuration = LiveEDConfiguration(
                output_center_frequency_hz=int(output_center_frequency_hz),
                lna_gain_db=int(lna_gain_db),
                vga_gain_db=int(vga_gain_db),
                frame_count=int(frame_count),
                device_serial=self._active_receiver_serial,
                # Every DSP frame is processed; only presentation is sampled.
                # The GUI mailbox bounds queued display work even during a stall.
                display_interval_frames=self._detection_settings["display_interval_frames"],
                startup_settling_frames=LIVE_STARTUP_SETTLING_FRAMES,
                display_fft_size=self._detection_settings["display_fft_size"],
                fpga_fft_size=(
                    self._card_detection_profile.fft_size
                    if fpga_enabled and self._card_detection_profile is not None and
                    self._card_detection_profile.runtime_fft_supported else 4096),
                fpga_enabled=fpga_enabled,
                rf_amplifier=self._receiver_rf_amplifier,
            )
        except Exception as exc:
            self._show_error(str(getattr(exc, "code", "invalid_rx_config")), str(exc))
            return
        same_fixed_settings = (
            self._live_receive_settings.get("rf_amplifier", False) == configuration.rf_amplifier
            and int(self._live_receive_settings.get("center_hz", -1))
            == configuration.output_center_frequency_hz
            and int(self._live_receive_settings.get("lna_db", -1))
            == configuration.lna_gain_db
            and int(self._live_receive_settings.get("vga_db", -1))
            == configuration.vga_gain_db
        )
        retained_history = (
            [dict(row) for row in self._live_detection_history]
            if same_fixed_settings else []
        )
        self.stop()
        if not preserve_fixed_context and not same_fixed_settings:
            self._fixed_verification_records.clear()
        if not preserve_fixed_context:
            self._fixed_verification_candidate = None
            self._fixed_verification_queue.clear()
            self._fixed_verifier = None
            self._fixed_verification_stop_requested = False
            self._fixed_resume_settings = None
            self._fixed_preserved_history = []
        self._generation += 1
        generation = self._generation
        self._live_catalog_session_id = f"{self._measurement_namespace}:{generation}"
        self._close_source()
        self._clear_results(keep_spectrum=same_fixed_settings, keep_direction=preserve_direction)
        if retained_history:
            self._live_detection_history = [
                self._last_observation(self._apply_fixed_verification(row))
                for row in retained_history
            ]
            self._refresh_live_detection_list(force=True)
        self._live_spur_guard_binding = None
        self._live_spur_guard_power.clear()
        self._live_spur_guard_passed.clear()
        self._live_has_data = False
        self._live_output_center_frequency_hz = configuration.output_center_frequency_hz
        self._receiver_sample_rate_hz = configuration.rx_config.sample_rate_hz
        self._spectrum_center_frequency_hz = float(configuration.input_center_frequency_hz)
        self._spectrum_sample_rate_hz = 8_000_000.0
        self._live_receive_settings = {
            "center_hz": configuration.output_center_frequency_hz,
            "lna_db": configuration.lna_gain_db, "vga_db": configuration.vga_gain_db,
            "rf_amplifier": configuration.rf_amplifier,
        }
        self.liveReceiveSettingsChanged.emit()
        self._live_presentation_error = None
        self._live_received_at = self._live_response_at = 0.0
        self._live_fpga_enabled = configuration.fpga_enabled
        self._live_sample_rate_hz = 2_000_000
        self._live_frames_per_second = 0.0
        self._frame_index = 0
        self._frame_count = configuration.frame_count
        self._source_name = "Alıcı ve FPGA"
        self._source_state = "Çalışıyor"
        self._status_message = "Sabit frekans taraması başlatılıyor."
        if not configuration.fpga_enabled:
            self._source_name = "Alıcı"
            self._status_message = "Yalnız gerçek alım görüntüsü başlatılıyor; FPGA tespiti yapılmayacak."
        self._error_title = ""
        self._error_message = ""
        self._playing = True
        session = self._live_session_factory(self._hackrf_transfer_executable, configuration)
        self._live_session = session
        task = _LiveTask(generation, session)
        task.processor = SpectrumProcessor(self._pipeline.processor.config)
        if configuration.display_fft_size != 16384:
            task.display_processor = SpectrumProcessor(SpectrumConfig(frame_length=configuration.display_fft_size))
        task.signals.snapshot.connect(self._live_snapshot)
        task.signals.preview.connect(self._live_preview)
        task.signals.coarse.connect(self._live_coarse)
        task.signals.coarseFailed.connect(self._live_coarse_failed)
        task.signals.completed.connect(self._live_completed)
        task.signals.failed.connect(self._live_failed)
        self._active_task_kind = "live"
        self._busy = True
        self._add_log("Canlı ED", "Alıcı → kanal seçici → FPGA taraması başlatıldı"
                      if configuration.fpga_enabled else "Yalnız RX önizleme başlatıldı; FPGA tespiti kapalı")
        self.pipelineChanged.emit()
        self.stateChanged.emit()
        self._start_retained_task(self._pool, task)
        self._live_health_timer.start()

    @Slot()
    def stopLiveEDSession(self) -> None:
        self.cancelDirectionMeasurement()
        if self._live_session is None and self._fixed_verifier is None:
            return
        self._fixed_verification_queue.clear()
        self._fixed_verification_stop_requested = True
        self._pending_listening_frequency_hz = None
        self._status_message = "Canlı ED oturumu durduruluyor…"
        if self._live_session is not None:
            self._live_session.cancel()
        if self._fixed_verifier is not None:
            self._fixed_verifier.cancel()
        self.stateChanged.emit()

    @Slot()
    def startScan(self) -> None:
        if self._source is None or self._busy:
            return
        if self._parameter_rows:
            self.clearDetectionSelection()
        was_playing = self._playing
        if self._measurement_requested:
            self._measurement_requested = False
            self._parameter_rows = []
            self.detectionsChanged.emit()
        self._playing = True
        self._status_message = "Sinyal taraması çalışıyor."
        self._timer.start()
        self._request_frame()
        if not was_playing:
            self._add_log("İşleme", "Sinyal taraması başlatıldı")
            self.pipelineChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def pause(self) -> None:
        if self._survey_controller.running:
            self._survey_controller.cancel()
            return
        if self._live_session is not None:
            self.stopLiveEDSession()
            return
        if self._fixed_verifier is not None:
            self._fixed_verification_queue.clear()
            self._fixed_verification_stop_requested = True
            self._fixed_verifier.cancel()
            return
        was_playing = self._playing
        self._playing = False
        self._timer.stop()
        if self._source is not None:
            self._status_message = "Tarama duraklatıldı."
            if was_playing:
                self._add_log("İşleme", "Sinyal taraması duraklatıldı")
                self.pipelineChanged.emit()
            self.stateChanged.emit()

    @Slot()
    def stop(self) -> None:
        self.cancelDirectionMeasurement()
        self._survey_controller.cancel()
        if self._live_session is not None:
            self._live_session.cancel()
        if self._fixed_verifier is not None:
            self._fixed_verification_stop_requested = True
            self._fixed_verifier.cancel()
        self._playing = False
        self._timer.stop()
