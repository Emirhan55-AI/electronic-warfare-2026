"""Durum güncelleme metotları mixin'i."""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QListWidgetItem
import numpy as np

from algorithms.sigmf.contract import ContractReport
from algorithms.detection import DetectionEvent, DetectionFrameResult
from algorithms.parameters import ParameterFrameResult
from algorithms.p0.models import P0ParameterResult
from algorithms.p0.search import P0SearchEngine
from .ui_text import TEXT

def _source_display_name(value: str) -> str:
    return {
        "REPLAY": "KAYIT OYNATMA",
        "HOST/SYNTHETIC": "YAZILIM REFERANS VERİSİ",
    }.get(value, value)


class StateMixin:
    def show_empty(self) -> None:
        self.source_value.setText(TEXT["no_source"])
        self.listening_source_value.setText(TEXT["no_source"])
        for value in self.metadata_values.values():
            value.setText("—")
        self._refresh_source_summary()
        self.state_value.setText(TEXT["empty"])
        if hasattr(self, "status_source_label"):
            self.status_source_label.setText("Kaynak: " + TEXT["no_source"])
            self.status_state_label.setText("Durum: " + TEXT["empty"])
        self.spectrum_view.clear_all()
        self.clear_detections()
        self.clear_parameters()
        self.clear_listening()
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def set_acquisition_mode(self, mode: str) -> None:
        is_hackrf = mode == "hackrf"
        self.hackrf_panel.setVisible(is_hackrf)
        self.open_button.setVisible(not is_hackrf)
        self.open_button.setText(TEXT["open_test_source"] if mode == "deterministic_test" else TEXT["open_sigmf"])
        if is_hackrf:
            self.set_hackrf_state("acceptance_pending")

    def set_hackrf_state(self, state: str) -> None:
        mapping = {
            "acceptance_pending": TEXT["hardware_acceptance_pending"],
            "tools_missing": TEXT["hackrf_tools_missing"] + " · " + TEXT["live_rx_unavailable"],
            "searching": TEXT["device_searching"],
            "device_missing": TEXT["hackrf_device_missing"] + " · " + TEXT["live_rx_unavailable"],
            "serial_unassigned": "HackRF bulundu; ED_RX seri kimliği atanmadı. Canlı alım kapalı.",
            "configured_device_missing": "Yapılandırılmış ED_RX seri kimliği bağlı cihazlar arasında bulunamadı.",
            "device_ready": TEXT["device_ready"],
            "capture_starting": TEXT["capture_starting"],
            "live": TEXT["live_capture"],
            "stopped": TEXT["capture_stopped"],
            "disconnected": TEXT["device_disconnected"],
            "timeout": TEXT["operation_timeout"],
            "test_source": TEXT["deterministic_source_active"],
            "cli_error": TEXT["hackrf_cli_error"],
        }
        self.hackrf_status.setText(mapping[state])
        ready = state in {"device_ready", "stopped"}
        busy = state in {"searching", "capture_starting", "live"}
        self.hackrf_refresh_button.setEnabled(not busy)
        self.hackrf_start_button.setEnabled(ready)
        self.hackrf_stop_button.setEnabled(busy)
        for widget in (
            self.hackrf_center_spin,
            self.hackrf_sample_combo,
            self.hackrf_lna_spin,
            self.hackrf_vga_spin,
            self.hackrf_amp_checkbox,
        ):
            widget.setEnabled(ready)

        tools_ready = state not in {"acceptance_pending", "tools_missing"}
        self.system_status_values["hackrf_tools"].setText("Hazır" if tools_ready else "Kullanılamıyor" if state == "tools_missing" else "Denetlenmedi")
        if state in {"device_ready", "capture_starting", "live", "stopped"}:
            self.system_status_values["hackrf"].setText("Bağlı")
        elif state == "serial_unassigned":
            self.system_status_values["hackrf"].setText("Seri Seçimi Gerekli")
        elif state == "configured_device_missing":
            self.system_status_values["hackrf"].setText("Yapılandırılmış Cihaz Yok")
        else:
            self.system_status_values["hackrf"].setText("Bağlı Değil")
        self.system_status_values["rx"].setText("Aktif" if state == "live" else "Durduruldu")
        self.system_status_values["source"].setText(
            "HackRF Canlı RX" if state == "live" else "HackRF Canlı RX · Etkin değil"
        )
        if state in {"device_missing", "tools_missing", "acceptance_pending"}:
            self.system_status_values["center"].setText("—")
            self.system_status_values["sampling"].setText("—")

    def set_hackrf_configuration(self, serial: str | None) -> None:
        self._configured_hackrf_serial = serial
        self.system_status_values["serial"].setText(serial if serial is not None else "Atanmadı")

    def set_hackrf_runtime(self, *, center_frequency_hz: int, sample_rate_hz: int, dropped_frames: int = 0) -> None:
        self.system_status_values["center"].setText(self._frequency(float(center_frequency_hz)))
        self.system_status_values["sampling"].setText(self._sample_rate(float(sample_rate_hz)))
        self.system_status_values["dropped"].setText(str(dropped_frames))

    @property
    def source_kind(self) -> str:
        return str(self.source_type_combo.currentData())

    @property
    def hackrf_settings(self) -> dict[str, int | bool]:
        return {
            "center_frequency_hz": round(self.hackrf_center_spin.value() * 1_000_000),
            "sample_rate_hz": int(self.hackrf_sample_combo.currentData()),
            "sample_count": 16_384,
            "rf_amplifier": self.hackrf_amp_checkbox.isChecked(),
            "lna_gain_db": self.hackrf_lna_spin.value(),
            "vga_gain_db": self.hackrf_vga_spin.value(),
        }

    def show_opening(self) -> None:
        self.state_value.setText(TEXT["opening_source"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT["opening_source"])
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def finish_opening(self, *, source_available: bool) -> None:
        self.set_source_controls_enabled(source_available)
        self.state_value.setText(TEXT["ready"] if source_available else TEXT["empty"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + (TEXT["ready"] if source_available else TEXT["empty"]))

    def set_replay_source_badge(self, badge: str) -> None:
        self._replay_source_badge = badge.strip() or "KAYIT OYNATMA"
        if self.metadata_values["center_frequency"].text() != "—":
            self._refresh_source_summary()

    def set_source(self, filename: str, report: ContractReport) -> None:
        self.source_value.setText(Path(filename).name)
        self.listening_source_value.setText(Path(filename).name)
        if hasattr(self, "status_source_label"):
            self.status_source_label.setText(f"Kaynak: {Path(filename).name}")
        self.metadata_values["center_frequency"].setText(self._frequency(report.center_frequency))
        self.metadata_values["sample_rate"].setText(self._sample_rate(report.sample_rate))
        self.metadata_values["datatype"].setText(report.source_datatype or "—")
        self.metadata_values["frame_length"].setText(
            self.locale.toString(report.frame_length) + " örnek"
        )
        self.metadata_values["channel"].setText("1")
        frame_count = report.full_frame_count or 0
        self.frame_spin.setMaximum(max(frame_count, 1))
        self.set_frame_position(0, frame_count)
        self.set_source_controls_enabled(frame_count > 0)
        self._refresh_source_summary()
        self.state_value.setText(TEXT["ready"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT["ready"])
        self.system_status_values["source"].setText(
            "HACKRF KAYDI · Aktif" if self._replay_source_badge == "HACKRF KAYDI" else "SigMF kaydı · Aktif"
        )
        self.system_status_values["center"].setText(self._frequency(report.center_frequency))
        self.system_status_values["sampling"].setText(self._sample_rate(report.sample_rate))
        self.system_status_values["rx"].setText("Replay aktif")
        self.system_status_values["processing"].setText("HOST REFERENCE · Aktif")
        self.system_status_values["hackrf"].setText("Bağlı Değil · Replay için kullanılmıyor")
        self.system_status_values["zedboard"].setText("Bağlı Değil · Replay için kullanılmıyor")
        self.system_status_values["fpga"].setText("Fiziksel olarak doğrulanmadı")
        self.system_status_values["petalinux"].setText("Fiziksel ARM çalıştırması doğrulanmadı")

    def set_frame_position(self, zero_based_index: int, frame_count: int) -> None:
        blocker = QSignalBlocker(self.frame_spin)
        self.frame_spin.setValue(zero_based_index + 1)
        del blocker
        self.metadata_values["frame_position"].setText(
            f"{self.locale.toString(zero_based_index + 1)} / {self.locale.toString(frame_count)}"
        )
        self._refresh_source_summary()

    def _refresh_source_summary(self) -> None:
        values = self.metadata_values
        if values["center_frequency"].text() == "—":
            self.source_summary.setText("Kaynak seçilmedi")
            return
        self.source_summary.setText(
            f"{self._replay_source_badge}\n{values['center_frequency'].text()} · {values['sample_rate'].text()}\n"
            f"{values['datatype'].text()} · Çerçeve {values['frame_position'].text()}"
        )

    def set_state(self, state: str) -> None:
        self.state_value.setText(TEXT[state])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT.get(state, state))

    def set_profile_summary(self, summary: str, *, validated: bool) -> None:
        suffix = TEXT["validated_envelope"] if validated else TEXT["parameter_error"]
        self.profile_value.setText(f"{summary}\n{suffix}")
        self.profile_value.setToolTip(f"{summary}\n{suffix}")

    def clear_detections(self) -> None:
        self.detection_state.setText(TEXT["no_detection"])
        self.detection_list.clear()
        self.detection_note.setText("")
        # Reset diff cache so next real frame rebuilds unconditionally.
        self._prev_event_snapshot: dict[int, str] = {}
        self._prev_selected_id: int | None = None
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText("Sinyaller")
        if hasattr(self, "selected_signal_badge"):
            self.selected_signal_badge.setText("Sinyal seçilmedi")
            self.selected_signal_badge.setProperty("state", "empty")
            self.card_freq_val.setText("—")
            self.card_bw_val.setText("—")
            self.card_power_val.setText("—")
            self.card_snr_val.setText("—")
            self.card_domain_val.setText("—")
            self.card_bearing_val.setText("—")
            self.card_details_text.setText("Ayrıntı görmek için sinyal seçin.")

    def clear_parameters(self) -> None:
        self.measurement_state.setText(TEXT["measurement_not_started"])
        self.parameter_state.setText(TEXT["no_parameter"])
        for value in self.parameter_values.values():
            value.setText(TEXT["not_validated"])
        self.quality_value.setText(TEXT["quality_not_available"])
        if hasattr(self, "analysis_freq_val"):
            self.analysis_freq_val.setText("—")
            self.analysis_event_value.setText(TEXT["select_confirmed_event"])

    def set_parameter_result(self, result: ParameterFrameResult | None) -> None:
        del result

    def set_detection_result(
        self,
        result: DetectionFrameResult,
        *,
        selected_event_id: int | None = None,
    ) -> None:
        active = list(result.active_events)
        confirmed = [event for event in active if event.state == "confirmed"]
        tentative = [event for event in active if event.state == "tentative"]
        total_count = len(confirmed) + len(tentative)
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText(f"Sinyaller ({total_count})" if total_count else "Sinyaller")

        if confirmed or tentative:
            self.detection_state.setText(
                f"{len(confirmed)} {TEXT['confirmed'].casefold()} · "
                f"{len(tentative)} {TEXT['tentative'].casefold()}"
            )
        else:
            self.detection_state.setText(TEXT["no_detection"])

        ordered = sorted(confirmed, key=self._event_sort_key) + sorted(
            tentative, key=self._event_sort_key
        )
        visible = ordered[:12]

        # --- Diff guard: skip costly clear+rebuild if nothing changed ---------
        new_snapshot = {
            int(event.event_id): self._event_text(event)
            for event in visible
        }
        if not hasattr(self, "_prev_event_snapshot"):
            self._prev_event_snapshot: dict[int, str] = {}
            self._prev_selected_id: int | None = None
        if new_snapshot == self._prev_event_snapshot and selected_event_id == self._prev_selected_id:
            # Only refresh the signal card in case real-time values changed.
            self._update_selected_signal_card(ordered[0] if ordered else None)
            return
        self._prev_event_snapshot = new_snapshot
        self._prev_selected_id = selected_event_id
        # ---------------------------------------------------------------------

        blocker = QSignalBlocker(self.detection_list)
        self.detection_list.clear()
        selected_item: QListWidgetItem | None = None
        for event in visible:
            item = QListWidgetItem(self._event_text(event))
            item.setToolTip(self._event_tooltip(event))
            item.setData(Qt.ItemDataRole.UserRole, event.event_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, event.state)
            item.setForeground(QColor("#10B981") if event.state == "confirmed" else QColor("#F59E0B"))
            if event.state != "confirmed" or not event.observed_this_frame:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            elif selected_event_id == int(event.event_id):
                selected_item = item
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, self._event_tooltip(event))
            self.detection_list.addItem(item)
        if selected_item is not None:
            selected_item.setSelected(True)
            self.detection_list.setCurrentItem(selected_item)
            self._update_selected_signal_card(ordered[0] if ordered else None)
        elif ordered:
            self._update_selected_signal_card(ordered[0])
        del blocker
        notes: list[str] = []
        hidden = max(0, len(ordered) - len(visible))
        if hidden:
            notes.append(f"+{hidden} sinyal")
        self.detection_note.setText(" · ".join(notes))

    @staticmethod
    def _set_label_if_changed(label: "QLabel", text: str) -> None:
        """Only call setText when value actually changes (eliminates redundant repaints)."""
        if label.text() != text:
            label.setText(text)

    def _update_selected_signal_card(self, event: DetectionEvent | None) -> None:
        if not hasattr(self, "card_freq_val") or event is None:
            return
        state_label = TEXT.get(event.state, event.state)
        self._set_label_if_changed(self.selected_signal_badge, f"{state_label}")
        self.selected_signal_badge.setProperty("state", "active")
        self._set_label_if_changed(
            self.card_freq_val, f"{event.region.peak_frequency_hz / 1_000_000.0:.3f} MHz"
        )
        bw_khz = (event.region.end_frequency_hz - event.region.start_frequency_hz) / 1000.0
        self._set_label_if_changed(self.card_bw_val, f"{max(bw_khz, 0.1):.1f} kHz")
        self._set_label_if_changed(self.card_power_val, f"{event.region.peak_power:.1f} dBFS")
        self._set_label_if_changed(self.card_snr_val, f"+{event.region.peak_to_noise_db:.1f} dB")
        self._set_label_if_changed(
            self.card_domain_val, "Izleniyor" if event.state == "tentative" else "Dogrulandi"
        )
        self.card_details_text.setText(
            f"Frekans: {event.region.start_frequency_hz/1e6:.3f} - {event.region.end_frequency_hz/1e6:.3f} MHz\n"
            f"Bolge: {event.region.start_bin}..{event.region.end_bin}\n"
            f"Cerceve: #{event.first_frame+1}-#{event.last_seen_frame+1} ({event.seen_count} kez)"
        )

    def set_analysis_event(self, event: DetectionEvent | None) -> None:
        if event is None:
            self.analysis_event_value.setText(TEXT["select_confirmed_event"])
            self.measure_button.setEnabled(False)
            return
        self.analysis_event_value.setText(self._event_text(event))
        self.analysis_event_value.setToolTip(self._event_tooltip(event))
        self.measure_button.setEnabled(event.state == "confirmed" and event.observed_this_frame)

    def set_analysis_span(self, lower: int, upper: int, provenance: str) -> None:
        label = TEXT[provenance]
        self.span_value.setText(f"{lower}–{upper} bin · {label}")
        self.clear_measurement_result()

    def clear_analysis(self) -> None:
        self.set_analysis_event(None)
        self.span_value.setText(TEXT["no_analysis_span"])
        self.analysis_spectrum.clear_span()
        self.clear_measurement_result()

    def set_listening_event(self, event: DetectionEvent | None, *, offset_hz: float | None = None) -> None:
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.listening_event_value.setText(TEXT["listening_select_event"])
            self.prepare_listening_button.setEnabled(False)
            return
        self.listening_event_value.setText(self._event_tooltip(event))
        self.listening_event_value.setToolTip(self._event_tooltip(event))
        if offset_hz is not None:
            with QSignalBlocker(self.listen_offset_spin):
                self.listen_offset_spin.setValue(offset_hz / 1000.0)
        self.prepare_listening_button.setEnabled(True)
        self.listening_values["carrier"].setText(self._frequency(event.region.peak_frequency_hz))
        self.listening_values["bandwidth"].setText(
            self.locale.toString(self.listen_bandwidth_spin.value(), "f", 1) + " kHz"
        )
        self.listening_values["backend"].setText("Replay")

    def clear_listening(self) -> None:
        self.listening_event_value.setText(TEXT["listening_select_event"])
        self.listening_state.setText(TEXT["listening_not_prepared"])
        self.prepare_listening_button.setEnabled(False)
        self.play_audio_button.setEnabled(False)
        self.pause_audio_button.setEnabled(False)
        self.stop_audio_button.setEnabled(False)
        self.export_wav_button.setEnabled(False)
        if hasattr(self, "listening_values"):
            for value in self.listening_values.values():
                value.setText("—")
        if hasattr(self, "listening_spectrum"):
            self.listening_spectrum.clear_span()

    def set_listening_busy(self) -> None:
        self.listening_state.setText(TEXT["listening_preparing"])
        for button in (
            self.prepare_listening_button,
            self.play_audio_button,
            self.pause_audio_button,
            self.stop_audio_button,
            self.export_wav_button,
        ):
            button.setEnabled(False)

    def set_listening_result(
        self,
        result: object,
        *,
        audio_available: bool,
        source_sample_rate_hz: float,
        carrier_frequency_hz: float,
        channel_bandwidth_hz: float,
        backend: str,
    ) -> None:
        tone = float(getattr(result, "dominant_tone_hz"))
        audio = np.asarray(getattr(result, "audio"), dtype=np.float64)
        sample_rate = int(getattr(result, "sample_rate_hz"))
        mode = str(getattr(result, "mode")).upper()
        duration = audio.size / sample_rate
        self.listening_state.setText(f"Hazır · {self.locale.toString(tone, 'f', 1)} Hz")
        self.listening_values["mode"].setText(mode)
        self.listening_values["carrier"].setText(self._frequency(carrier_frequency_hz))
        self.listening_values["bandwidth"].setText(
            self.locale.toString(channel_bandwidth_hz / 1000.0, "f", 1) + " kHz"
        )
        self.listening_values["iq_rate"].setText(self._sample_rate(source_sample_rate_hz))
        self.listening_values["audio_rate"].setText(
            f"{self.locale.toString(sample_rate / 1000.0, 'f', 1)} kHz mono PCM16"
        )
        self.listening_values["duration"].setText(self.locale.toString(duration, "f", 2) + " s")
        rf_power = float(getattr(result, "rf_power_dbfs", float("nan")))
        self.listening_values["levels"].setText(
            self.locale.toString(rf_power, "f", 1) + " dBFS"
        )
        self.listening_values["backend"].setText(backend)
        self.prepare_listening_button.setEnabled(True)
        self.play_audio_button.setEnabled(audio_available)
        self.pause_audio_button.setEnabled(audio_available)
        self.stop_audio_button.setEnabled(audio_available)
        self.export_wav_button.setEnabled(True)

    def set_audio_availability(self, available: bool) -> None:
        self.audio_backend_state.setText(
            TEXT["audio_backend_ready"] if available else TEXT["audio_backend_unavailable"]
        )

    def set_fixture_source(self, active: bool) -> None:
        self.fixture_live_warning.setVisible(active)
        self.fixture_live_warning.setText(TEXT["fixture_not_live"] if active else "")

    def clear_measurement_result(self) -> None:
        self.clear_parameters()
        self.measure_button.setText(TEXT["start_measurement"])

    def set_measurement_busy(self) -> None:
        self.measurement_state.setText("Ölçülüyor…")
        self.parameter_state.setText("Sonuç bekleniyor")
        self.measure_button.setText("Ölçülüyor…")
        self.measure_button.setEnabled(False)

    def set_measurement_complete(self) -> None:
        self._measurement_run_count += 1
        self.measurement_state.setText(f"● Ölçüm tamamlandı · #{self._measurement_run_count}")
        self.parameter_state.setText(f"Sonuçlar güncellendi · Ölçüm #{self._measurement_run_count}")
        self.measure_button.setText(TEXT["start_measurement"])
        self.measure_button.setEnabled(True)

    def show_measurement_rejected(self, message: str) -> None:
        self.measurement_state.setText(message)
        self.parameter_state.setText("Ölçüm başlatılmadı")
        self.measure_button.setText(TEXT["start_measurement"])
        self.show_warning(message)

    def set_operator_measurement(self, result: object, validated_fields: tuple[str, ...]) -> None:
        from algorithms.parameters import OperatorAssistedParameterResult
        if not isinstance(result, OperatorAssistedParameterResult):
            self.clear_measurement_result()
            return
        self.measurement_state.setText(TEXT["measurement_complete"] if result.quality.state == "valid" else TEXT["measurement_failed"])
        mapping = {
            "emission_center": ("emission_center_frequency", result.emission_center_frequency),
            "carrier_line": ("carrier_line_frequency", result.carrier_line_frequency),
            "lower_edge": ("occupied_bandwidth", result.lower_band_edge),
            "upper_edge": ("occupied_bandwidth", result.upper_band_edge),
            "bandwidth": ("occupied_bandwidth", result.occupied_bandwidth),
            "peak_power": ("uncalibrated_power_dbfs", result.peak_power_dbfs_per_bin),
            "channel_power": ("uncalibrated_power_dbfs", result.channel_power_dbfs),
            "domain": ("signal_domain", result.signal_domain),
        }
        for key, (capability, field) in mapping.items():
            if capability not in validated_fields:
                self.parameter_values[key].setText(TEXT["not_validated"])
            elif field.state != "valid" or field.value is None:
                self.parameter_values[key].setText(TEXT.get(field.state, TEXT["measurement_failed"]))
            elif field.unit == "Hz":
                self.parameter_values[key].setText(self._frequency(float(field.value)) if key not in {"bandwidth"} else self.locale.toString(float(field.value) / 1000.0, "f", 2) + " kHz")
            elif isinstance(field.value, float):
                self.parameter_values[key].setText(self.locale.toString(field.value, "f", 2) + (f" {field.unit}" if field.unit else ""))
            else:
                self.parameter_values[key].setText(str(field.value))
        reasons = ", ".join(TEXT.get(reason, reason) for reason in result.quality.reasons) if result.quality.reasons else TEXT["quality_passed"]
        self.quality_value.setText(reasons)
        self.parameter_state.setText("Sonuçlar güncellendi")
        self.measure_button.setText(TEXT["start_measurement"])
        self.measure_button.setEnabled(True)

    def set_p0_parameter_result(self, result: P0ParameterResult | None) -> None:
        if result is None:
            for key in (
                "p0_detection", "p0_center", "p0_bandwidth", "p0_lower", "p0_upper",
                "p0_bandwidth_method", "p0_coarse_span", "p0_peak_power", "p0_power",
                "p0_snr", "p0_domain", "p0_region", "p0_backend", "p0_source",
                "emission_center", "carrier_line", "lower_edge", "upper_edge", "bandwidth",
                "peak_power", "channel_power", "domain",
            ):
                self.parameter_values[key].setText(TEXT["not_validated"])
            self.quality_value.setText(TEXT["quality_not_available"])
            if hasattr(self, "analysis_freq_val"):
                self.analysis_freq_val.setText("—")
                self.analysis_event_value.setText("Sinyal seçilmedi")
            return
        locale = self.locale
        status_str = "● Doğrulandı" if result.confirmed else "İzleniyor"
        self.parameter_values["p0_detection"].setText(status_str)
        self.parameter_values["p0_center"].setText(self._frequency(result.emission_center_frequency_hz))
        self.parameter_values["p0_bandwidth"].setText(locale.toString(result.bandwidth_hz / 1000.0, "f", 2) + " kHz")
        self.parameter_values["p0_lower"].setText(self._frequency(result.lower_frequency_hz))
        self.parameter_values["p0_upper"].setText(self._frequency(result.upper_frequency_hz))
        method_text = "Eşik sınırları" if result.bandwidth_method == "threshold_edges" else "%98 güç"
        self.parameter_values["p0_bandwidth_method"].setText(method_text)
        self.parameter_values["p0_coarse_span"].setText(
            locale.toString(result.coarse_candidate_bandwidth_hz / 1000.0, "f", 2) + " kHz"
        )
        self.parameter_values["p0_peak_power"].setText(locale.toString(result.peak_power_dbfs_per_bin, "f", 1) + " dBFS/bin · " + TEXT["calibration_pending"])
        self.parameter_values["p0_power"].setText(locale.toString(result.channel_power_dbfs, "f", 1) + " dBFS · " + TEXT["calibration_pending"])
        self.parameter_values["p0_snr"].setText(locale.toString(result.snr_db, "f", 1) + " dB")
        self.parameter_values["p0_domain"].setText(result.signal_domain)
        self.parameter_values["p0_region"].setText(f"{result.candidate.start_bin}–{result.candidate.end_bin}")
        self.parameter_values["p0_backend"].setText(result.backend)
        source_name = _source_display_name(result.provenance)
        self.parameter_values["p0_source"].setText(source_name)
        self.parameter_values["emission_center"].setText(self._frequency(result.emission_center_frequency_hz))
        self.parameter_values["carrier_line"].setText(TEXT["carrier_line_not_separate"])
        self.parameter_values["lower_edge"].setText(self._frequency(result.lower_frequency_hz))
        self.parameter_values["upper_edge"].setText(self._frequency(result.upper_frequency_hz))
        self.parameter_values["bandwidth"].setText(locale.toString(result.bandwidth_hz / 1000.0, "f", 2) + " kHz")
        self.parameter_values["peak_power"].setText(locale.toString(result.peak_power_dbfs_per_bin, "f", 1) + " dBFS/bin")
        self.parameter_values["channel_power"].setText(locale.toString(result.channel_power_dbfs, "f", 1) + " dBFS")
        self.parameter_values["domain"].setText(result.signal_domain)
        self.quality_value.setText(" · ".join(result.classification_reasons))
        self.parameter_state.setText("Sonuçlar güncellendi")

        if hasattr(self, "analysis_freq_val"):
            self.analysis_freq_val.setText(f"{result.emission_center_frequency_hz / 1_000_000.0:.3f} MHz")
            self.analysis_event_value.setText(status_str)

        if hasattr(self, "card_freq_val"):
            self.card_freq_val.setText(f"{result.emission_center_frequency_hz / 1_000_000.0:.3f} MHz")
            self.card_bw_val.setText(f"{result.bandwidth_hz / 1000.0:.2f} kHz")
            self.card_power_val.setText(f"{result.peak_power_dbfs_per_bin:.1f} dBFS")
            self.card_snr_val.setText(f"+{result.snr_db:.1f} dB")
            self.card_domain_val.setText(result.signal_domain)
            self.selected_signal_badge.setText(status_str)
            self.selected_signal_badge.setProperty("state", "active")
            self.card_details_text.setText(
                f"Frekans: {result.lower_frequency_hz/1e6:.3f} - {result.upper_frequency_hz/1e6:.3f} MHz\n"
                f"Yöntem: {method_text}\n"
                f"Kaynak: {source_name}"
            )

    def set_p0_detection_summary(self, result: P0ParameterResult) -> None:
        self.detection_list.clear()
        state = "Doğrulandı" if result.confirmed else "İzleniyor"
        source_name = _source_display_name(result.provenance)
        freq_str = f"{result.emission_center_frequency_hz / 1_000_000.0:.3f} MHz"
        snr_str = f"+{result.snr_db:.1f} dB"
        item = QListWidgetItem(f"{freq_str}    {snr_str}    {state}")
        item.setToolTip(
            f"Emisyon merkez frekansı: {result.emission_center_frequency_hz/1e6:.3f} MHz\n"
            f"Bant: {result.bandwidth_hz/1000.0:.2f} kHz\n"
            f"Kaynak: {source_name}"
        )
        self.detection_list.addItem(item)
        self.detection_state.setText(f"1 {state.casefold()}")
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText("Sinyaller (1)")

    def set_p0_search_engine(self, engine: P0SearchEngine | None) -> None:
        self.p0_search_engine = engine
        self.last_search_result = None
        self.search_start_button.setEnabled(engine is not None)
        self.active_search_mode_label.setText("● Hazır" if engine is not None else "● Bekliyor")

    def _event_text(self, event: DetectionEvent) -> str:
        label = TEXT[event.state]
        peak_mhz = self.locale.toString(event.region.peak_frequency_hz / 1_000_000.0, "f", 3)
        delta = self.locale.toString(event.region.peak_to_noise_db, "f", 1)
        return f"{peak_mhz} MHz    +{delta} dB    {label}"

    def _event_tooltip(self, event: DetectionEvent) -> str:
        start = self.locale.toString(event.region.start_frequency_hz / 1_000_000.0, "f", 3)
        end = self.locale.toString(event.region.end_frequency_hz / 1_000_000.0, "f", 3)
        return (
            f"Frekans: {start}–{end} MHz\n"
            f"Çerçeve: #{event.first_frame + 1}–#{event.last_seen_frame + 1}\n"
            f"Görülme: {event.seen_count}"
        )

    @staticmethod
    def _event_sort_key(event: DetectionEvent) -> tuple[float, int]:
        return (-event.region.peak_to_noise_db, event.event_id)

    def show_warning(self, message: str) -> None:
        self._show_notification(message, "warning")

    def show_error(self, message: str) -> None:
        self._show_notification(message, "error")

    def _show_notification(self, message: str, kind: str) -> None:
        self.notification.setProperty("kind", kind)
        self.notification.setText(message)
        self.notification.style().unpolish(self.notification)
        self.notification.style().polish(self.notification)
        self.notification.show()

    def hide_notification(self) -> None:
        self.notification.hide()
        self.notification.setText("")

    def set_source_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.start_button,
            self.pause_button,
            self.stop_button,
            self.frame_spin,
            self.speed_spin,
            self.axis_combo,
            self.metric_combo,
            self.dc_checkbox,
            self.average_checkbox,
            self.detection_layer_checkbox,
            self.pfa_combo,
            self.center_checkbox,
        ):
            widget.setEnabled(enabled)
