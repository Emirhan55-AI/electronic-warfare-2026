#ifndef P0_ED_PIPELINE_H
#define P0_ED_PIPELINE_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"
#include "p0_parameter_runtime.h"
#include "p0_persistent_weak.h"
#include "p0_st05_stream.h"
#include "phase06j_temporal.h"

typedef struct {
    double *power;
    uint64_t *raw_power;
    double *noise;
    double *threshold;
    uint8_t *detections;
    p0_candidate_region_t *candidates;
    phase06i_candidate_v1 *candidate_records;
    void *temporal_state;
    void *temporal_backup;
    void *weak_state;
    void *weak_backup;
    p0_weak_nomination_v1 *weak_nominations;
    p0_persistent_weak_result_v1 previous_weak_result;
    void *wideband_stream_state;
    void *wideband_stream_backup;
    size_t wideband_stream_state_bytes;
    uint32_t wideband_last_frame_id;
    int wideband_has_frame_id;
    p0_os_cfar_config_t config;
    uint64_t weak_alpha_q32;
    int custom_cfar_profile;
    p0_parameter_runtime_t parameter_runtime;
} p0_ed_pipeline_t;

int p0_ed_pipeline_init(p0_ed_pipeline_t *pipeline);
void p0_ed_pipeline_release(p0_ed_pipeline_t *pipeline);
int p0_ed_pipeline_reset(p0_ed_pipeline_t *pipeline);
int p0_ed_pipeline_set_cfar(p0_ed_pipeline_t *pipeline, uint64_t alpha_q32,
                            uint64_t weak_alpha_q32);
int p0_ed_pipeline_process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count);
int p0_ed_pipeline_process_packet(p0_ed_pipeline_t *pipeline, int reset_requested,
                                  const uint8_t *packet, size_t packet_bytes,
                                  phase06j_frame_result_v1 *result,
                                  size_t *raw_candidate_count,
                                  uint32_t *packet_frame_id);
int p0_ed_pipeline_measure(p0_ed_pipeline_t *pipeline,
                           int start_measurement,
                           uint64_t intent_id,
                           uint64_t event_id,
                           uint32_t frame_id,
                           uint64_t sample_rate_hz,
                           int64_t center_frequency_hz,
                           uint16_t lower_shifted_bin,
                           uint16_t upper_shifted_bin,
                           const uint8_t *iq,
                           size_t iq_bytes,
                           const phase06j_frame_result_v1 *temporal,
                           p0_parameter_result_t *result);

/* Internal service path; arrays come from successful p0_pl_os_cfar_decode_with_weak. */
int p0_ed_pipeline_process_decoded_trusted(p0_ed_pipeline_t *, uint32_t, int, int,
    phase06j_frame_result_v1 *, size_t *);
#endif
