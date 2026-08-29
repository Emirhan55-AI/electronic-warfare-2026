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
    uint32_t payload_bytes;

    if (packet == NULL || frame == NULL || packet_bytes < P0_IQ_HEADER_BYTES ||
        memcmp(packet, "P0IQ", 4U) != 0 ||
        packet[4] != P0_IQ_TRANSPORT_VERSION ||
        packet[5] != P0_IQ_SAMPLE_FORMAT_CI8 ||
        load_le16(packet + 6U) != P0_IQ_HEADER_BYTES ||
        load_le32(packet + 44U) != p0_iq_crc32(packet, P0_IQ_HEADER_PREFIX_BYTES))
        return -1;
    payload_bytes = load_le32(packet + 36U);
    if (payload_bytes == 0U || payload_bytes > P0_IQ_MAX_PAYLOAD_BYTES ||
        (payload_bytes & 1U) != 0U ||
        packet_bytes != P0_IQ_HEADER_BYTES + (size_t)payload_bytes ||
        load_le32(packet + 32U) * 2U != payload_bytes ||
        load_le64(packet + 20U) == 0U || load_le32(packet + 28U) == 0U ||
        load_le16(packet + 18U) == 0U ||
        load_le16(packet + 16U) >= load_le16(packet + 18U) ||
        load_le32(packet + 40U) !=
            p0_iq_crc32(packet + P0_IQ_HEADER_BYTES, payload_bytes))
        return -1;
    memset(frame, 0, sizeof(*frame));
    frame->sequence_number = load_le32(packet + 8U);
    frame->frame_id = load_le32(packet + 12U);
    frame->chunk_index = load_le16(packet + 16U);
    frame->chunk_count = load_le16(packet + 18U);
    frame->center_frequency_hz = load_le64(packet + 20U);
    frame->sample_rate_hz = load_le32(packet + 28U);
    frame->complex_sample_count = load_le32(packet + 32U);
    frame->payload = packet + P0_IQ_HEADER_BYTES;
    frame->payload_bytes = payload_bytes;
    return 0;
}

int p0_iq_processing_frame_decode(const uint8_t *packet, size_t packet_bytes,
                                  p0_iq_frame_view_t *frame)
{
    if (p0_iq_frame_decode(packet, packet_bytes, frame) != 0)
        return -1;
    return frame->chunk_index == 0U && frame->chunk_count == 1U &&
                   frame->sample_rate_hz == P0_IQ_PROCESSING_SAMPLE_RATE_HZ &&
                   frame->complex_sample_count == P0_IQ_PROCESSING_COMPLEX_SAMPLES &&
                   frame->payload_bytes == P0_IQ_PROCESSING_PAYLOAD_BYTES
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
