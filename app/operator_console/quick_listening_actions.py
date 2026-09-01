"""Analog listening actions for the Qt Quick view model."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QUrl, Slot

from algorithms.monitoring import (
    AnalogMonitor,
    AnalogMonitorConfig,
    AnalogMonitorResult,
    MonitoringError,
    write_wav,
)
from platforms.acquisition import decode_ci8

from .live_ed import LIVE_AUDIO_WINDOW_FRAMES
from .quick_runtime import ERROR_TEXT


class QuickListeningActionsMixin:
    """Prepare, play and export operator-selected receive audio."""

    @Slot(str, float, float, float)
    def requestListening(self, mode: str, center_offset_khz: float, bandwidth_khz: float, volume: float) -> None:
        if self._source_mode == "hackrf":
            self._request_live_listening(mode, center_offset_khz, bandwidth_khz, volume)
            return
        if self._source is None or self._last_result is None or self._busy or not self.selectedDetectionReady:
            self._listening_state = "Dinleme için doğrulanmış bir tespit ve hazır kaynak gerekir."
            self.listeningChanged.emit()
            return
        event = next(
            (
                item for item in self._last_result.detection.active_events
                if item.event_id == self._selected_detection_id and item.state == "confirmed"
            ),
            None,
        )
        if event is None:
            self._listening_state = "Seçili tespit artık etkin değil; yeniden seçin."
            self.listeningChanged.emit()
            return
        try:
            config = AnalogMonitorConfig(
                mode,  # type: ignore[arg-type]
                self.sampleRateHz,
                center_offset_khz * 1_000.0,
                bandwidth_khz * 1_000.0,
            )
            if not math.isfinite(volume) or not 0.0 <= volume <= 1.0:
                raise MonitoringError("invalid_volume", "Ses düzeyi 0 ile 1 arasında olmalıdır.")
        except Exception as exc:
            code = str(getattr(exc, "code", "invalid_channel_bandwidth"))
            self._listening_state = ERROR_TEXT.get(code, "Dinleme ayarları geçerli değil.")
            self.listeningChanged.emit()
            return

        self.pause()
        self._clear_listening("Seçili kanal hazırlanıyor…")
        source = self._source
        frame_length = int(getattr(source, "frame_length"))
        frame_count = int(getattr(source, "frame_count"))
        total_samples = frame_length * frame_count
        sample_rate = float(getattr(source, "sample_rate_hz"))
        current_sample = self._frame_index * frame_length
        selected_id = self._selected_detection_id

        def operation() -> tuple[AnalogMonitorResult, str, float, float, float]:
            continuous_samples = int(math.ceil(5.0 * sample_rate))
            if (
                hasattr(source, "read_samples")
                and total_samples >= continuous_samples
                and continuous_samples <= 10_000_000
            ):
                start_sample = max(0, min(current_sample - continuous_samples // 2, total_samples - continuous_samples))
                block_size = max(frame_length, int(sample_rate))
                blocks = tuple(
                    source.read_samples(  # type: ignore[attr-defined]
                        start_sample + offset,
                        min(block_size, continuous_samples - offset),
                    )
                    for offset in range(0, continuous_samples, block_size)
                )
                result = AnalogMonitor().process_continuous(blocks, config, volume=volume)
                return result, "Kesintisiz kayıt", continuous_samples / sample_rate, config.center_offset_hz, config.channel_bandwidth_hz
            if frame_count < 4:
                raise MonitoringError("insufficient_iq", "Dinleme için dört ardışık I/Q karesi gerekir.")
            start_frame = max(0, min(self._frame_index - 3, frame_count - 4))
            frames = tuple(source.read_frame(start_frame + offset) for offset in range(4))  # type: ignore[attr-defined]
            result = AnalogMonitor().process(frames, config, volume=volume)
            return result, "Kısa I/Q önizlemesi", 4 * frame_length / sample_rate, config.center_offset_hz, config.channel_bandwidth_hz

        self._set_busy(True, f"Tespit #{selected_id} için {mode.upper()} kanalı hazırlanıyor…")
        self._submit(self._generation, "listening", operation)
        self._add_log("Dinleme", f"Tespit #{selected_id} · {mode.upper()} hazırlama istendi")

    def _request_live_listening(
        self,
        mode: str,
        center_offset_khz: float,
        bandwidth_khz: float,
        volume: float,
    ) -> None:
        session = self._live_session
        if (
            session is None
            or (self._busy and not self.liveSessionActive)
            or not self.listeningSelectionReady
            or not hasattr(session, "audio_window")
        ):
            self._listening_state = (
                "Canlı dinleme için aynı doğrulanmış tespitin beş saniye boyunca gözlenmesi gerekir."
            )
            self.listeningChanged.emit()
            return
        try:
            config = AnalogMonitorConfig(
                mode,  # type: ignore[arg-type]
                self.sampleRateHz,
                center_offset_khz * 1_000.0,
                bandwidth_khz * 1_000.0,
            )
            if not math.isfinite(volume) or not 0.0 <= volume <= 1.0:
                raise MonitoringError("invalid_volume", "Ses düzeyi 0 ile 1 arasında olmalıdır.")
        except Exception as exc:
            code = str(getattr(exc, "code", "invalid_channel_bandwidth"))
            self._listening_state = ERROR_TEXT.get(code, "Dinleme ayarları geçerli değil.")
            self.listeningChanged.emit()
            return

        window = tuple(session.audio_window(self._selected_detection_id))
        if len(window) != LIVE_AUDIO_WINDOW_FRAMES:
            self._listening_state = "Canlı I/Q tamponu henüz beş saniyeye ulaşmadı."
            self.listeningChanged.emit()
            return
        sequences = tuple(frame.sequence_number for frame in window)
        if sequences != tuple(range(sequences[0], sequences[0] + LIVE_AUDIO_WINDOW_FRAMES)):
            self._listening_state = "Canlı I/Q tamponu ardışık değil; yeni gözlem bekleniyor."
            self.listeningChanged.emit()
            return

        selected_id = self._selected_detection_id
        input_duration = len(window) * 4096.0 / config.sample_rate_hz

        def operation() -> tuple[AnalogMonitorResult, str, float, float, float]:
            frames_per_block = max(1, int(math.ceil(config.sample_rate_hz / 4096.0)))
            blocks = tuple(
                decode_ci8(
                    b"".join(frame.payload for frame in window[start:start + frames_per_block]),
                    expected_complex_samples=(
                        len(window[start:start + frames_per_block]) * 4096
                    ),
                )
                for start in range(0, len(window), frames_per_block)
            )
            result = AnalogMonitor().process_continuous(blocks, config, volume=volume)
            return (
                result,
                "Canlı kesintisiz alım",
                input_duration,
                config.center_offset_hz,
                config.channel_bandwidth_hz,
            )

        self._pending_live_measurement = None
        self._pending_live_listening = operation
        self._clear_listening("Beş saniyelik canlı I/Q sabitlendi; alım durdurulup kanal hazırlanıyor…")
        self._status_message = "Canlı dinleme penceresi sabitlendi; alım güvenli biçimde durduruluyor."
        self._add_log("Dinleme", f"Tespit #{selected_id} canlı dinleme penceresi sabitlendi")
        session.cancel()
        self.stateChanged.emit()

    def _start_pending_live_listening(self) -> bool:
        operation, self._pending_live_listening = self._pending_live_listening, None
        if operation is None:
            return False
        self._set_busy(True, f"Tespit #{self._selected_detection_id} canlı dinleme kanalı hazırlanıyor…")
        self._submit(self._generation, "listening", operation)
        return True

    @Slot()
    def playListening(self) -> None:
        if not self._audio_playback.play():
            self._listening_playback_state = "Ses çıkış aygıtı kullanılamıyor"
            self.playbackChanged.emit()
            self.listeningChanged.emit()
            return
        self._listening_playback_state = "Oynatılıyor"
        self._playback_timer.start()
        self._refresh_listening_playback()

    @Slot()
    def pauseListening(self) -> None:
        self._audio_playback.pause()
        self._playback_timer.stop()
        self._listening_playback_position_s = self._audio_playback.position_seconds
        self._listening_playback_state = "Duraklatıldı"
        self.playbackChanged.emit()

    @Slot()
    def stopListening(self) -> None:
        self._playback_timer.stop()
        self._audio_playback.stop()
        self._listening_playback_position_s = 0.0
        self._listening_playback_state = "Durduruldu"
        self.playbackChanged.emit()

    @Slot(str)
    def exportListeningWav(self, value: str) -> None:
        if self._listening_result is None or self._busy:
            return
        url = QUrl(value)
        path = Path(url.toLocalFile() if url.isLocalFile() else value)
        if not path.name:
            return
        if path.suffix.casefold() != ".wav":
            path = path.with_suffix(".wav")
        payload = bytes(self._listening_result.pcm16)

        def operation() -> str:
            try:
                write_wav(path, payload)
            except OSError as exc:
                raise MonitoringError("wav_write_failed", "WAV dosyası yazılamadı.") from exc
            return str(path)

        self._set_busy(True, "WAV dosyası kaydediliyor…")
        self._submit(self._generation, "wav_export", operation)
