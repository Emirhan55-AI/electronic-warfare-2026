#include "p0_st05_stream.h"

#include "p0_st05_wideband_internal.h"

#include <math.h>
#include <stdint.h>
#include <string.h>
#ifdef P0_ED_PIPELINE_PROFILE
#include <inttypes.h>
#include <stdio.h>
#include <time.h>
#endif

#ifdef P0_ED_PIPELINE_PROFILE
enum { P0_STREAM_SUM, P0_STREAM_REGION_MEDIAN, P0_STREAM_COPY,
       P0_STREAM_REGION_MEAN, P0_STREAM_DETECTOR, P0_STREAM_PROFILE_STAGES };
static uint64_t stream_profile_totals[P0_STREAM_PROFILE_STAGES];
static uint64_t stream_profile_frames;

static uint64_t stream_profile_now(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0)
        return 0U;
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

static void stream_profile_record(const uint64_t *marks)
{
    static const char *const names[P0_STREAM_PROFILE_STAGES] = {
        "sum", "region_median", "copy", "region_mean", "detector"
    };
    size_t index;
    for (index = 0U; index < P0_STREAM_PROFILE_STAGES; ++index)
        stream_profile_totals[index] += marks[index + 1U] - marks[index];
    ++stream_profile_frames;
    if (stream_profile_frames % UINT64_C(4096) != 0U)
        return;
    fprintf(stderr, "{\"schema\":\"p0-st05-stream-profile-v1\",\"frames\":%" PRIu64,
            stream_profile_frames);
    for (index = 0U; index < P0_STREAM_PROFILE_STAGES; ++index)
        fprintf(stderr, ",\"%s_mean_ms\":%.9f", names[index],
                (double)stream_profile_totals[index] /
                    (double)stream_profile_frames / 1000000.0);
    fputs("}\n", stderr);
}
#endif

typedef struct {
    uint32_t write_index;
    uint32_t valid_frames;
    double frames[P0_ST05_MINIMUM_FRAMES][P0_ST05_FRAME_BINS];
    double power_sum[P0_ST05_FRAME_BINS];
    double mean_power[P0_ST05_FRAME_BINS];
    double region_noise[P0_ST05_MINIMUM_FRAMES][P0_ST05_INTERNAL_REGION_COUNT];
    double mean_region_noise[P0_ST05_INTERNAL_REGION_COUNT];
} p0_st05_stream_state_t;

typedef struct {
    uint32_t write_index;
    uint32_t valid_frames;
    double overwritten_frame[P0_ST05_FRAME_BINS];
    double power_sum[P0_ST05_FRAME_BINS];
    double overwritten_region_noise[P0_ST05_INTERNAL_REGION_COUNT];
    double mean_region_noise[P0_ST05_INTERNAL_REGION_COUNT];
} p0_st05_stream_checkpoint_t;

size_t p0_st05_stream_checkpoint_bytes(void)
{
    return sizeof(p0_st05_stream_checkpoint_t);
}

int p0_st05_stream_checkpoint_save(
    const void *memory, size_t memory_bytes, void *checkpoint, size_t checkpoint_bytes)
{
    const p0_st05_stream_state_t *state = memory;
    p0_st05_stream_checkpoint_t *saved = checkpoint;
    if (state == NULL || saved == NULL || memory_bytes != sizeof(*state) ||
        checkpoint_bytes < sizeof(*saved) || state->write_index >= P0_ST05_MINIMUM_FRAMES ||
        state->valid_frames > P0_ST05_MINIMUM_FRAMES)
        return P0_ST05_INVALID_ARGUMENT;
    saved->write_index = state->write_index;
    saved->valid_frames = state->valid_frames;
    memcpy(saved->overwritten_frame, state->frames[state->write_index],
           sizeof(saved->overwritten_frame));
    memcpy(saved->power_sum, state->power_sum, sizeof(saved->power_sum));
    memcpy(saved->overwritten_region_noise, state->region_noise[state->write_index],
           sizeof(saved->overwritten_region_noise));
    memcpy(saved->mean_region_noise, state->mean_region_noise, sizeof(saved->mean_region_noise));
    return P0_ST05_OK;
}

int p0_st05_stream_checkpoint_restore(
    void *memory, size_t memory_bytes, const void *checkpoint, size_t checkpoint_bytes)
{
    p0_st05_stream_state_t *state = memory;
    const p0_st05_stream_checkpoint_t *saved = checkpoint;
    if (state == NULL || saved == NULL || memory_bytes != sizeof(*state) ||
        checkpoint_bytes < sizeof(*saved) || saved->write_index >= P0_ST05_MINIMUM_FRAMES ||
        saved->valid_frames > P0_ST05_MINIMUM_FRAMES)
        return P0_ST05_INVALID_ARGUMENT;
    state->write_index = saved->write_index;
    state->valid_frames = saved->valid_frames;
    memcpy(state->frames[state->write_index], saved->overwritten_frame,
           sizeof(saved->overwritten_frame));
    memcpy(state->power_sum, saved->power_sum, sizeof(saved->power_sum));
    /* The mean is derived from the exact saved sum, not reverse arithmetic. */
    {
        size_t index;
        for (index = 0U; index < P0_ST05_FRAME_BINS; ++index)
            state->mean_power[index] = saved->valid_frames < P0_ST05_MINIMUM_FRAMES
                ? 0.0 : saved->power_sum[index] / (double)P0_ST05_MINIMUM_FRAMES;
    }
    memcpy(state->region_noise[state->write_index], saved->overwritten_region_noise,
           sizeof(saved->overwritten_region_noise));
    memcpy(state->mean_region_noise, saved->mean_region_noise, sizeof(saved->mean_region_noise));
    return P0_ST05_OK;
}

size_t p0_st05_stream_state_bytes(void)
{
    return sizeof(p0_st05_stream_state_t);
}

int p0_st05_stream_init(void *memory, size_t memory_bytes)
{
    if (memory == NULL || memory_bytes != sizeof(p0_st05_stream_state_t))
        return P0_ST05_INVALID_ARGUMENT;
    memset(memory, 0, memory_bytes);
    return P0_ST05_OK;
}

int p0_st05_stream_reset(void *memory, size_t memory_bytes)
{
    return p0_st05_stream_init(memory, memory_bytes);
}

static int stream_update_trusted(
    void *memory,
    size_t memory_bytes,
    const double *power,
    size_t power_count,
    p0_st05_result_t *result,
    int *result_valid
)
{
    p0_st05_stream_state_t *state = (p0_st05_stream_state_t *)memory;
    size_t index;
    size_t region;
    int code;
#ifdef P0_ED_PIPELINE_PROFILE
    uint64_t profile_marks[P0_STREAM_PROFILE_STAGES + 1U];
#endif

    if (memory == NULL || memory_bytes != sizeof(*state) || power == NULL ||
        power_count != P0_ST05_FRAME_BINS || result == NULL || result_valid == NULL)
        return P0_ST05_INVALID_ARGUMENT;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[0] = stream_profile_now();
#endif

    if (state->valid_frames == P0_ST05_MINIMUM_FRAMES) {
        const double *overwritten = state->frames[state->write_index];
        for (index = 0U; index < power_count; ++index) {
            double updated = state->power_sum[index] - overwritten[index] + power[index];
            state->power_sum[index] = updated;
            state->mean_power[index] = updated / (double)P0_ST05_MINIMUM_FRAMES;
        }
    } else if (state->valid_frames + 1U == P0_ST05_MINIMUM_FRAMES) {
        for (index = 0U; index < power_count; ++index) {
            double updated = state->power_sum[index] + power[index];
            state->power_sum[index] = updated;
            state->mean_power[index] = updated / (double)P0_ST05_MINIMUM_FRAMES;
        }
    } else {
        for (index = 0U; index < power_count; ++index)
            state->power_sum[index] += power[index];
    }
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[1] = stream_profile_now();
#endif
    p0_st05_region_noise_trusted(
        power, state->region_noise[state->write_index]);
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[2] = stream_profile_now();
#endif
    memcpy(state->frames[state->write_index], power,
           P0_ST05_FRAME_BINS * sizeof(*power));
    state->write_index = (state->write_index + 1U) % P0_ST05_MINIMUM_FRAMES;
    if (state->valid_frames < P0_ST05_MINIMUM_FRAMES)
        ++state->valid_frames;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[3] = stream_profile_now();
#endif

    memset(result, 0, sizeof(*result));
    *result_valid = 0;
    if (state->valid_frames < P0_ST05_MINIMUM_FRAMES)
        return P0_ST05_OK;
    memset(state->mean_region_noise, 0, sizeof(state->mean_region_noise));
    for (region = 0U; region < P0_ST05_INTERNAL_REGION_COUNT; ++region) {
        for (index = 0U; index < P0_ST05_MINIMUM_FRAMES; ++index)
            state->mean_region_noise[region] += state->region_noise[index][region];
        state->mean_region_noise[region] /= (double)P0_ST05_MINIMUM_FRAMES;
    }
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[4] = stream_profile_now();
#endif
    code = p0_st05_wideband_process_precomputed_trusted(
        &state->frames[0U][0U], P0_ST05_MINIMUM_FRAMES,
        state->mean_power, state->mean_region_noise, result);
    if (code != P0_ST05_OK)
        return code;
#ifdef P0_ED_PIPELINE_PROFILE
    profile_marks[5] = stream_profile_now();
    stream_profile_record(profile_marks);
#endif
    *result_valid = 1;
    return P0_ST05_OK;
}

int p0_st05_stream_update_trusted(
    void *memory,
    size_t memory_bytes,
    const double *power,
    size_t power_count,
    p0_st05_result_t *result,
    int *result_valid
)
{
    return stream_update_trusted(memory, memory_bytes, power, power_count,
                                 result, result_valid);
}

int p0_st05_stream_update(
    void *memory,
    size_t memory_bytes,
    const double *power,
    size_t power_count,
    p0_st05_result_t *result,
    int *result_valid
)
{
    size_t index;

    if (memory == NULL || power == NULL || power_count != P0_ST05_FRAME_BINS)
        return P0_ST05_INVALID_ARGUMENT;
    for (index = 0U; index < power_count; ++index) {
        if (!isfinite(power[index]) || power[index] < 0.0)
            return P0_ST05_INVALID_ARGUMENT;
    }
    return stream_update_trusted(memory, memory_bytes, power, power_count,
                                 result, result_valid);
}
