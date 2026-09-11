#ifndef P0_ED_SERVICE_PROTOCOL_H
#define P0_ED_SERVICE_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#include "p0_amplitude_df.h"
#include "p0_parameter_runtime.h"
#include "phase06j_temporal.h"

#define P0_ED_SERVICE_ABI_VERSION_V1 1U
#define P0_ED_SERVICE_ABI_VERSION_V2 2U
#define P0_ED_SERVICE_ABI_VERSION_V3 3U
#define P0_ED_SERVICE_ABI_VERSION_V4 4U
#define P0_ED_SERVICE_ABI_VERSION P0_ED_SERVICE_ABI_VERSION_V1
#define P0_ED_REQUEST_MAGIC UINT32_C(0x31514550)
#define P0_ED_RESPONSE_MAGIC UINT32_C(0x31534550)
#define P0_ED_REQUEST_HEADER_BYTES_V1 32U
#define P0_ED_REQUEST_HEADER_BYTES_V2 80U
#define P0_ED_REQUEST_HEADER_BYTES_V3 32U
#define P0_ED_REQUEST_HEADER_BYTES_V4 32U
#define P0_ED_RESPONSE_HEADER_BYTES_V1 48U
#define P0_ED_RESPONSE_HEADER_BYTES_V2 64U
#define P0_ED_RESPONSE_HEADER_BYTES_V3 48U
#define P0_ED_REQUEST_HEADER_BYTES P0_ED_REQUEST_HEADER_BYTES_V1
#define P0_ED_RESPONSE_HEADER_BYTES P0_ED_RESPONSE_HEADER_BYTES_V1
#define P0_ED_IQ_FRAME_BYTES 8192U
#define P0_ED_MAX_IQ_FRAME_BYTES 32768U
#define P0_ED_RESULT_HEADER_BYTES 20U
#define P0_ED_EVENT_BYTES 68U
#define P0_ED_RESULT_BYTES 8724U
#define P0_ED_PARAMETER_RESULT_BYTES 128U
#define P0_ED_REQUEST_BYTES_V1 (P0_ED_REQUEST_HEADER_BYTES_V1 + P0_ED_IQ_FRAME_BYTES)
#define P0_ED_REQUEST_BYTES_V2 (P0_ED_REQUEST_HEADER_BYTES_V2 + P0_ED_IQ_FRAME_BYTES)
#define P0_ED_REQUEST_BYTES_V3 (P0_ED_REQUEST_HEADER_BYTES_V3 + P0_ED_IQ_FRAME_BYTES)
#define P0_ED_REQUEST_MAX_BYTES_V4 \
    (P0_ED_REQUEST_HEADER_BYTES_V4 + P0_ED_MAX_IQ_FRAME_BYTES)
#define P0_ED_RESPONSE_BYTES_V1 (P0_ED_RESPONSE_HEADER_BYTES_V1 + P0_ED_RESULT_BYTES)
#define P0_ED_RESPONSE_BYTES_V2 \
    (P0_ED_RESPONSE_HEADER_BYTES_V2 + P0_ED_RESULT_BYTES + P0_ED_PARAMETER_RESULT_BYTES)
#define P0_ED_RESPONSE_BYTES_V3 (P0_ED_RESPONSE_HEADER_BYTES_V3 + P0_ED_RESULT_BYTES)
#define P0_ED_REQUEST_BYTES P0_ED_REQUEST_BYTES_V1
#define P0_ED_RESPONSE_BYTES P0_ED_RESPONSE_BYTES_V2
#define P0_ED_REQUEST_FLAG_RESET 0x00000001U
#define P0_ED_REQUEST_FLAG_PARAMETER 0x00000002U
#define P0_ED_REQUEST_FLAG_PARAMETER_START 0x00000004U
#define P0_ED_REQUEST_FLAGS_V1_ALLOWED P0_ED_REQUEST_FLAG_RESET
#define P0_ED_REQUEST_FLAGS_V3_ALLOWED P0_ED_REQUEST_FLAG_RESET
#define P0_ED_REQUEST_FLAGS_V4_ALLOWED P0_ED_REQUEST_FLAG_RESET
#define P0_ED_REQUEST_FLAGS_V2_ALLOWED \
    (P0_ED_REQUEST_FLAG_RESET | P0_ED_REQUEST_FLAG_PARAMETER | \
     P0_ED_REQUEST_FLAG_PARAMETER_START)
#define P0_ED_REQUEST_FLAGS_ALLOWED P0_ED_REQUEST_FLAGS_V1_ALLOWED

#define P0_DETECTION_MESSAGE_BYTES 48U
/* Explicit replay of four operator-selected CI8 frames through PL + ARM.
 * This operation does not assert a new live detection or classify modulation. */
#define P0_PARAMETER_BATCH_HEADER_BYTES 64U
#define P0_PARAMETER_BATCH_REQUEST_BYTES (64U + 32768U)
#define P0_PARAMETER_BATCH_RESPONSE_BYTES 176U
typedef struct {
    uint32_t token, first_frame_id, sample_rate_hz;
    int64_t center_frequency_hz;
    uint64_t event_id;
    uint16_t lower_bin, upper_bin;
    uint32_t iq_crc32;
    const uint8_t *iq;
} p0_parameter_batch_request_t;
int p0_parameter_batch_decode(const uint8_t *, size_t, p0_parameter_batch_request_t *);
int p0_parameter_batch_response_encode(const p0_parameter_batch_request_t *, uint32_t,
    uint32_t, uint32_t, const p0_parameter_result_t *, uint8_t *);
int p0_parameter_batch_response_check(const uint8_t *, size_t, uint32_t);

/* Fixed-size amplitude-DF batch. Channel powers must already be bound to one
 * PL/ARM parameter measurement configuration; the PC only transports rows. */
#define P0_DF_BATCH_HEADER_BYTES 32U
#define P0_DF_BATCH_MEASUREMENT_BYTES 64U
#define P0_DF_BATCH_REQUEST_BYTES \
    (P0_DF_BATCH_HEADER_BYTES + P0_DF_MAX_MEASUREMENTS * P0_DF_BATCH_MEASUREMENT_BYTES)
#define P0_DF_BATCH_RESPONSE_BYTES 104U
#define P0_DF_BATCH_OK 0U
#define P0_DF_BATCH_INVALID 1U
#define P0_DF_BATCH_COMPUTATION_FAILED 2U
typedef struct {
    uint32_t token;
    uint32_t measurement_count;
    p0_df_measurement_t measurements[P0_DF_MAX_MEASUREMENTS];
} p0_df_batch_request_t;
int p0_df_batch_decode(const uint8_t *, size_t, p0_df_batch_request_t *);
int p0_df_batch_response_encode(const p0_df_batch_request_t *, uint32_t,
                                const p0_df_result_t *, uint8_t *);
int p0_df_batch_response_check(const uint8_t *, size_t, uint32_t);
#define P0_DETECTION_GET 1U
#define P0_DETECTION_SET 2U
#define P0_DETECTION_OK 0U
#define P0_DETECTION_UNSUPPORTED 1U
#define P0_DETECTION_BUSY 2U
#define P0_DETECTION_INVALID 3U
#define P0_DETECTION_STALE 4U
#define P0_DETECTION_INTERNAL 5U
typedef struct {
    uint32_t protocol_version, operation, request_id, status, generation;
    uint64_t alpha_q32, weak_alpha_q32;
    uint32_t fft_size;
} p0_detection_message_t;
int p0_detection_message_decode(const uint8_t *bytes, size_t size, int response,
                                 p0_detection_message_t *message);
int p0_detection_message_encode(const p0_detection_message_t *message, int response,
                                 uint8_t bytes[P0_DETECTION_MESSAGE_BYTES]);

_Static_assert(sizeof(phase06j_frame_result_v1) == P0_ED_RESULT_BYTES,
               "P0 ED result wire size drift");

enum p0_ed_service_status {
    P0_ED_SERVICE_OK = 0,
    P0_ED_SERVICE_INVALID_REQUEST = 1,
    P0_ED_SERVICE_DMA_FAILURE = 2,
    P0_ED_SERVICE_PIPELINE_FAILURE = 3,
    P0_ED_SERVICE_INTERNAL_FAILURE = 4
};

typedef struct {
    uint16_t abi_version;
    uint32_t frame_id;
    uint32_t flags;
    uint64_t sample_rate_hz;
    int64_t center_frequency_hz;
    uint64_t parameter_intent_id;
    uint64_t parameter_event_id;
    uint16_t parameter_lower_shifted_bin;
    uint16_t parameter_upper_shifted_bin;
    uint32_t iq_bytes;
    const uint8_t *iq;
} p0_ed_request_view_t;

typedef struct {
    uint16_t abi_version;
    uint32_t frame_id;
    uint32_t status;
    uint32_t raw_candidate_count;
    uint32_t dma_status_flags;
    phase06j_frame_result_v1 result;
    uint8_t parameter_present;
    p0_parameter_result_t parameter;
} p0_ed_response_t;

uint32_t p0_ed_crc32(const uint8_t *data, size_t length);
int p0_ed_request_encode(uint32_t frame_id, uint32_t flags, const uint8_t *iq,
                         size_t iq_bytes, uint8_t *message, size_t capacity);
int p0_ed_request_encode_compact(uint32_t frame_id, uint32_t flags,
                                 const uint8_t *iq, size_t iq_bytes,
                                 uint8_t *message, size_t capacity);
int p0_ed_request_encode_runtime(uint32_t frame_id, uint32_t flags,
                                 const uint8_t *iq, size_t iq_bytes,
                                 uint8_t *message, size_t capacity);
int p0_ed_request_encode_v2(uint32_t frame_id, uint32_t flags,
                            uint64_t sample_rate_hz, int64_t center_frequency_hz,
                            uint64_t parameter_intent_id, uint64_t parameter_event_id,
                            uint16_t parameter_lower_shifted_bin,
                            uint16_t parameter_upper_shifted_bin,
                            const uint8_t *iq, size_t iq_bytes,
                            uint8_t *message, size_t capacity);
int p0_ed_request_decode(const uint8_t *message, size_t message_bytes,
                         p0_ed_request_view_t *request);
int p0_ed_response_encode(const p0_ed_response_t *response, uint8_t *message,
                          size_t capacity, size_t *message_bytes);
int p0_ed_response_decode(const uint8_t *message, size_t message_bytes,
                          p0_ed_response_t *response);

#endif
