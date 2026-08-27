#ifndef P0_ED_SERVICE_PROTOCOL_H
#define P0_ED_SERVICE_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#include "phase06j_temporal.h"

#define P0_ED_SERVICE_ABI_VERSION 1U
#define P0_ED_REQUEST_MAGIC UINT32_C(0x31514550)
#define P0_ED_RESPONSE_MAGIC UINT32_C(0x31534550)
#define P0_ED_REQUEST_HEADER_BYTES 32U
#define P0_ED_RESPONSE_HEADER_BYTES 48U
#define P0_ED_IQ_FRAME_BYTES 8192U
#define P0_ED_RESULT_BYTES 8724U
#define P0_ED_REQUEST_BYTES (P0_ED_REQUEST_HEADER_BYTES + P0_ED_IQ_FRAME_BYTES)
#define P0_ED_RESPONSE_BYTES (P0_ED_RESPONSE_HEADER_BYTES + P0_ED_RESULT_BYTES)
#define P0_ED_REQUEST_FLAG_RESET 0x00000001U
#define P0_ED_REQUEST_FLAGS_ALLOWED P0_ED_REQUEST_FLAG_RESET

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
    uint32_t frame_id;
    uint32_t flags;
    const uint8_t *iq;
} p0_ed_request_view_t;

typedef struct {
    uint32_t frame_id;
    uint32_t status;
    uint32_t raw_candidate_count;
    uint32_t dma_status_flags;
    phase06j_frame_result_v1 result;
} p0_ed_response_t;

uint32_t p0_ed_crc32(const uint8_t *data, size_t length);
int p0_ed_request_encode(uint32_t frame_id, uint32_t flags, const uint8_t *iq,
                         size_t iq_bytes, uint8_t *message, size_t capacity);
int p0_ed_request_decode(const uint8_t *message, size_t message_bytes,
                         p0_ed_request_view_t *request);
int p0_ed_response_encode(const p0_ed_response_t *response, uint8_t *message,
                          size_t capacity, size_t *message_bytes);
int p0_ed_response_decode(const uint8_t *message, size_t message_bytes,
                          p0_ed_response_t *response);

#endif
