"""Bounded, CRC-protected Computer-1 to ZedBoard IQ transport abstraction."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import math
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
PARAMETER_HEADER_PREFIX = struct.Struct("<4sBBHIIHHQIIIIIIQQHHI")
PARAMETER_HEADER = struct.Struct("<4sBBHIIHHQIIIIIIQQHHII")
RESPONSE_HEADER_PREFIX = struct.Struct("<4sBBHIII")
RESPONSE_HEADER = struct.Struct("<4sBBHIIII")
CAPABILITY_PREFIX = struct.Struct("<4sBBHIIIIII12s")
CAPABILITY_MESSAGE = struct.Struct("<4sBBHIIIIII12sI")
MAX_PAYLOAD_BYTES = 131_072
MAX_RESPONSE_BYTES = 16_384
P0_SAMPLE_RATE_HZ = 2_000_000
P0_WIDEBAND_SAMPLE_RATE_HZ = 10_000_000
P0_SUPPORTED_SAMPLE_RATES_HZ = (P0_SAMPLE_RATE_HZ, P0_WIDEBAND_SAMPLE_RATE_HZ)
P0_COMPLEX_SAMPLES = 4_096
P0_SUPPORTED_COMPLEX_SAMPLES = (4_096, 8_192, 16_384)
P0_PAYLOAD_BYTES = P0_COMPLEX_SAMPLES * 2
P0_PIPELINE_DEPTH = 4
LOCAL_ED_RESPONSE_MAGIC = 0x31534550
LOCAL_ED_RESPONSE_HEADER_BYTES = 48
LOCAL_ED_RESPONSE_HEADER_BYTES_V2 = 64
LOCAL_ED_RESULT_BYTES = 8_724
LOCAL_ED_PARAMETER_RESULT_BYTES = 128
PARAMETER_REQUEST_FLAG = 0x00000001
PARAMETER_REQUEST_START_FLAG = 0x00000002
PARAMETER_REQUEST_ALLOWED_FLAGS = PARAMETER_REQUEST_FLAG | PARAMETER_REQUEST_START_FLAG
CAPABILITY_MAGIC_QUERY = b"P0CQ"
CAPABILITY_MAGIC_RESPONSE = b"P0CR"
CAPABILITY_TYPE_QUERY = 1
CAPABILITY_TYPE_RESPONSE = 2
CAPABILITY_INLINE_PARAMETER = 0x00000001
CAPABILITY_WIDEBAND_BURST = 0x00000002
CAPABILITY_EXTENDED_PARAMETER = 0x00000004
CAPABILITY_CARRIER_RECOVERY = 0x00000008


class TransportError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParameterObservationRequest:
    intent_id: int
    event_id: int
    lower_shifted_bin: int
    upper_shifted_bin: int
    start: bool = False


@dataclass(frozen=True)
class TransportCapabilities:
    inline_parameter_observation: bool = False
    maximum_parameter_span_bins: int = 0
    parameter_contexts: int = 0
    wideband_burst: bool = False
    extended_parameter: bool = False
    carrier_recovery: bool = False


@dataclass(frozen=True)
class InlineParameterField:
    state: str
    value: float | None
    reason: str | None


@dataclass(frozen=True)
class InlineParameterResult:
    intent_id: int
    event_id: int
    frame_id: int
    observation_count: int
    emission_center_frequency_hz: InlineParameterField
    lower_occupied_edge_hz: InlineParameterField
    upper_occupied_edge_hz: InlineParameterField
    occupied_bandwidth_hz: InlineParameterField
    channel_power_dbfs: InlineParameterField
    snr_estimate_db: InlineParameterField
    reference_difference_db: float
    detection_significance: float
    center_uncertainty_bins: float
    temporal_edge_range_bins: float


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
    parameter_request: ParameterObservationRequest | None = None

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
    abi_version: int = 3
    result_offset: int = LOCAL_ED_RESPONSE_HEADER_BYTES
    result_bytes: int = 0
    compact_result: bool = True
    parameter: InlineParameterResult | None = None


def _decode_inline_parameter(payload: bytes, offset: int) -> InlineParameterResult:
    states = {
        0: "insufficient_quality",
        1: "valid",
        2: "insufficient_quality",
        3: "uncertain",
    }
    reasons = {
        0: None,
        1: "accumulating",
        2: "event_ownership_lost",
        3: "reference_power_unavailable",
        4: "reference_mismatch",
        5: "excess_power_not_significant",
        6: "center_temporal_uncertainty",
        7: "span_edge_clipping",
        8: "obw_temporal_instability",
        9: "carrier_line_below_threshold",
        10: "quality_below_carrier_threshold",
    }

    def field(field_offset: int) -> InlineParameterField:
        state, reason, reserved, value = struct.unpack_from(
            "<BBHd", payload, field_offset
        )
        if (
            state not in states
            or reason not in reasons
            or reserved != 0
            or not math.isfinite(value)
            or (state == 1 and reason != 0)
        ):
            raise TransportError(
                "local_response_parameter", "Kart parametre alanı doğrulanamadı."
            )
        return InlineParameterField(
            states[state], value if state == 1 else None, reasons[reason]
        )

    intent_id, event_id, frame_id, observation_count = struct.unpack_from(
        "<QQIB", payload, offset
    )
    if (
        intent_id == 0
        or event_id == 0
        or observation_count > 4
        or any(payload[offset + 21 : offset + 24])
    ):
        raise TransportError(
            "local_response_parameter", "Kart parametre sonucu doğrulanamadı."
        )
    fields = tuple(field(offset + item) for item in range(24, 96, 12))
    qualities = struct.unpack_from("<dddd", payload, offset + 96)
    if any(not math.isfinite(value) for value in qualities):
        raise TransportError(
            "local_response_parameter", "Kart parametre kalite değerleri geçersiz."
        )
    return InlineParameterResult(
        intent_id,
        event_id,
        frame_id,
        observation_count,
        *fields,
        *qualities,
    )


def decode_local_ed_response(payload: bytes, expected_frame_id: int) -> LocalEDResponse:
    """Decode compact ABI-v3/v4 or full ABI-v2 board-service responses."""
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
    if magic != LOCAL_ED_RESPONSE_MAGIC or version not in (2, 3, 4):
        raise TransportError("local_response_header", "Yerel kart hizmeti yanıt başlığı doğrulanamadı.")
    if version == 2:
        expected_header_bytes = LOCAL_ED_RESPONSE_HEADER_BYTES_V2
        header_crc = struct.unpack_from("<I", payload, 60)[0] if len(payload) >= 64 else -1
        parameter_bytes, parameter_crc, parameter_present = struct.unpack_from(
            "<III", payload, 36
        ) if len(payload) >= 48 else (-1, -1, -1)
        reserved_valid = len(payload) >= 64 and not any(payload[48:60])
        parameter_contract = (
            (parameter_bytes == 0 and parameter_crc == 0 and parameter_present == 0)
            or (
                parameter_bytes == LOCAL_ED_PARAMETER_RESULT_BYTES
                and parameter_present == 1
            )
        )
    else:
        expected_header_bytes = LOCAL_ED_RESPONSE_HEADER_BYTES
        header_crc = struct.unpack_from("<I", payload, 44)[0]
        parameter_bytes = 0
        parameter_crc = 0
        parameter_present = 0
        reserved_valid = not any(payload[offset] != 0 for offset in range(32, 44))
        parameter_contract = True
    if (
        header_bytes != expected_header_bytes
        or total_bytes != len(payload)
        or frame_id != expected_frame_id
        or header_crc != zlib.crc32(payload[: expected_header_bytes - 4]) & 0xFFFFFFFF
        or not reserved_valid
        or not parameter_contract
    ):
        raise TransportError("local_response_header", "Yerel kart hizmeti kompakt yanıt başlığı doğrulanamadı.")
    if status != 0:
        errors = {
            1: ("local_invalid_request", "FPGA hizmeti örnek boyutu veya istek biçimini reddetti."),
            2: ("local_dma_failure", "FPGA DMA işlemi tamamlanamadı."),
            3: ("local_pipeline_failure", "FPGA tespit işleme hattı sonucu tamamlayamadı."),
            4: ("local_internal_failure", "FPGA hizmetinde iç işlem hatası oluştu."),
        }
        code, message = errors.get(
            status,
            ("local_service_failure", "FPGA hizmeti tanımsız bir hata durumu döndürdü."),
        )
        raise TransportError(code, message)
    result_offset = expected_header_bytes
    result = payload[result_offset : result_offset + result_bytes]
    if len(result) != result_bytes or result_bytes < 20 or len(payload) != result_offset + result_bytes + parameter_bytes:
        raise TransportError("local_response_length", "Yerel kart hizmeti sonuç uzunluğu geçersiz.")
    if version == 2:
        if result_bytes != LOCAL_ED_RESULT_BYTES or struct.unpack_from("<I", payload, 32)[0] != zlib.crc32(result) & 0xFFFFFFFF:
            raise TransportError("local_response_result", "Tam kart sonucu CRC kontrolünden geçmedi.")
    elif result_bytes != 20 + 68 * (
        struct.unpack_from("<H", result, 4)[0] + struct.unpack_from("<H", result, 6)[0]
    ):
        raise TransportError("local_response_result", "Kompakt kart sonucu uzunluğu geçersiz.")
    result_frame_id = struct.unpack_from("<I", result, 0)[0]
    active_count, ended_count, dropped_candidates = struct.unpack_from("<HHH", result, 4)
    reset_applied = result[10]
    if (
        result_frame_id != expected_frame_id
        or result[11] != 0
        or (version != 2 and result_bytes != 20 + 68 * (active_count + ended_count))
    ):
        raise TransportError("local_response_result", "Kompakt kart sonucu doğrulanamadı.")
    parameter = None
    if parameter_bytes:
        parameter_offset = result_offset + result_bytes
        parameter_payload = payload[parameter_offset : parameter_offset + parameter_bytes]
        if parameter_crc != zlib.crc32(parameter_payload) & 0xFFFFFFFF:
            raise TransportError("local_response_parameter", "Kart parametre sonucu CRC kontrolünden geçmedi.")
        parameter = _decode_inline_parameter(payload, parameter_offset)
        if parameter.frame_id != frame_id:
            raise TransportError("local_response_parameter", "Kart parametre karesi istekle eşleşmiyor.")
    return LocalEDResponse(
        frame_id=frame_id,
        raw_candidate_count=raw_candidate_count,
        dma_status_flags=dma_status_flags,
        active_count=active_count,
        ended_count=ended_count,
        dropped_candidates=dropped_candidates,
        reset_applied=reset_applied,
        response_bytes=len(payload),
        abi_version=version,
        result_offset=result_offset,
        result_bytes=result_bytes,
        compact_result=version in (3, 4),
        parameter=parameter,
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
        common = (
            MAGIC,
            VERSION,
            SAMPLE_FORMAT_CI8,
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
        parameter = frame.parameter_request
        if parameter is None:
            prefix = HEADER_PREFIX.pack(common[0], common[1], common[2], HEADER.size, *common[3:])
        else:
            flags = PARAMETER_REQUEST_FLAG
            if parameter.start:
                flags |= PARAMETER_REQUEST_START_FLAG
            if (
                frame.complex_sample_count != P0_COMPLEX_SAMPLES
                or not 0 < parameter.intent_id < 1 << 64
                or not 0 < parameter.event_id < 1 << 64
                or not 56 <= parameter.lower_shifted_bin <= parameter.upper_shifted_bin <= 4039
                or not 8 <= parameter.upper_shifted_bin - parameter.lower_shifted_bin + 1 <= 512
            ):
                raise TransportError(
                    "invalid_parameter_request",
                    "Otomatik parametre isteği kartın sınırlı canlı ölçüm zarfına uymuyor.",
                )
            prefix = PARAMETER_HEADER_PREFIX.pack(
                common[0], common[1], common[2], PARAMETER_HEADER.size, *common[3:],
                flags, 0, parameter.intent_id, parameter.event_id,
                parameter.lower_shifted_bin, parameter.upper_shifted_bin, 0,
            )
        header_crc = zlib.crc32(prefix) & 0xFFFFFFFF
        return prefix + struct.pack("<I", header_crc) + payload

    @staticmethod
    def decode(packet: bytes) -> IQFrame:
        if len(packet) < HEADER.size:
            raise TransportError("short_header", "IQ paketi başlıktan kısadır.")
        magic, version, sample_format, header_size = struct.unpack_from("<4sBBH", packet)
        if magic != MAGIC or version != VERSION or header_size not in {HEADER.size, PARAMETER_HEADER.size}:
            raise TransportError("header_contract", "IQ paket başlığı veya sürümü uyumsuzdur.")
        if len(packet) < header_size:
            raise TransportError("short_header", "IQ paketi bildirilen başlıktan kısadır.")
        if header_size == HEADER.size:
            unpacked = HEADER.unpack_from(packet)
            (_, _, _, _, sequence, frame_id, chunk_index, chunk_count, center, rate,
             sample_count, payload_length, crc, header_crc) = unpacked
            parameter = None
            prefix_size = HEADER_PREFIX.size
        else:
            unpacked = PARAMETER_HEADER.unpack_from(packet)
            (_, _, _, _, sequence, frame_id, chunk_index, chunk_count, center, rate,
             sample_count, payload_length, crc, flags, reserved, intent_id, event_id,
             lower, upper, reserved_tail, header_crc) = unpacked
            if (
                reserved != 0
                or reserved_tail != 0
                or (flags & ~PARAMETER_REQUEST_ALLOWED_FLAGS) != 0
                or (flags & PARAMETER_REQUEST_FLAG) == 0
                or not 0 < intent_id < 1 << 64
                or not 0 < event_id < 1 << 64
                or not 56 <= lower <= upper <= 4039
                or not 8 <= upper - lower + 1 <= 512
            ):
                raise TransportError("parameter_contract", "IQ otomatik parametre alanları geçersizdir.")
            parameter = ParameterObservationRequest(
                intent_id, event_id, lower, upper,
                bool(flags & PARAMETER_REQUEST_START_FLAG),
            )
            prefix_size = PARAMETER_HEADER_PREFIX.size
        if zlib.crc32(packet[:prefix_size]) & 0xFFFFFFFF != header_crc:
            raise TransportError("header_crc_mismatch", "IQ paket başlık CRC kontrolü başarısızdır.")
        if sample_format != SAMPLE_FORMAT_CI8:
            raise TransportError("unsupported_sample_format", "IQ örnek biçimi desteklenmiyor.")
        if payload_length == 0 or payload_length > MAX_PAYLOAD_BYTES or payload_length % 2 or len(packet) != header_size + payload_length:
            raise TransportError("payload_contract", "IQ paket yük uzunluğu uyumsuzdur.")
        if center == 0 or rate == 0:
            raise TransportError("metadata_contract", "IQ paket örnekleme veya merkez frekansı geçersizdir.")
        if sample_count * 2 != payload_length or chunk_count < 1 or chunk_index >= chunk_count:
            raise TransportError("chunk_contract", "IQ frame/chunk alanları uyumsuzdur.")
        if parameter is not None and sample_count != P0_COMPLEX_SAMPLES:
            raise TransportError("parameter_contract", "Canlı parametre isteği yalnız 4096 örneklik çerçeveyi destekler.")
        payload = bytes(packet[header_size:])
        if zlib.crc32(payload) & 0xFFFFFFFF != crc:
            raise TransportError("crc_mismatch", "IQ paket CRC kontrolü başarısızdır.")
        return IQFrame(sequence, rate, center, payload, "ci8", frame_id, chunk_index, chunk_count, parameter)

    @staticmethod
    def validate_processing_frame(frame: IQFrame) -> None:
        if (
            frame.sample_format != "ci8"
            or frame.sample_rate_hz not in P0_SUPPORTED_SAMPLE_RATES_HZ
            or frame.complex_sample_count not in P0_SUPPORTED_COMPLEX_SAMPLES
            or len(frame.payload) != frame.complex_sample_count * 2
            or frame.chunk_index != 0
            or frame.chunk_count != 1
            or (
                frame.parameter_request is not None
                and frame.sample_rate_hz != P0_SAMPLE_RATE_HZ
            )
        ):
            raise TransportError(
                "processing_profile_mismatch",
                "FPGA işleme yolu 2 veya 10 MS/s, 4096 örnek ile 8192/16384 seçeneklerinden birini ve tek parça ci8 çerçeveyi gerektirir; parametre isteği yalnız 2 MS/s'dir.",
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


class IQCapabilityCodec:
    @staticmethod
    def _encode(magic: bytes, message_type: int, capabilities: TransportCapabilities) -> bytes:
        flags = CAPABILITY_INLINE_PARAMETER if capabilities.inline_parameter_observation else 0
        if capabilities.wideband_burst:
            flags |= CAPABILITY_WIDEBAND_BURST
        if capabilities.extended_parameter:
            flags |= CAPABILITY_EXTENDED_PARAMETER
        if capabilities.carrier_recovery:
            flags |= CAPABILITY_CARRIER_RECOVERY
        prefix = CAPABILITY_PREFIX.pack(
            magic,
            VERSION,
            message_type,
            CAPABILITY_MESSAGE.size,
            flags,
            capabilities.maximum_parameter_span_bins,
            capabilities.parameter_contexts,
            0,
            0,
            0,
            bytes(12),
        )
        return prefix + struct.pack("<I", zlib.crc32(prefix) & 0xFFFFFFFF)

    @classmethod
    def encode_query(cls) -> bytes:
        return cls._encode(
            CAPABILITY_MAGIC_QUERY,
            CAPABILITY_TYPE_QUERY,
            TransportCapabilities(False, 0, 0),
        )

    @classmethod
    def encode_response(cls, capabilities: TransportCapabilities) -> bytes:
        return cls._encode(CAPABILITY_MAGIC_RESPONSE, CAPABILITY_TYPE_RESPONSE, capabilities)

    @staticmethod
    def decode_response(packet: bytes) -> TransportCapabilities:
        if len(packet) != CAPABILITY_MESSAGE.size:
            raise TransportError("capability_length", "Kart yetenek yanıtı uzunluğu geçersizdir.")
        (magic, version, message_type, header_size, flags, maximum_span,
         contexts, reserved_a, reserved_b, reserved_c, reserved_tail,
         header_crc) = CAPABILITY_MESSAGE.unpack(packet)
        if (
            magic != CAPABILITY_MAGIC_RESPONSE
            or version != VERSION
            or message_type != CAPABILITY_TYPE_RESPONSE
            or header_size != CAPABILITY_MESSAGE.size
            or (flags & ~(CAPABILITY_INLINE_PARAMETER | CAPABILITY_WIDEBAND_BURST | CAPABILITY_EXTENDED_PARAMETER | CAPABILITY_CARRIER_RECOVERY)) != 0
            or reserved_a != 0
            or reserved_b != 0
            or reserved_c != 0
            or any(reserved_tail)
            or header_crc != zlib.crc32(packet[: CAPABILITY_PREFIX.size]) & 0xFFFFFFFF
        ):
            raise TransportError("capability_contract", "Kart yetenek yanıtı doğrulanamadı.")
        inline = bool(flags & CAPABILITY_INLINE_PARAMETER)
        if flags & CAPABILITY_CARRIER_RECOVERY and not flags & CAPABILITY_EXTENDED_PARAMETER:
            raise TransportError("capability_contract", "Taşıyıcı kestirimi 16 kare yeteneği gerektirir.")
        if (
            inline
            and (not 8 <= maximum_span <= 512 or contexts != 1)
        ) or (not inline and (maximum_span != 0 or contexts != 0)):
            raise TransportError("capability_contract", "Kart yetenek sınırları geçersizdir.")
        return TransportCapabilities(
            inline, maximum_span, contexts,
            bool(flags & CAPABILITY_WIDEBAND_BURST), bool(flags & CAPABILITY_EXTENDED_PARAMETER),
            bool(flags & CAPABILITY_CARRIER_RECOVERY),
        )


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
        self._capabilities = TransportCapabilities()

    @property
    def stats(self) -> TransportStats:
        return self._stats

    @property
    def capabilities(self) -> TransportCapabilities:
        return self._capabilities

    def probe_capabilities(
        self, host: str, port: int, *, timeout_seconds: float = 2.0
    ) -> TransportCapabilities:
        """Probe on a separate connection so a legacy bridge cannot break RX."""
        if not host or not 1 <= port <= 65535 or not 0 < timeout_seconds <= 10.0:
            raise TransportError("invalid_endpoint", "ZedBoard ağ uç noktası geçersizdir.")
        response = bytearray()
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds) as connection:
                connection.settimeout(timeout_seconds)
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                connection.sendall(IQCapabilityCodec.encode_query())
                while len(response) < CAPABILITY_MESSAGE.size:
                    block = connection.recv(CAPABILITY_MESSAGE.size - len(response))
                    if not block:
                        break
                    response.extend(block)
        except OSError:
            self._capabilities = TransportCapabilities()
            return self._capabilities
        try:
            self._capabilities = IQCapabilityCodec.decode_response(bytes(response))
        except TransportError:
            self._capabilities = TransportCapabilities()
        return self._capabilities

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
            # Refill the bounded request window before host-side decoding and
            # presentation. This keeps the card busy while the callback works;
            # scheduler decisions intentionally take effect one frame later.
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
