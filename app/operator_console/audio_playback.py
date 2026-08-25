"""Optional QtMultimedia PCM16 playback with a safe unavailable state."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject

try:
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
except ImportError:  # pragma: no cover - exercised by injected unavailable tests
    QAudioFormat = QAudioSink = QMediaDevices = None  # type: ignore[assignment]


class AudioPlayback(QObject):
    """Own one bounded in-memory audio sink without affecting WAV export."""

    SAMPLE_RATE_HZ = 48_000
    BYTES_PER_SAMPLE = 2

    def __init__(self, parent: QObject | None = None, *, available_override: bool | None = None) -> None:
        super().__init__(parent)
        self._sink: object | None = None
        self._buffer: QBuffer | None = None
        self._pcm = b""
        if available_override is not None:
            self.available = bool(available_override)
        elif QMediaDevices is None:
            self.available = False
        else:
            self.available = not QMediaDevices.defaultAudioOutput().isNull()

    def load(self, pcm16: bytes) -> None:
        self.stop()
        self._pcm = bytes(pcm16)

    @property
    def duration_seconds(self) -> float:
        return len(self._pcm) / (self.SAMPLE_RATE_HZ * self.BYTES_PER_SAMPLE)

    @property
    def position_seconds(self) -> float:
        if self._sink is None:
            return 0.0
        processed_us = max(0, int(self._sink.processedUSecs()))  # type: ignore[attr-defined]
        return min(self.duration_seconds, processed_us / 1_000_000.0)

    def play(self) -> bool:
        if not self.available or not self._pcm or QAudioSink is None or QMediaDevices is None:
            return False
        if self._sink is not None:
            if self.position_seconds < max(0.0, self.duration_seconds - 0.01):
                self._sink.resume()  # type: ignore[attr-defined]
                return True
            self.stop()
        audio_format = QAudioFormat()
        audio_format.setSampleRate(self.SAMPLE_RATE_HZ)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull() or not device.isFormatSupported(audio_format):
            self.available = False
            return False
        self._buffer = QBuffer(self)
        self._buffer.setData(QByteArray(self._pcm))
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink = QAudioSink(device, audio_format, self)
        self._sink.start(self._buffer)  # type: ignore[attr-defined]
        return True

    def pause(self) -> None:
        if self._sink is not None:
            self._sink.suspend()  # type: ignore[attr-defined]

    def stop(self) -> None:
        if self._sink is not None:
            self._sink.stop()  # type: ignore[attr-defined]
            self._sink.deleteLater()  # type: ignore[attr-defined]
            self._sink = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer.deleteLater()
            self._buffer = None

    def close(self) -> None:
        self.stop()
        self._pcm = b""
