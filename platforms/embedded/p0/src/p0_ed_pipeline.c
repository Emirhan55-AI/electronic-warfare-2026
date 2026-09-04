#include "p0_ed_pipeline.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "p0_candidate_packet.h"
#include "p0_multiscale_detector.h"
#include "p0_pl_os_cfar.h"
#include "p0_persistent_weak.h"
#include "phase06i_transport_abi.h"

#define P0_FRAME_BINS PHASE06I_FFT_SIZE
#define P0_POWER_BYTES_PER_BIN 8U
#define P0_POWER_FRAME_BYTES (P0_FRAME_BINS * P0_POWER_BYTES_PER_BIN)

typedef struct {
    uint64_t high;
    uint64_t low;
} p0_u128_pair_t;

static p0_u128_pair_t weak_multiply_u64(uint64_t left, uint64_t right)
{
    const uint64_t mask = UINT64_C(0xffffffff);
    uint64_t left_low = left & mask;
    uint64_t left_high = left >> 32U;
    uint64_t right_low = right & mask;
    uint64_t right_high = right >> 32U;
    uint64_t low_product = left_low * right_low;
    uint64_t cross_left = left_low * right_high;
    uint64_t cross_right = left_high * right_low;
    uint64_t high_product = left_high * right_high;
    uint64_t middle = (low_product >> 32U) + (cross_left & mask) +
                      (cross_right & mask);
    p0_u128_pair_t product;

    product.low = (low_product & mask) | (middle << 32U);
    product.high = high_product + (cross_left >> 32U) +
                   (cross_right >> 32U) + (middle >> 32U);
    return product;
}

static int weak_ratio_better(const p0_weak_nomination_v1 *left,
                             const p0_weak_nomination_v1 *right)
{
    p0_u128_pair_t left_product;
    p0_u128_pair_t right_product;
    int left_infinite = left->peak_power != 0U && left->order_statistic == 0U;
    int right_infinite = right->peak_power != 0U && right->order_statistic == 0U;

    if (left_infinite != right_infinite)
        return left_infinite;
    left_product = weak_multiply_u64(left->peak_power,
                                     right->order_statistic);
    right_product = weak_multiply_u64(right->peak_power,
                                      left->order_statistic);
    if (left_product.high != right_product.high)
        return left_product.high > right_product.high;
    if (left_product.low != right_product.low)
        return left_product.low > right_product.low;
    if (left->peak_shifted_bin != right->peak_shifted_bin)
        return left->peak_shifted_bin < right->peak_shifted_bin;
    return left->start_shifted_bin < right->start_shifted_bin;
}

static void admit_weak_nomination(p0_weak_nomination_v1 *selected,
                                  uint16_t *selected_count,
                                  const p0_weak_nomination_v1 *candidate)
{
    uint16_t position = 0U;
    uint16_t count = *selected_count;

    while (position < count &&
           !weak_ratio_better(candidate, &selected[position]))
        ++position;
    if (position >= P0_WEAK_MAX_TRACKED_PER_FRAME)
        return;
    if (count < P0_WEAK_MAX_TRACKED_PER_FRAME)
        ++count;
    if (position + 1U < count) {
        memmove(&selected[position + 1U], &selected[position],
                (size_t)(count - position - 1U) * sizeof(*selected));
    }
    selected[position] = *candidate;
    *selected_count = count;
}

static void sort_weak_nominations_by_bin(p0_weak_nomination_v1 *selected,
                                         uint16_t count)
{
    uint16_t index;

    for (index = 1U; index < count; ++index) {
        p0_weak_nomination_v1 value = selected[index];
        uint16_t position = index;
        while (position != 0U &&
               selected[position - 1U].start_shifted_bin >
                   value.start_shifted_bin) {
            selected[position] = selected[position - 1U];
            --position;
        }
        selected[position] = value;
    }
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
    pipeline->candidate_records = calloc(PHASE06I_MAX_CANDIDATES,
                                         sizeof(*pipeline->candidate_records));
    pipeline->temporal_state = calloc(1U, phase06j_state_bytes());
    pipeline->temporal_backup = malloc(phase06j_state_bytes());
    pipeline->weak_state = calloc(1U, p0_persistent_weak_state_bytes());
    pipeline->weak_backup = malloc(p0_persistent_weak_state_bytes());
    pipeline->weak_nominations = calloc(P0_WEAK_MAX_NOMINATIONS,
                                        sizeof(*pipeline->weak_nominations));
    if (pipeline->power == NULL || pipeline->raw_power == NULL || pipeline->noise == NULL ||
        pipeline->threshold == NULL || pipeline->detections == NULL ||
        pipeline->candidates == NULL || pipeline->candidate_records == NULL ||
        pipeline->temporal_state == NULL || pipeline->temporal_backup == NULL ||
        pipeline->weak_state == NULL || pipeline->weak_backup == NULL ||
        pipeline->weak_nominations == NULL ||
        p0_os_cfar_canonical_config(&pipeline->config) != P0_OS_CFAR_OK ||
        phase06j_state_init(pipeline->temporal_state, phase06j_state_bytes()) != PHASE06J_OK ||
        p0_persistent_weak_init(pipeline->weak_state,
                                p0_persistent_weak_state_bytes()) != 0 ||
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
    free(pipeline->weak_nominations);
    free(pipeline->weak_backup);
    free(pipeline->weak_state);
    free(pipeline->temporal_backup);
    free(pipeline->temporal_state);
    free(pipeline->candidate_records);
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
    memset(&pipeline->previous_weak_result, 0, sizeof(pipeline->previous_weak_result));
    if (phase06j_state_reset(pipeline->temporal_state, phase06j_state_bytes()) != PHASE06J_OK)
        return -1;
    return p0_persistent_weak_init(pipeline->weak_state,
                                   p0_persistent_weak_state_bytes());
}

static int weak_candidates_overlap(
    const p0_persistent_weak_candidate_v1 *left,
    const p0_persistent_weak_candidate_v1 *right)
{
    return left->start_shifted_bin <= right->end_shifted_bin &&
           right->start_shifted_bin <= left->end_shifted_bin;
}

static void write_persistent_weak_event(
    phase06j_event_v1 *event, uint32_t frame_id,
    const p0_persistent_weak_candidate_v1 *source, uint8_t state,
    uint8_t observed_this_frame)
{
    memset(event, 0, sizeof(*event));
    event->event_id = UINT64_C(0x8000000000000000) | source->peak_shifted_bin;
    event->first_frame_id = frame_id >= (P0_WEAK_WINDOW_FRAMES - 1U)
                                ? frame_id - (P0_WEAK_WINDOW_FRAMES - 1U)
                                : 0U;
    event->last_seen_frame_id = frame_id;
    event->seen_count = source->observed_frames;
    event->state = state;
    event->observed_this_frame = observed_this_frame;
    event->candidate.start_shifted_bin = source->start_shifted_bin;
    event->candidate.end_shifted_bin = source->end_shifted_bin;
    event->candidate.peak_shifted_bin = source->peak_shifted_bin;
    event->candidate.coarse_span_bins =
        (uint16_t)(source->end_shifted_bin - source->start_shifted_bin + 1U);
    event->candidate.pfa_select = 1U;
    event->candidate.flags = PHASE06I_RECORD_VALID | PHASE06I_RECORD_WEAK_EVIDENCE;
    event->candidate.peak_power_uq28_30 = (uint64_t)source->mean_ratio_q8 << 22U;
    event->candidate.regional_noise_uq28_30 = UINT64_C(1) << 30U;
    event->candidate.threshold_uq32_30 = UINT64_C(4274643195);
}

static int append_persistent_weak(
    p0_ed_pipeline_t *pipeline, phase06j_frame_result_v1 *result,
    uint32_t frame_id, const p0_persistent_weak_result_v1 *weak)
{
    p0_persistent_weak_result_v1 emitted;
    uint8_t consumed[P0_WEAK_MAX_RESULTS] = {0};
    uint16_t index;
    memset(&emitted, 0, sizeof(emitted));

    while (emitted.count < P0_WEAK_MAX_EMITTED &&
           result->active_count < PHASE06J_MAX_ACTIVE_TRACKS) {
        const p0_persistent_weak_candidate_v1 *source = NULL;
        uint16_t selected_index = 0U;
        for (index = 0U; index < weak->count; ++index) {
            const p0_persistent_weak_candidate_v1 *candidate = &weak->candidates[index];
            uint16_t normal_index;
            int overlaps_normal = 0;
            if (consumed[index] != 0U)
                continue;
            for (normal_index = 0U; normal_index < result->active_count;
                 ++normal_index) {
                const phase06j_event_v1 *normal = &result->active[normal_index];
                if ((normal->candidate.flags & PHASE06I_RECORD_WEAK_EVIDENCE) == 0U &&
                    normal->state == PHASE06J_EVENT_CONFIRMED &&
                    normal->candidate.start_shifted_bin <= candidate->end_shifted_bin &&
                    candidate->start_shifted_bin <= normal->candidate.end_shifted_bin) {
                    overlaps_normal = 1;
                    break;
                }
            }
            if (overlaps_normal) {
                consumed[index] = 1U;
                continue;
            }
            if (source == NULL || candidate->mean_ratio_q8 > source->mean_ratio_q8 ||
                (candidate->mean_ratio_q8 == source->mean_ratio_q8 &&
                 candidate->observed_frames > source->observed_frames) ||
                (candidate->mean_ratio_q8 == source->mean_ratio_q8 &&
                 candidate->observed_frames == source->observed_frames &&
                 candidate->peak_shifted_bin < source->peak_shifted_bin)) {
                source = candidate;
                selected_index = index;
            }
        }
        if (source == NULL)
            break;
        consumed[selected_index] = 1U;
        {
        phase06j_event_v1 *event;
        event = &result->active[result->active_count++];
        write_persistent_weak_event(
            event, frame_id, source, PHASE06J_EVENT_CONFIRMED, 1U);
        if (emitted.count >= P0_WEAK_MAX_RESULTS)
            return -1;
        emitted.candidates[emitted.count++] = *source;
        }
    }
    for (index = 0U; index < pipeline->previous_weak_result.count; ++index) {
        const p0_persistent_weak_candidate_v1 *previous =
            &pipeline->previous_weak_result.candidates[index];
        uint16_t current_index;
        int remains_active = 0;
        for (current_index = 0U; current_index < emitted.count; ++current_index) {
            if (weak_candidates_overlap(previous, &emitted.candidates[current_index])) {
                remains_active = 1;
                break;
            }
        }
        if (!remains_active) {
            if (result->ended_count >= PHASE06J_MAX_ACTIVE_TRACKS)
                return -1;
            write_persistent_weak_event(
                &result->ended[result->ended_count++], frame_id, previous,
                PHASE06J_EVENT_ENDED, 0U);
        }
    }
    pipeline->previous_weak_result = emitted;
    return 0;
}

int p0_ed_pipeline_process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count)
{
    size_t candidate_count = 0U;
    size_t recovery_count = 0U;
    int pl_decisions_present = 0;
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
    code = p0_pl_os_cfar_decode(natural_power, power_bytes, pipeline->raw_power,
                                pipeline->power, pipeline->detections,
                                &pl_decisions_present);
    if (code != P0_PL_OS_CFAR_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    if (pl_decisions_present) {
        code = p0_multiscale_process_pl_trusted(
            pipeline->power, P0_FRAME_BINS, &pipeline->config,
            pipeline->detections, pipeline->noise, pipeline->threshold,
            pipeline->candidates, PHASE06I_MAX_CANDIDATES,
            &candidate_count, &recovery_count);
    } else {
        code = p0_multiscale_process(
            pipeline->power, P0_FRAME_BINS, &pipeline->config,
            pipeline->detections, pipeline->noise, pipeline->threshold,
            pipeline->candidates, PHASE06I_MAX_CANDIDATES,
            &candidate_count, &recovery_count);
    }
    if (code != P0_MULTISCALE_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    code = p0_candidate_records_encode(
        pipeline->raw_power, P0_FRAME_BINS, &pipeline->config,
        pipeline->candidates, candidate_count, pipeline->candidate_records,
        PHASE06I_MAX_CANDIDATES);
    if (code != P0_CANDIDATE_PACKET_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    code = phase06j_process_candidates(
        pipeline->temporal_state, phase06j_state_bytes(), frame_id,
        pipeline->candidate_records, (uint16_t)candidate_count, result);
    if (code != PHASE06J_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        errno = EPROTO;
        return -1;
    }
    *raw_candidate_count = candidate_count;
    return 0;
}

int p0_ed_pipeline_process_packet(p0_ed_pipeline_t *pipeline, int reset_requested,
                                  const uint8_t *packet, size_t packet_bytes,
                                  phase06j_frame_result_v1 *result,
                                  size_t *raw_candidate_count,
                                  uint32_t *packet_frame_id)
{
    uint32_t decoded_frame_id = 0U;
    uint16_t candidate_count = 0U;
    uint16_t normal_count = 0U;
    uint16_t weak_count = 0U;
    uint16_t index;
    p0_persistent_weak_result_v1 weak_result;
    p0_persistent_weak_result_v1 previous_weak_backup;
    int code;

    if (pipeline == NULL || pipeline->temporal_state == NULL ||
        pipeline->temporal_backup == NULL || packet == NULL || result == NULL ||
        raw_candidate_count == NULL || packet_frame_id == NULL) {
        errno = EINVAL;
        return -1;
    }
    code = phase06j_decode_packet_records(
        packet, packet_bytes, &decoded_frame_id, pipeline->candidate_records,
        PHASE06I_MAX_CANDIDATES, &candidate_count);
    if (code != PHASE06J_OK) {
        errno = EPROTO;
        return -1;
    }
    memcpy(pipeline->temporal_backup, pipeline->temporal_state, phase06j_state_bytes());
    memcpy(pipeline->weak_backup, pipeline->weak_state,
           p0_persistent_weak_state_bytes());
    previous_weak_backup = pipeline->previous_weak_result;
    if (reset_requested && p0_ed_pipeline_reset(pipeline) != 0) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        memcpy(pipeline->weak_state, pipeline->weak_backup,
               p0_persistent_weak_state_bytes());
        pipeline->previous_weak_result = previous_weak_backup;
        return -1;
    }
    for (index = 0U; index < candidate_count; ++index) {
        phase06i_candidate_v1 record = pipeline->candidate_records[index];
        if ((record.flags & PHASE06I_RECORD_WEAK_EVIDENCE) != 0U &&
            (record.flags & PHASE06I_RECORD_SINGLE_FRAME_CONFIDENT) == 0U) {
            p0_weak_nomination_v1 nomination;
            nomination.start_shifted_bin = record.start_shifted_bin;
            nomination.end_shifted_bin = record.end_shifted_bin;
            nomination.peak_shifted_bin = record.peak_shifted_bin;
            nomination.reserved = 0U;
            nomination.peak_power = record.peak_power_uq28_30;
            nomination.order_statistic = record.regional_noise_uq28_30;
            admit_weak_nomination(pipeline->weak_nominations, &weak_count,
                                  &nomination);
        }
        if ((record.flags & PHASE06I_RECORD_WEAK_EVIDENCE) == 0U ||
            (record.flags & PHASE06I_RECORD_SINGLE_FRAME_CONFIDENT) != 0U) {
            pipeline->candidate_records[normal_count++] = record;
        }
    }
    if (index != candidate_count) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        memcpy(pipeline->weak_state, pipeline->weak_backup,
               p0_persistent_weak_state_bytes());
        pipeline->previous_weak_result = previous_weak_backup;
        errno = EOVERFLOW;
        return -1;
    }
    sort_weak_nominations_by_bin(pipeline->weak_nominations, weak_count);
    code = phase06j_process_candidates(
        pipeline->temporal_state, phase06j_state_bytes(), decoded_frame_id,
        pipeline->candidate_records, normal_count, result);
    if (code != PHASE06J_OK) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        memcpy(pipeline->weak_state, pipeline->weak_backup,
               p0_persistent_weak_state_bytes());
        pipeline->previous_weak_result = previous_weak_backup;
        errno = EPROTO;
        return -1;
    }
    if (result->reset_applied != 0U) {
        if (p0_persistent_weak_init(pipeline->weak_state,
                                    p0_persistent_weak_state_bytes()) != 0) {
            memcpy(pipeline->temporal_state, pipeline->temporal_backup,
                   phase06j_state_bytes());
            memcpy(pipeline->weak_state, pipeline->weak_backup,
                   p0_persistent_weak_state_bytes());
            pipeline->previous_weak_result = previous_weak_backup;
            errno = EPROTO;
            return -1;
        }
        memset(&pipeline->previous_weak_result, 0,
               sizeof(pipeline->previous_weak_result));
    }
    code = p0_persistent_weak_update(
        pipeline->weak_state, p0_persistent_weak_state_bytes(),
        pipeline->weak_nominations, weak_count, &weak_result);
    if (code != 0 || append_persistent_weak(
                         pipeline, result, decoded_frame_id, &weak_result) != 0) {
        memcpy(pipeline->temporal_state, pipeline->temporal_backup, phase06j_state_bytes());
        memcpy(pipeline->weak_state, pipeline->weak_backup,
               p0_persistent_weak_state_bytes());
        pipeline->previous_weak_result = previous_weak_backup;
        errno = EPROTO;
        return -1;
    }
    *raw_candidate_count = candidate_count;
    *packet_frame_id = decoded_frame_id;
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
    if (p0_parameter_power_from_ci8(iq, iq_bytes, pipeline->raw_power,
                                    P0_FRAME_BINS) != 0)
        return -1;
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
