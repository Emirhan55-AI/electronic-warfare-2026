"""Worker completion and failure publication for the Qt Quick view model."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import Slot

from algorithms.monitoring import AnalogMonitorResult
from algorithms.p0.df import FIELD_AMPLITUDE_DF_PROFILE
from algorithms.p0.direction_client import BoardDFEstimate
from algorithms.pipeline import RuntimeFrameResult
from .fixed_band_verification import FixedBandVerification
from .live_ed import LIVE_AUDIO_WINDOW_SECONDS
from .measurement_record import RecordedMeasurement
from .quick_runtime import ERROR_TEXT


def _analog_voice_bandwidth_khz(occupied_bandwidth_hz: float) -> float:
    return max(6.0, min(25.0, 1.2 * float(occupied_bandwidth_hz) / 1_000.0))


class QuickTaskCompletionMixin:
    """Publish bounded worker results on the GUI thread."""

    @Slot(int, str, object, float)
    def _task_completed(self, generation: int, kind: str, result: object, elapsed: float) -> None:
        self._busy = False
        self._active_task_kind = ""
        if generation != self._generation:
            if hasattr(result, "close"):
                result.close()  # type: ignore[attr-defined]
            if kind != "frame":
                self.pipelineChanged.emit()
            self.stateChanged.emit()
            return
        if kind == "fixed_verify":
            if not isinstance(result, FixedBandVerification):
                self._show_error("fixed_verification_result", "Sabit bant doğrulama sonucu geçersiz.")
                self.stateChanged.emit()
                return
            record = self._fixed_verification_record(result.candidate.frequency_hz)
            if record is not None:
                record.update(state=result.state, result=result)
            resume = self._fixed_resume_settings
            preserved = [self._apply_fixed_verification(row) for row in self._fixed_preserved_history]
            self._fixed_verification_candidate = None
            self._fixed_verifier = None
            self._fixed_verification_stop_requested = False
            self._fixed_resume_settings = None
            self._fixed_preserved_history = []
            if resume is None:
                self._show_error("fixed_verification_resume", "Sabit bant görünümü yeniden başlatılamadı.")
                self.stateChanged.emit()
                return
            center_hz = resume["center_hz"]
            self._status_message = (
                (
                    "Aday FPGA tarafından iki alıcı ayarında yeniden görüldü; görünüm sürdürülüyor."
                    if result.verification_method == "fpga"
                    else "Aday alıcı spektrumunda iki fiziksel ayarda yeniden görüldü; FPGA görünümü sürdürülüyor."
                )
                if result.verified else
                "Aday ikinci ayarlarda yeniden görülmedi; önceki görünüm sürdürülüyor."
            )
            self._add_log("Sabit bant doğrulama", self._status_message)
            self.startLiveEDSession(
                center_hz,
                resume["lna_db"],
                resume["vga_db"],
                resume["frame_count"],
                preserve_fixed_context=True,
            )
            if self._live_session is not None:
                self._live_detection_history = preserved
                self._refresh_live_detection_list(force=True)
            return
        if kind == "open":
            self._install_source(result, Path(getattr(result, "metadata_path")).name)
        elif kind == "probe":
            inventory, device, fpga_ready, fpga_reason, portapack_error = result  # type: ignore[misc]
            self._apply_probe(inventory, device, fpga_ready, fpga_reason, portapack_error)
        elif kind == "frame":
            if not isinstance(result, RuntimeFrameResult):
                self._show_error("processing_failed", "İşleme sonucu sözleşmeyle eşleşmedi.")
                return
            self._operation_samples_ms.append(elapsed * 1000.0)
            self._operation_samples_ms = self._operation_samples_ms[-256:]
            self._last_result = result
            self._update_spectrum(result)
            self._update_detections(result)
            self._status_message = f"Kare {self._frame_index + 1}/{self._frame_count} işlendi."
            if self._pending_frame:
                self._pending_frame = False
                self._advance()
        elif kind == "measurement":
            self._measurement_requested = False
            if not isinstance(result, RecordedMeasurement) or self._parameter_capability is None:
                self._show_error("measurement_failed", "Parametre sonucu sözleşmeyle eşleşmedi.")
                return
            if (
                result.persistent_payload_limit <= 0
                or result.result.persistent_payload_bytes > result.persistent_payload_limit
            ):
                self._show_error("measurement_failed", "Parametre ölçümü kalıcı bellek sınırını aştı.")
                return
            self._measurement_record_path = str(result.path)
            self._measurement_info = {"completedUtc": result.completed_utc, "durationMs": result.observation_duration_s * 1000.0}
            self._add_log("Parametre kaydı", f"{result.path} · SHA-256 {result.sha256}")
            result = result.result
            pending_direction = self._pending_direction_measurement
            if pending_direction is not None:
                self._pending_direction_measurement = None
                self._df_capture_message = ""
                power_field = result.channel_power_dbfs
                resume = pending_direction["resume_settings"]
                if (
                    power_field.state == "valid"
                    and isinstance(power_field.value, (int, float))
                    and math.isfinite(float(power_field.value))
                ):
                    self._commit_direction_measurement(
                        antenna_angle_deg=float(pending_direction["antenna_angle_deg"]),
                        reference=str(pending_direction["reference"]),
                        reference_deg=float(pending_direction["reference_deg"]),
                        relative_power_db=float(power_field.value),
                        frequency_hz=float(pending_direction["frequency_hz"]),
                        bandwidth_hz=float(pending_direction["bandwidth_hz"]),
                        receiver_binding=str(pending_direction["receiver_binding"]),
                        frame_id=(
                            int(pending_direction["frame_id"])
                            if pending_direction["frame_id"] is not None else None
                        ),
                        board_endpoint=tuple(pending_direction["board_endpoint"]),
                    )
                    if self.directionDistinctAngleCount < FIELD_AMPLITUDE_DF_PROFILE.minimum_distinct_angles:
                        self._status_message = (
                            f"{float(pending_direction['antenna_angle_deg']):.1f}° kart PL/ARM "
                            "kanal gücü kaydedildi; alım yeniden başlatılıyor."
                        )
                else:
                    self._df_status = "Kart kanal gücü bu açıda geçerli ölçülemedi."
                    self._df_capture_message = self._df_status
                    self._df_relative = "—"
                    self._df_bearing = "—"
                    self._status_message = self._df_status
                    self.directionChanged.emit()
                if (
                    self.directionDistinctAngleCount < FIELD_AMPLITUDE_DF_PROFILE.minimum_distinct_angles
                    and isinstance(resume, dict)
                ):
                    self.startLiveEDSession(
                        int(resume["center_hz"]),
                        int(resume["lna_db"]),
                        int(resume["vga_db"]),
                        int(resume["frame_count"]),
                        preserve_direction=True,
                    )
            else:
                center_field = result.emission_center_frequency
                bandwidth_field = result.occupied_bandwidth
                if (
                    center_field.state == "valid"
                    and isinstance(center_field.value, (int, float))
                    and math.isfinite(float(center_field.value))
                ):
                    self._listening_parameter_target_hz = float(center_field.value)
                    if (
                        bandwidth_field.state == "valid"
                        and isinstance(bandwidth_field.value, (int, float))
                        and math.isfinite(float(bandwidth_field.value))
                    ):
                        self._listening_parameter_bandwidth_khz = _analog_voice_bandwidth_khz(
                            float(bandwidth_field.value)
                        )
                    else:
                        self._listening_parameter_bandwidth_khz = 16.0
                    self._listening_parameter_record_path = self._measurement_record_path
                    self.listeningChanged.emit()
                self._parameter_rows = self._f5_parameter_rows(result)
                self._status_message = f"Tespit #{self._selected_detection_id} parametre ölçümü tamamlandı."
                self._add_log("Parametre", self._status_message)
                self.detectionsChanged.emit()
        elif kind == "direction":
            if not isinstance(result, BoardDFEstimate):
                self._show_error("direction_failed", "Kart ARM yön sonucu sözleşmeyle eşleşmedi.")
                return
            self._apply_direction_estimate(result.estimate)
            self._status_message = "Genlik tabanlı yön sonucu kart ARM'ında doğrulandı."
            self._add_log("Yön Bulma", self._status_message)
            self.directionChanged.emit()
        elif kind == "listening":
            if not isinstance(result, tuple) or len(result) != 6 or not isinstance(result[0], AnalogMonitorResult):
                self._show_error("insufficient_audio", "Dinleme sonucu sözleşmeyle eşleşmedi.")
                return
            listening, _scope, input_duration, offset_hz, bandwidth_hz, _continuity = result
            self._listening_result = listening
            self._audio_playback.load(listening.pcm16)
            self._playback_timer.stop()
            self._listening_playback_position_s = 0.0
            self._listening_playback_duration_s = self._audio_playback.duration_seconds
            self._listening_playback_state = "Oynatmaya hazır"
            self._listening_short_preview = float(input_duration) < LIVE_AUDIO_WINDOW_SECONDS
            channel_frequency = self.centerFrequencyHz + float(offset_hz)
            self._listening_rows = [
                {"label": "Yayın türü", "value": "AM" if listening.mode == "am" else "Dar Bant FM (NFM)"},
                {"label": "Frekans", "value": self._format_frequency(channel_frequency)},
                {"label": "Alım bant genişliği", "value": self._format_rate(float(bandwidth_hz))},
                {"label": "Ses profili", "value": (
                    f"Telsiz düzeltmesi ({listening.nfm_deemphasis_us:g} µs)"
                    if listening.mode == "nfm" and listening.nfm_deemphasis_us > 0
                    else "Net ses")},
            ]
            if listening.channel_power_dbfs_trace:
                power_low = min(listening.channel_power_dbfs_trace)
                power_high = max(listening.channel_power_dbfs_trace)
                frequency_low = min(listening.residual_frequency_hz_trace)
                frequency_high = max(listening.residual_frequency_hz_trace)
                self._listening_rows.extend(
                    [
                        {
                            "label": "Alım seviyesi",
                            "value": f"{power_low:.2f}…{power_high:.2f} dBFS",
                        },
                        {
                            "label": "Frekans sapması",
                            "value": f"{frequency_low:+.1f}…{frequency_high:+.1f} Hz",
                        },
                    ]
                )
            self._listening_observation_points = [
                {"time": float(time_s), "power": float(power_dbfs), "frequency": float(frequency_hz)}
                for time_s, power_dbfs, frequency_hz in zip(
                    listening.observation_times_s,
                    listening.channel_power_dbfs_trace,
                    listening.residual_frequency_hz_trace,
                )
            ]
            waveform_points = min(720, listening.audio.size)
            indices = np.linspace(0, listening.audio.size - 1, waveform_points, dtype=np.int64)
            self._listening_waveform = [float(listening.audio[index]) for index in indices]
            self._listening_state = (
                "Kısa önizleme hazır; kesintisiz dinleme kabulü için en az 5 saniyelik kayıt gerekir."
                if self._listening_short_preview
                else "Ses hazır."
            )
            self._status_message = f"Tespit #{self._selected_detection_id} dinleme kanalı hazırlandı."
            self._add_log("Dinleme", self._status_message)
            self.playbackChanged.emit()
            self.listeningChanged.emit()
        elif kind == "wav_export":
            self._status_message = f"WAV kaydedildi: {Path(str(result)).name}"
            self._listening_state = self._status_message
            self._add_log("Dinleme", self._status_message)
            self.listeningChanged.emit()
        if kind != "frame":
            self.pipelineChanged.emit()
        self.stateChanged.emit()

    @Slot(int, str, str)
    def _task_failed(self, generation: int, code: str, detail: str) -> None:
        self._busy = False
        task_kind = self._active_task_kind
        self._active_task_kind = ""
        if generation == self._generation:
            if task_kind == "fixed_verify":
                candidate = self._fixed_verification_candidate
                resume = self._fixed_resume_settings
                if candidate is not None:
                    record = self._fixed_verification_record(candidate.frequency_hz)
                    if record is not None:
                        record.update(state="verification_error", result=None)
                stopped = self._fixed_verification_stop_requested or self._closed
                self._fixed_verification_candidate = None
                self._fixed_verifier = None
                self._fixed_verification_stop_requested = False
                self._fixed_resume_settings = None
                self._fixed_preserved_history = []
                if stopped and code == "operation_cancelled":
                    self._source_state = "Hazır" if self._live_has_data else "Kullanılmıyor"
                    self._status_message = "Sabit frekans taraması durduruldu."
                elif resume is not None and not self._closed:
                    self._add_log(
                        "Sabit bant doğrulama",
                        "İkinci alıcı ayarı tamamlanamadı; ana görünüm yeniden başlatılıyor.",
                    )
                    self.startLiveEDSession(
                        resume["center_hz"],
                        resume["lna_db"],
                        resume["vga_db"],
                        resume["frame_count"],
                        preserve_fixed_context=True,
                    )
                else:
                    self._show_error(code, detail)
                self.pipelineChanged.emit()
                self.stateChanged.emit()
                return
            if task_kind == "measurement":
                self._measurement_requested = False
                pending_direction = self._pending_direction_measurement
                self._pending_direction_measurement = None
                if pending_direction is not None:
                    resume = pending_direction.get("resume_settings")
                    self._df_status = "Kart kanal gücü ölçümü tamamlanamadı; bu açı kaydedilmedi."
                    self._df_capture_message = self._df_status
                    self._df_relative = "—"
                    self._df_bearing = "—"
                    self.directionChanged.emit()
                    if isinstance(resume, dict):
                        self.startLiveEDSession(
                            int(resume["center_hz"]),
                            int(resume["lna_db"]),
                            int(resume["vga_db"]),
                            int(resume["frame_count"]),
                            preserve_direction=True,
                        )
                    self.pipelineChanged.emit()
                    self.stateChanged.emit()
                    return
            if task_kind == "direction":
                self._df_status = "Kart ARM yön hesabı tamamlanamadı."
                self._df_relative = "—"
                self._df_bearing = "—"
                self.directionChanged.emit()
            if task_kind in {"listening", "wav_export"}:
                self._listening_state = ERROR_TEXT.get(code, f"Dinleme işlemi tamamlanamadı ({code}).")
                self._add_log("Dinleme", self._listening_state)
                self.listeningChanged.emit()
            else:
                self._show_error(code, detail)
        self.pipelineChanged.emit()
        self.stateChanged.emit()
