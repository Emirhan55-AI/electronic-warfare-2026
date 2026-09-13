#ifndef P0_IQ_TRANSPORT_H
#define P0_IQ_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#define P0_IQ_TRANSPORT_VERSION 2U
#define P0_IQ_SAMPLE_FORMAT_CI8 1U
#define P0_IQ_HEADER_BYTES 48U
#define P0_IQ_HEADER_PREFIX_BYTES 44U
#define P0_IQ_PARAMETER_HEADER_BYTES 80U
#define P0_IQ_PARAMETER_HEADER_PREFIX_BYTES 76U
#define P0_IQ_PARAMETER_FLAG_REQUEST 0x00000001U
#define P0_IQ_PARAMETER_FLAG_START 0x00000002U
#define P0_IQ_PARAMETER_FLAGS_ALLOWED \
    (P0_IQ_PARAMETER_FLAG_REQUEST | P0_IQ_PARAMETER_FLAG_START)
#define P0_IQ_MAX_PAYLOAD_BYTES 131072U
#define P0_IQ_PROCESSING_SAMPLE_RATE_HZ 2000000U
#define P0_IQ_PROCESSING_COMPLEX_SAMPLES 4096U
#define P0_IQ_PROCESSING_PAYLOAD_BYTES 8192U
#define P0_IQ_PROCESSING_MAX_COMPLEX_SAMPLES 16384U
#define P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES 32768U

#define P0_IQ_RESPONSE_HEADER_BYTES 24U
#define P0_IQ_RESPONSE_HEADER_PREFIX_BYTES 20U
#define P0_IQ_MAX_RESPONSE_BYTES 16384U

#define P0_IQ_CAPABILITY_BYTES 48U
#define P0_IQ_CAPABILITY_PREFIX_BYTES 44U
#define P0_IQ_CAPABILITY_INLINE_PARAMETER 0x00000001U
#define P0_IQ_CAPABILITY_MAXIMUM_PARAMETER_SPAN 512U
#define P0_IQ_CAPABILITY_PARAMETER_CONTEXTS 1U

typedef struct {
    uint32_t sequence_number;
    uint32_t frame_id;
    uint16_t chunk_index;
    uint16_t chunk_count;
    uint64_t center_frequency_hz;
    uint32_t sample_rate_hz;
    uint32_t complex_sample_count;
    const uint8_t *payload;
    uint32_t payload_bytes;
    uint32_t parameter_flags;
    uint64_t parameter_intent_id;
    uint64_t parameter_event_id;
    uint16_t parameter_lower_shifted_bin;
    uint16_t parameter_upper_shifted_bin;
} p0_iq_frame_view_t;

uint32_t p0_iq_crc32(const uint8_t *data, size_t length);
int p0_iq_frame_decode(const uint8_t *packet, size_t packet_bytes,
                       p0_iq_frame_view_t *frame);
int p0_iq_processing_frame_decode(const uint8_t *packet, size_t packet_bytes,
                                  p0_iq_frame_view_t *frame);
int p0_iq_response_encode(uint32_t sequence_number, const uint8_t *payload,
                          size_t payload_bytes, uint8_t *packet,
                          size_t capacity, size_t *packet_bytes);
int p0_iq_capability_query_check(
    const uint8_t packet[P0_IQ_CAPABILITY_BYTES]);
int p0_iq_capability_response_encode(
    uint8_t packet[P0_IQ_CAPABILITY_BYTES]);

#endif
