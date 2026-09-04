#ifndef P0_MULTIFRAME_NARROWBAND_H
#define P0_MULTIFRAME_NARROWBAND_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"

enum {
    P0_MFNB_OK = 0,
    P0_MFNB_INVALID_ARGUMENT = -1,
    P0_MFNB_ALLOCATION_FAILED = -2,
    P0_MFNB_MINIMUM_FRAMES = 32,
    P0_MFNB_MAXIMUM_FRAMES = 512
};

typedef struct {
    double center_bin;
    uint16_t peak_bin;
    uint16_t lower_bin;
    uint16_t upper_bin;
    double peak_to_noise_db;
    uint16_t observed_frames;
    uint16_t total_frames;
    uint16_t component_count;
} p0_multiframe_narrowband_candidate_t;

/*
 * Row-major linear-power frames. Frequency is intentionally absent from this
 * core: RF conversion is origin_hz + bin * sample_rate_hz / bin_count.
 */
P0_API int p0_multiframe_narrowband_process(
    const double *frame_power,
    size_t frame_count,
    size_t bin_count,
    double sample_rate_hz,
    size_t first_bin,
    size_t last_bin,
    p0_multiframe_narrowband_candidate_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count
);

#endif
