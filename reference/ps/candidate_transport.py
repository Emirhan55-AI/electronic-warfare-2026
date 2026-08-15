"""Versioned little-endian PHASE-06I PL-to-PS candidate packet ABI."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Iterable

from reference.rtl.candidate_grouping import CandidateRecord, MAX_CANDIDATES


ABI_VERSION = 1
HEADER_MAGIC = 0x48493650  # bytes: P6IH
TRAILER_MAGIC = 0x54493650  # bytes: P6IT
HEADER_BYTES = 32
RECORD_BYTES = 40
TRAILER_BYTES = 32
FFT_SIZE = 4096
MAX_FRAME_BYTES = HEADER_BYTES + MAX_CANDIDATES * RECORD_BYTES + TRAILER_BYTES
HEADER_EMPTY = 1 << 0
RECORD_VALID = 1 << 0
RECORD_EVALUATE_CENTER = 1 << 1
STATUS_INPUT_CONTRACT_ERROR = 1 << 0
STATUS_CANDIDATE_OVERFLOW = 1 << 1
STATUS_PACKETIZER_INTERNAL_ERROR = 1 << 2

_HEADER = struct.Struct("<IHHIHHIIII")
_RECORD = struct.Struct("<HHHHBBHIQQQ")
_TRAILER = struct.Struct("<IHHIHHIIII")


@dataclass(frozen=True)
class CandidatePacket:
    frame_id: int
    candidates: tuple[CandidateRecord, ...]
    status: int = 0


def _check_frame_id(frame_id: int) -> None:
    if not 0 <= frame_id <= 0xFFFF_FFFF:
        raise ValueError("frame_id must be uint32")


def _encode_record(candidate: CandidateRecord) -> bytes:
    if not (0 <= candidate.start_shifted_bin <= candidate.peak_shifted_bin <= candidate.end_shifted_bin < FFT_SIZE):
        raise ValueError("candidate bin ordering is invalid")
    if candidate.coarse_span_bins != candidate.end_shifted_bin - candidate.start_shifted_bin + 1:
        raise ValueError("candidate coarse span is invalid")
    if candidate.pfa_select not in (0, 1, 2):
        raise ValueError("candidate Pfa selector is invalid")
    if not 0 <= candidate.peak_power < (1 << 58):
        raise ValueError("candidate peak power exceeds 58 bits")
    if not 0 <= candidate.regional_noise < (1 << 58):
        raise ValueError("candidate noise exceeds 58 bits")
    if not 0 <= candidate.threshold < (1 << 62):
        raise ValueError("candidate threshold exceeds 62 bits")
    flags = RECORD_VALID | (RECORD_EVALUATE_CENTER if candidate.evaluate_center else 0)
    return _RECORD.pack(
        candidate.start_shifted_bin,
        candidate.end_shifted_bin,
        candidate.peak_shifted_bin,
        candidate.coarse_span_bins,
        candidate.pfa_select,
        flags,
        0,
        0,
        candidate.peak_power,
        candidate.regional_noise,
        candidate.threshold,
    )


def encode_packet(frame_id: int, candidates: Iterable[CandidateRecord], *, status: int = 0) -> bytes:
    """Encode one DMA packet. Empty semantic frames contain no candidate records."""
    _check_frame_id(frame_id)
    records = tuple(candidates)
    if len(records) > MAX_CANDIDATES:
        raise ValueError("candidate count exceeds the proven frame bound")
    if not 0 <= status <= 0xFFFF:
        raise ValueError("status must be uint16")
    payload = b"".join(_encode_record(candidate) for candidate in records)
    flags = HEADER_EMPTY if not records else 0
    header = _HEADER.pack(
        HEADER_MAGIC, ABI_VERSION, HEADER_BYTES, frame_id, FFT_SIZE, RECORD_BYTES,
        flags, 0, 0, 0,
    )
    packet_bytes = HEADER_BYTES + len(payload) + TRAILER_BYTES
    trailer = _TRAILER.pack(
        TRAILER_MAGIC, ABI_VERSION, TRAILER_BYTES, frame_id, len(records), status,
        len(payload), packet_bytes, zlib.crc32(payload), 0,
    )
    return header + payload + trailer


def decode_packet(data: bytes) -> CandidatePacket:
    """Strictly decode and validate one complete DMA packet."""
    if len(data) < HEADER_BYTES + TRAILER_BYTES or len(data) > MAX_FRAME_BYTES:
        raise ValueError("packet length is outside the bounded ABI")
    header = _HEADER.unpack_from(data, 0)
    magic, version, header_bytes, frame_id, fft_size, record_bytes, flags, r0, r1, r2 = header
    if (magic, version, header_bytes, fft_size, record_bytes) != (
        HEADER_MAGIC, ABI_VERSION, HEADER_BYTES, FFT_SIZE, RECORD_BYTES
    ):
        raise ValueError("packet header contract mismatch")
    if flags & ~HEADER_EMPTY or (r0, r1, r2) != (0, 0, 0):
        raise ValueError("packet header flags/reserved fields are invalid")
    trailer_offset = len(data) - TRAILER_BYTES
    trailer = _TRAILER.unpack_from(data, trailer_offset)
    tmagic, tversion, trailer_bytes, trailer_frame, count, status, payload_bytes, packet_bytes, crc32, reserved = trailer
    if (tmagic, tversion, trailer_bytes, trailer_frame) != (
        TRAILER_MAGIC, ABI_VERSION, TRAILER_BYTES, frame_id
    ):
        raise ValueError("packet trailer contract mismatch")
    if reserved != 0 or packet_bytes != len(data) or payload_bytes != trailer_offset - HEADER_BYTES:
        raise ValueError("packet length metadata mismatch")
    if count > MAX_CANDIDATES or payload_bytes != count * RECORD_BYTES:
        raise ValueError("candidate count/record length mismatch")
    payload = data[HEADER_BYTES:trailer_offset]
    if zlib.crc32(payload) != crc32:
        raise ValueError("candidate payload CRC32 mismatch")
    if bool(flags & HEADER_EMPTY) != (count == 0):
        raise ValueError("empty-frame flag/count mismatch")
    candidates: list[CandidateRecord] = []
    for offset in range(0, len(payload), RECORD_BYTES):
        start, end, peak, span, pfa, record_flags, rr0, rr1, power, noise, threshold = _RECORD.unpack_from(payload, offset)
        if record_flags & ~(RECORD_VALID | RECORD_EVALUATE_CENTER) or not record_flags & RECORD_VALID:
            raise ValueError("candidate record flags are invalid")
        if rr0 != 0 or rr1 != 0:
            raise ValueError("candidate reserved fields are nonzero")
        candidate = CandidateRecord(
            start_shifted_bin=start,
            end_shifted_bin=end,
            peak_shifted_bin=peak,
            peak_power=power,
            regional_noise=noise,
            threshold=threshold,
            pfa_select=pfa,
            evaluate_center=bool(record_flags & RECORD_EVALUATE_CENTER),
        )
        if span != candidate.coarse_span_bins:
            raise ValueError("candidate record span mismatch")
        _encode_record(candidate)
        candidates.append(candidate)
    return CandidatePacket(frame_id=frame_id, candidates=tuple(candidates), status=status)


def architecture_study() -> dict[str, object]:
    return {
        "selected": "AXI4-Stream packetizer to interrupt-driven AXI DMA S2MM bounded DDR buffers",
        "dma_instantiated": False,
        "reason": "variable sparse packets, 54144-byte proven maximum, low CPU copy overhead, Linux-friendly descriptor/IRQ flow",
        "rejected": {
            "axi4_lite_polling": "up to 1352 records/frame creates excessive register transactions and CPU polling",
            "axi_fifo_only": "useful elastic component but does not by itself provide bounded DDR ownership or Linux DMA completion",
            "unframed_dma": "lacks explicit version/frame/count/CRC integrity boundary",
        },
        "maximum_frame_bytes": MAX_FRAME_BYTES,
        "recommended_ddr_buffers": 2,
        "recommended_total_ddr_bytes": 2 * MAX_FRAME_BYTES,
        "loss_policy": "AXI backpressure; malformed packet is explicitly status-marked and rejected by PS; no silent drop",
    }
