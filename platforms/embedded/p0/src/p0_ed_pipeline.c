#include "p0_ed_pipeline.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#ifdef P0_ED_PIPELINE_PROFILE
#include <inttypes.h>
#include <stdio.h>
#include <time.h>
#endif

#include "p0_candidate_packet.h"
#include "p0_multiscale_detector.h"
#include "p0_pl_os_cfar.h"
#include "p0_persistent_weak.h"
#include "phase06i_transport_abi.h"

#define P0_FRAME_BINS PHASE06I_FFT_SIZE
#define P0_POWER_BYTES_PER_BIN 8U
#define P0_POWER_FRAME_BYTES (P0_FRAME_BINS * P0_POWER_BYTES_PER_BIN)

#ifdef P0_ED_PIPELINE_PROFILE
enum {
    P0_PROFILE_CHECKPOINT,
    P0_PROFILE_WEAK_COLLECT,
    P0_PROFILE_GROUP,
    P0_PROFILE_WIDEBAND,
    P0_PROFILE_ENCODE,
    P0_PROFILE_TEMPORAL,
    P0_PROFILE_WEAK_STATE,
    P0_PROFILE_FINALIZE,
    P0_PROFILE_STAGE_COUNT
};

static uint64_t pipeline_profile_totals[P0_PROFILE_STAGE_COUNT];
static uint64_t pipeline_profile_frames;

static uint64_t pipeline_profile_now(void)
{
    struct timespec value;

    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0)
        return 0U;
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

static void pipeline_profile_record(const uint64_t *marks)
{
    static const char *const names[P0_PROFILE_STAGE_COUNT] = {
        "checkpoint", "weak_collect", "group", "wideband", "encode",
        "temporal", "weak_state", "finalize"
    };
    size_t index;

    for (index = 0U; index < P0_PROFILE_STAGE_COUNT; ++index)
        pipeline_profile_totals[index] += marks[index + 1U] - marks[index];
    ++pipeline_profile_frames;
    if (pipeline_profile_frames % UINT64_C(4096) != 0U)
        return;
    fprintf(stderr, "{\"schema\":\"p0-ed-pipeline-profile-v1\",\"frames\":%" PRIu64,
            pipeline_profile_frames);
    for (index = 0U; index < P0_PROFILE_STAGE_COUNT; ++index) {
        fprintf(stderr, ",\"%s_mean_ms\":%.9f", names[index],
                (double)pipeline_profile_totals[index] /
                    (double)pipeline_profile_frames / 1000000.0);
    }
    fputs("}\n", stderr);
}
#endif

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

static int regions_overlap(const p0_candidate_region_t *narrow,
                           const p0_st05_candidate_t *wide)
{
    return narrow->start_bin <= wide->end_bin &&
           wide->start_bin <= narrow->end_bin;
}

static int narrow_overlaps_wideband(
    const p0_candidate_region_t *narrow,
    const p0_st05_result_t *wideband)
{
    uint32_t index;

    for (index = 0U; index < wideband->candidate_count; ++index) {
        if (regions_overlap(narrow, &wideband->candidates[index]))
            return 1;
    }
    return 0;
}

static int append_wideband_candidates(
    p0_ed_pipeline_t *pipeline,
    const p0_st05_result_t *wideband,
    size_t *candidate_count,
    size_t *first_wideband,
    uint16_t *dropped_narrow)
{
    size_t read_index;
    size_t write_index = 0U;
    uint32_t wide_index;

    if (wideband->candidate_count > PHASE06I_MAX_CANDIDATES)
        return -1;
    for (read_index = 0U; read_index < *candidate_count; ++read_index) {
        if (!narrow_overlaps_wideband(&pipeline->candidates[read_index], wideband))
            pipeline->candidates[write_index++] = pipeline->candidates[read_index];
    }
    while (write_index + wideband->candidate_count > PHASE06I_MAX_CANDIDATES) {
        size_t weakest = 0U;
        double weakest_ratio;

        if (write_index == 0U)
            return -1;
        weakest_ratio = pipeline->candidates[0].noise_power_per_bin > 0.0
                            ? pipeline->candidates[0].peak_power /
                                  pipeline->candidates[0].noise_power_per_bin
                            : pipeline->candidates[0].peak_power;
        for (read_index = 1U; read_index < write_index; ++read_index) {
            double ratio = pipeline->candidates[read_index].noise_power_per_bin > 0.0
                               ? pipeline->candidates[read_index].peak_power /
                                     pipeline->candidates[read_index].noise_power_per_bin
                               : pipeline->candidates[read_index].peak_power;
            if (ratio < weakest_ratio) {
                weakest = read_index;
                weakest_ratio = ratio;
            }
        }
        memmove(&pipeline->candidates[weakest],
                &pipeline->candidates[weakest + 1U],
                (write_index - weakest - 1U) * sizeof(*pipeline->candidates));
        --write_index;
        if (*dropped_narrow != UINT16_MAX)
            ++*dropped_narrow;
    }
    *first_wideband = write_index;
    for (wide_index = 0U; wide_index < wideband->candidate_count; ++wide_index) {
        const p0_st05_candidate_t *source = &wideband->candidates[wide_index];
        p0_candidate_region_t *target = &pipeline->candidates[write_index++];

        target->start_bin = source->start_bin;
        target->end_bin = source->end_bin;
        target->peak_bin = source->peak_bin;
        target->peak_power = source->peak_power;
        target->noise_power_per_bin = source->reference_power_per_bin;
        target->threshold_power = source->threshold_power_per_bin;
    }
    *candidate_count = write_index;
    return 0;
}

static int rounded_uq30(double value, unsigned int width, uint64_t *encoded)
{
    double scaled = value * (double)(UINT64_C(1) << 30U);

    if (encoded == NULL || !isfinite(scaled) || scaled < 0.0 || width > 63U ||
        scaled >= (double)(UINT64_C(1) << width))
        return -1;
    *encoded = (uint64_t)floor(scaled + 0.5);
    return 0;
}

static int mark_wideband_records(
    p0_ed_pipeline_t *pipeline,
    const p0_st05_result_t *wideband,
    size_t first_wideband)
{
    uint32_t index;

    for (index = 0U; index < wideband->candidate_count; ++index) {
        phase06i_candidate_v1 *record =
            &pipeline->candidate_records[first_wideband + index];
        uint64_t peak_power;
        uint64_t noise_power;
        uint64_t threshold_power;

        if (rounded_uq30(wideband->candidates[index].peak_power, 58U,
                         &peak_power) != 0 ||
            rounded_uq30(wideband->candidates[index].reference_power_per_bin,
                         58U, &noise_power) != 0 ||
            rounded_uq30(wideband->candidates[index].threshold_power_per_bin,
                         62U, &threshold_power) != 0)
            return -1;
        record->pfa_select = 0U;
        record->flags |= PHASE06I_RECORD_WIDEBAND_EVIDENCE;
        record->peak_power_uq28_30 = peak_power;
        record->regional_noise_uq28_30 = noise_power;
        record->threshold_uq32_30 = threshold_power;
    }
    return 0;
}

int p0_ed_pipeline_init(p0_ed_pipeline_t *pipeline)
{
    if (pipeline == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(pipeline, 0, sizeof(*pipeline));
    pipeline->weak_alpha_q32 = UINT64_C(17098572778);
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
    pipeline->wideband_stream_state_bytes = p0_st05_stream_state_bytes();
    pipeline->wideband_stream_state =
        calloc(1U, pipeline->wideband_stream_state_bytes);
    pipeline->wideband_stream_backup =
        malloc(pipeline->wideband_stream_state_bytes);
    if (pipeline->power == NULL || pipeline->raw_power == NULL || pipeline->noise == NULL ||
        pipeline->threshold == NULL || pipeline->detections == NULL ||
        pipeline->candidates == NULL || pipeline->candidate_records == NULL ||
        pipeline->temporal_state == NULL || pipeline->temporal_backup == NULL ||
        pipeline->weak_state == NULL || pipeline->weak_backup == NULL ||
        pipeline->weak_nominations == NULL || pipeline->wideband_stream_state == NULL ||
        pipeline->wideband_stream_backup == NULL ||
        p0_os_cfar_canonical_config(&pipeline->config) != P0_OS_CFAR_OK ||
        phase06j_state_init(pipeline->temporal_state, phase06j_state_bytes()) != PHASE06J_OK ||
        p0_persistent_weak_init(pipeline->weak_state,
                                p0_persistent_weak_state_bytes()) != 0 ||
        p0_st05_stream_init(pipeline->wideband_stream_state,
                            pipeline->wideband_stream_state_bytes) != P0_ST05_OK ||
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
    free(pipeline->wideband_stream_backup);
    free(pipeline->wideband_stream_state);
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
    if (pipeline == NULL || pipeline->temporal_state == NULL ||
        pipeline->wideband_stream_state == NULL) {
        errno = EINVAL;
        return -1;
    }
    p0_parameter_runtime_reset(&pipeline->parameter_runtime);
    memset(&pipeline->previous_weak_result, 0, sizeof(pipeline->previous_weak_result));
    pipeline->wideband_last_frame_id = 0U;
    pipeline->wideband_has_frame_id = 0;
    if (phase06j_state_reset(pipeline->temporal_state, phase06j_state_bytes()) != PHASE06J_OK)
        return -1;
    if (p0_persistent_weak_init(pipeline->weak_state,
                                p0_persistent_weak_state_bytes()) != 0)
        return -1;
    return p0_st05_stream_reset(pipeline->wideband_stream_state,
                                pipeline->wideband_stream_state_bytes) == P0_ST05_OK
               ? 0 : -1;
}

static int weak_candidates_overlap(
    const p0_persistent_weak_candidate_v1 *left,
    const p0_persistent_weak_candidate_v1 *right);

int p0_ed_pipeline_set_cfar(p0_ed_pipeline_t *pipeline, uint64_t alpha_q32,
                            uint64_t weak_alpha_q32)
{
    if (pipeline == NULL || alpha_q32 < (UINT64_C(1) << 32) ||
        alpha_q32 >= (UINT64_C(1) << 36) || weak_alpha_q32 < (UINT64_C(1) << 32) ||
        weak_alpha_q32 >= (UINT64_C(1) << 34) || weak_alpha_q32 > alpha_q32) {
        errno = EINVAL;
        return -1;
    }
    if (p0_ed_pipeline_reset(pipeline) != 0) return -1;
    pipeline->custom_cfar_profile = alpha_q32 != UINT64_C(36851433755) ||
                                    weak_alpha_q32 != UINT64_C(17098572778);
    if (!pipeline->custom_cfar_profile) {
        // Preserve the original floating reference coefficient exactly.
        if (p0_os_cfar_canonical_config(&pipeline->config) != 0) return -1;
    } else {
        pipeline->config.threshold_coefficient = (double)alpha_q32 / 4294967296.0;
    }
    pipeline->weak_alpha_q32 = weak_alpha_q32;
    return 0;
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

static uint64_t power_rank24(const uint64_t *power, uint32_t peak)
{
    uint64_t references[32];
    uint32_t source, length = 0U;
    for (source = peak - 20U; source <= peak + 20U; ++source) {
        uint32_t position;
        uint64_t value;
        if (source >= peak - 4U && source <= peak + 4U) continue;
        value = power[source];
        position = length++;
        while (position != 0U && references[position - 1U] > value) {
            references[position] = references[position - 1U];
            --position;
        }
        references[position] = value;
    }
    return references[23];
}

/* Consume PL weak metadata before the ordinary grouping path sees its bool mask.
 * Rank work is limited to nominated region peaks; the PL still decides all cells. */
static uint16_t collect_power_weak(p0_ed_pipeline_t *pipeline)
{
    uint16_t count = 0U;
    uint32_t index;

    for (index = 0U; index < 20U; ++index)
        pipeline->detections[index] &= 1U;
    while (index < P0_FRAME_BINS - 20U) {
        uint32_t start, end, peak;
        p0_weak_nomination_v1 nomination;
        if (pipeline->detections[index] != 2U) {
            pipeline->detections[index] &= 1U;
            ++index;
            continue;
        }
        start = end = peak = index++;
        pipeline->detections[start] &= 1U;
        while (index < P0_FRAME_BINS - 20U && index - end <= 2U) {
            uint8_t detection = pipeline->detections[index];
            pipeline->detections[index] &= 1U;
            if (detection == 2U) {
                end = index;
                if (pipeline->raw_power[index] > pipeline->raw_power[peak]) peak = index;
            }
            ++index;
        }
        nomination.start_shifted_bin = (uint16_t)start;
        nomination.end_shifted_bin = (uint16_t)end;
        nomination.peak_shifted_bin = (uint16_t)peak;
        nomination.reserved = 0U;
        nomination.peak_power = pipeline->raw_power[peak];
        nomination.order_statistic = power_rank24(pipeline->raw_power, peak);
        admit_weak_nomination(pipeline->weak_nominations, &count, &nomination);
    }
    for (; index < P0_FRAME_BINS; ++index)
        pipeline->detections[index] &= 1U;
    sort_weak_nominations_by_bin(pipeline->weak_nominations, count);
    return count;
}

static int process_power(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count, int decoded)
{
    size_t candidate_count = 0U;
    size_t first_wideband = 0U;
    uint16_t dropped_narrow = 0U;
    p0_st05_result_t wideband;
    int wideband_valid = 0;
    int pl_decisions_present = 0;
    int context_reset;
    uint32_t previous_frame_id;
    int previous_has_frame_id;
    int code;
    uint16_t weak_count;
    int weak_checkpoint_saved = 0;
    p0_persistent_weak_result_v1 weak_result;
    p0_persistent_weak_result_v1 previous_weak_backup;
#ifdef P0_ED_PIPELINE_PROFILE
    uint64_t profile_marks[P0_PROFILE_STAGE_COUNT + 1U];
#endif

    if (pipeline == NULL || pipeline->temporal_state == NULL ||
        pipeline->temporal_backup == NULL || pipeline->wideband_stream_state == NULL ||
        pipeline->wideband_stream_backup == NULL || natural_power == NULL ||
        result == NULL || raw_candidate_count == NULL ||
        power_bytes != P0_POWER_FRAME_BYTES) {
        errno = EINVAL;
        return -1;
    }
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[0] = pipeline_profile_now();
#endif
    previous_frame_id = pipeline->wideband_last_frame_id;
    previous_has_frame_id = pipeline->wideband_has_frame_id;
    context_reset = reset_requested ||
                    (pipeline->wideband_has_frame_id &&
                     frame_id != pipeline->wideband_last_frame_id + UINT32_C(1));
    memcpy(pipeline->temporal_backup, pipeline->temporal_state, phase06j_state_bytes());
    if (context_reset)
        memcpy(pipeline->weak_backup, pipeline->weak_state, p0_persistent_weak_state_bytes());
    previous_weak_backup = pipeline->previous_weak_result;
    if (context_reset) {
        memcpy(pipeline->wideband_stream_backup, pipeline->wideband_stream_state,
               pipeline->wideband_stream_state_bytes);
    } else if (p0_st05_stream_checkpoint_save(
                   pipeline->wideband_stream_state, pipeline->wideband_stream_state_bytes,
                   pipeline->wideband_stream_backup,
                   pipeline->wideband_stream_state_bytes) != P0_ST05_OK) {
        errno = EPROTO;
        return -1;
    }
    if (context_reset && p0_ed_pipeline_reset(pipeline) != 0)
        goto rollback;
    if (decoded < 0) {
    code = p0_pl_os_cfar_decode_with_weak(natural_power, power_bytes, pipeline->raw_power,
                                pipeline->power, pipeline->detections,
                                &pl_decisions_present);
    if (code != P0_PL_OS_CFAR_OK)
        goto protocol_error;
    } else {
        pl_decisions_present = decoded;
    }
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[1] = pipeline_profile_now();
#endif
    weak_count = collect_power_weak(pipeline);
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[2] = pipeline_profile_now();
#endif
    if (pl_decisions_present) {
        code = p0_os_cfar_group_detections_trusted(
            pipeline->power, P0_FRAME_BINS, &pipeline->config,
            pipeline->detections, pipeline->noise, pipeline->threshold,
            pipeline->candidates, PHASE06I_MAX_CANDIDATES,
            &candidate_count);
    } else {
        code = p0_os_cfar_process(
            pipeline->power, P0_FRAME_BINS, &pipeline->config,
            pipeline->detections, pipeline->noise, pipeline->threshold,
            pipeline->candidates, PHASE06I_MAX_CANDIDATES,
            &candidate_count);
    }
    if (code != P0_OS_CFAR_OK)
        goto protocol_error;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[3] = pipeline_profile_now();
#endif
    code = p0_st05_stream_update_trusted(
        pipeline->wideband_stream_state, pipeline->wideband_stream_state_bytes,
        pipeline->power, P0_FRAME_BINS, &wideband, &wideband_valid);
    if (code != P0_ST05_OK)
        goto protocol_error;
    if (wideband_valid && wideband.candidate_count != 0U) {
        if (append_wideband_candidates(
                pipeline, &wideband, &candidate_count, &first_wideband,
                &dropped_narrow) != 0)
            goto protocol_error;
    } else {
        first_wideband = candidate_count;
    }
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[4] = pipeline_profile_now();
#endif
    code = p0_candidate_records_encode(
        pipeline->raw_power, P0_FRAME_BINS, &pipeline->config,
        pipeline->candidates, candidate_count, pipeline->candidate_records,
        PHASE06I_MAX_CANDIDATES);
    if (code != P0_CANDIDATE_PACKET_OK)
        goto protocol_error;
    if (pipeline->custom_cfar_profile) {
        size_t custom_index;
        for (custom_index = 0; custom_index < candidate_count; ++custom_index)
            pipeline->candidate_records[custom_index].pfa_select = 3U;
    }
    if (wideband_valid && wideband.candidate_count != 0U &&
        mark_wideband_records(pipeline, &wideband, first_wideband) != 0)
        goto protocol_error;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[5] = pipeline_profile_now();
#endif
    code = phase06j_process_candidates(
        pipeline->temporal_state, phase06j_state_bytes(), frame_id,
        pipeline->candidate_records, (uint16_t)candidate_count, result);
    if (code != PHASE06J_OK)
        goto protocol_error;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[6] = pipeline_profile_now();
#endif
    if (!context_reset) {
        if (p0_persistent_weak_checkpoint_save(pipeline->weak_state,
                p0_persistent_weak_state_bytes(), pipeline->weak_nominations, weak_count,
                pipeline->weak_backup, p0_persistent_weak_state_bytes()) != 0)
            goto protocol_error;
        weak_checkpoint_saved = 1;
    }
    code = p0_persistent_weak_update(
        pipeline->weak_state, p0_persistent_weak_state_bytes(),
        pipeline->weak_nominations, weak_count, &weak_result);
    if (code != 0 || append_persistent_weak(pipeline, result, frame_id, &weak_result) != 0)
        goto protocol_error;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[7] = pipeline_profile_now();
#endif
    {
        uint16_t event_index;
        for (event_index = 0; event_index < result->active_count + result->ended_count; ++event_index) {
            phase06j_event_v1 *event = event_index < result->active_count
                ? &result->active[event_index] : &result->ended[event_index - result->active_count];
            uint32_t peak = event->candidate.peak_shifted_bin;
            uint64_t rank;
            p0_u128_pair_t threshold;
            int age;
            if (!(event->candidate.flags & PHASE06I_RECORD_WEAK_EVIDENCE)) continue;
            age = p0_persistent_weak_last_seen_age(pipeline->weak_state,
                p0_persistent_weak_state_bytes(), (uint16_t)peak);
            if (age < 0 || peak < 20U || peak >= P0_FRAME_BINS - 20U) goto protocol_error;
            event->observed_this_frame = event_index < result->active_count && age == 0;
            event->last_seen_frame_id = frame_id - (uint32_t)age;
            /* Current measured power, never a ratio masquerading as absolute power. */
            rank = power_rank24(pipeline->raw_power, peak);
            threshold = weak_multiply_u64(rank, pipeline->weak_alpha_q32);
            if (pipeline->custom_cfar_profile) event->candidate.pfa_select = 3U;
            event->candidate.peak_power_uq28_30 = pipeline->raw_power[peak];
            event->candidate.regional_noise_uq28_30 = rank;
            event->candidate.threshold_uq32_30 = (threshold.high << 32U) | (threshold.low >> 32U);
        }
    }
    if ((uint32_t)result->dropped_candidates + dropped_narrow > UINT16_MAX)
        result->dropped_candidates = UINT16_MAX;
    else
        result->dropped_candidates =
            (uint16_t)(result->dropped_candidates + dropped_narrow);
    if (context_reset)
        result->reset_applied = 1U;
    pipeline->wideband_last_frame_id = frame_id;
    pipeline->wideband_has_frame_id = 1;
    *raw_candidate_count = candidate_count + weak_count;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[8] = pipeline_profile_now();
    pipeline_profile_record(profile_marks);
#endif
    return 0;

protocol_error:
    errno = EPROTO;
rollback:
    if (context_reset)
        memcpy(pipeline->weak_state, pipeline->weak_backup, p0_persistent_weak_state_bytes());
    else if (weak_checkpoint_saved)
        (void)p0_persistent_weak_checkpoint_restore(pipeline->weak_state,
            p0_persistent_weak_state_bytes(), pipeline->weak_backup, p0_persistent_weak_state_bytes());
    pipeline->previous_weak_result = previous_weak_backup;
    memcpy(pipeline->temporal_state, pipeline->temporal_backup,
           phase06j_state_bytes());
    if (context_reset) {
        memcpy(pipeline->wideband_stream_state, pipeline->wideband_stream_backup,
               pipeline->wideband_stream_state_bytes);
    } else {
        (void)p0_st05_stream_checkpoint_restore(
            pipeline->wideband_stream_state, pipeline->wideband_stream_state_bytes,
            pipeline->wideband_stream_backup, pipeline->wideband_stream_state_bytes);
    }
    pipeline->wideband_last_frame_id = previous_frame_id;
    pipeline->wideband_has_frame_id = previous_has_frame_id;
    return -1;
}

int p0_ed_pipeline_process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset_requested,
                           const uint8_t *natural_power, size_t power_bytes,
                           phase06j_frame_result_v1 *result, size_t *raw_candidate_count)
{
    return process_power(pipeline, frame_id, reset_requested, natural_power, power_bytes,
                         result, raw_candidate_count, -1);
}

/* Internal trusted path: service has decoded and validated the slot already. */
int p0_ed_pipeline_process_decoded_trusted(p0_ed_pipeline_t *pipeline, uint32_t frame_id,
    int reset_requested, int pl_decisions_present, phase06j_frame_result_v1 *result,
    size_t *raw_candidate_count)
{
    if (pipeline == NULL || (pl_decisions_present != 0 && pl_decisions_present != 1)) {
        errno = EINVAL;
        return -1;
    }
    return process_power(pipeline, frame_id, reset_requested, (const uint8_t *)pipeline->raw_power,
                         P0_POWER_FRAME_BYTES, result, raw_candidate_count, pl_decisions_present);
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
    /* Consume the same decoded PL power frame that produced the event.
     * Recomputing Hann/FFT here discards the hardware measurement. */
    if (!pipeline->wideband_has_frame_id || pipeline->wideband_last_frame_id != frame_id ||
        temporal->frame_id != frame_id) {
        p0_parameter_runtime_reset(&pipeline->parameter_runtime);
        errno = EPROTO;
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
