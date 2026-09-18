#include "p0_iq_transport.h"

#include <string.h>

#ifdef P0_IQ_USE_SERVICE_CRC32
#include "p0_ed_service_protocol.h"
#endif

static uint16_t load_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | (uint16_t)((uint16_t)data[1] << 8U);
}

static uint32_t load_le32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8U) |
           ((uint32_t)data[2] << 16U) | ((uint32_t)data[3] << 24U);
}

static uint64_t load_le64(const uint8_t *data)
{
    return (uint64_t)load_le32(data) | ((uint64_t)load_le32(data + 4U) << 32U);
}

static void store_le16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8U);
}

static void store_le32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8U);
    data[2] = (uint8_t)(value >> 16U);
    data[3] = (uint8_t)(value >> 24U);
}

uint32_t p0_iq_crc32(const uint8_t *data, size_t length)
{
#ifdef P0_IQ_USE_SERVICE_CRC32
    return p0_ed_crc32(data, length);
#else
    static const uint32_t table[16] = {
        UINT32_C(0x00000000), UINT32_C(0x1db71064),
        UINT32_C(0x3b6e20c8), UINT32_C(0x26d930ac),
        UINT32_C(0x76dc4190), UINT32_C(0x6b6b51f4),
        UINT32_C(0x4db26158), UINT32_C(0x5005713c),
        UINT32_C(0xedb88320), UINT32_C(0xf00f9344),
        UINT32_C(0xd6d6a3e8), UINT32_C(0xcb61b38c),
        UINT32_C(0x9b64c2b0), UINT32_C(0x86d3d2d4),
        UINT32_C(0xa00ae278), UINT32_C(0xbdbdf21c),
    };
    uint32_t crc = UINT32_C(0xffffffff);
    size_t index;

    if (data == NULL && length != 0U)
        return 0U;
    for (index = 0U; index < length; ++index) {
        crc ^= data[index];
        crc = (crc >> 4U) ^ table[crc & 0x0fU];
        crc = (crc >> 4U) ^ table[crc & 0x0fU];
    }
    return ~crc;
#endif
}

int p0_iq_frame_decode(const uint8_t *packet, size_t packet_bytes,
                       p0_iq_frame_view_t *frame)
{
    uint16_t header_bytes;
    uint32_t payload_bytes;

    if (packet == NULL || frame == NULL || packet_bytes < P0_IQ_HEADER_BYTES ||
        memcmp(packet, "P0IQ", 4U) != 0 ||
        packet[4] != P0_IQ_TRANSPORT_VERSION ||
        packet[5] != P0_IQ_SAMPLE_FORMAT_CI8)
        return -1;
    header_bytes = load_le16(packet + 6U);
    if ((header_bytes != P0_IQ_HEADER_BYTES &&
         header_bytes != P0_IQ_PARAMETER_HEADER_BYTES) ||
        packet_bytes < header_bytes ||
        load_le32(packet + header_bytes - 4U) !=
            p0_iq_crc32(packet, header_bytes - 4U))
        return -1;
    payload_bytes = load_le32(packet + 36U);
    if (payload_bytes == 0U || payload_bytes > P0_IQ_MAX_PAYLOAD_BYTES ||
        (payload_bytes & 1U) != 0U ||
        packet_bytes != (size_t)header_bytes + (size_t)payload_bytes ||
        load_le32(packet + 32U) * 2U != payload_bytes ||
        load_le64(packet + 20U) == 0U || load_le32(packet + 28U) == 0U ||
        load_le16(packet + 18U) == 0U ||
        load_le16(packet + 16U) >= load_le16(packet + 18U) ||
        load_le32(packet + 40U) !=
            p0_iq_crc32(packet + header_bytes, payload_bytes))
        return -1;
    memset(frame, 0, sizeof(*frame));
    frame->sequence_number = load_le32(packet + 8U);
    frame->frame_id = load_le32(packet + 12U);
    frame->chunk_index = load_le16(packet + 16U);
    frame->chunk_count = load_le16(packet + 18U);
    frame->center_frequency_hz = load_le64(packet + 20U);
    frame->sample_rate_hz = load_le32(packet + 28U);
    frame->complex_sample_count = load_le32(packet + 32U);
    if (header_bytes == P0_IQ_PARAMETER_HEADER_BYTES) {
        uint32_t flags = load_le32(packet + 44U);
        uint16_t lower = load_le16(packet + 68U);
        uint16_t upper = load_le16(packet + 70U);
        unsigned int width = (unsigned int)upper - lower + 1U;

        if ((flags & ~P0_IQ_PARAMETER_FLAGS_ALLOWED) != 0U ||
            (flags & P0_IQ_PARAMETER_FLAG_REQUEST) == 0U ||
            load_le32(packet + 48U) != 0U ||
            load_le64(packet + 52U) == 0U ||
            load_le64(packet + 60U) == 0U || lower > upper ||
            lower < 56U || upper > 4039U || width < 8U || width > 512U ||
            load_le32(packet + 72U) != 0U)
            return -1;
        frame->parameter_flags = flags;
        frame->parameter_intent_id = load_le64(packet + 52U);
        frame->parameter_event_id = load_le64(packet + 60U);
        frame->parameter_lower_shifted_bin = lower;
        frame->parameter_upper_shifted_bin = upper;
    }
    frame->payload = packet + header_bytes;
    frame->payload_bytes = payload_bytes;
    return 0;
}

int p0_iq_processing_frame_decode(const uint8_t *packet, size_t packet_bytes,
                                  p0_iq_frame_view_t *frame)
{
    if (p0_iq_frame_decode(packet, packet_bytes, frame) != 0)
        return -1;
    return frame->chunk_index == 0U && frame->chunk_count == 1U &&
                   (frame->sample_rate_hz == P0_IQ_PROCESSING_SAMPLE_RATE_HZ ||
                    frame->sample_rate_hz == P0_IQ_WIDEBAND_SAMPLE_RATE_HZ) &&
                   (frame->complex_sample_count == 4096U ||
                    frame->complex_sample_count == 8192U ||
                    frame->complex_sample_count == 16384U) &&
                   frame->payload_bytes == frame->complex_sample_count * 2U &&
                   (frame->parameter_flags == 0U ||
                    (frame->sample_rate_hz == P0_IQ_PROCESSING_SAMPLE_RATE_HZ &&
                     frame->complex_sample_count ==
                         P0_IQ_PROCESSING_COMPLEX_SAMPLES))
               ? 0 : -1;
}

int p0_iq_response_encode(uint32_t sequence_number, const uint8_t *payload,
                          size_t payload_bytes, uint8_t *packet,
                          size_t capacity, size_t *packet_bytes)
{
    size_t total = P0_IQ_RESPONSE_HEADER_BYTES + payload_bytes;

    if (payload == NULL || packet == NULL || packet_bytes == NULL ||
        payload_bytes == 0U || payload_bytes > P0_IQ_MAX_RESPONSE_BYTES ||
        capacity < total)
        return -1;
    memset(packet, 0, P0_IQ_RESPONSE_HEADER_BYTES);
    memcpy(packet, "P0RS", 4U);
    packet[4] = P0_IQ_TRANSPORT_VERSION;
    packet[5] = 1U;
    store_le16(packet + 6U, P0_IQ_RESPONSE_HEADER_BYTES);
    store_le32(packet + 8U, sequence_number);
    store_le32(packet + 12U, (uint32_t)payload_bytes);
    store_le32(packet + 16U, p0_iq_crc32(payload, payload_bytes));
    store_le32(packet + 20U,
               p0_iq_crc32(packet, P0_IQ_RESPONSE_HEADER_PREFIX_BYTES));
    memcpy(packet + P0_IQ_RESPONSE_HEADER_BYTES, payload, payload_bytes);
    *packet_bytes = total;
    return 0;
}

static int capability_common_valid(const uint8_t *packet, const char magic[4],
                                   uint8_t message_type)
{
    return packet != NULL && memcmp(packet, magic, 4U) == 0 &&
           packet[4] == P0_IQ_TRANSPORT_VERSION &&
           packet[5] == message_type &&
           load_le16(packet + 6U) == P0_IQ_CAPABILITY_BYTES &&
           load_le32(packet + 44U) ==
               p0_iq_crc32(packet, P0_IQ_CAPABILITY_PREFIX_BYTES);
}

int p0_iq_capability_query_check(
    const uint8_t packet[P0_IQ_CAPABILITY_BYTES])
{
    size_t index;

    if (!capability_common_valid(packet, "P0CQ", 1U))
        return -1;
    for (index = 8U; index < P0_IQ_CAPABILITY_PREFIX_BYTES; ++index) {
        if (packet[index] != 0U)
            return -1;
    }
    return 0;
}

int p0_iq_capability_response_encode(
    uint8_t packet[P0_IQ_CAPABILITY_BYTES])
{
    if (packet == NULL)
        return -1;
    memset(packet, 0, P0_IQ_CAPABILITY_BYTES);
    memcpy(packet, "P0CR", 4U);
    packet[4] = P0_IQ_TRANSPORT_VERSION;
    packet[5] = 2U;
    store_le16(packet + 6U, P0_IQ_CAPABILITY_BYTES);
    store_le32(packet + 8U, P0_IQ_CAPABILITY_INLINE_PARAMETER |
                              P0_IQ_CAPABILITY_WIDEBAND_BURST | P0_IQ_CAPABILITY_EXTENDED_PARAMETER |
                              P0_IQ_CAPABILITY_CARRIER_RECOVERY);
    store_le32(packet + 12U, P0_IQ_CAPABILITY_MAXIMUM_PARAMETER_SPAN);
    store_le32(packet + 16U, P0_IQ_CAPABILITY_PARAMETER_CONTEXTS);
    store_le32(packet + 44U,
               p0_iq_crc32(packet, P0_IQ_CAPABILITY_PREFIX_BYTES));
    return 0;
}
