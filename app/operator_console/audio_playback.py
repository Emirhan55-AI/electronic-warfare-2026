"""Optional QtMultimedia PCM16 playback with a safe unavailable state."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, QTimer

try:
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
except ImportError:  # pragma: no cover - exercised by injected unavailable tests
    QAudioFormat = QAudioSink = QMediaDevices = None  # type: ignore[assignment]


class AudioPlayback(QObject):
    """Own bounded clip playback or a bounded push-mode live audio sink."""

    SAMPLE_RATE_HZ = 48_000
    BYTES_PER_SAMPLE = 2

    def __init__(self, parent: QObject | None = None, *, available_override: bool | None = None) -> None:
        super().__init__(parent)
        self._sink: object | None = None
        self._buffer: QBuffer | None = None
        self._stream_io: QIODevice | None = None
        self._stream_pending = bytearray()
        self._stream_total_bytes = 0
        self._stream_max_pending_bytes = 20 * self.SAMPLE_RATE_HZ * self.BYTES_PER_SAMPLE
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(20)
        self._stream_timer.timeout.connect(self._flush_stream)
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
        byte_count = self._stream_total_bytes if self.streaming else len(self._pcm)
        return byte_count / (self.SAMPLE_RATE_HZ * self.BYTES_PER_SAMPLE)

    @property
    def streaming(self) -> bool:
        return self._stream_io is not None

    @property
    def stream_pending_seconds(self) -> float:
        return len(self._stream_pending) / (self.SAMPLE_RATE_HZ * self.BYTES_PER_SAMPLE)

    @property
    def position_seconds(self) -> float:
        if self._sink is None:
            return 0.0
        processed_us = max(0, int(self._sink.processedUSecs()))  # type: ignore[attr-defined]
        return min(self.duration_seconds, processed_us / 1_000_000.0)

    def play(self) -> bool:
        if self.streaming and self._sink is not None:
            self._sink.resume()  # type: ignore[attr-defined]
            return True
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

    @staticmethod
    def _audio_format():
        audio_format = QAudioFormat()
        audio_format.setSampleRate(AudioPlayback.SAMPLE_RATE_HZ)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        return audio_format

    def start_stream(self) -> bool:
        """Start push-mode PCM playback; callers may append bounded chunks."""
        self.stop()
        self._pcm = b""
        self._stream_total_bytes = 0
        if not self.available or QAudioSink is None or QMediaDevices is None:
            return False
        audio_format = self._audio_format()
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull() or not device.isFormatSupported(audio_format):
            self.available = False
            return False
        self._sink = QAudioSink(device, audio_format, self)
        self._sink.setBufferSize(2 * self.SAMPLE_RATE_HZ * self.BYTES_PER_SAMPLE)  # type: ignore[attr-defined]
        stream_io = self._sink.start()  # type: ignore[attr-defined]
        if stream_io is None:
            self.stop()
            return False
        self._stream_io = stream_io
        self._stream_timer.start()
        return True

    def append_stream(self, pcm16: bytes) -> bool:
        """Queue PCM without blocking the GUI or allowing unbounded backlog."""
        payload = bytes(pcm16)
        if not self.streaming or len(payload) % self.BYTES_PER_SAMPLE:
            return False
        if len(self._stream_pending) + len(payload) > self._stream_max_pending_bytes:
            return False
        self._stream_pending.extend(payload)
        self._stream_total_bytes += len(payload)
        self._flush_stream()
        return True

    def _flush_stream(self) -> None:
        if not self.streaming or self._sink is None or not self._stream_pending:
            return
        free = max(0, int(self._sink.bytesFree()))  # type: ignore[attr-defined]
        if free <= 0:
            return
        count = min(free, len(self._stream_pending))
        written = int(self._stream_io.write(bytes(self._stream_pending[:count])))  # type: ignore[union-attr]
        if written > 0:
            del self._stream_pending[:written]

    def pause(self) -> None:
        if self._sink is not None:
            self._sink.suspend()  # type: ignore[attr-defined]

    def stop(self) -> None:
        self._stream_timer.stop()
        if self._sink is not None:
            self._sink.stop()  # type: ignore[attr-defined]
            self._sink.deleteLater()  # type: ignore[attr-defined]
            self._sink = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer.deleteLater()
            self._buffer = None
        self._stream_io = None
        self._stream_pending.clear()
        self._stream_total_bytes = 0

    def close(self) -> None:
        self.stop()
        self._pcm = b""
