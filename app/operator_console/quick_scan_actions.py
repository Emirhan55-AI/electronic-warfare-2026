"""Survey and fixed-frequency scan actions for the Qt Quick view model."""

from __future__ import annotations

import time

from PySide6.QtCore import Slot

from algorithms.spectrum import SpectrumProcessor

from .live_ed import LiveEDConfiguration
from .quick_runtime import _LiveTask
from .rx_survey import SURVEY_MONITOR_CENTER_OFFSET_HZ, SurveyConfig


class QuickScanActionsMixin:
    """Coordinate RX scans without owning presentation state or DSP algorithms."""

    @Slot(float, float, int, int)
    def startFrequencySurvey(self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db) -> None:
        self._start_frequency_survey(
            lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, "unspecified"
        )

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
        self, lower_mhz, upper_mhz, lna_gain_db, vga_gain_db, operator_condition
    ) -> None:
        if (self._closed or self._busy or self._source_mode != "hackrf"
                or not self._hackrf_ready or not self._hackrf_transfer_executable
                or self._device_config.serial is None):
            return
        try:
            config = SurveyConfig(
                round(lower_mhz * 1e6), round(upper_mhz * 1e6),
                lna_gain_db, vga_gain_db, operator_condition=operator_condition,
            )
        except (ValueError, OverflowError) as exc:
            self._show_error("invalid_survey_config", str(exc))
            return
        if operator_condition == "tx_on_comparison" and not self._survey_controller.reference_matches(config, self._device_config.serial):
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
        self._live_sample_rate_hz = 2_000_000
        self._source_name = "Alıcı ve FPGA"
        self._live_fpga_enabled = True
        self._live_response_at = self._live_received_at = 0.0
        self._source_state = "Çalışıyor"
        self._active_task_kind = "survey"
        self._playing = True
        condition_text = {
            "tx_off_reference": "TX kapalı referans taraması başlatılıyor.",
            "tx_on_comparison": "TX açık karşılaştırma taraması başlatılıyor.",
        }.get(operator_condition, "Frekans taraması başlatılıyor.")
        self._set_busy(True, condition_text)
        self._survey_controller.start(self._hackrf_transfer_executable, self._device_config.serial, config, self._pool)
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

    @Slot(result=bool)
    def monitorSurveyObservation(self):
        frequency = self._survey_controller.selectedFrequency
        if self._busy or frequency <= 0:
            return False
        config = self._survey_controller._config
        target_hz = round(frequency)
        analysis_center_hz = target_hz - SURVEY_MONITOR_CENTER_OFFSET_HZ
        if analysis_center_hz < 1_000_000:
            analysis_center_hz = target_hz + SURVEY_MONITOR_CENTER_OFFSET_HZ
        self.startLiveEDSession(analysis_center_hz, config.lna_gain_db, config.vga_gain_db, 878_906)
        return self.liveSessionActive

    @Slot(float, int, int, int, bool)
    def startManagedLiveEDSession(self, center_hz, lna_gain_db, vga_gain_db, frame_count, automatic):
        if self._busy or self._live_session is not None:
            return
        self._managed_gain = {"visited": set(), "attempts": 0} if automatic else None
        self.startLiveEDSession(center_hz, lna_gain_db, vga_gain_db, frame_count, managed_gain=automatic)

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
        managed_gain: bool = False,
    ) -> None:
        if (
            self._source_mode != "hackrf"
            or not self._hackrf_ready
            or not self._hackrf_transfer_executable
            or self._busy
            or self._live_session is not None
            or self._device_config.serial is None
        ):
            return
        try:
            configuration = LiveEDConfiguration(
                output_center_frequency_hz=int(output_center_frequency_hz),
                lna_gain_db=int(lna_gain_db),
                vga_gain_db=int(vga_gain_db),
                frame_count=int(frame_count),
                device_serial=self._device_config.serial,
                # Every DSP frame is processed; only presentation is sampled.
                # The GUI mailbox bounds queued display work even during a stall.
                display_interval_frames=15,
                fpga_enabled=fpga_enabled,
                assess_receive_level=managed_gain,
            )
        except Exception as exc:
            self._show_error(str(getattr(exc, "code", "invalid_rx_config")), str(exc))
            return
        if not managed_gain:
            self._managed_gain = None
        elif self._managed_gain is not None:
            self._managed_gain["visited"].add((configuration.lna_gain_db, configuration.vga_gain_db))
            self._managed_gain["attempts"] += 1
        same_fixed_settings = (
            int(self._live_receive_settings.get("center_hz", -1))
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
        self._close_source()
        self._clear_results(keep_spectrum=same_fixed_settings)
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
        self._spectrum_center_frequency_hz = float(configuration.input_center_frequency_hz)
        self._spectrum_sample_rate_hz = 8_000_000.0
        self._live_receive_settings = {
            "center_hz": configuration.output_center_frequency_hz,
            "lna_db": configuration.lna_gain_db, "vga_db": configuration.vga_gain_db,
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
        self._pool.start(task)
        self._live_health_timer.start()

    @Slot()
    def stopLiveEDSession(self) -> None:
        self._managed_gain = None
        if self._live_session is None and self._fixed_verifier is None:
            return
        self._fixed_verification_queue.clear()
        self._fixed_verification_stop_requested = True
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
        self._survey_controller.cancel()
        if self._live_session is not None:
            self._live_session.cancel()
        if self._fixed_verifier is not None:
            self._fixed_verification_stop_requested = True
            self._fixed_verifier.cancel()
        self._playing = False
        self._timer.stop()
