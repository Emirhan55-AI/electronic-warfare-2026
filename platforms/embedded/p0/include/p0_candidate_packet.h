#ifndef P0_CANDIDATE_PACKET_H
#define P0_CANDIDATE_PACKET_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"

enum {
    P0_CANDIDATE_PACKET_OK = 0,
    P0_CANDIDATE_PACKET_INVALID_ARGUMENT = -1,
    P0_CANDIDATE_PACKET_CAPACITY = -2,
    P0_CANDIDATE_PACKET_RANGE = -3
};

size_t p0_candidate_packet_bytes(size_t candidate_count);

int p0_candidate_packet_encode(
    uint32_t frame_id,
    const uint64_t *shifted_power_uq28_30,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const p0_candidate_region_t *candidates,
    size_t candidate_count,
    uint8_t *packet,
    size_t packet_capacity,
    size_t *packet_bytes
);

#endif
