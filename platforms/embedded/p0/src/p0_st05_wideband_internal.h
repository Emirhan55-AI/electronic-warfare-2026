#ifndef P0_ST05_WIDEBAND_INTERNAL_H
#define P0_ST05_WIDEBAND_INTERNAL_H

#include <stddef.h>

#include "p0_st05_wideband.h"

enum {
    P0_ST05_INTERNAL_REGION_BINS = 256,
    P0_ST05_INTERNAL_REGION_COUNT = P0_ST05_FRAME_BINS / P0_ST05_INTERNAL_REGION_BINS
};

void p0_st05_region_noise_trusted(
    const double *power,
    double *region_noise
);

int p0_st05_wideband_process_precomputed_trusted(
    const double *frame_power,
    size_t frame_count,
    const double *mean_power,
    const double *region_noise,
    p0_st05_result_t *result
);

#endif
