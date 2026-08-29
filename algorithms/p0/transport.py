"""Bounded, CRC-protected Computer-1 to ZedBoard IQ transport abstraction."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import socket
import struct
import threading
from typing import Callable, Iterable, Protocol
import zlib


MAGIC = b"P0IQ"
RESPONSE_MAGIC = b"P0RS"
VERSION = 2
SAMPLE_FORMAT_CI8 = 1
HEADER_PREFIX = struct.Struct("<4sBBHIIHHQIIII")
HEADER = struct.Struct("<4sBBHIIHHQIIIII")
RESPONSE_HEADER_PREFIX = struct.Struct("<4sBBHIII")
RESPONSE_HEADER = struct.Struct("<4sBBHIIII")
MAX_PAYLOAD_BYTES = 131_072
MAX_RESPONSE_BYTES = 16_384
P0_SAMPLE_RATE_HZ = 2_000_000
P0_COMPLEX_SAMPLES = 4_096
P0_PAYLOAD_BYTES = P0_COMPLEX_SAMPLES * 2
P0_PIPELINE_DEPTH = 4
LOCAL_ED_RESPONSE_MAGIC = 0x31534550
LOCAL_ED_RESPONSE_HEADER_BYTES = 48


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
class IQResponse:
    sequence_number: int
    payload: bytes


@dataclass(frozen=True)
class LocalEDResponse:
    frame_id: int
    raw_candidate_count: int
    dma_status_flags: int
    active_count: int
    ended_count: int
    dropped_candidates: int
    reset_applied: int
    response_bytes: int


def decode_local_ed_response(payload: bytes, expected_frame_id: int) -> LocalEDResponse:
    """Decode the compact ABI-v3 response returned by the persistent board service."""
    if len(payload) < LOCAL_ED_RESPONSE_HEADER_BYTES:
        raise TransportError("local_response_short", "Yerel kart yanıtı başlıktan kısa.")
    (
        magic,
        version,
        header_bytes,
        total_bytes,
        frame_id,
        status,
        result_bytes,
        raw_candidate_count,
        dma_status_flags,
    ) = struct.unpack_from("<IHHIIIIII", payload, 0)
    header_crc = struct.unpack_from("<I", payload, 44)[0]
    if (
        magic != LOCAL_ED_RESPONSE_MAGIC
        or version != 3
        or header_bytes != LOCAL_ED_RESPONSE_HEADER_BYTES
        or total_bytes != len(payload)
        or frame_id != expected_frame_id
        or status != 0
        or header_crc != zlib.crc32(payload[:44]) & 0xFFFFFFFF
        or any(payload[offset] != 0 for offset in range(32, 44))
    ):
        raise TransportError("local_response_header", "Yerel kart hizmeti sürüm 3 başlığı doğrulanamadı.")
    result = payload[LOCAL_ED_RESPONSE_HEADER_BYTES:]
    if len(result) != result_bytes or result_bytes < 20:
        raise TransportError("local_response_length", "Yerel kart hizmeti sonuç uzunluğu geçersiz.")
    result_frame_id = struct.unpack_from("<I", result, 0)[0]
    active_count, ended_count, dropped_candidates = struct.unpack_from("<HHH", result, 4)
    reset_applied = result[10]
    if (
        result_frame_id != expected_frame_id
        or result[11] != 0
        or result_bytes != 20 + 68 * (active_count + ended_count)
    ):
        raise TransportError("local_response_result", "Kompakt kart sonucu doğrulanamadı.")
    return LocalEDResponse(
        frame_id=frame_id,
        raw_candidate_count=raw_candidate_count,
        dma_status_flags=dma_status_flags,
        active_count=active_count,
        ended_count=ended_count,
        dropped_candidates=dropped_candidates,
        reset_applied=reset_applied,
        response_bytes=len(payload),
    )


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
        prefix = HEADER_PREFIX.pack(
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
        header_crc = zlib.crc32(prefix) & 0xFFFFFFFF
        return prefix + struct.pack("<I", header_crc) + payload

    @staticmethod
    def decode(packet: bytes) -> IQFrame:
        if len(packet) < HEADER.size:
            raise TransportError("short_header", "IQ paketi başlıktan kısadır.")
        magic, version, sample_format, header_size, sequence, frame_id, chunk_index, chunk_count, center, rate, sample_count, payload_length, crc, header_crc = HEADER.unpack_from(packet)
        if magic != MAGIC or version != VERSION or header_size != HEADER.size:
            raise TransportError("header_contract", "IQ paket başlığı veya sürümü uyumsuzdur.")
        if zlib.crc32(packet[: HEADER_PREFIX.size]) & 0xFFFFFFFF != header_crc:
            raise TransportError("header_crc_mismatch", "IQ paket başlık CRC kontrolü başarısızdır.")
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

    @staticmethod
    def validate_processing_frame(frame: IQFrame) -> None:
        if (
            frame.sample_format != "ci8"
            or frame.sample_rate_hz != P0_SAMPLE_RATE_HZ
            or frame.complex_sample_count != P0_COMPLEX_SAMPLES
            or len(frame.payload) != P0_PAYLOAD_BYTES
            or frame.chunk_index != 0
            or frame.chunk_count != 1
        ):
            raise TransportError(
                "processing_profile_mismatch",
                "FPGA işleme yolu tam 2 MS/s, 4096 örnek, tek parça ci8 çerçeve gerektirir.",
            )


class IQResponseCodec:
    @staticmethod
    def encode(response: IQResponse) -> bytes:
        if not 0 <= response.sequence_number <= 0xFFFFFFFF:
            raise TransportError("invalid_sequence", "Yanıt sıra numarası uint32 sınırında olmalıdır.")
        payload = bytes(response.payload)
        if not payload or len(payload) > MAX_RESPONSE_BYTES:
            raise TransportError("invalid_response_length", "Kart yanıtı bounded uzunlukta olmalıdır.")
        payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
        prefix = RESPONSE_HEADER_PREFIX.pack(
            RESPONSE_MAGIC,
            VERSION,
            1,
            RESPONSE_HEADER.size,
            response.sequence_number,
            len(payload),
            payload_crc,
        )
        header_crc = zlib.crc32(prefix) & 0xFFFFFFFF
        return prefix + struct.pack("<I", header_crc) + payload

    @staticmethod
    def decode(packet: bytes) -> IQResponse:
        if len(packet) < RESPONSE_HEADER.size:
            raise TransportError("short_response_header", "Kart yanıtı başlıktan kısadır.")
        magic, version, response_type, header_size, sequence, payload_length, payload_crc, header_crc = RESPONSE_HEADER.unpack_from(packet)
        if magic != RESPONSE_MAGIC or version != VERSION or response_type != 1 or header_size != RESPONSE_HEADER.size:
            raise TransportError("response_header_contract", "Kart yanıt başlığı veya sürümü uyumsuzdur.")
        if zlib.crc32(packet[: RESPONSE_HEADER_PREFIX.size]) & 0xFFFFFFFF != header_crc:
            raise TransportError("response_header_crc_mismatch", "Kart yanıt başlık CRC kontrolü başarısızdır.")
        if payload_length == 0 or payload_length > MAX_RESPONSE_BYTES or len(packet) != RESPONSE_HEADER.size + payload_length:
            raise TransportError("response_length_contract", "Kart yanıt uzunluğu uyumsuzdur.")
        payload = bytes(packet[RESPONSE_HEADER.size :])
        if zlib.crc32(payload) & 0xFFFFFFFF != payload_crc:
            raise TransportError("response_crc_mismatch", "Kart yanıt CRC kontrolü başarısızdır.")
        return IQResponse(sequence, payload)


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
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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

    def exchange(self, frame: IQFrame) -> IQResponse:
        return self.exchange_batch((frame,))[0]

    def exchange_batch(self, frames: tuple[IQFrame, ...]) -> tuple[IQResponse, ...]:
        if not 1 <= len(frames) <= P0_PIPELINE_DEPTH:
            raise TransportError("invalid_batch_depth", "Ağ istek grubu 1–4 çerçeve içermelidir.")
        for index, frame in enumerate(frames):
            IQFrameCodec.validate_processing_frame(frame)
            if index and frame.sequence_number != ((frames[index - 1].sequence_number + 1) & 0xFFFFFFFF):
                raise TransportError("invalid_batch_sequence", "Ağ istek grubu ardışık sıra numaraları taşımalıdır.")
        for frame in frames:
            self.send(frame)
        return tuple(self._receive_response(frame.sequence_number) for frame in frames)

    def exchange_stream(
        self,
        frames: Iterable[IQFrame],
        response_handler: Callable[[IQResponse], None] | None = None,
    ) -> int:
        """Exchange a bounded continuous stream with at most four requests in flight."""
        iterator = iter(frames)
        pending_sequences: deque[int] = deque()
        previous_sequence: int | None = None
        exhausted = False

        def submit_next() -> bool:
            nonlocal exhausted, previous_sequence
            if exhausted:
                return False
            try:
                frame = next(iterator)
            except StopIteration:
                exhausted = True
                return False
            IQFrameCodec.validate_processing_frame(frame)
            if (
                previous_sequence is not None
                and frame.sequence_number != ((previous_sequence + 1) & 0xFFFFFFFF)
            ):
                raise TransportError(
                    "invalid_stream_sequence",
                    "Ağ istek akışı ardışık sıra numaraları taşımalıdır.",
                )
            self.send(frame)
            pending_sequences.append(frame.sequence_number)
            previous_sequence = frame.sequence_number
            return True

        while len(pending_sequences) < P0_PIPELINE_DEPTH and submit_next():
            pass
        if not pending_sequences:
            raise TransportError("empty_stream", "Ağ istek akışı boş olamaz.")

        completed = 0
        while pending_sequences:
            response = self._receive_response(pending_sequences.popleft())
            submit_next()
            if response_handler is not None:
                response_handler(response)
            completed += 1
        return completed

    def _receive_response(self, expected_sequence: int) -> IQResponse:
        assert self._socket is not None
        try:
            header = self._receive_exact(RESPONSE_HEADER.size)
            unpacked = RESPONSE_HEADER.unpack(header)
            payload_length = unpacked[5]
            if payload_length == 0 or payload_length > MAX_RESPONSE_BYTES:
                raise TransportError("response_length_contract", "Kart yanıt uzunluğu uyumsuzdur.")
            response = IQResponseCodec.decode(header + self._receive_exact(payload_length))
        except OSError as exc:
            self._stats = replace(self._stats, state="ERROR", last_error="receive_failed")
            raise TransportError("receive_failed", "ZedBoard yanıtı tamamlanamadı.") from exc
        if response.sequence_number != expected_sequence:
            self._stats = replace(
                self._stats,
                state="ERROR",
                sequence_errors=self._stats.sequence_errors + 1,
                last_error="response_sequence_mismatch",
            )
            raise TransportError("response_sequence_mismatch", "Kart yanıt sıra numarası istekle eşleşmiyor.")
        self._stats = replace(
            self._stats,
            frames_received=self._stats.frames_received + 1,
            bytes_received=self._stats.bytes_received + RESPONSE_HEADER.size + len(response.payload),
            last_error=None,
        )
        return response

    def _receive_exact(self, byte_count: int) -> bytes:
        assert self._socket is not None
        result = bytearray()
        while len(result) < byte_count:
            block = self._socket.recv(byte_count - len(result))
            if not block:
                raise OSError("connection closed before response completed")
            result.extend(block)
        return bytes(result)

    def close(self) -> None:
        connection, self._socket = self._socket, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        self._stats = replace(self._stats, state="DISCONNECTED")
