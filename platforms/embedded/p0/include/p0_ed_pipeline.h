#ifndef P0_ED_PIPELINE_H
#define P0_ED_PIPELINE_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"
#include "phase06j_temporal.h"

typedef struct {
    double *power;
    uint64_t *raw_power;
    double *noise;
    double *threshold;
    uint8_t *detections;
    p0_candidate_region_t *candidates;
    uint8_t *packet;
    void *temporal_state;
    void *temporal_backup;
    p0_os_cfar_config_t config;
} p0_ed_pipeline_t;

int p0_ed_pipeline_init(p0_ed_pipeline_t *pipeline);
void p0_ed_pipeline_release(p0_ed_pipeline_t *pipeline);
int p0_ed_pipeline_reset(p0_ed_pipeline_t *pipeline);
int p0_ed_pipeline_process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count);

#endif
