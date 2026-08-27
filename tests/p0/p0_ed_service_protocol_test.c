#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "p0_ed_service_protocol.h"

#define REQUIRE(condition) do { if (!(condition)) { \
    fprintf(stderr, "test failure at line %d\n", __LINE__); return 1; } } while (0)

int main(void)
{
    uint8_t iq[P0_ED_IQ_FRAME_BYTES];
    uint8_t request[P0_ED_REQUEST_BYTES];
    uint8_t reply[P0_ED_RESPONSE_BYTES];
    p0_ed_request_view_t request_view;
    p0_ed_response_t response;
    p0_ed_response_t decoded;
    size_t reply_bytes = 0U;
    size_t index;

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
    REQUIRE(reply_bytes == P0_ED_RESPONSE_BYTES);
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

    response.result.frame_id = 43U;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) != 0);

    memset(&response, 0, sizeof(response));
    response.frame_id = 7U;
    response.status = P0_ED_SERVICE_DMA_FAILURE;
    REQUIRE(p0_ed_response_encode(&response, reply, sizeof(reply), &reply_bytes) == 0);
    REQUIRE(reply_bytes == P0_ED_RESPONSE_HEADER_BYTES);
    REQUIRE(p0_ed_response_decode(reply, reply_bytes, &decoded) == 0);
    REQUIRE(decoded.status == P0_ED_SERVICE_DMA_FAILURE && decoded.frame_id == 7U);

    puts("P0_ED_SERVICE_PROTOCOL_TEST=PASS");
    return 0;
}
