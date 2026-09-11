"""Read and apply the card's CFAR profile over its versioned control path."""
from dataclasses import dataclass
import secrets
import socket
import struct
import zlib

NORMAL_DEFAULT = 36_851_433_755
WEAK_DEFAULT = 17_098_572_778
_MESSAGE = struct.Struct('<4sHHIIIIQQII')


class DetectionConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class DetectionProfile:
    generation: int
    alpha_q32: int
    weak_alpha_q32: int
    fft_size: int = 4096
    runtime_fft_supported: bool = False

    def __post_init__(self):
        for value, lower, upper in ((self.generation, 0, 1 << 32),
                (self.alpha_q32, 1 << 32, 1 << 36),
                (self.weak_alpha_q32, 1 << 32, 1 << 34)):
            if type(value) is not int or not lower <= value < upper:
                raise DetectionConfigError('Kart tespit profili desteklenen aralıkta değil.')
        if self.weak_alpha_q32 > self.alpha_q32:
            raise DetectionConfigError('Zayıf aday eşiği normal eşikten büyük olamaz.')
        if self.fft_size not in (4096, 8192, 16384) or not isinstance(self.runtime_fft_supported, bool):
            raise DetectionConfigError('Kart FFT profili desteklenen aralıkta değil.')


def encode_request(operation: int, request_id: int, profile: DetectionProfile | None = None,
                   *, protocol_version: int = 1) -> bytes:
    if type(operation) is not int or operation not in (1, 2) or type(request_id) is not int or not 0 <= request_id < 1 << 32:
        raise DetectionConfigError('Geçersiz ayar isteği.')
    if (operation == 1 and profile is not None) or (operation == 2 and not isinstance(profile, DetectionProfile)):
        raise DetectionConfigError('Ayar işlemi ve profil eşleşmiyor.')
    if protocol_version not in (1, 2):
        raise DetectionConfigError('Kart ayar protokolü desteklenmiyor.')
    fields = (profile.generation, profile.alpha_q32, profile.weak_alpha_q32) if profile else (0, 0, 0)
    fft_size = profile.fft_size if profile and protocol_version == 2 else 0
    payload = _MESSAGE.pack(b'P0DC', protocol_version, 48, operation, request_id, 0,
                            *fields, fft_size, 0)
    return payload[:44] + struct.pack('<I', zlib.crc32(payload[:44]))


def decode_response(payload: bytes, operation: int, request_id: int,
                    *, protocol_version: int = 1) -> DetectionProfile:
    if len(payload) != 48:
        raise DetectionConfigError('Kart ayar yanıtının uzunluğu geçersiz.')
    magic, version, length, op, token, status, generation, alpha, weak, fft_size, crc = _MESSAGE.unpack(payload)
    if (magic, version, length, op, token) != (b'P0DR', protocol_version, 48, operation, request_id) or crc != zlib.crc32(payload[:44]):
        raise DetectionConfigError('Kart ayar yanıtı doğrulanamadı.')
    errors = {1: 'Kartın mevcut imajı çalışma sırasında ayar değiştirmeyi desteklemiyor.',
              2: 'Kart meşgul; alımı durdurup tekrar deneyin.',
              3: 'Kart bu ayar birleşimini reddetti.',
              4: 'Kart profili değişmiş; etkin ayarları yeniden okuyun.',
              5: 'Kart ayarı uygulanamadı veya sonucu doğrulanamadı.'}
    if status:
        if generation or alpha or weak or fft_size or status not in errors:
            raise DetectionConfigError('Kart hata yanıtı geçersiz.')
        raise DetectionConfigError(errors[status])
    if protocol_version == 1 and fft_size != 0:
        raise DetectionConfigError('Kart ayar yanıtı doğrulanamadı.')
    if protocol_version == 2 and fft_size not in (4096, 8192, 16384):
        raise DetectionConfigError('Kart FFT ayar yanıtı doğrulanamadı.')
    return DetectionProfile(generation, alpha, weak,
                            fft_size if protocol_version == 2 else 4096,
                            protocol_version == 2)


def _exchange_version(host: str, port: int, operation: int, token: int,
                      profile: DetectionProfile | None, timeout: float,
                      protocol_version: int) -> DetectionProfile:
    request = encode_request(operation, token, profile, protocol_version=protocol_version)
    response = bytearray()
    try:
        with socket.create_connection((host, port), timeout=timeout) as connection:
            connection.settimeout(timeout)
            connection.sendall(request)
            while len(response) < 48:
                chunk = connection.recv(48 - len(response))
                if not chunk:
                    raise DetectionConfigError('Kart ayar bağlantısını kapattı; hizmet sürümü uyumsuz olabilir.')
                response.extend(chunk)
    except OSError as exc:
        raise DetectionConfigError('Kart ayar bağlantısı kurulamadı veya yanıt alınamadı.') from exc
    return decode_response(bytes(response), operation, token, protocol_version=protocol_version)


def exchange_profile(host: str, port: int = 47007, *, profile: DetectionProfile | None = None,
                     timeout: float = 3.0) -> DetectionProfile:
    if not host or type(port) is not int or not 1 <= port <= 65535 or not 0 < timeout <= 10:
        raise DetectionConfigError('Kart bağlantı ayarları geçersiz.')
    operation = 1 if profile is None else 2
    token = secrets.randbits(32)
    if profile is None:
        try:
            actual = _exchange_version(host, port, operation, token, None, timeout, 2)
        except DetectionConfigError:
            actual = _exchange_version(host, port, operation, token, None, timeout, 1)
    else:
        version = 2 if profile.runtime_fft_supported else 1
        actual = _exchange_version(host, port, operation, token, profile, timeout, version)
    expected = (DetectionProfile((profile.generation + 1) & 0xffffffff,
                                 profile.alpha_q32, profile.weak_alpha_q32,
                                 profile.fft_size, profile.runtime_fft_supported)
                if profile is not None else None)
    if expected is not None and actual != expected:
        raise DetectionConfigError('Kartın uyguladığı değerler istenen ayarlarla eşleşmiyor.')
    return actual
