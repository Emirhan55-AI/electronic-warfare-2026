#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "p0_ed_service_protocol.h"

#define REQUIRE(value) do { if (!(value)) return __LINE__; } while (0)

int main(void)
{
    uint8_t bytes[P0_DETECTION_MESSAGE_BYTES];
    p0_detection_message_t source;
    p0_detection_message_t decoded;

    memset(&source, 0, sizeof(source));
    source.protocol_version = 2U;
    source.operation = P0_DETECTION_SET;
    source.request_id = 91U;
    source.generation = 7U;
    source.alpha_q32 = UINT64_C(36851433755);
    source.weak_alpha_q32 = UINT64_C(17098572778);
    source.fft_size = 16384U;
    REQUIRE(p0_detection_message_encode(&source, 0, bytes) == 0);
    REQUIRE(p0_detection_message_decode(bytes, sizeof(bytes), 0, &decoded) == 0);
    REQUIRE(decoded.protocol_version == 2U && decoded.fft_size == 16384U &&
            decoded.generation == 7U);
    source.fft_size = 2048U;
    REQUIRE(p0_detection_message_encode(&source, 0, bytes) != 0);
    source.protocol_version = 1U;
    source.fft_size = 4096U;
    REQUIRE(p0_detection_message_encode(&source, 0, bytes) == 0);
    REQUIRE(p0_detection_message_decode(bytes, sizeof(bytes), 0, &decoded) == 0);
    REQUIRE(decoded.protocol_version == 1U && decoded.fft_size == 4096U);
    puts("DETECTION_PROFILE_PROTOCOL_PASS");
    return 0;
}
