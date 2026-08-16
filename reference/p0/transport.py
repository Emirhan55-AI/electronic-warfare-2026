"""Bounded, CRC-protected Computer-1 to ZedBoard IQ transport abstraction."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import socket
import struct
import threading
from typing import Protocol
import zlib


MAGIC = b"P0IQ"
VERSION = 1
SAMPLE_FORMAT_CI8 = 1
HEADER = struct.Struct("<4sBBHIIHHQIIII")
MAX_PAYLOAD_BYTES = 131_072


class TransportError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class IQFrame:
    sequence_number: int
    sample_rate_hz: int
    center_frequency_hz: int
    payload: bytes
    sample_format: str = "ci8"
    frame_id: int = 0
    chunk_index: int = 0
    chunk_count: int = 1

    @property
    def complex_sample_count(self) -> int:
        return len(self.payload) // 2


@dataclass(frozen=True)
class TransportStats:
    state: str = "DISCONNECTED"
    frames_sent: int = 0
    frames_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    crc_errors: int = 0
    sequence_errors: int = 0
    queue_drops: int = 0
    last_error: str | None = None


class IQTransport(Protocol):
    @property
    def stats(self) -> TransportStats: ...
    def send(self, frame: IQFrame) -> bool: ...
    def close(self) -> None: ...


class IQFrameCodec:
    @staticmethod
    def encode(frame: IQFrame) -> bytes:
        if frame.sample_format != "ci8":
            raise TransportError("unsupported_sample_format", "P0 taşıması yalnız ci8 kabul eder.")
        if not 0 <= frame.sequence_number <= 0xFFFFFFFF:
            raise TransportError("invalid_sequence", "Sıra numarası uint32 sınırında olmalıdır.")
        payload = bytes(frame.payload)
        if not payload or len(payload) % 2 or len(payload) > MAX_PAYLOAD_BYTES:
            raise TransportError("invalid_payload_length", "IQ yükü bounded tam I/Q çiftlerinden oluşmalıdır.")
        if frame.sample_rate_hz <= 0 or frame.center_frequency_hz <= 0:
            raise TransportError("invalid_metadata", "Örnekleme veya merkez frekansı geçersizdir.")
        if not 0 <= frame.frame_id <= 0xFFFFFFFF or not 1 <= frame.chunk_count <= 0xFFFF or not 0 <= frame.chunk_index < frame.chunk_count:
            raise TransportError("invalid_chunk", "Frame/chunk kimliği veya sırası geçersizdir.")
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        header = HEADER.pack(
            MAGIC,
            VERSION,
            SAMPLE_FORMAT_CI8,
            HEADER.size,
            frame.sequence_number,
            frame.frame_id,
            frame.chunk_index,
            frame.chunk_count,
            frame.center_frequency_hz,
            frame.sample_rate_hz,
            frame.complex_sample_count,
            len(payload),
            crc,
        )
        return header + payload

    @staticmethod
    def decode(packet: bytes) -> IQFrame:
        if len(packet) < HEADER.size:
            raise TransportError("short_header", "IQ paketi başlıktan kısadır.")
        magic, version, sample_format, header_size, sequence, frame_id, chunk_index, chunk_count, center, rate, sample_count, payload_length, crc = HEADER.unpack_from(packet)
        if magic != MAGIC or version != VERSION or header_size != HEADER.size:
            raise TransportError("header_contract", "IQ paket başlığı veya sürümü uyumsuzdur.")
        if sample_format != SAMPLE_FORMAT_CI8:
            raise TransportError("unsupported_sample_format", "IQ örnek biçimi desteklenmiyor.")
        if payload_length == 0 or payload_length > MAX_PAYLOAD_BYTES or payload_length % 2 or len(packet) != HEADER.size + payload_length:
            raise TransportError("payload_contract", "IQ paket yük uzunluğu uyumsuzdur.")
        if center == 0 or rate == 0:
            raise TransportError("metadata_contract", "IQ paket örnekleme veya merkez frekansı geçersizdir.")
        if sample_count * 2 != payload_length or chunk_count < 1 or chunk_index >= chunk_count:
            raise TransportError("chunk_contract", "IQ frame/chunk alanları uyumsuzdur.")
        payload = bytes(packet[HEADER.size:])
        if zlib.crc32(payload) & 0xFFFFFFFF != crc:
            raise TransportError("crc_mismatch", "IQ paket CRC kontrolü başarısızdır.")
        return IQFrame(sequence, rate, center, payload, "ci8", frame_id, chunk_index, chunk_count)


class BoundedIQQueue:
    def __init__(self, capacity: int = 8) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items: deque[IQFrame] = deque()
        self.drop_count = 0
        self._lock = threading.Lock()

    def put(self, frame: IQFrame) -> bool:
        with self._lock:
            if len(self._items) >= self.capacity:
                self.drop_count += 1
                return False
            self._items.append(frame)
            return True

    def get(self) -> IQFrame | None:
        with self._lock:
            return self._items.popleft() if self._items else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


class LoopbackIQTransport:
    """Local emulator with the same framing/integrity/sequence checks as Ethernet."""

    def __init__(self, *, queue_capacity: int = 8) -> None:
        self.queue = BoundedIQQueue(queue_capacity)
        self.stats = TransportStats()
        self._expected_sequence: int | None = None

    def connect(self) -> None:
        self.stats = replace(self.stats, state="LOOPBACK")

    def close(self) -> None:
        self.stats = replace(self.stats, state="DISCONNECTED")

    def send(self, frame: IQFrame) -> bool:
        if self.stats.state != "LOOPBACK":
            raise TransportError("not_connected", "Taşıma bağlantısı hazır değil.")
        packet = IQFrameCodec.encode(frame)
        try:
            decoded = IQFrameCodec.decode(packet)
        except TransportError as exc:
            self.stats = replace(self.stats, crc_errors=self.stats.crc_errors + 1, last_error=exc.code)
            raise
        expected = self._expected_sequence
        sequence_errors = self.stats.sequence_errors
        if expected is not None and decoded.sequence_number != expected:
            sequence_errors += 1
        self._expected_sequence = (decoded.sequence_number + 1) & 0xFFFFFFFF
        accepted = self.queue.put(decoded)
        self.stats = replace(
            self.stats,
            frames_sent=self.stats.frames_sent + 1,
            bytes_sent=self.stats.bytes_sent + len(packet),
            sequence_errors=sequence_errors,
            queue_drops=self.queue.drop_count,
            last_error=None if accepted else "queue_full",
        )
        return accepted

    def receive(self) -> IQFrame | None:
        frame = self.queue.get()
        if frame is not None:
            self.stats = replace(
                self.stats,
                frames_received=self.stats.frames_received + 1,
                bytes_received=self.stats.bytes_received + len(frame.payload),
            )
        return frame


class TCPClientIQTransport:
    """Computer-1 client only; absence of a ZedBoard server is reported truthfully."""

    def __init__(self) -> None:
        self._socket: socket.socket | None = None
        self._stats = TransportStats()

    @property
    def stats(self) -> TransportStats:
        return self._stats

    def connect(self, host: str, port: int, *, timeout_seconds: float = 2.0) -> None:
        if not host or not 1 <= port <= 65535 or not 0 < timeout_seconds <= 10.0:
            raise TransportError("invalid_endpoint", "ZedBoard ağ uç noktası geçersizdir.")
        self.close()
        try:
            connection = socket.create_connection((host, port), timeout=timeout_seconds)
        except OSError as exc:
            self._stats = replace(self._stats, state="ERROR", last_error="connection_failed")
            raise TransportError("connection_failed", "ZedBoard IQ sunucusuna bağlanılamadı.") from exc
        connection.settimeout(timeout_seconds)
        self._socket = connection
        self._stats = replace(self._stats, state="CONNECTED", last_error=None)

    def send(self, frame: IQFrame) -> bool:
        if self._socket is None or self._stats.state != "CONNECTED":
            raise TransportError("not_connected", "ZedBoard IQ taşıması bağlı değil.")
        packet = IQFrameCodec.encode(frame)
        try:
            self._socket.sendall(packet)
        except OSError as exc:
            self._stats = replace(self._stats, state="ERROR", last_error="send_failed")
            raise TransportError("send_failed", "IQ frame gönderimi tamamlanamadı.") from exc
        self._stats = replace(self._stats, frames_sent=self._stats.frames_sent + 1, bytes_sent=self._stats.bytes_sent + len(packet), last_error=None)
        return True

    def close(self) -> None:
        connection, self._socket = self._socket, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        self._stats = replace(self._stats, state="DISCONNECTED")
