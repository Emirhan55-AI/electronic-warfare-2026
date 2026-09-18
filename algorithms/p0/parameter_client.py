"""Bounded recorded-I/Q measurement on the ZedBoard PL and ARM."""
from dataclasses import dataclass
import math
import secrets
import socket
import struct
import zlib

from algorithms.parameters.f1_estimator import F1ParameterResult, F1Quality
from algorithms.parameters.operator_assisted import AnalysisSpan, FieldMeasurement, MeasurementIntent

MAXIMUM_BOARD_SPAN_BINS = 3984
BOARD_PERSISTENT_PAYLOAD_BYTES = 4 * (MAXIMUM_BOARD_SPAN_BINS + 72) * 24
EXTENDED_BOARD_PAYLOAD_BYTES = BOARD_PERSISTENT_PAYLOAD_BYTES * 4
LOCKED_CHANNEL_POWER_METHOD = "power.locked-channel-total-signal-plus-noise-v1"


def locked_channel_total_power_dbfs(
    shifted_power_frames: tuple[tuple[int, ...], ...],
    lower_shifted_bin: int,
    upper_shifted_bin: int,
) -> float:
    """Reference model for P0PM-v4 over four PL UQ28.30 power frames."""
    if (len(shifted_power_frames) != 4 or
            not 0 <= lower_shifted_bin <= upper_shifted_bin < 4096 or
            any(len(frame) != 4096 for frame in shifted_power_frames)):
        raise ValueError("Kilitli kanal güç referans girdisi geçersiz.")
    selected = []
    for frame in shifted_power_frames:
        values = frame[lower_shifted_bin:upper_shifted_bin + 1]
        if any(type(value) is not int or not 0 <= value < 1 << 58 for value in values):
            raise ValueError("PL güç hücresi UQ28.30 sınırının dışında.")
        selected.append(sum(values))
    # C runtime divides by sample_rate * Hann power sum (1536) and then
    # integrates with sample_rate / FFT size; sample_rate cancels exactly.
    power_fs2 = (sum(selected) / 4.0) / ((1 << 30) * 1536.0 * 4096.0)
    if not power_fs2 > 0.0 or not math.isfinite(power_fs2):
        raise ValueError("Kilitli kanal toplam gücü sıfır veya sonlu değil.")
    return 10.0 * math.log10(power_fs2)


@dataclass(frozen=True)
class BoardAnalysisSpan(AnalysisSpan):
    """P0PM-v2 span; the frozen 512-bin host profile remains unchanged."""

    def __post_init__(self) -> None:
        if not 56 <= self.lower_shifted_bin <= self.upper_shifted_bin <= 4039:
            raise ValueError("Kart analiz aralığının iki yanında gürültü referansı kalmalıdır.")
        if not 8 <= self.width_bins <= MAXIMUM_BOARD_SPAN_BINS:
            raise ValueError("Kart analiz aralığı 8–3984 hücre olmalıdır.")

HEADER = struct.Struct("<4sHHIIIqQHHII")
RESPONSE_BYTES = 176
STATES = {0: "insufficient_quality", 1: "valid", 2: "insufficient_quality",
          3: "uncertain", 4: "not_observed"}
REASONS = {0: None, 1: "accumulating", 2: "event_ownership_lost",
           3: "reference_power_unavailable", 4: "reference_mismatch",
           5: "excess_power_not_significant", 6: "center_temporal_uncertainty",
           7: "span_edge_clipping", 8: "obw_temporal_instability",
           9: "carrier_line_below_threshold", 10: "quality_below_carrier_threshold"}


@dataclass(frozen=True)
class BoardMeasurement:
    result: F1ParameterResult
    response: bytes
    elapsed_us: int
    profile_generation: int


def encode_request(intent: MeasurementIntent, iq: bytes, sample_rate_hz: int,
                   center_frequency_hz: int, token: int, *,
                   locked_channel_power: bool = False) -> bytes:
    lower, upper = intent.span.lower_shifted_bin, intent.span.upper_shifted_bin
    count = len(iq) // 8192
    if (len(iq) not in (32768, 131072) or type(sample_rate_hz) is not int or not 0 < sample_rate_hz <= 20_000_000
            or type(center_frequency_hz) is not int or not -(1 << 63) <= center_frequency_hz < 1 << 63
            or not 0 < token < 1 << 32 or not 0 < intent.event_id < 1 << 64
            or not 0 <= intent.start_frame <= (1 << 32) - count
            or not 56 <= lower <= upper <= 4039 or not 8 <= upper - lower + 1 <= MAXIMUM_BOARD_SPAN_BINS):
        raise ValueError("Kart ölçüm girdisi veya frekans bağlamı geçersiz.")
    if locked_channel_power and count != 4:
        raise ValueError("Kilitli yön kanalı güç ölçümü tam dört kare gerektirir.")
    version = (4 if locked_channel_power else
               3 if count == 16 else 2 if intent.span.width_bins > 512 else 1)
    header = HEADER.pack(b"P0PM", version, 64, token, intent.start_frame, sample_rate_hz,
                         center_frequency_hz, intent.event_id, lower, upper, zlib.crc32(iq), 0)
    header = header + bytes(12)
    return header + struct.pack("<I", zlib.crc32(header)) + iq


def decode_response(payload: bytes, intent: MeasurementIntent, iq: bytes, token: int, *,
                    locked_channel_power: bool = False) -> BoardMeasurement:
    count = len(iq) // 8192
    if len(iq) not in (32768, 131072):
        raise ValueError("Kart ölçümü 4 veya 16 özgün I/Q karesi gerektirir.")
    if len(payload) != RESPONSE_BYTES:
        raise ValueError("Kart parametre yanıtının uzunluğu geçersiz.")
    magic, version, length, actual_token, status = struct.unpack_from("<4sHHII", payload)
    if ((magic, length, actual_token) != (b"P0PR", RESPONSE_BYTES, token)
            or version not in (1, 2, 3, 4) or ((count == 16) != (version == 3))
            or ((version == 4) != locked_channel_power)
            or (intent.span.width_bins > 512 and version < 2)
            or struct.unpack_from("<I", payload, 172)[0] != zlib.crc32(payload[:172])):
        raise ValueError("Kart parametre yanıtı doğrulanamadı.")
    errors = {1: "Parametre ölçümü için FPGA FFT boyutu 4096 olmalıdır.",
              2: "Kart ölçümü durduruldu.", 3: "Kart ölçüm girdisini reddetti.",
              4: "Parametre ölçümünde FPGA veya DMA işlemi başarısız.",
              5: "Kart parametre hesabı veya profil doğrulaması başarısız."}
    if status:
        if status not in errors or any(payload[16:172]):
            raise ValueError("Kart parametre hata yanıtı geçersiz.")
        raise RuntimeError(errors[status])
    intent_id, event_id, frame_id, actual_count = struct.unpack_from("<QQIB", payload, 16)
    elapsed, iq_crc, generation, fft_size = struct.unpack_from("<IIII", payload, 156)
    if ((intent_id, event_id, frame_id, actual_count) !=
            (token, intent.event_id, intent.start_frame + count - 1, count)
            or any(payload[37:40]) or iq_crc != zlib.crc32(iq) or fft_size != 4096):
        raise ValueError("Kart sonucu seçilen I/Q kareleriyle eşleşmiyor.")

    def field(offset: int, unit: str, carrier: bool = False) -> FieldMeasurement:
        state, reason, reserved, value = struct.unpack_from("<BBHd", payload, offset)
        if (state not in STATES or reason not in REASONS or reserved or not math.isfinite(value)
                or (state == 1 and reason != 0) or (not carrier and (state > 3 or reason > 8))):
            raise ValueError("Kart ölçüm alanı geçersiz.")
        return FieldMeasurement(STATES[state], value if state == 1 else None, unit, REASONS[reason])

    center, lower, upper, bandwidth, power, snr = (
        field(offset, unit) for offset, unit in zip(range(40, 112, 12), ("Hz", "Hz", "Hz", "Hz", "dBFS", "dB")))
    carrier = field(144, "Hz", True)
    quality = struct.unpack_from("<dddd", payload, 112)
    if not all(math.isfinite(value) for value in quality):
        raise ValueError("Kart kalite göstergeleri geçersiz.")
    invalid = [item for item in (center, lower, upper, bandwidth, power, snr) if item.state != "valid"]
    state = invalid[0].state if invalid else "valid"
    reasons = tuple(dict.fromkeys(item.reason for item in invalid if item.reason))
    result = F1ParameterResult(intent, center, carrier, lower, upper, bandwidth, power, snr,
        FieldMeasurement("not_applicable", reason="classification_deferred"),
        F1Quality(state, reasons, count, *quality),
        EXTENDED_BOARD_PAYLOAD_BYTES if version == 3 else BOARD_PERSISTENT_PAYLOAD_BYTES if version in (2, 4) else 56064)
    return BoardMeasurement(result, payload, elapsed, generation)


def measure_on_board(host: str, port: int, intent: MeasurementIntent, iq: bytes, *,
                     sample_rate_hz: int, center_frequency_hz: int,
                     locked_channel_power: bool = False) -> BoardMeasurement:
    token = secrets.randbelow((1 << 32) - 1) + 1
    request = encode_request(intent, iq, sample_rate_hz, center_frequency_hz, token,
                             locked_channel_power=locked_channel_power)
    response = bytearray()
    try:
        with socket.create_connection((host, port), timeout=5.0) as connection:
            connection.settimeout(30.0)
            connection.sendall(request)
            while len(response) < RESPONSE_BYTES:
                chunk = connection.recv(RESPONSE_BYTES - len(response))
                if not chunk:
                    required = "yön kanalı için P0PM-v4" if locked_channel_power else "16 kare için P0PM-v3"
                    raise RuntimeError(f"Kart ölçüm bağlantısı kapandı. Kart hizmeti ve ağ köprüsü istenen ölçüm sürümünü birlikte desteklemelidir ({required}).")
                response.extend(chunk)
    except OSError as exc:
        raise RuntimeError("Kart parametre ölçümüne yanıt vermedi.") from exc
    return decode_response(bytes(response), intent, iq, token,
                           locked_channel_power=locked_channel_power)
