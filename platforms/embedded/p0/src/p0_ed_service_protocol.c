#include "p0_ed_service_protocol.h"

#include <string.h>

static uint16_t load_le16(const uint8_t *source)
{
    return (uint16_t)((uint16_t)source[0] | ((uint16_t)source[1] << 8));
}

static uint32_t load_le32(const uint8_t *source)
{
    return (uint32_t)source[0] | ((uint32_t)source[1] << 8) |
           ((uint32_t)source[2] << 16) | ((uint32_t)source[3] << 24);
}

static uint64_t load_le64(const uint8_t *source)
{
    return (uint64_t)load_le32(source) | ((uint64_t)load_le32(source + 4) << 32);
}

static void store_le16(uint8_t *target, uint16_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
}

static void store_le32(uint8_t *target, uint32_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
    target[2] = (uint8_t)(value >> 16);
    target[3] = (uint8_t)(value >> 24);
}

static void store_le64(uint8_t *target, uint64_t value)
{
    store_le32(target, (uint32_t)value);
    store_le32(target + 4, (uint32_t)(value >> 32));
}

uint32_t p0_ed_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = UINT32_MAX;
    size_t index;
    unsigned int bit;

    if (data == NULL && length != 0U)
        return 0U;
    for (index = 0U; index < length; ++index) {
        crc ^= data[index];
        for (bit = 0U; bit < 8U; ++bit)
            crc = (crc >> 1) ^ (UINT32_C(0xEDB88320) & (uint32_t)-(int32_t)(crc & 1U));
    }
    return crc ^ UINT32_MAX;
}

static void encode_event(uint8_t *target, const phase06j_event_v1 *event)
{
    store_le64(target + 0U, event->event_id);
    store_le32(target + 8U, event->first_frame_id);
    store_le32(target + 12U, event->last_seen_frame_id);
    store_le64(target + 16U, event->seen_count);
    target[24U] = event->state;
    target[25U] = event->observed_this_frame;
    store_le16(target + 26U, 0U);
    store_le16(target + 28U, event->candidate.start_shifted_bin);
    store_le16(target + 30U, event->candidate.end_shifted_bin);
    store_le16(target + 32U, event->candidate.peak_shifted_bin);
    store_le16(target + 34U, event->candidate.coarse_span_bins);
    target[36U] = event->candidate.pfa_select;
    target[37U] = event->candidate.flags;
    store_le16(target + 38U, 0U);
    store_le64(target + 40U, event->candidate.peak_power_uq28_30);
    store_le64(target + 48U, event->candidate.regional_noise_uq28_30);
    store_le64(target + 56U, event->candidate.threshold_uq32_30);
    store_le32(target + 64U, 0U);
}

static int decode_event(const uint8_t *source, phase06j_event_v1 *event)
{
    memset(event, 0, sizeof(*event));
    if (load_le16(source + 26U) != 0U || load_le16(source + 38U) != 0U ||
        load_le32(source + 64U) != 0U)
        return -1;
    event->event_id = load_le64(source + 0U);
    event->first_frame_id = load_le32(source + 8U);
    event->last_seen_frame_id = load_le32(source + 12U);
    event->seen_count = load_le64(source + 16U);
    event->state = source[24U];
    event->observed_this_frame = source[25U];
    event->candidate.start_shifted_bin = load_le16(source + 28U);
    event->candidate.end_shifted_bin = load_le16(source + 30U);
    event->candidate.peak_shifted_bin = load_le16(source + 32U);
    event->candidate.coarse_span_bins = load_le16(source + 34U);
    event->candidate.pfa_select = source[36U];
    event->candidate.flags = source[37U];
    event->candidate.peak_power_uq28_30 = load_le64(source + 40U);
    event->candidate.regional_noise_uq28_30 = load_le64(source + 48U);
    event->candidate.threshold_uq32_30 = load_le64(source + 56U);
    return 0;
}

static void encode_result(uint8_t *target, const phase06j_frame_result_v1 *result)
{
    size_t index;

    memset(target, 0, P0_ED_RESULT_BYTES);
    store_le32(target + 0U, result->frame_id);
    store_le16(target + 4U, result->active_count);
    store_le16(target + 6U, result->ended_count);
    store_le16(target + 8U, result->dropped_candidates);
    target[10U] = result->reset_applied;
    store_le64(target + 12U, result->evicted_history_count);
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index)
        encode_event(target + 20U + index * 68U, &result->active[index]);
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index)
        encode_event(target + 4372U + index * 68U, &result->ended[index]);
}

static int decode_result(const uint8_t *source, phase06j_frame_result_v1 *result)
{
    size_t index;

    memset(result, 0, sizeof(*result));
    if (source[11U] != 0U)
        return -1;
    result->frame_id = load_le32(source + 0U);
    result->active_count = load_le16(source + 4U);
    result->ended_count = load_le16(source + 6U);
    result->dropped_candidates = load_le16(source + 8U);
    result->reset_applied = source[10U];
    result->evicted_history_count = load_le64(source + 12U);
    if (result->active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
        result->ended_count > PHASE06J_MAX_ACTIVE_TRACKS)
        return -1;
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index) {
        if (decode_event(source + 20U + index * 68U, &result->active[index]) != 0)
            return -1;
    }
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index) {
        if (decode_event(source + 4372U + index * 68U, &result->ended[index]) != 0)
            return -1;
    }
    return 0;
}

int p0_ed_request_encode(uint32_t frame_id, uint32_t flags, const uint8_t *iq,
                         size_t iq_bytes, uint8_t *message, size_t capacity)
{
    if (iq == NULL || message == NULL || iq_bytes != P0_ED_IQ_FRAME_BYTES ||
        capacity < P0_ED_REQUEST_BYTES || (flags & ~P0_ED_REQUEST_FLAGS_ALLOWED) != 0U)
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES);
    store_le32(message + 8U, P0_ED_REQUEST_BYTES);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, P0_ED_IQ_FRAME_BYTES);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, p0_ed_crc32(iq, iq_bytes));
    store_le32(message + 28U, p0_ed_crc32(message, 28U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES, iq, iq_bytes);
    return 0;
}

int p0_ed_request_decode(const uint8_t *message, size_t message_bytes,
                         p0_ed_request_view_t *request)
{
    uint32_t flags;

    if (message == NULL || request == NULL || message_bytes != P0_ED_REQUEST_BYTES ||
        load_le32(message + 0U) != P0_ED_REQUEST_MAGIC ||
        load_le16(message + 4U) != P0_ED_SERVICE_ABI_VERSION ||
        load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES ||
        load_le32(message + 8U) != P0_ED_REQUEST_BYTES ||
        load_le32(message + 16U) != P0_ED_IQ_FRAME_BYTES ||
        load_le32(message + 28U) != p0_ed_crc32(message, 28U) ||
        load_le32(message + 24U) !=
            p0_ed_crc32(message + P0_ED_REQUEST_HEADER_BYTES, P0_ED_IQ_FRAME_BYTES))
        return -1;
    flags = load_le32(message + 20U);
    if ((flags & ~P0_ED_REQUEST_FLAGS_ALLOWED) != 0U)
        return -1;
    request->frame_id = load_le32(message + 12U);
    request->flags = flags;
    request->iq = message + P0_ED_REQUEST_HEADER_BYTES;
    return 0;
}

int p0_ed_response_encode(const p0_ed_response_t *response, uint8_t *message,
                          size_t capacity, size_t *message_bytes)
{
    size_t total;
    uint32_t result_bytes;

    if (response == NULL || message == NULL || message_bytes == NULL)
        return -1;
    result_bytes = response->status == P0_ED_SERVICE_OK ? P0_ED_RESULT_BYTES : 0U;
    total = P0_ED_RESPONSE_HEADER_BYTES + result_bytes;
    if (capacity < total || response->status > P0_ED_SERVICE_INTERNAL_FAILURE ||
        (response->status == P0_ED_SERVICE_OK &&
         (response->result.frame_id != response->frame_id ||
          response->result.active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
          response->result.ended_count > PHASE06J_MAX_ACTIVE_TRACKS)))
        return -1;
    memset(message, 0, P0_ED_RESPONSE_HEADER_BYTES);
    store_le32(message + 0U, P0_ED_RESPONSE_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION);
    store_le16(message + 6U, P0_ED_RESPONSE_HEADER_BYTES);
    store_le32(message + 8U, (uint32_t)total);
    store_le32(message + 12U, response->frame_id);
    store_le32(message + 16U, response->status);
    store_le32(message + 20U, result_bytes);
    store_le32(message + 24U, response->raw_candidate_count);
    store_le32(message + 28U, response->dma_status_flags);
    if (result_bytes != 0U) {
        encode_result(message + P0_ED_RESPONSE_HEADER_BYTES, &response->result);
        store_le32(message + 32U,
                   p0_ed_crc32(message + P0_ED_RESPONSE_HEADER_BYTES, result_bytes));
    }
    store_le32(message + 44U, p0_ed_crc32(message, 44U));
    *message_bytes = total;
    return 0;
}

int p0_ed_response_decode(const uint8_t *message, size_t message_bytes,
                          p0_ed_response_t *response)
{
    uint32_t result_bytes;

    if (message == NULL || response == NULL || message_bytes < P0_ED_RESPONSE_HEADER_BYTES ||
        message_bytes > P0_ED_RESPONSE_BYTES ||
        load_le32(message + 0U) != P0_ED_RESPONSE_MAGIC ||
        load_le16(message + 4U) != P0_ED_SERVICE_ABI_VERSION ||
        load_le16(message + 6U) != P0_ED_RESPONSE_HEADER_BYTES ||
        load_le32(message + 8U) != message_bytes ||
        load_le32(message + 36U) != 0U || load_le32(message + 40U) != 0U ||
        load_le32(message + 44U) != p0_ed_crc32(message, 44U))
        return -1;
    memset(response, 0, sizeof(*response));
    response->frame_id = load_le32(message + 12U);
    response->status = load_le32(message + 16U);
    result_bytes = load_le32(message + 20U);
    response->raw_candidate_count = load_le32(message + 24U);
    response->dma_status_flags = load_le32(message + 28U);
    if (response->status > P0_ED_SERVICE_INTERNAL_FAILURE)
        return -1;
    if (response->status != P0_ED_SERVICE_OK)
        return result_bytes == 0U && message_bytes == P0_ED_RESPONSE_HEADER_BYTES &&
                       load_le32(message + 32U) == 0U ? 0 : -1;
    if (result_bytes != P0_ED_RESULT_BYTES || message_bytes != P0_ED_RESPONSE_BYTES ||
        load_le32(message + 32U) !=
            p0_ed_crc32(message + P0_ED_RESPONSE_HEADER_BYTES, result_bytes))
        return -1;
    if (decode_result(message + P0_ED_RESPONSE_HEADER_BYTES, &response->result) != 0 ||
        response->result.frame_id != response->frame_id)
        return -1;
    return 0;
}
