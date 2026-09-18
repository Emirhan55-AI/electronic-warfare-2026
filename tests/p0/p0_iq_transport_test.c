#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "p0_iq_transport.h"

#define REQUIRE(condition) do { if (!(condition)) return __LINE__; } while (0)

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

static void store_le64(uint8_t *data, uint64_t value)
{
    store_le32(data, (uint32_t)value);
    store_le32(data + 4U, (uint32_t)(value >> 32U));
}

static uint32_t load_le32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8U) |
           ((uint32_t)data[2] << 16U) | ((uint32_t)data[3] << 24U);
}

int main(void)
{
    static uint8_t packet[P0_IQ_PARAMETER_HEADER_BYTES + P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES];
    static uint8_t response[P0_IQ_RESPONSE_HEADER_BYTES + 128U];
    uint8_t capability[P0_IQ_CAPABILITY_BYTES];
    uint8_t result[128U];
    p0_iq_frame_view_t frame;
    size_t response_bytes = 0U;
    size_t index;

    REQUIRE(p0_iq_crc32((const uint8_t *)"123456789", 9U) == UINT32_C(0xcbf43926));

    memset(packet, 0, sizeof(packet));
    memcpy(packet, "P0IQ", 4U);
    packet[4] = P0_IQ_TRANSPORT_VERSION;
    packet[5] = P0_IQ_SAMPLE_FORMAT_CI8;
    store_le16(packet + 6U, P0_IQ_HEADER_BYTES);
    store_le32(packet + 8U, 17U);
    store_le32(packet + 12U, 23U);
    store_le16(packet + 16U, 0U);
    store_le16(packet + 18U, 1U);
    store_le64(packet + 20U, UINT64_C(101500000));
    store_le32(packet + 28U, P0_IQ_PROCESSING_SAMPLE_RATE_HZ);
    store_le32(packet + 32U, P0_IQ_PROCESSING_COMPLEX_SAMPLES);
    store_le32(packet + 36U, P0_IQ_PROCESSING_PAYLOAD_BYTES);
    for (index = 0U; index < P0_IQ_PROCESSING_PAYLOAD_BYTES; ++index)
        packet[P0_IQ_HEADER_BYTES + index] = (uint8_t)(index * 17U + 3U);
    store_le32(packet + 40U,
               p0_iq_crc32(packet + P0_IQ_HEADER_BYTES,
                           P0_IQ_PROCESSING_PAYLOAD_BYTES));
    store_le32(packet + 44U, p0_iq_crc32(packet, P0_IQ_HEADER_PREFIX_BYTES));

    REQUIRE(p0_iq_processing_frame_decode(
                packet, P0_IQ_HEADER_BYTES + P0_IQ_PROCESSING_PAYLOAD_BYTES,
                &frame) == 0);
    REQUIRE(frame.sequence_number == 17U && frame.frame_id == 23U);
    REQUIRE(frame.center_frequency_hz == UINT64_C(101500000));
    REQUIRE(frame.payload_bytes == P0_IQ_PROCESSING_PAYLOAD_BYTES);

    store_le32(packet + 28U, P0_IQ_WIDEBAND_SAMPLE_RATE_HZ);
    store_le32(packet + 44U, p0_iq_crc32(packet, P0_IQ_HEADER_PREFIX_BYTES));
    REQUIRE(p0_iq_processing_frame_decode(
                packet, P0_IQ_HEADER_BYTES + P0_IQ_PROCESSING_PAYLOAD_BYTES,
                &frame) == 0);
    REQUIRE(frame.sample_rate_hz == P0_IQ_WIDEBAND_SAMPLE_RATE_HZ);
    store_le32(packet + 28U, P0_IQ_PROCESSING_SAMPLE_RATE_HZ);
    store_le32(packet + 44U, p0_iq_crc32(packet, P0_IQ_HEADER_PREFIX_BYTES));

    packet[12] ^= 1U;
    REQUIRE(p0_iq_processing_frame_decode(
                packet, P0_IQ_HEADER_BYTES + P0_IQ_PROCESSING_PAYLOAD_BYTES,
                &frame) != 0);
    packet[12] ^= 1U;
    packet[P0_IQ_HEADER_BYTES + 99U] ^= 1U;
    REQUIRE(p0_iq_processing_frame_decode(
                packet, P0_IQ_HEADER_BYTES + P0_IQ_PROCESSING_PAYLOAD_BYTES,
                &frame) != 0);
    packet[P0_IQ_HEADER_BYTES + 99U] ^= 1U;
    for (index = 0U; index < P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES; ++index)
        packet[P0_IQ_HEADER_BYTES + index] = (uint8_t)(index * 19U + 7U);
    store_le32(packet + 32U, P0_IQ_PROCESSING_MAX_COMPLEX_SAMPLES);
    store_le32(packet + 36U, P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES);
    store_le32(packet + 40U, p0_iq_crc32(
        packet + P0_IQ_HEADER_BYTES, P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES));
    store_le32(packet + 44U, p0_iq_crc32(packet, P0_IQ_HEADER_PREFIX_BYTES));
    REQUIRE(p0_iq_processing_frame_decode(
                packet,
                P0_IQ_HEADER_BYTES + P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES,
                &frame) == 0);
    REQUIRE(frame.complex_sample_count == P0_IQ_PROCESSING_MAX_COMPLEX_SAMPLES);

    memset(packet, 0, sizeof(packet));
    memcpy(packet, "P0IQ", 4U);
    packet[4] = P0_IQ_TRANSPORT_VERSION;
    packet[5] = P0_IQ_SAMPLE_FORMAT_CI8;
    store_le16(packet + 6U, P0_IQ_PARAMETER_HEADER_BYTES);
    store_le32(packet + 8U, 18U);
    store_le32(packet + 12U, 24U);
    store_le16(packet + 18U, 1U);
    store_le64(packet + 20U, UINT64_C(820000000));
    store_le32(packet + 28U, P0_IQ_PROCESSING_SAMPLE_RATE_HZ);
    store_le32(packet + 32U, P0_IQ_PROCESSING_COMPLEX_SAMPLES);
    store_le32(packet + 36U, P0_IQ_PROCESSING_PAYLOAD_BYTES);
    for (index = 0U; index < P0_IQ_PROCESSING_PAYLOAD_BYTES; ++index)
        packet[P0_IQ_PARAMETER_HEADER_BYTES + index] =
            (uint8_t)(index * 13U + 5U);
    store_le32(packet + 40U,
               p0_iq_crc32(packet + P0_IQ_PARAMETER_HEADER_BYTES,
                           P0_IQ_PROCESSING_PAYLOAD_BYTES));
    store_le32(packet + 44U, P0_IQ_PARAMETER_FLAGS_ALLOWED);
    store_le64(packet + 52U, UINT64_C(91));
    store_le64(packet + 60U, UINT64_C(77));
    store_le16(packet + 68U, 1000U);
    store_le16(packet + 70U, 1100U);
    store_le32(packet + 76U,
               p0_iq_crc32(packet, P0_IQ_PARAMETER_HEADER_PREFIX_BYTES));
    REQUIRE(p0_iq_processing_frame_decode(
                packet,
                P0_IQ_PARAMETER_HEADER_BYTES + P0_IQ_PROCESSING_PAYLOAD_BYTES,
                &frame) == 0);
    REQUIRE(frame.parameter_flags == P0_IQ_PARAMETER_FLAGS_ALLOWED);
    REQUIRE(frame.parameter_intent_id == UINT64_C(91));
    REQUIRE(frame.parameter_event_id == UINT64_C(77));
    REQUIRE(frame.parameter_lower_shifted_bin == 1000U &&
            frame.parameter_upper_shifted_bin == 1100U);

    memset(capability, 0, sizeof(capability));
    memcpy(capability, "P0CQ", 4U);
    capability[4] = P0_IQ_TRANSPORT_VERSION;
    capability[5] = 1U;
    store_le16(capability + 6U, P0_IQ_CAPABILITY_BYTES);
    store_le32(capability + 44U,
               p0_iq_crc32(capability, P0_IQ_CAPABILITY_PREFIX_BYTES));
    REQUIRE(p0_iq_capability_query_check(capability) == 0);
    REQUIRE(p0_iq_capability_response_encode(capability) == 0);
    REQUIRE(memcmp(capability, "P0CR", 4U) == 0);
    REQUIRE(load_le32(capability + 8U) ==
            (P0_IQ_CAPABILITY_INLINE_PARAMETER |
             P0_IQ_CAPABILITY_WIDEBAND_BURST | P0_IQ_CAPABILITY_EXTENDED_PARAMETER));
    REQUIRE(load_le32(capability + 12U) ==
            P0_IQ_CAPABILITY_MAXIMUM_PARAMETER_SPAN);
    REQUIRE(load_le32(capability + 16U) ==
            P0_IQ_CAPABILITY_PARAMETER_CONTEXTS);

    for (index = 0U; index < sizeof(result); ++index)
        result[index] = (uint8_t)index;
    REQUIRE(p0_iq_response_encode(17U, result, sizeof(result), response,
                                  sizeof(response), &response_bytes) == 0);
    REQUIRE(response_bytes == sizeof(response));
    REQUIRE(memcmp(response, "P0RS", 4U) == 0);
    REQUIRE(p0_iq_crc32(response, P0_IQ_RESPONSE_HEADER_PREFIX_BYTES) ==
            load_le32(response + 20U));

    puts("P0_IQ_TRANSPORT_TEST=PASS");
    return 0;
}
