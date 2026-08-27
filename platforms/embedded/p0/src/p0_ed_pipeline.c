#include "p0_ed_pipeline.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "p0_candidate_packet.h"
#include "phase06i_transport_abi.h"

#define P0_FRAME_BINS PHASE06I_FFT_SIZE
#define P0_POWER_BYTES_PER_BIN 8U
#define P0_POWER_FRAME_BYTES (P0_FRAME_BINS * P0_POWER_BYTES_PER_BIN)
#define P0_POWER_FRACTION_BITS 30U

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value = 0U;
    unsigned int index;

    for (index = 0U; index < P0_POWER_BYTES_PER_BIN; ++index)
        value |= (uint64_t)source[index] << (index * 8U);
    return value;
}

int p0_ed_pipeline_init(p0_ed_pipeline_t *pipeline)
{
    if (pipeline == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(pipeline, 0, sizeof(*pipeline));
    pipeline->power = calloc(P0_FRAME_BINS, sizeof(*pipeline->power));
    pipeline->raw_power = calloc(P0_FRAME_BINS, sizeof(*pipeline->raw_power));
    pipeline->noise = calloc(P0_FRAME_BINS, sizeof(*pipeline->noise));
    pipeline->threshold = calloc(P0_FRAME_BINS, sizeof(*pipeline->threshold));
    pipeline->detections = calloc(P0_FRAME_BINS, sizeof(*pipeline->detections));
    pipeline->candidates = calloc(PHASE06I_MAX_CANDIDATES, sizeof(*pipeline->candidates));
    pipeline->packet = malloc(PHASE06I_MAX_FRAME_BYTES);
    pipeline->temporal_state = calloc(1U, phase06j_state_bytes());
    pipeline->temporal_backup = malloc(phase06j_state_bytes());
    if (pipeline->power == NULL || pipeline->raw_power == NULL || pipeline->noise == NULL ||
        pipeline->threshold == NULL || pipeline->detections == NULL ||
        pipeline->candidates == NULL || pipeline->packet == NULL ||
        pipeline->temporal_state == NULL || pipeline->temporal_backup == NULL ||
        p0_os_cfar_canonical_config(&pipeline->config) != P0_OS_CFAR_OK ||
        phase06j_state_init(pipeline->temporal_state, phase06j_state_bytes()) != PHASE06J_OK ||
        p0_parameter_runtime_init(&pipeline->parameter_runtime) != 0) {
        p0_ed_pipeline_release(pipeline);
        errno = ENOMEM;
        return -1;
    }
    return 0;
}

void p0_ed_pipeline_release(p0_ed_pipeline_t *pipeline)
{
    if (pipeline == NULL)
        return;
    p0_parameter_runtime_release(&pipeline->parameter_runtime);
    free(pipeline->temporal_backup);
    free(pipeline->temporal_state);
    free(pipeline->packet);
    free(pipeline->candidates);
    free(pipeline->detections);
    free(pipeline->threshold);
    free(pipeline->noise);
    free(pipeline->raw_power);
    free(pipeline->power);
    memset(pipeline, 0, sizeof(*pipeline));
}

int p0_ed_pipeline_reset(p0_ed_pipeline_t *pipeline)
{
    if (pipeline == NULL || pipeline->temporal_state == NULL) {
        errno = EINVAL;
        return -1;
    }
    p0_parameter_runtime_reset(&pipeline->parameter_runtime);
    return phase06j_state_reset(pipeline->temporal_state, phase06j_state_bytes()) == PHASE06J_OK
               ? 0 : -1;
}

int p0_ed_pipeline_process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count)
{
    size_t natural_bin;
    size_t candidate_count = 0U;
    size_t packet_bytes = 0U;
    int code;

    if (pipeline == NULL || pipeline->temporal_state == NULL ||
        pipeline->temporal_backup == NULL || natural_power == NULL || result == NULL ||
        raw_candidate_count == NULL || power_bytes != P0_POWER_FRAME_BYTES) {
        errno = EINVAL;
        return -1;
    }
    memcpy(pipeline->temporal_backup, pipeline->temporal_state, phase06j_state_bytes());
    if (reset_requested && p0_ed_pipeline_reset(pipeline) != 0) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        return -1;
    }
    for (natural_bin = 0U; natural_bin < P0_FRAME_BINS; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (P0_FRAME_BINS / 2U);
        uint64_t raw = load_u64_le(natural_power + natural_bin * P0_POWER_BYTES_PER_BIN);

        if (raw >= (UINT64_C(1) << 58)) {
            memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
            errno = ERANGE;
            return -1;
        }
        pipeline->raw_power[shifted_bin] = raw;
        pipeline->power[shifted_bin] =
            (double)raw / (double)(UINT64_C(1) << P0_POWER_FRACTION_BITS);
    }
    code = p0_os_cfar_process(pipeline->power, P0_FRAME_BINS, &pipeline->config,
                              pipeline->detections, pipeline->noise, pipeline->threshold,
                              pipeline->candidates, PHASE06I_MAX_CANDIDATES,
                              &candidate_count);
    if (code != P0_OS_CFAR_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    code = p0_candidate_packet_encode(frame_id, pipeline->raw_power, P0_FRAME_BINS,
                                      &pipeline->config, pipeline->candidates, candidate_count,
                                      pipeline->packet, PHASE06I_MAX_FRAME_BYTES, &packet_bytes);
    if (code != P0_CANDIDATE_PACKET_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    code = phase06j_process_packet(pipeline->temporal_state, phase06j_state_bytes(),
                                   pipeline->packet, packet_bytes, result);
    if (code != PHASE06J_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    *raw_candidate_count = candidate_count;
    return 0;
}

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
                           p0_parameter_result_t *result)
{
    uint16_t index;
    unsigned int protected_lower;
    unsigned int protected_upper;
    int confirmed_and_observed = 0;

    if (pipeline == NULL || iq == NULL || temporal == NULL || result == NULL) {
        errno = EINVAL;
        return -1;
    }
    protected_lower = lower_shifted_bin >= P0_PARAMETER_LOCAL_PADDING
                          ? lower_shifted_bin - P0_PARAMETER_LOCAL_PADDING
                          : 0U;
    protected_upper = (unsigned int)upper_shifted_bin + P0_PARAMETER_LOCAL_PADDING;
    if (protected_upper >= P0_FRAME_BINS)
        protected_upper = P0_FRAME_BINS - 1U;
    for (index = 0U; index < temporal->active_count; ++index) {
        const phase06j_event_v1 *event = &temporal->active[index];

        if (event->event_id == event_id && event->state == PHASE06J_EVENT_CONFIRMED &&
            event->observed_this_frame != 0U &&
            event->candidate.peak_shifted_bin >= lower_shifted_bin &&
            event->candidate.peak_shifted_bin <= upper_shifted_bin) {
            confirmed_and_observed = 1;
        } else if (event->event_id != event_id &&
                   event->state == PHASE06J_EVENT_CONFIRMED &&
                   event->candidate.start_shifted_bin <= protected_upper &&
                   event->candidate.end_shifted_bin >= protected_lower) {
            confirmed_and_observed = 0;
            break;
        }
    }
    return p0_parameter_runtime_observe(
        &pipeline->parameter_runtime, start_measurement, intent_id, event_id, frame_id,
        sample_rate_hz, center_frequency_hz, lower_shifted_bin, upper_shifted_bin,
        confirmed_and_observed, iq, iq_bytes, pipeline->raw_power, P0_FRAME_BINS, result);
}
