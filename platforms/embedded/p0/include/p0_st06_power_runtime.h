#ifndef P0_ST06_POWER_RUNTIME_H
#define P0_ST06_POWER_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#include "p0_st05_wideband.h"

typedef struct {
    double *shifted_power;
    uint64_t *shifted_power_uq28_30;
    uint8_t *shifted_detections;
    void *stream_state;
    size_t stream_state_bytes;
    uint32_t last_frame_id;
    int has_frame_id;
} p0_st06_power_runtime_t;

P0_API int p0_st06_power_runtime_init(p0_st06_power_runtime_t *runtime);
P0_API void p0_st06_power_runtime_release(p0_st06_power_runtime_t *runtime);
P0_API int p0_st06_power_runtime_reset(p0_st06_power_runtime_t *runtime);

P0_API int p0_st06_power_runtime_process(
    p0_st06_power_runtime_t *runtime,
    uint32_t frame_id,
    int reset_requested,
    const uint8_t *natural_power_words,
    size_t power_bytes,
    p0_st05_result_t *result,
    int *result_valid,
    int *context_reset_applied
);

#endif
