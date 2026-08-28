#include "p0_ed_service_protocol.h"

#include <math.h>
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

static double load_le_double(const uint8_t *source)
{
    uint64_t bits = load_le64(source);
    double value;

    memcpy(&value, &bits, sizeof(value));
    return value;
}

static void store_le_double(uint8_t *target, double value)
{
    uint64_t bits;

    memcpy(&bits, &value, sizeof(bits));
    store_le64(target, bits);
}

uint32_t p0_ed_crc32(const uint8_t *data, size_t length)
{
    static const uint32_t table[16] = {
        UINT32_C(0x00000000), UINT32_C(0x1DB71064),
        UINT32_C(0x3B6E20C8), UINT32_C(0x26D930AC),
        UINT32_C(0x76DC4190), UINT32_C(0x6B6B51F4),
        UINT32_C(0x4DB26158), UINT32_C(0x5005713C),
        UINT32_C(0xEDB88320), UINT32_C(0xF00F9344),
        UINT32_C(0xD6D6A3E8), UINT32_C(0xCB61B38C),
        UINT32_C(0x9B64C2B0), UINT32_C(0x86D3D2D4),
        UINT32_C(0xA00AE278), UINT32_C(0xBDBDF21C),
    };
    uint32_t crc = UINT32_MAX;
    size_t index;

    if (data == NULL && length != 0U)
        return 0U;
    for (index = 0U; index < length; ++index) {
        crc ^= data[index];
        crc = (crc >> 4) ^ table[crc & 0x0FU];
        crc = (crc >> 4) ^ table[crc & 0x0FU];
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

static void encode_parameter_field(uint8_t *target, const p0_parameter_field_t *field)
{
    target[0U] = field->state;
    target[1U] = field->reason;
    store_le16(target + 2U, 0U);
    store_le_double(target + 4U, field->value);
}

static int parameter_field_valid(const p0_parameter_field_t *field)
{
    return field->state <= P0_PARAMETER_FIELD_UNCERTAIN &&
           field->reason <= P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY &&
           isfinite(field->value) &&
           (field->state != P0_PARAMETER_FIELD_VALID ||
            field->reason == P0_PARAMETER_REASON_NONE);
}

static int decode_parameter_field(const uint8_t *source, p0_parameter_field_t *field)
{
    if (source[0U] > P0_PARAMETER_FIELD_UNCERTAIN ||
        source[1U] > P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY ||
        load_le16(source + 2U) != 0U)
        return -1;
    field->state = source[0U];
    field->reason = source[1U];
    field->value = load_le_double(source + 4U);
    return parameter_field_valid(field) ? 0 : -1;
}

static void encode_parameter_result(uint8_t *target,
                                    const p0_parameter_result_t *result)
{
    memset(target, 0, P0_ED_PARAMETER_RESULT_BYTES);
    store_le64(target + 0U, result->intent_id);
    store_le64(target + 8U, result->event_id);
    store_le32(target + 16U, result->frame_id);
    target[20U] = result->observation_count;
    encode_parameter_field(target + 24U, &result->emission_center_frequency_hz);
    encode_parameter_field(target + 36U, &result->lower_occupied_edge_hz);
    encode_parameter_field(target + 48U, &result->upper_occupied_edge_hz);
    encode_parameter_field(target + 60U, &result->occupied_bandwidth_hz);
    encode_parameter_field(target + 72U, &result->channel_power_dbfs);
    encode_parameter_field(target + 84U, &result->snr_estimate_db);
    store_le_double(target + 96U, isfinite(result->reference_difference_db)
                                      ? result->reference_difference_db : 0.0);
    store_le_double(target + 104U, isfinite(result->detection_significance)
                                       ? result->detection_significance : 0.0);
    store_le_double(target + 112U, isfinite(result->center_uncertainty_bins)
                                       ? result->center_uncertainty_bins : 0.0);
    store_le_double(target + 120U, isfinite(result->temporal_edge_range_bins)
                                       ? result->temporal_edge_range_bins : 0.0);
}

static int decode_parameter_result(const uint8_t *source,
                                   p0_parameter_result_t *result)
{
    if (source[21U] != 0U || source[22U] != 0U || source[23U] != 0U ||
        source[20U] > P0_PARAMETER_REQUIRED_FRAMES)
        return -1;
    memset(result, 0, sizeof(*result));
    result->intent_id = load_le64(source + 0U);
    result->event_id = load_le64(source + 8U);
    result->frame_id = load_le32(source + 16U);
    result->observation_count = source[20U];
    if (decode_parameter_field(source + 24U, &result->emission_center_frequency_hz) != 0 ||
        decode_parameter_field(source + 36U, &result->lower_occupied_edge_hz) != 0 ||
        decode_parameter_field(source + 48U, &result->upper_occupied_edge_hz) != 0 ||
        decode_parameter_field(source + 60U, &result->occupied_bandwidth_hz) != 0 ||
        decode_parameter_field(source + 72U, &result->channel_power_dbfs) != 0 ||
        decode_parameter_field(source + 84U, &result->snr_estimate_db) != 0)
        return -1;
    result->reference_difference_db = load_le_double(source + 96U);
    result->detection_significance = load_le_double(source + 104U);
    result->center_uncertainty_bins = load_le_double(source + 112U);
    result->temporal_edge_range_bins = load_le_double(source + 120U);
    return isfinite(result->reference_difference_db) &&
                   isfinite(result->detection_significance) &&
                   isfinite(result->center_uncertainty_bins) &&
                   isfinite(result->temporal_edge_range_bins)
               ? 0 : -1;
}

static int parameter_result_valid(const p0_parameter_result_t *result)
{
    return result->intent_id != 0U && result->event_id != 0U &&
           parameter_field_valid(&result->emission_center_frequency_hz) &&
           parameter_field_valid(&result->lower_occupied_edge_hz) &&
           parameter_field_valid(&result->upper_occupied_edge_hz) &&
           parameter_field_valid(&result->occupied_bandwidth_hz) &&
           parameter_field_valid(&result->channel_power_dbfs) &&
           parameter_field_valid(&result->snr_estimate_db);
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

int p0_ed_request_encode_v2(uint32_t frame_id, uint32_t flags,
                            uint64_t sample_rate_hz, int64_t center_frequency_hz,
                            uint64_t parameter_intent_id, uint64_t parameter_event_id,
                            uint16_t parameter_lower_shifted_bin,
                            uint16_t parameter_upper_shifted_bin,
                            const uint8_t *iq, size_t iq_bytes,
                            uint8_t *message, size_t capacity)
{
    int parameter_requested = (flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U;

    if (iq == NULL || message == NULL || iq_bytes != P0_ED_IQ_FRAME_BYTES ||
        capacity < P0_ED_REQUEST_BYTES_V2 ||
        (flags & ~P0_ED_REQUEST_FLAGS_V2_ALLOWED) != 0U ||
        ((flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U && !parameter_requested) ||
        (parameter_requested &&
         (sample_rate_hz == 0U || parameter_intent_id == 0U || parameter_event_id == 0U ||
          parameter_lower_shifted_bin > parameter_upper_shifted_bin)) ||
        (!parameter_requested &&
         (sample_rate_hz != 0U || center_frequency_hz != 0 || parameter_intent_id != 0U ||
          parameter_event_id != 0U || parameter_lower_shifted_bin != 0U ||
          parameter_upper_shifted_bin != 0U)))
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES_V2);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION_V2);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES_V2);
    store_le32(message + 8U, P0_ED_REQUEST_BYTES_V2);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, P0_ED_IQ_FRAME_BYTES);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, p0_ed_crc32(iq, iq_bytes));
    store_le64(message + 32U, sample_rate_hz);
    store_le64(message + 40U, (uint64_t)center_frequency_hz);
    store_le64(message + 48U, parameter_intent_id);
    store_le64(message + 56U, parameter_event_id);
    store_le16(message + 64U, parameter_lower_shifted_bin);
    store_le16(message + 66U, parameter_upper_shifted_bin);
    store_le32(message + 76U, p0_ed_crc32(message, 76U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES_V2, iq, iq_bytes);
    return 0;
}

int p0_ed_request_decode(const uint8_t *message, size_t message_bytes,
                         p0_ed_request_view_t *request)
{
    uint16_t version;
    uint32_t flags;

    if (message == NULL || request == NULL || message_bytes < P0_ED_REQUEST_HEADER_BYTES_V1 ||
        load_le32(message + 0U) != P0_ED_REQUEST_MAGIC)
        return -1;
    memset(request, 0, sizeof(*request));
    version = load_le16(message + 4U);
    if (version == P0_ED_SERVICE_ABI_VERSION_V1) {
        if (message_bytes != P0_ED_REQUEST_BYTES_V1 ||
            load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES_V1 ||
            load_le32(message + 8U) != P0_ED_REQUEST_BYTES_V1 ||
            load_le32(message + 16U) != P0_ED_IQ_FRAME_BYTES ||
            load_le32(message + 28U) != p0_ed_crc32(message, 28U) ||
            load_le32(message + 24U) !=
                p0_ed_crc32(message + P0_ED_REQUEST_HEADER_BYTES_V1,
                            P0_ED_IQ_FRAME_BYTES))
            return -1;
        flags = load_le32(message + 20U);
        if ((flags & ~P0_ED_REQUEST_FLAGS_V1_ALLOWED) != 0U)
            return -1;
        request->iq = message + P0_ED_REQUEST_HEADER_BYTES_V1;
    } else if (version == P0_ED_SERVICE_ABI_VERSION_V2) {
        if (message_bytes != P0_ED_REQUEST_BYTES_V2 ||
            load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES_V2 ||
            load_le32(message + 8U) != P0_ED_REQUEST_BYTES_V2 ||
            load_le32(message + 16U) != P0_ED_IQ_FRAME_BYTES ||
            load_le32(message + 28U) != 0U || load_le32(message + 68U) != 0U ||
            load_le32(message + 72U) != 0U ||
            load_le32(message + 76U) != p0_ed_crc32(message, 76U) ||
            load_le32(message + 24U) !=
                p0_ed_crc32(message + P0_ED_REQUEST_HEADER_BYTES_V2,
                            P0_ED_IQ_FRAME_BYTES))
            return -1;
        flags = load_le32(message + 20U);
        if ((flags & ~P0_ED_REQUEST_FLAGS_V2_ALLOWED) != 0U ||
            ((flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U &&
             (flags & P0_ED_REQUEST_FLAG_PARAMETER) == 0U))
            return -1;
        request->sample_rate_hz = load_le64(message + 32U);
        request->center_frequency_hz = (int64_t)load_le64(message + 40U);
        request->parameter_intent_id = load_le64(message + 48U);
        request->parameter_event_id = load_le64(message + 56U);
        request->parameter_lower_shifted_bin = load_le16(message + 64U);
        request->parameter_upper_shifted_bin = load_le16(message + 66U);
        if ((flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U) {
            unsigned int width = (unsigned int)request->parameter_upper_shifted_bin -
                                 request->parameter_lower_shifted_bin + 1U;
            if (request->sample_rate_hz == 0U || request->parameter_intent_id == 0U ||
                request->parameter_event_id == 0U ||
                request->parameter_lower_shifted_bin > request->parameter_upper_shifted_bin ||
                width < P0_PARAMETER_MINIMUM_SPAN_BINS ||
                width > P0_PARAMETER_MAXIMUM_SPAN_BINS ||
                request->parameter_lower_shifted_bin <
                    20U + P0_PARAMETER_LOCAL_PADDING ||
                request->parameter_upper_shifted_bin >
                    4075U - P0_PARAMETER_LOCAL_PADDING)
                return -1;
        } else if (request->sample_rate_hz != 0U || request->center_frequency_hz != 0 ||
                   request->parameter_intent_id != 0U || request->parameter_event_id != 0U ||
                   request->parameter_lower_shifted_bin != 0U ||
                   request->parameter_upper_shifted_bin != 0U) {
            return -1;
        }
        request->iq = message + P0_ED_REQUEST_HEADER_BYTES_V2;
    } else {
        return -1;
    }
    request->abi_version = version;
    request->frame_id = load_le32(message + 12U);
    request->flags = flags;
    return 0;
}

int p0_ed_response_encode(const p0_ed_response_t *response, uint8_t *message,
                          size_t capacity, size_t *message_bytes)
{
    uint16_t version;
    size_t header_bytes;
    size_t total;
    uint32_t result_bytes;
    uint32_t parameter_bytes;

    if (response == NULL || message == NULL || message_bytes == NULL)
        return -1;
    version = response->abi_version == 0U ? P0_ED_SERVICE_ABI_VERSION_V1 :
                                           response->abi_version;
    if (version != P0_ED_SERVICE_ABI_VERSION_V1 &&
        version != P0_ED_SERVICE_ABI_VERSION_V2)
        return -1;
    if (version == P0_ED_SERVICE_ABI_VERSION_V1 && response->parameter_present != 0U)
        return -1;
    header_bytes = version == P0_ED_SERVICE_ABI_VERSION_V1
                       ? P0_ED_RESPONSE_HEADER_BYTES_V1
                       : P0_ED_RESPONSE_HEADER_BYTES_V2;
    result_bytes = response->status == P0_ED_SERVICE_OK ? P0_ED_RESULT_BYTES : 0U;
    parameter_bytes = response->status == P0_ED_SERVICE_OK &&
                              response->parameter_present != 0U
                          ? P0_ED_PARAMETER_RESULT_BYTES
                          : 0U;
    total = header_bytes + result_bytes + parameter_bytes;
    if (capacity < total || response->status > P0_ED_SERVICE_INTERNAL_FAILURE ||
        (response->status == P0_ED_SERVICE_OK &&
         (response->result.frame_id != response->frame_id ||
           response->result.active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
           response->result.ended_count > PHASE06J_MAX_ACTIVE_TRACKS ||
           (parameter_bytes != 0U &&
            (response->parameter.frame_id != response->frame_id ||
             response->parameter.observation_count > P0_PARAMETER_REQUIRED_FRAMES ||
             !parameter_result_valid(&response->parameter))))))
        return -1;
    memset(message, 0, header_bytes);
    store_le32(message + 0U, P0_ED_RESPONSE_MAGIC);
    store_le16(message + 4U, version);
    store_le16(message + 6U, (uint16_t)header_bytes);
    store_le32(message + 8U, (uint32_t)total);
    store_le32(message + 12U, response->frame_id);
    store_le32(message + 16U, response->status);
    store_le32(message + 20U, result_bytes);
    store_le32(message + 24U, response->raw_candidate_count);
    store_le32(message + 28U, response->dma_status_flags);
    if (result_bytes != 0U) {
        encode_result(message + header_bytes, &response->result);
        store_le32(message + 32U,
                   p0_ed_crc32(message + header_bytes, result_bytes));
    }
    if (version == P0_ED_SERVICE_ABI_VERSION_V1) {
        store_le32(message + 44U, p0_ed_crc32(message, 44U));
    } else {
        store_le32(message + 36U, parameter_bytes);
        if (parameter_bytes != 0U) {
            encode_parameter_result(message + header_bytes + result_bytes,
                                    &response->parameter);
            store_le32(message + 40U,
                       p0_ed_crc32(message + header_bytes + result_bytes,
                                   parameter_bytes));
            store_le32(message + 44U, 1U);
        }
        store_le32(message + 60U, p0_ed_crc32(message, 60U));
    }
    *message_bytes = total;
    return 0;
}

int p0_ed_response_decode(const uint8_t *message, size_t message_bytes,
                          p0_ed_response_t *response)
{
    uint16_t version;
    size_t header_bytes;
    uint32_t result_bytes;
    uint32_t parameter_bytes = 0U;

    if (message == NULL || response == NULL ||
        message_bytes < P0_ED_RESPONSE_HEADER_BYTES_V1 ||
        message_bytes > P0_ED_RESPONSE_BYTES ||
        load_le32(message + 0U) != P0_ED_RESPONSE_MAGIC)
        return -1;
    version = load_le16(message + 4U);
    if (version == P0_ED_SERVICE_ABI_VERSION_V1) {
        header_bytes = P0_ED_RESPONSE_HEADER_BYTES_V1;
        if (load_le16(message + 6U) != header_bytes ||
            load_le32(message + 8U) != message_bytes ||
            load_le32(message + 36U) != 0U || load_le32(message + 40U) != 0U ||
            load_le32(message + 44U) != p0_ed_crc32(message, 44U))
            return -1;
    } else if (version == P0_ED_SERVICE_ABI_VERSION_V2) {
        header_bytes = P0_ED_RESPONSE_HEADER_BYTES_V2;
        if (message_bytes < header_bytes || load_le16(message + 6U) != header_bytes ||
            load_le32(message + 8U) != message_bytes ||
            load_le32(message + 48U) != 0U || load_le32(message + 52U) != 0U ||
            load_le32(message + 56U) != 0U ||
            load_le32(message + 60U) != p0_ed_crc32(message, 60U))
            return -1;
        parameter_bytes = load_le32(message + 36U);
        if ((parameter_bytes == 0U &&
             (load_le32(message + 40U) != 0U || load_le32(message + 44U) != 0U)) ||
            (parameter_bytes != 0U &&
             (parameter_bytes != P0_ED_PARAMETER_RESULT_BYTES ||
              load_le32(message + 44U) != 1U)))
            return -1;
    } else {
        return -1;
    }
    memset(response, 0, sizeof(*response));
    response->abi_version = version;
    response->frame_id = load_le32(message + 12U);
    response->status = load_le32(message + 16U);
    result_bytes = load_le32(message + 20U);
    response->raw_candidate_count = load_le32(message + 24U);
    response->dma_status_flags = load_le32(message + 28U);
    if (response->status > P0_ED_SERVICE_INTERNAL_FAILURE)
        return -1;
    if (response->status != P0_ED_SERVICE_OK)
        return result_bytes == 0U && parameter_bytes == 0U &&
                       message_bytes == header_bytes && load_le32(message + 32U) == 0U
                   ? 0 : -1;
    if (result_bytes != P0_ED_RESULT_BYTES ||
        message_bytes != header_bytes + result_bytes + parameter_bytes ||
        load_le32(message + 32U) !=
            p0_ed_crc32(message + header_bytes, result_bytes))
        return -1;
    if (decode_result(message + header_bytes, &response->result) != 0 ||
        response->result.frame_id != response->frame_id)
        return -1;
    if (parameter_bytes != 0U) {
        if (load_le32(message + 40U) !=
                p0_ed_crc32(message + header_bytes + result_bytes, parameter_bytes) ||
            decode_parameter_result(message + header_bytes + result_bytes,
                                    &response->parameter) != 0 ||
            response->parameter.frame_id != response->frame_id)
            return -1;
        response->parameter_present = 1U;
    }
    return 0;
}
