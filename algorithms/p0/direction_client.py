"""Versioned client for amplitude-DF estimation on the ZedBoard ARM."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import secrets
import socket
import struct
import zlib

from .df import DFEstimate, DFMeasurement, FIELD_AMPLITUDE_DF_PROFILE

REQUEST_BYTES = 6176
RESPONSE_BYTES = 104
MAX_MEASUREMENTS = 96
STATUS = (
    "YETERSİZ AÇI",
    "YETERSİZ AÇI KAPSAMI",
    "YETERSİZ TEKRAR",
    "ALICI AYARI DEĞİŞTİ",
    "HEDEF FREKANSI DEĞİŞTİ",
    "ÖN/ARKA BELİRSİZ",
    "BELİRSİZ MAKSİMUM",
    "LOB HAZIR",
)


@dataclass(frozen=True)
class BoardDFEstimate:
    estimate: DFEstimate
    request_token: int
    response: bytes


def _binding_hash(binding: str) -> int:
    if not binding:
        raise ValueError("Yön ölçümünde alıcı ayarı bağı zorunludur.")
    return int.from_bytes(hashlib.sha256(binding.encode("utf-8")).digest()[:8], "little")


def encode_df_request(measurements: tuple[DFMeasurement, ...], token: int) -> bytes:
    if not 0 < token < 1 << 32 or not 0 < len(measurements) <= MAX_MEASUREMENTS:
        raise ValueError("Yön isteği kimliği veya ölçüm sayısı geçersiz.")
    message = bytearray(REQUEST_BYTES)
    for index, item in enumerate(measurements):
        if item.channel_bandwidth_hz is None or item.frame_id is None:
            raise ValueError("Yön ölçümü kanal bant genişliği ve kaynak karesiyle bağlı olmalıdır.")
        struct.pack_into(
            "<5dII dQ", message, 32 + index * 64,
            item.angle_deg, item.relative_power_db, item.frequency_hz,
            item.confidence, item.power_spread_db, item.observation_count,
            item.frame_id, item.channel_bandwidth_hz, _binding_hash(item.receiver_binding),
        )
    struct.pack_into("<4sHHIIII", message, 0, b"P0DF", 1, 32, REQUEST_BYTES,
                     token, len(measurements), zlib.crc32(message[32:]))
    struct.pack_into("<I", message, 28, zlib.crc32(message[:28]))
    return bytes(message)


def decode_df_response(payload: bytes, token: int) -> BoardDFEstimate:
    if len(payload) != RESPONSE_BYTES:
        raise ValueError("Kart yön yanıtının uzunluğu geçersiz.")
    magic, version, length, actual_token, service_status = struct.unpack_from("<4sHHII", payload)
    if ((magic, version, length, actual_token) != (b"P0FR", 1, RESPONSE_BYTES, token)
            or zlib.crc32(payload[:100]) != struct.unpack_from("<I", payload, 100)[0]):
        raise ValueError("Kart yön yanıtı doğrulanamadı.")
    if service_status:
        if service_status not in (1, 2) or any(payload[16:100]):
            raise ValueError("Kart yön hata yanıtı geçersiz.")
        error = "Kart yön ölçümlerini reddetti." if service_status == 1 else "Kart yön hesabı başarısız."
        raise RuntimeError(error)
    status_code, measurement_count, distinct_count, flags = struct.unpack_from("<IIII", payload, 16)
    values = struct.unpack_from("<8d", payload, 32)
    if (status_code >= len(STATUS) or flags & ~3 or not all(math.isfinite(value) for value in values)
            or not 0 < measurement_count <= MAX_MEASUREMENTS
            or not 0 < distinct_count <= measurement_count):
        raise ValueError("Kart yön sonucu geçersiz.")
    front_to_back = values[6] if flags & 1 else None
    sampling_rms = values[7] if flags & 2 else None
    estimate = DFEstimate(
        raw_maximum_angle_deg=values[0],
        estimated_angle_deg=values[1],
        peak_power_db=values[2],
        confidence=values[3],
        measurement_count=measurement_count,
        status=STATUS[status_code],
        distinct_angle_count=distinct_count,
        maximum_angular_gap_deg=values[4],
        peak_prominence_db=values[5],
        front_to_back_db=front_to_back,
        angular_sampling_rms_deg=sampling_rms,
        profile_id=FIELD_AMPLITUDE_DF_PROFILE.profile_id,
    )
    return BoardDFEstimate(estimate, token, payload)


def estimate_on_board(host: str, port: int,
                      measurements: tuple[DFMeasurement, ...]) -> BoardDFEstimate:
    token = secrets.randbelow((1 << 32) - 1) + 1
    request = encode_df_request(measurements, token)
    response = bytearray()
    try:
        with socket.create_connection((host, port), timeout=5.0) as connection:
            connection.settimeout(10.0)
            connection.sendall(request)
            while len(response) < RESPONSE_BYTES:
                chunk = connection.recv(RESPONSE_BYTES - len(response))
                if not chunk:
                    raise RuntimeError("Kart yön bağlantısı yanıt tamamlanmadan kapandı.")
                response.extend(chunk)
    except OSError as exc:
        raise RuntimeError("Kart ARM yön hesabına yanıt vermedi.") from exc
    return decode_df_response(bytes(response), token)
