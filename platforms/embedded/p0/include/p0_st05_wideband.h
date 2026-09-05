#ifndef P0_ST05_WIDEBAND_H
#define P0_ST05_WIDEBAND_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"

enum {
    P0_ST05_OK = 0,
    P0_ST05_INVALID_ARGUMENT = -1,
    P0_ST05_OUTPUT_OVERFLOW = -2,
    P0_ST05_FRAME_BINS = 4096,
    P0_ST05_REGION_BINS = 256,
    P0_ST05_MINIMUM_FRAMES = 8,
    P0_ST05_MAXIMUM_FRAMES = 64,
    P0_ST05_MAXIMUM_CANDIDATES = 64,
    P0_ST05_MAXIMUM_UNRESOLVED = 64
};

typedef enum {
    P0_ST05_REFERENCE_UNAVAILABLE = 0,
    P0_ST05_NO_BOUNDED_EMISSION = 1,
    P0_ST05_RETUNE_REQUIRED = 2,
    P0_ST05_BOUNDED_CANDIDATES = 3
} p0_st05_decision_t;

typedef enum {
    P0_ST05_INDEPENDENT_FLANKS_UNAVAILABLE = 1,
    P0_ST05_NONHOMOGENEOUS_FLANKS = 2
} p0_st05_unresolved_reason_t;

typedef struct {
    uint32_t start_bin;
    uint32_t end_bin;
    uint32_t peak_bin;
    double peak_power;
    double reference_power_per_bin;
    double threshold_power_per_bin;
    uint32_t observed_frames;
    uint32_t total_frames;
} p0_st05_candidate_t;

typedef struct {
    uint32_t start_bin;
    uint32_t end_bin;
    uint32_t reason;
} p0_st05_unresolved_t;

typedef struct {
    uint32_t decision;
    uint32_t candidate_count;
    uint32_t unresolved_count;
    uint32_t absolute_absence_supported;
    double relative_reference_power_per_bin;
    p0_st05_candidate_t candidates[P0_ST05_MAXIMUM_CANDIDATES];
    p0_st05_unresolved_t unresolved[P0_ST05_MAXIMUM_UNRESOLVED];
} p0_st05_result_t;

P0_API int p0_st05_wideband_process(
    const double *frame_power,
    size_t frame_count,
    size_t frame_bins,
    p0_st05_result_t *result
);

#endif
