#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include <string.h>

#include "p0_ed_service_protocol.h"

#define REQUIRE(condition) do { if (!(condition)) { \
    fprintf(stderr, "test failure at line %d\n", __LINE__); return 1; } } while (0)

static void put32(uint8_t *bytes, uint32_t value)
{
    unsigned int i;
    for (i = 0; i < 4U; ++i) bytes[i] = (uint8_t)(value >> (8U * i));
}

static int test_wide_batch(void)
{
    uint8_t bytes[P0_PARAMETER_BATCH_REQUEST_BYTES] = {0};
    uint8_t reply[P0_PARAMETER_BATCH_RESPONSE_BYTES];
    p0_parameter_batch_request_t request;
    memcpy(bytes, "P0PM", 4U);
    bytes[4] = 2U;
    bytes[6] = 64U;
    bytes[8] = 7U;
    put32(bytes + 16U, 2000000U);
    bytes[28] = 1U;
    bytes[36] = 56U;
    bytes[38] = 199U; bytes[39] = 15U; /* 4039 */
    put32(bytes + 40U, p0_ed_crc32(bytes + 64U, 32768U));
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == 0);
    REQUIRE(request.lower_bin == 56U && request.upper_bin == 4039U);
    REQUIRE(p0_parameter_batch_response_encode(&request, 1U, 0U, 0U, NULL, reply) == 0);
    REQUIRE(reply[4] == 2U);
    REQUIRE(p0_parameter_batch_response_check(reply, sizeof(reply), request.token) == 0);
    REQUIRE(p0_parameter_batch_response_check(reply, sizeof(reply), request.token + 1U) == -1);
    reply[4] = 3U;
    put32(reply + 172U, p0_ed_crc32(reply, 172U));
    REQUIRE(p0_parameter_batch_response_check(reply, sizeof(reply), request.token) == -1);
    bytes[4] = 1U;
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == -1);
    bytes[38] = 55U; bytes[39] = 2U; /* 567: legacy width 512 */
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == 0);
    bytes[4] = 2U;
    bytes[36] = 55U;
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == -1);
    bytes[36] = 56U;
    bytes[38] = 200U; bytes[39] = 15U; /* 4040: no reference room */
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == -1);
    bytes[38] = 199U;
    put32(bytes + 60U, p0_ed_crc32(bytes, 60U));
    bytes[70] ^= 1U;
    REQUIRE(p0_parameter_batch_decode(bytes, sizeof(bytes), &request) == -1);
    return 0;
}

int main(void)
{
    uint8_t iq[P0_ED_IQ_FRAME_BYTES];
    uint8_t request[P0_ED_REQUEST_BYTES];
    uint8_t request_v2[P0_ED_REQUEST_BYTES_V2];
    uint8_t runtime_iq[P0_ED_MAX_IQ_FRAME_BYTES];
    uint8_t request_v4[P0_ED_REQUEST_MAX_BYTES_V4];
    uint8_t reply[P0_ED_RESPONSE_BYTES];
    p0_ed_request_view_t request_view;
    p0_ed_response_t response;
    p0_ed_response_t decoded;
    size_t reply_bytes = 0U;
    size_t index;

    REQUIRE(test_wide_batch() == 0);

    REQUIRE(p0_ed_crc32((const uint8_t *)"123456789", 9U) ==
            UINT32_C(0xCBF43926));
    REQUIRE(p0_ed_crc32(NULL, 0U) == 0U);
    for (index = 0U; index < sizeof(iq); ++index)
        iq[index] = (uint8_t)(index * 37U + 11U);
    REQUIRE(p0_ed_request_encode(UINT32_C(0xFFFFFFFE), P0_ED_REQUEST_FLAG_RESET,
                                 iq, sizeof(iq), request, sizeof(request)) == 0);
    REQUIRE(p0_ed_request_decode(request, sizeof(request), &request_view) == 0);
    REQUIRE(request_view.frame_id == UINT32_C(0xFFFFFFFE));
    REQUIRE(request_view.flags == P0_ED_REQUEST_FLAG_RESET);
    REQUIRE(memcmp(request_view.iq, iq, sizeof(iq)) == 0);
    request[P0_ED_REQUEST_HEADER_BYTES + 17U] ^= 1U;
    REQUIRE(p0_ed_request_decode(request, sizeof(request), &request_view) != 0);
    request[P0_ED_REQUEST_HEADER_BYTES + 17U] ^= 1U;
    request[4U] = 2U;
    REQUIRE(p0_ed_request_decode(request, sizeof(request), &request_view) != 0);
    REQUIRE(p0_ed_request_decode(request, sizeof(request) - 1U, &request_view) != 0);
    REQUIRE(p0_ed_request_encode(1U, 0x80000000U, iq, sizeof(iq), request,
                                 sizeof(request)) != 0);
    REQUIRE(p0_ed_request_encode_compact(17U, P0_ED_REQUEST_FLAG_RESET, iq,
                                         sizeof(iq), request,
                                         sizeof(request)) == 0);
    REQUIRE(p0_ed_request_decode(request, sizeof(request), &request_view) == 0);
    REQUIRE(request_view.abi_version == P0_ED_SERVICE_ABI_VERSION_V3);
    REQUIRE(request_view.frame_id == 17U);
    REQUIRE(request_view.flags == P0_ED_REQUEST_FLAG_RESET);
    REQUIRE(memcmp(request_view.iq, iq, sizeof(iq)) == 0);
    REQUIRE(request[24U] == 0U && request[25U] == 0U &&
            request[26U] == 0U && request[27U] == 0U);
    request[28U] ^= 1U;
    REQUIRE(p0_ed_request_decode(request, sizeof(request), &request_view) != 0);
    request[28U] ^= 1U;
    REQUIRE(p0_ed_request_encode_compact(17U, P0_ED_REQUEST_FLAG_PARAMETER, iq,
                                         sizeof(iq), request,
                                         sizeof(request)) != 0);
    REQUIRE(p0_ed_request_encode_v2(
                9U, P0_ED_REQUEST_FLAG_PARAMETER | P0_ED_REQUEST_FLAG_PARAMETER_START,
                UINT64_C(2000000), INT64_C(2600000000), UINT64_C(77), UINT64_C(5),
                1900U, 2200U, iq, sizeof(iq), request_v2, sizeof(request_v2)) == 0);
    REQUIRE(p0_ed_request_decode(request_v2, sizeof(request_v2), &request_view) == 0);
    REQUIRE(request_view.abi_version == P0_ED_SERVICE_ABI_VERSION_V2);
    REQUIRE(request_view.frame_id == 9U && request_view.sample_rate_hz == UINT64_C(2000000));
    REQUIRE(request_view.center_frequency_hz == INT64_C(2600000000));
    REQUIRE(request_view.parameter_intent_id == UINT64_C(77));
    REQUIRE(request_view.parameter_event_id == UINT64_C(5));
    REQUIRE(request_view.parameter_lower_shifted_bin == 1900U);
    REQUIRE(request_view.parameter_upper_shifted_bin == 2200U);
    request_v2[72U] = 1U;
    REQUIRE(p0_ed_request_decode(request_v2, sizeof(request_v2), &request_view) != 0);
    request_v2[72U] = 0U;
    REQUIRE(p0_ed_request_encode_v2(
                9U, P0_ED_REQUEST_FLAG_PARAMETER_START, UINT64_C(2000000),
                INT64_C(2600000000), UINT64_C(77), UINT64_C(5), 1900U, 2200U,
                iq, sizeof(iq), request_v2, sizeof(request_v2)) != 0);
    memset(runtime_iq, 0x5a, sizeof(runtime_iq));
    REQUIRE(p0_ed_request_encode_runtime(
                19U, P0_ED_REQUEST_FLAG_RESET, runtime_iq, sizeof(runtime_iq),
                request_v4, sizeof(request_v4)) == 0);
    REQUIRE(p0_ed_request_decode(request_v4, sizeof(request_v4), &request_view) == 0);
    REQUIRE(request_view.abi_version == P0_ED_SERVICE_ABI_VERSION_V4);
    REQUIRE(request_view.frame_id == 19U && request_view.iq_bytes == sizeof(runtime_iq));
    REQUIRE(memcmp(request_view.iq, runtime_iq, sizeof(runtime_iq)) == 0);
    REQUIRE(p0_ed_request_encode_runtime(
                19U, 0U, runtime_iq, 12288U, request_v4, sizeof(request_v4)) != 0);

    memset(&response, 0, sizeof(response));
    response.frame_id = 42U;
    response.status = P0_ED_SERVICE_OK;
    response.raw_candidate_count = 147U;
    response.dma_status_flags = 7U;
    response.result.frame_id = 42U;
    response.result.active_count = 1U;
    response.result.ended_count = 1U;
    response.result.dropped_candidates = 83U;
    response.result.evicted_history_count = UINT64_C(9);
    response.result.active[0].event_id = UINT64_C(0x1122334455667788);
    response.result.active[0].first_frame_id = 41U;
    response.result.active[0].last_seen_frame_id = 42U;
    response.result.active[0].seen_count = 2U;
    response.result.active[0].state = PHASE06J_EVENT_CONFIRMED;
    response.result.active[0].observed_this_frame = 1U;
    response.result.active[0].candidate.start_shifted_bin = 2299U;
    response.result.active[0].candidate.end_shifted_bin = 2308U;
    response.result.active[0].candidate.peak_shifted_bin = 2304U;
    response.result.active[0].candidate.coarse_span_bins = 10U;
    response.result.active[0].candidate.pfa_select = 1U;
    response.result.active[0].candidate.flags = 1U;
    response.result.active[0].candidate.peak_power_uq28_30 = UINT64_C(1000000);
    response.result.active[0].candidate.regional_noise_uq28_30 = UINT64_C(100);
    response.result.active[0].candidate.threshold_uq32_30 = UINT64_C(858);
    response.result.ended[0] = response.result.active[0];
    response.result.ended[0].state = PHASE06J_EVENT_ENDED;
    response.result.ended[0].observed_this_frame = 0U;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(reply_bytes == P0_ED_RESPONSE_BYTES_V1);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.frame_id == response.frame_id);
    REQUIRE(decoded.status == P0_ED_SERVICE_OK);
    REQUIRE(decoded.raw_candidate_count == 147U && decoded.dma_status_flags == 7U);
    REQUIRE(memcmp(&decoded.result, &response.result, sizeof(response.result)) == 0);
    reply[P0_ED_RESPONSE_HEADER_BYTES + 99U] ^= 1U;
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) != 0);
    reply[P0_ED_RESPONSE_HEADER_BYTES + 99U] ^= 1U;
    reply[44U] ^= 1U;
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) != 0);
    REQUIRE(p0_ed_response_decode(reply, sizeof(reply) + 1U, &decoded) != 0);

    response.abi_version = P0_ED_SERVICE_ABI_VERSION_V3;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(reply_bytes == P0_ED_RESPONSE_HEADER_BYTES_V3 +
                               P0_ED_RESULT_HEADER_BYTES + 2U * P0_ED_EVENT_BYTES);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.abi_version == P0_ED_SERVICE_ABI_VERSION_V3);
    REQUIRE(memcmp(&decoded.result, &response.result, sizeof(response.result)) == 0);
    REQUIRE(reply[32U] == 0U && reply[33U] == 0U &&
            reply[34U] == 0U && reply[35U] == 0U);
    reply[44U] ^= 1U;
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) != 0);
    reply[44U] ^= 1U;
    REQUIRE(p0_ed_response_decode(reply, reply_bytes - 1U, &decoded) != 0);

    response.abi_version = P0_ED_SERVICE_ABI_VERSION_V4;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.abi_version == P0_ED_SERVICE_ABI_VERSION_V4);

    response.result.frame_id = 43U;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) != 0);

    memset(&response, 0, sizeof(response));
    response.frame_id = 7U;
    response.status = P0_ED_SERVICE_DMA_FAILURE;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(reply_bytes == P0_ED_RESPONSE_HEADER_BYTES);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.status == P0_ED_SERVICE_DMA_FAILURE && decoded.frame_id == 7U);

    memset(&response, 0, sizeof(response));
    response.abi_version = P0_ED_SERVICE_ABI_VERSION_V2;
    response.frame_id = 12U;
    response.status = P0_ED_SERVICE_OK;
    response.result.frame_id = 12U;
    response.parameter_present = 1U;
    response.parameter.intent_id = UINT64_C(77);
    response.parameter.event_id = UINT64_C(5);
    response.parameter.frame_id = 12U;
    response.parameter.observation_count = 4U;
    response.parameter.emission_center_frequency_hz.state = P0_PARAMETER_FIELD_VALID;
    response.parameter.emission_center_frequency_hz.value = 2600123456.25;
    response.parameter.occupied_bandwidth_hz.state = P0_PARAMETER_FIELD_UNCERTAIN;
    response.parameter.occupied_bandwidth_hz.reason =
        P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY;
    response.parameter.reference_difference_db = 0.25;
    response.parameter.detection_significance = 18.0;
    response.parameter.center_uncertainty_bins = 0.5;
    response.parameter.temporal_edge_range_bins = 8.0;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(reply_bytes == P0_ED_RESPONSE_BYTES_V2);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.abi_version == P0_ED_SERVICE_ABI_VERSION_V2);
    REQUIRE(decoded.parameter_present == 1U);
    REQUIRE(decoded.parameter.intent_id == UINT64_C(77));
    REQUIRE(decoded.parameter.event_id == UINT64_C(5));
    REQUIRE(decoded.parameter.emission_center_frequency_hz.value == 2600123456.25);
    response.parameter.emission_center_frequency_hz.value = NAN;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) != 0);
    response.parameter.emission_center_frequency_hz.value = 2600123456.25;
    reply[P0_ED_RESPONSE_HEADER_BYTES_V2 + P0_ED_RESULT_BYTES + 17U] ^= 1U;
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) != 0);

    puts("P0_ED_SERVICE_PROTOCOL_TEST=PASS");
    return 0;
}
